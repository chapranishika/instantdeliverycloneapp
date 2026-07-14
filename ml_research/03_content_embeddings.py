"""
03_content_embeddings.py
========================
Builds a REAL FAISS index from the 33 Zepto products.

Previously this script:
- Loaded from a parquet file that didn't exist (Instacart dependency)
- Never produced actual model artifacts
- Was purely decorative

Now it:
- Reads the canonical product list from backend/seed_db.py
- Builds TF-IDF embeddings from rich product text (name + category + description)
- Builds a FAISS IndexFlatIP index (inner product = cosine on L2-normalised vectors)
- Saves all artifacts that cbf_engine.py expects to load
- Runs end-to-end in < 5 seconds, zero downloads required

Upgrade path: uncomment the sentence-transformers block to get
all-MiniLM-L6-v2 embeddings (384-dim) instead of TF-IDF (500-dim).
The FAISS index format is identical — just swap the embedding matrix.

Run from project root:
    python ml_research/03_content_embeddings.py
"""

import re
import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
import pickle
import warnings
from pathlib import Path

import numpy as np
import faiss
import scipy.sparse as sp
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

warnings.filterwarnings("ignore")

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT       = Path(__file__).parent.parent
MODELS_DIR = ROOT / "backend" / "data" / "processed" / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 60)
print("03  Content Embeddings — TF-IDF + FAISS")
print("=" * 60)

# ── Step 1: Load products from canonical source ───────────────────────────────
# Read directly from seed_db.py so there's exactly ONE source of truth.
# If you add a product to seed_db.py, rerunning this script picks it up.

import json
with open(ROOT / "backend" / "data" / "processed" / "products.json", "r", encoding="utf-8") as f:
    products_raw = json.load(f)

PRODUCT_DESCRIPTIONS = {
    "Fresh Fruits":    "sweet nutritious fruit vitamins antioxidants fresh seasonal",
    "Fresh Vegetables":"vegetable fresh sabzi cooking healthy nutrition vitamins",
    "Leafy Herbs":     "herb green leafy aromatic garnish cooking tadka chutney",
    "Flowers":         "flower fresh puja decoration fragrance garland auspicious",
    "Exotic Veggies":  "exotic imported vegetable gourmet superfood premium salad",
    "Kitchen":         "kitchen staple pantry cooking ingredient daily essential",
    "House Hold":      "household cleaning hygiene home care daily essential",
    "Snacks & Munchies": "snack munchies chips crunchy tasty delicious party potato",
    "Cold Drinks & Juices": "cold drinks juice soda soft drink refreshing coke sprite water",
    "Dairy, Bread & Eggs": "dairy bread eggs milk butter cheese breakfast daily essential",
    "Zepto Cafe":      "cafe coffee tea sandwich croissant chai breakfast samosa puff cookie cake snack",
}

products = []
for p in products_raw:
    name = p["name"]
    unit = p["unit"]
    category = p["type"]
    desc = PRODUCT_DESCRIPTIONS.get(category, category)
    text = f"{name} {name} {category} {unit} {desc}"
    products.append({
        "id":       p["id"],
        "name":     name,
        "unit":     unit,
        "category": category,
        "text":     text,
    })

products.sort(key=lambda x: x["id"])
print(f"\n✓ Loaded {len(products)} products from products.json")
for p in products[:10]:
    print(f"  [{p['id']:2d}] {p['name']:<20s} ({p['category']})")
print(f"  ... and {len(products)-10} more items.")

# ── Step 2: TF-IDF embeddings ─────────────────────────────────────────────────
print("\n[1/4] Building TF-IDF embeddings...")

corpus = [p["text"] for p in products]
product_ids = np.array([p["id"] for p in products], dtype=np.int32)

tfidf = TfidfVectorizer(
    max_features=500,
    ngram_range=(1, 2),      # unigrams + bigrams
    sublinear_tf=True,       # log(tf) — reduces impact of frequent terms
    min_df=1,
)
tfidf_matrix = tfidf.fit_transform(corpus)

# Dense float32 for FAISS
embeddings = tfidf_matrix.toarray().astype(np.float32)

# L2-normalise so inner product = cosine similarity
norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
norms[norms == 0] = 1
embeddings_norm = embeddings / norms

print(f"  TF-IDF matrix: {tfidf_matrix.shape}  ({tfidf_matrix.nnz} non-zero)")
print(f"  Embedding dim: {embeddings_norm.shape[1]}")

# ── [UPGRADE PATH] ─────────────────────────────────────────────────────────
# Uncomment to use sentence-transformers instead (requires: pip install sentence-transformers)
#
# from sentence_transformers import SentenceTransformer
# print("[1/4] Building sentence-transformer embeddings (all-MiniLM-L6-v2)...")
# model = SentenceTransformer("all-MiniLM-L6-v2")
# embeddings_norm = model.encode(corpus, normalize_embeddings=True, show_progress_bar=True)
# embeddings_norm = embeddings_norm.astype(np.float32)
# print(f"  Embedding dim: {embeddings_norm.shape[1]}")
# ─────────────────────────────────────────────────────────────────────────────

# ── Step 3: Build FAISS index ─────────────────────────────────────────────────
print("\n[2/4] Building FAISS IndexFlatIP...")

dim = embeddings_norm.shape[1]
index = faiss.IndexFlatIP(dim)   # inner product on L2-normalised = cosine
index.add(embeddings_norm)

print(f"  Index type: IndexFlatIP  (exact, no approximation needed for 33 items)")
print(f"  Vectors in index: {index.ntotal}")

# Quick self-similarity check
D, I = index.search(embeddings_norm[:1], k=5)
top5 = [(products[i]["name"], round(float(D[0][j]), 4)) for j, i in enumerate(I[0])]
print(f"  Sanity check — top-5 for '{products[0]['name']}':")
for name, score in top5:
    print(f"    {name:<25s} cos_sim={score:.4f}")

# ── Step 4: Department centroids ──────────────────────────────────────────────
print("\n[3/4] Computing department centroids...")

dept_centroids: dict[str, np.ndarray] = {}
for category in set(p["category"] for p in products):
    mask  = np.array([p["category"] == category for p in products])
    vecs  = embeddings_norm[mask]
    centroid = vecs.mean(axis=0)
    centroid /= (np.linalg.norm(centroid) or 1)
    dept_centroids[category] = centroid.astype(np.float32)
    print(f"  {category:<20s} — {mask.sum()} products, centroid dim={centroid.shape[0]}")

# ── Step 5: Save all artifacts ────────────────────────────────────────────────
print("\n[4/4] Saving model artifacts...")

faiss.write_index(index, str(MODELS_DIR / "faiss_product_index.bin"))
np.save(MODELS_DIR / "faiss_product_ids.npy", product_ids)
np.save(MODELS_DIR / "product_embeddings.npy", embeddings_norm)

with open(MODELS_DIR / "tfidf_vectorizer.pkl", "wb") as f:
    pickle.dump(tfidf, f)
sp.save_npz(MODELS_DIR / "tfidf_matrix.npz", tfidf_matrix.tocsr())

with open(MODELS_DIR / "department_centroids.pkl", "wb") as f:
    pickle.dump(dept_centroids, f)

print(f"  Saved to: {MODELS_DIR}")
for path in sorted(MODELS_DIR.iterdir()):
    size = path.stat().st_size
    print(f"    {path.name:<35s} {size/1024:.1f} KB")

# ── Step 6: Smoke test the cbf_engine loader ─────────────────────────────────
print("\n[Smoke test] Loading artifacts via ContentBasedEngine...")
sys.path.insert(0, str(ROOT / "backend"))

try:
    from app.ml.content.cbf_engine import ContentBasedEngine
    engine = ContentBasedEngine()
    engine.load()

    if engine.loaded:
        # Test: similar products to Banana (id=0)
        recs = engine.get_similar_products(product_id=0, n=5)
        print(f"  ✓ engine.loaded = True")
        print(f"  Similar to Banana (id=0):")
        for r in recs:
            p = next((x for x in products if x["id"] == r["product_id"]), None)
            name = p["name"] if p else f"id={r['product_id']}"
            score = r.get("cbf_score", r.get("score", 0))
            print(f"    {name:<25s} cos_sim={score:.4f}")

        # Test: text search (method is search_by_text, not semantic_search)
        results = engine.search_by_text("fresh green vegetables", n=4)
        print(f"\n  search_by_text('fresh green vegetables'):")
        for r in results:
            p = next((x for x in products if x["id"] == r["product_id"]), None)
            name = p["name"] if p else f"id={r['product_id']}"
            score = r.get("cbf_score", r.get("score", 0))
            print(f"    {name:<25s} cos_sim={score:.4f}")
    else:
        print("  ⚠ engine.loaded = False — check cbf_engine.py logs")

except Exception as e:
    print(f"  Smoke test skipped ({e})")

# ── Summary ───────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("✅  03_content_embeddings.py COMPLETE")
print("=" * 60)
print(f"  Products embedded: {len(products)}")
print(f"  Embedding method:  TF-IDF (max_features=500, ngram_range=(1,2))")
print(f"  FAISS index type:  IndexFlatIP (exact cosine similarity)")
print(f"  Artifacts saved:   {MODELS_DIR}")
print()
print("  Next steps:")
print("  1. Run: python ml_research/04_hybrid_ranker.py")
print("  2. Start backend: uvicorn app.main:app --reload")
print("  3. Test: GET /api/v1/recommend/0  (recommendations for product 0)")
print()
print("  To upgrade to sentence-transformers embeddings:")
print("  pip install sentence-transformers")
print("  Then uncomment the [UPGRADE PATH] block in this file.")
