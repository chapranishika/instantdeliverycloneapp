"""
Celery Background Tasks
Nightly model retraining — the feedback loop that makes recommendations improve.
"""
import logging
import os
from celery import Celery
from celery.schedules import crontab

logger = logging.getLogger(__name__)

REDIS_URL  = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
celery_app = Celery("zepto", broker=REDIS_URL, backend=REDIS_URL)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Kolkata",
    enable_utc=True,
    beat_schedule={
        # Rebuild interaction matrix every night at 2 AM IST
        "rebuild-interaction-matrix": {
            "task": "app.tasks.celery_tasks.rebuild_interaction_matrix",
            "schedule": crontab(hour=2, minute=0),
        },
        # Refresh product embeddings weekly (for new products)
        "refresh-product-embeddings": {
            "task": "app.tasks.celery_tasks.refresh_product_embeddings",
            "schedule": crontab(hour=3, minute=0, day_of_week=0),  # Sunday 3 AM
        },
        # Flush Redis recommendation cache every 10 minutes
        "flush-rec-cache": {
            "task": "app.tasks.celery_tasks.flush_stale_cache",
            "schedule": crontab(minute="*/10"),
        },
    },
)


@celery_app.task(name="app.tasks.celery_tasks.rebuild_interaction_matrix")
def rebuild_interaction_matrix():
    """
    Pull latest events from PostgreSQL, rebuild the user-item matrix,
    retrain ALS, and hot-swap the CF engine's model.
    """
    import asyncio
    from pathlib import Path
    import pandas as pd
    import numpy as np
    from sqlalchemy import text

    logger.info("Starting nightly interaction matrix rebuild...")

    async def _fetch_events():
        from app.db.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                text("""
                    SELECT user_id, product_id,
                           COUNT(*) as purchase_count,
                           SUM(CASE WHEN event_type = 'purchase' THEN 3
                                    WHEN event_type = 'add_to_cart' THEN 2
                                    ELSE 1 END) as confidence
                    FROM user_events
                    WHERE event_type IN ('view', 'click', 'add_to_cart', 'purchase')
                      AND product_id IS NOT NULL
                      AND created_at > NOW() - INTERVAL '90 days'
                    GROUP BY user_id, product_id
                """)
            )
            return result.fetchall()

    rows = asyncio.run(_fetch_events())
    if not rows:
        logger.warning("No events found — skipping rebuild")
        return

    df = pd.DataFrame(rows, columns=["user_id", "product_id", "purchase_count", "confidence"])
    logger.info(f"Loaded {len(df)} interactions from events")

    PROCESSED_DIR = Path("data/processed")
    df.to_parquet(PROCESSED_DIR / "user_item_interactions.parquet", index=False)

    # Retrain ALS if we have enough data
    if len(df) > 1000:
        try:
            import implicit
            from scipy.sparse import csr_matrix
            import pickle

            user_ids = df["user_id"].unique()
            prod_ids = df["product_id"].unique()
            user2idx = {u: i for i, u in enumerate(user_ids)}
            prod2idx = {p: i for i, p in enumerate(prod_ids)}

            df["u_idx"] = df["user_id"].map(user2idx)
            df["p_idx"] = df["product_id"].map(prod2idx)

            matrix = csr_matrix(
                (df["confidence"].values, (df["p_idx"].values, df["u_idx"].values)),
                shape=(len(prod_ids), len(user_ids)),
            )

            als = implicit.als.AlternatingLeastSquares(
                factors=64, regularization=0.01, iterations=15, use_gpu=False
            )
            als.fit(matrix)

            MODELS_DIR = PROCESSED_DIR / "models"
            als.save(str(MODELS_DIR / "als_model_new.npz"))
            # Atomic swap
            (MODELS_DIR / "als_model_new.npz").rename(MODELS_DIR / "als_model.npz")

            # Update mappings
            idx2prod = {i: p for p, i in prod2idx.items()}
            mappings = {
                "user2idx": user2idx,
                "idx2user": {i: u for u, i in user2idx.items()},
                "prod2idx": prod2idx,
                "idx2prod": idx2prod,
                "user_ids": user_ids,
                "product_ids": prod_ids,
            }
            with open(MODELS_DIR / "index_mappings.pkl", "wb") as f:
                pickle.dump(mappings, f)

            # Reload the CF engine singleton
            from app.ml.collaborative.cf_engine import _cf_engine
            if _cf_engine:
                _cf_engine.load()

            logger.info(f"ALS retrained: {len(user_ids)} users, {len(prod_ids)} products")
        except Exception as exc:
            logger.error(f"ALS retrain failed: {exc}")

    return {"status": "done", "interactions": len(df)}


@celery_app.task(name="app.tasks.celery_tasks.refresh_product_embeddings")
def refresh_product_embeddings():
    """
    Re-embed any products added since last run and update the FAISS index.
    Incremental — only processes new products.
    """
    import asyncio
    from pathlib import Path
    import numpy as np

    logger.info("Refreshing product embeddings...")

    MODELS_DIR = Path("data/processed/models")

    async def _fetch_new_products():
        from app.db.database import AsyncSessionLocal
        from app.models.db_models import Product
        from sqlalchemy import select

        async with AsyncSessionLocal() as db:
            existing_ids = np.load(MODELS_DIR / "faiss_product_ids.npy").tolist()
            result = await db.execute(
                select(Product).where(
                    Product.is_available == True,
                    Product.id.not_in(existing_ids)
                )
            )
            return result.scalars().all()

    try:
        new_products = asyncio.run(_fetch_new_products())
        if not new_products:
            logger.info("No new products to embed")
            return {"status": "skipped", "new_products": 0}

        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")

        texts = [
            f"{p.name} {getattr(p, 'department', '')}".lower()
            for p in new_products
        ]
        new_embeddings = model.encode(texts, normalize_embeddings=True).astype("float32")

        # Append to FAISS index
        import faiss
        index = faiss.read_index(str(MODELS_DIR / "faiss_product_index.bin"))
        index.add(new_embeddings)
        faiss.write_index(index, str(MODELS_DIR / "faiss_product_index.bin"))

        # Append IDs
        existing_ids = np.load(MODELS_DIR / "faiss_product_ids.npy").tolist()
        new_ids = [p.id for p in new_products]
        np.save(MODELS_DIR / "faiss_product_ids.npy",
                np.array(existing_ids + new_ids))

        # Reload CBF engine
        from app.ml.content.cbf_engine import _cbf_engine
        if _cbf_engine:
            _cbf_engine.load()

        logger.info(f"Added {len(new_products)} new product embeddings to FAISS")
        return {"status": "done", "new_products": len(new_products)}

    except Exception as exc:
        logger.error(f"Embedding refresh failed: {exc}")
        return {"status": "error", "error": str(exc)}


@celery_app.task(name="app.tasks.celery_tasks.flush_stale_cache")
def flush_stale_cache():
    """
    Remove stale recommendation cache keys.
    Redis TTL handles most of this, but this task cleans up user-specific keys
    for users who have had recent purchase events.
    """
    import asyncio

    async def _flush():
        from app.db.database import AsyncSessionLocal, get_redis
        from sqlalchemy import text

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                text("""
                    SELECT DISTINCT user_id FROM user_events
                    WHERE event_type = 'purchase'
                      AND created_at > NOW() - INTERVAL '15 minutes'
                """)
            )
            user_ids = [row[0] for row in result.fetchall()]

        redis = get_redis()
        if redis and user_ids:
            keys = [f"rec:{uid}:20" for uid in user_ids]
            await redis.delete(*keys)
            logger.info(f"Flushed cache for {len(user_ids)} active users")

    asyncio.run(_flush())
