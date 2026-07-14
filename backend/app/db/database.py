"""
database.py — PostgreSQL (Supabase zepto-clone) + Redis

Project: zepto-clone (lqvldpojrcokvfmlfuhe)
URL:     https://lqvldpojrcokvfmlfuhe.supabase.co
Schema:  public (dedicated project — no schema isolation needed)

Connection strings:
  Transaction Pooler (app runtime, port 6543):
    postgresql+asyncpg://postgres.lqvldpojrcokvfmlfuhe:[pw]@aws-0-ap-south-1.pooler.supabase.com:6543/postgres

  Direct (migrations + seed only, port 5432):
    postgresql+asyncpg://postgres:[pw]@db.lqvldpojrcokvfmlfuhe.supabase.co:5432/postgres
"""
import json
import logging
import os
from typing import Any, AsyncGenerator, Optional
from urllib.parse import urlparse

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/zepto",
)

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)

# Supabase Transaction Pooler (port 6543) = pgBouncer transaction mode
# which does NOT support prepared statements — must disable them.
_parsed = urlparse(DATABASE_URL)
_is_supabase_pooler = (
    "pooler.supabase.com" in (_parsed.hostname or "")
    and _parsed.port == 6543
)
_connect_args: dict = {}
if _is_supabase_pooler:
    _connect_args = {"statement_cache_size": 0}
    logger.info("Supabase Transaction Pooler detected — prepared statements disabled")

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    poolclass=NullPool,
    connect_args=_connect_args,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tables() -> None:
    """Create all ORM tables. Idempotent — safe to call on startup."""
    from app.models.db_models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✓ Database tables ensured (zepto-clone project)")


# ── Redis ─────────────────────────────────────────────────────────────────────
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
_redis_client = None


def get_redis():
    global _redis_client
    if _redis_client is None:
        try:
            import redis.asyncio as aioredis
            _redis_client = aioredis.from_url(
                REDIS_URL, encoding="utf-8", decode_responses=True
            )
        except Exception as exc:
            logger.warning(f"Redis unavailable — caching disabled: {exc}")
    return _redis_client


CACHE_TTL = 300


async def cache_get(key: str) -> Optional[Any]:
    r = get_redis()
    if r is None: return None
    try:
        value = await r.get(key)
        return json.loads(value) if value else None
    except Exception:
        return None


async def cache_set(key: str, value: Any, ttl: int = CACHE_TTL) -> None:
    r = get_redis()
    if r is None: return
    try:
        await r.setex(key, ttl, json.dumps(value))
    except Exception as exc:
        logger.debug(f"Cache write failed: {exc}")


async def cache_delete(key: str) -> None:
    r = get_redis()
    if r is None: return
    try:
        await r.delete(key)
    except Exception:
        pass
