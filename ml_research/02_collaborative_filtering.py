"""
02_collaborative_filtering.py
==============================
Collaborative filtering on SYNTHETIC interaction data.

WHY SYNTHETIC DATA:
The original version of this script (and 01_eda.py) depended on the
Instacart Market Basket dataset (3.4M orders, ~30MB download from Kaggle).
That dataset was never downloaded, so 01/02/04 never ran — they were
decorative. With only 33 products in the Zepto catalogue, real ALS/SVD
also needs *some* interaction matrix to factorise; Instacart's products
don't map to our 33 SKUs anyway.

This script generates a REALISTIC SYNTHETIC interaction dataset using
persona-based sampling (defined below), then trains a real matrix
factorisation model (TruncatedSVD) on it. Everything downstream — factors,
metrics, saved artifacts — is computed for real, not hardcoded.

[UPGRADE PATH] To use real Instacart data instead:
  1. Download from https://www.kaggle.com/c/instacart-market-basket-analysis
  2. Map Instacart product categories → our 7 categories
  3. Replace generate_synthetic_interactions() with a loader for the real data
  4. Everything else (SVD training, evaluation, saved artifact format) is unchanged

Run from project root:
    python ml_research/02_collaborative_filtering.py
"""

import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

import re
import pickle
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.decomposition import TruncatedSVD

warnings.filterwarnings("ignore")
np.random.seed(42)

ROOT          = Path(__file__).parent.parent
PROCESSED_DIR = ROOT / "backend" / "data" / "processed"
MODELS_DIR    = PROCESSED_DIR / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 60)
print("Notebook 02: Collaborative Filtering (TruncatedSVD)")
print("=" * 60)


# ════════════════════════════════════════════════════════════
# Step 1 — Load the 33 products (single source of truth: seed_db.py)
# ════════════════════════════════════════════════════════════
import json
with open(ROOT / "backend" / "data" / "processed" / "products.json", "r", encoding="utf-8") as f:
    products_raw = json.load(f)
products = []
for p in products_raw:
    products.append({
        "id": p["id"], "name": p["name"], "category": p["type"],
        "mrp": p["price"], "price": p["disc"], "rating": p["rating"],
    })
products.sort(key=lambda x: x["id"])
N_PRODUCTS = len(products)
print(f"\n✓ Loaded {N_PRODUCTS} products from products.json")

CATEGORIES = sorted(set(p["category"] for p in products))
prod_by_id = {p["id"]: p for p in products}


# ════════════════════════════════════════════════════════════
# Step 2 — Persona-based synthetic interaction generator
# ════════════════════════════════════════════════════════════
#
# Each persona is a probability distribution over the 7 categories.
# A synthetic user is 80% their assigned persona + 20% "general shopper"
# (uniform over categories), which gives realistic-but-noisy preferences —
# similar to how real shoppers have a dominant pattern plus occasional
# off-pattern purchases.

PERSONAS = {
    "fruit_lover":       {"Fresh Fruits": 0.40, "Exotic Veggies": 0.15, "Fresh Vegetables": 0.15,
                           "Leafy Herbs": 0.10, "Kitchen": 0.10, "Flowers": 0.05, "House Hold": 0.05},
    "veg_cook":          {"Fresh Vegetables": 0.35, "Leafy Herbs": 0.20, "Exotic Veggies": 0.15,
                           "Kitchen": 0.15, "Fresh Fruits": 0.05, "Flowers": 0.05, "House Hold": 0.05},
    "household_stocker": {"House Hold": 0.40, "Kitchen": 0.25, "Fresh Vegetables": 0.10,
                           "Fresh Fruits": 0.10, "Leafy Herbs": 0.05, "Exotic Veggies": 0.05, "Flowers": 0.05},
    "festival_shopper":  {"Flowers": 0.30, "Fresh Fruits": 0.20, "Fresh Vegetables": 0.15,
                           "Kitchen": 0.15, "Leafy Herbs": 0.10, "Exotic Veggies": 0.05, "House Hold": 0.05},
    "gourmet":           {"Exotic Veggies": 0.35, "Fresh Vegetables": 0.15, "Kitchen": 0.15,
                           "Fresh Fruits": 0.15, "Leafy Herbs": 0.10, "House Hold": 0.05, "Flowers": 0.05},
    "snack_lover":       {"Snacks & Munchies": 0.40, "Cold Drinks & Juices": 0.30, "Dairy, Bread & Eggs": 0.15, "House Hold": 0.15},
    "breakfast_shopper": {"Dairy, Bread & Eggs": 0.40, "Kitchen": 0.25, "Fresh Fruits": 0.15, "Fresh Vegetables": 0.10, "Snacks & Munchies": 0.10},
    "general_shopper":   {c: 1 / len(CATEGORIES) for c in CATEGORIES},
}
GENERAL = PERSONAS["general_shopper"]

N_USERS = 600
MIN_INTERACTIONS, MAX_INTERACTIONS = 8, 25

print(f"\n✓ {len(PERSONAS)} personas defined: {list(PERSONAS.keys())}")
print(f"  Generating {N_USERS} synthetic users, "
      f"{MIN_INTERACTIONS}-{MAX_INTERACTIONS} interactions each...")


def sample_category_weights(persona_name: str) -> dict:
    """Blend 80% persona + 20% general shopper."""
    persona = PERSONAS[persona_name]
    raw_weights = {c: 0.8 * persona.get(c, 0.0) + 0.2 * GENERAL[c] for c in CATEGORIES}
    total = sum(raw_weights.values())
    return {c: w / total for c, w in raw_weights.items()}


def generate_synthetic_interactions(n_users: int) -> pd.DataFrame:
    persona_names = [p for p in PERSONAS if p != "general_shopper"]
    rows = []
    for u in range(n_users):
        user_id = f"u_{u:04d}"
        persona = np.random.choice(persona_names)
        weights = sample_category_weights(persona)

        n_interactions = np.random.randint(MIN_INTERACTIONS, MAX_INTERACTIONS + 1)
        for _ in range(n_interactions):
            # Pick category by persona weights, then a product within it
            cat = np.random.choice(CATEGORIES, p=[weights[c] for c in CATEGORIES])
            cat_products = [p["id"] for p in products if p["category"] == cat]
            # Higher-rated products are slightly more likely to be (re)bought
            cat_ratings = np.array([prod_by_id[pid]["rating"] for pid in cat_products])
            p_weights = cat_ratings / cat_ratings.sum()
            pid = np.random.choice(cat_products, p=p_weights)
            rows.append({"user_id": user_id, "product_id": int(pid), "persona": persona})

    df = pd.DataFrame(rows)
    # Aggregate repeat purchases into a count (implicit feedback signal)
    agg = df.groupby(["user_id", "product_id"], as_index=False).size()
    agg = agg.rename(columns={"size": "count"})
    # Keep persona for inspection (most common persona per user)
    persona_map = df.groupby("user_id")["persona"].first()
    agg["persona"] = agg["user_id"].map(persona_map)
    return agg


interactions = generate_synthetic_interactions(N_USERS)
print(f"  Generated {len(interactions):,} (user, product) interaction rows")
print(f"  Unique users: {interactions['user_id'].nunique()}")
print(f"  Avg products/user: {interactions.groupby('user_id').size().mean():.1f}")

print("\n  Persona distribution:")
for persona, cnt in interactions.groupby("user_id")["persona"].first().value_counts().items():
    print(f"    {persona:<20s} {cnt:>4d} users")


# ════════════════════════════════════════════════════════════
# Step 3 — Train/test split (per user, last 20% held out)
# ════════════════════════════════════════════════════════════
print("\n[1/3] Splitting interactions into train/test (80/20 per user)...")

train_rows, test_rows = [], []
for user_id, grp in interactions.groupby("user_id"):
    # Deterministic per-user shuffle seed. NOTE: Python's built-in hash()
    # is randomised per-process for strings (PYTHONHASHSEED), so using
    # hash(user_id) here would make results non-reproducible across runs
    # even with np.random.seed(42) set above. Use the numeric suffix of
    # the synthetic user id (u_0001 -> 1) instead, which is deterministic.
    user_num = int(user_id.split("_")[1])
    grp = grp.sample(frac=1, random_state=42 + user_num)
    split = max(1, int(len(grp) * 0.8))
    train_rows.append(grp.iloc[:split])
    if split < len(grp):
        test_rows.append(grp.iloc[split:])

train_df = pd.concat(train_rows, ignore_index=True)
test_df  = pd.concat(test_rows, ignore_index=True) if test_rows else pd.DataFrame(columns=interactions.columns)

print(f"  Train: {len(train_df):,} rows | Test: {len(test_df):,} rows")
print(f"  Users with test interactions: {test_df['user_id'].nunique()}")


# ════════════════════════════════════════════════════════════
# Step 4 — Build user-item matrix and train TruncatedSVD
# ════════════════════════════════════════════════════════════
print("\n[2/3] Training TruncatedSVD on train interactions...")

users = sorted(interactions["user_id"].unique())
user2idx = {u: i for i, u in enumerate(users)}
idx2user = {i: u for u, i in user2idx.items()}
prod2idx = {p["id"]: i for i, p in enumerate(products)}
idx2prod = {i: pid for pid, i in prod2idx.items()}

n_users_total = len(users)
matrix = np.zeros((n_users_total, N_PRODUCTS), dtype=np.float32)
for _, row in train_df.iterrows():
    u_idx = user2idx[row["user_id"]]
    p_idx = prod2idx[row["product_id"]]
    # Log-scaled implicit-feedback confidence (standard for purchase counts)
    matrix[u_idx, p_idx] += np.log1p(row["count"])

n_components = 8   # < n_personas-ish, well under N_PRODUCTS=33
svd = TruncatedSVD(n_components=n_components, random_state=42)
user_factors = svd.fit_transform(matrix)          # (n_users, k)
item_factors = svd.components_.T                  # (n_products, k)

explained = svd.explained_variance_ratio_.sum()
print(f"  Matrix shape: {matrix.shape}  (users × products)")
print(f"  Latent factors: {n_components}")
print(f"  Explained variance: {explained:.1%}")
print(f"  user_factors: {user_factors.shape}  item_factors: {item_factors.shape}")

# [UPGRADE PATH] For true ALS with confidence weighting:
#   from implicit.als import AlternatingLeastSquares
#   model = AlternatingLeastSquares(factors=n_components, regularization=0.01)
#   model.fit(sparse_matrix)
#   user_factors, item_factors = model.user_factors, model.item_factors


# ════════════════════════════════════════════════════════════
# Step 5 — Evaluate CF-only on held-out test set
# ════════════════════════════════════════════════════════════
print("\n[3/3] Evaluating CF-only on held-out test interactions...")


def precision_recall_ndcg_at_k(ranked_ids, relevant_ids, k=10):
    top_k = ranked_ids[:k]
    hits = [1 if pid in relevant_ids else 0 for pid in top_k]
    precision = sum(hits) / k
    recall = sum(hits) / len(relevant_ids) if relevant_ids else 0.0
    dcg = sum(h / np.log2(i + 2) for i, h in enumerate(hits))
    ideal_hits = [1] * min(len(relevant_ids), k) + [0] * max(0, k - len(relevant_ids))
    idcg = sum(h / np.log2(i + 2) for i, h in enumerate(ideal_hits))
    ndcg = dcg / idcg if idcg > 0 else 0.0
    return precision, recall, ndcg


precisions, recalls, ndcgs = [], [], []
for user_id, grp in test_df.groupby("user_id"):
    if user_id not in user2idx:
        continue
    u_idx = user2idx[user_id]
    relevant = set(grp["product_id"].tolist())

    known = set(train_df[train_df["user_id"] == user_id]["product_id"].tolist())
    candidates = [pid for pid in prod2idx if pid not in known]
    if not candidates:
        continue

    scores = [float(user_factors[u_idx] @ item_factors[prod2idx[pid]]) for pid in candidates]
    ranked = [pid for pid, _ in sorted(zip(candidates, scores), key=lambda x: -x[1])]

    p, r, n = precision_recall_ndcg_at_k(ranked, relevant, k=10)
    precisions.append(p); recalls.append(r); ndcgs.append(n)

print(f"  Evaluated on {len(precisions)} users")
print(f"  Precision@10: {np.mean(precisions):.4f}")
print(f"  Recall@10:    {np.mean(recalls):.4f}")
print(f"  NDCG@10:      {np.mean(ndcgs):.4f}")
print(f"  (Note: candidate pool per user is ~{N_PRODUCTS - 10}-{N_PRODUCTS - MIN_INTERACTIONS} "
      f"items — small catalogue means @10 covers a large fraction of it.)")


# ════════════════════════════════════════════════════════════
# Step 6 — Popularity table (used by trending + ranker features)
# ════════════════════════════════════════════════════════════
popularity = (
    interactions.groupby("product_id")["count"].sum()
    .reindex(range(N_PRODUCTS), fill_value=0)
    .rename("purchase_count")
    .reset_index()
    .rename(columns={"index": "product_id"})
)
popularity["log_popularity"] = np.log1p(popularity["purchase_count"])
popularity["popularity_norm"] = popularity["log_popularity"] / popularity["log_popularity"].max()

print("\n  Top-5 most popular products (synthetic):")
top5 = popularity.sort_values("purchase_count", ascending=False).head(5)
for _, row in top5.iterrows():
    name = prod_by_id[int(row["product_id"])]["name"]
    print(f"    {name:<20s} purchases={int(row['purchase_count']):>3d}  "
          f"norm={row['popularity_norm']:.3f}")


# ════════════════════════════════════════════════════════════
# Step 7 — Save all artifacts for 04_hybrid_ranker.py
# ════════════════════════════════════════════════════════════
print("\nSaving artifacts...")

interactions.to_csv(PROCESSED_DIR / "synthetic_interactions.csv", index=False)
train_df.to_csv(PROCESSED_DIR / "synthetic_train.csv", index=False)
test_df.to_csv(PROCESSED_DIR / "synthetic_test.csv", index=False)
popularity.to_csv(PROCESSED_DIR / "product_popularity.csv", index=False)

np.save(MODELS_DIR / "cf_user_factors.npy", user_factors)
np.save(MODELS_DIR / "cf_item_factors.npy", item_factors)

with open(MODELS_DIR / "cf_mappings.pkl", "wb") as f:
    pickle.dump({
        "user2idx": user2idx, "idx2user": idx2user,
        "prod2idx": prod2idx, "idx2prod": idx2prod,
    }, f)

print(f"  Saved to {PROCESSED_DIR} and {MODELS_DIR}")

print("\n" + "=" * 60)
print("✅  02_collaborative_filtering.py COMPLETE")
print("=" * 60)
print(f"  Synthetic users:     {N_USERS}")
print(f"  Interaction rows:    {len(interactions):,}")
print(f"  CF-only Precision@10: {np.mean(precisions):.4f}")
print(f"  CF-only NDCG@10:      {np.mean(ndcgs):.4f}")
print()
print("  Next: python ml_research/04_hybrid_ranker.py")
