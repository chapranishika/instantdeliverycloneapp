"""
04_hybrid_ranker.py
====================
Hybrid Ranker — LightGBM LambdaMART blending CF + CBF + popularity signals.

WHAT THIS SCRIPT ACTUALLY DOES (previously it didn't run at all — it
depended on Instacart parquet files that were never generated):

  1. Loads REAL CF factors from 02_collaborative_filtering.py
     (TruncatedSVD trained on synthetic persona-based interactions)
  2. Loads REAL CBF embeddings from 03_content_embeddings.py
     (TF-IDF + FAISS index over the 33 products)
  3. Builds per-(user, candidate) feature vectors: CF score, CBF score
     (cosine similarity to the user's "taste centroid"), popularity,
     rating, price, and category one-hot / category-match
  4. Trains a real `lightgbm.LGBMRanker` with objective="lambdarank"
  5. Evaluates Precision@10 / Recall@10 / NDCG@10 for FOUR systems on a
     held-out set of users: Popularity-only, CF-only, CBF-only, and the
     trained Hybrid ranker — all computed from real predictions, nothing
     hardcoded.

Prerequisites (run first):
    python ml_research/02_collaborative_filtering.py
    python ml_research/03_content_embeddings.py

Run from project root:
    python ml_research/04_hybrid_ranker.py
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
import lightgbm as lgb

warnings.filterwarnings("ignore")
np.random.seed(42)

ROOT          = Path(__file__).parent.parent
PROCESSED_DIR = ROOT / "backend" / "data" / "processed"
MODELS_DIR    = PROCESSED_DIR / "models"

print("=" * 60)
print("Notebook 04: Hybrid Ranker (LightGBM LambdaMART)")
print("=" * 60)


# ════════════════════════════════════════════════════════════
# Step 0 — Load products + check prerequisites
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
prod_by_id = {p["id"]: p for p in products}
N_PRODUCTS = len(products)
CATEGORIES = sorted(set(p["category"] for p in products))
cat2idx = {c: i for i, c in enumerate(CATEGORIES)}

required = {
    "CF factors":  MODELS_DIR / "cf_item_factors.npy",
    "CF mappings": MODELS_DIR / "cf_mappings.pkl",
    "CBF index":   MODELS_DIR / "faiss_product_index.bin",
    "CBF embeddings": MODELS_DIR / "product_embeddings.npy",
    "Train interactions": PROCESSED_DIR / "synthetic_train.csv",
    "Test interactions":  PROCESSED_DIR / "synthetic_test.csv",
    "Popularity":  PROCESSED_DIR / "product_popularity.csv",
}
missing = [name for name, path in required.items() if not path.exists()]
if missing:
    print("\n❌ Missing prerequisite artifacts:", ", ".join(missing))
    print("   Run these first:")
    print("     python ml_research/02_collaborative_filtering.py")
    print("     python ml_research/03_content_embeddings.py")
    raise SystemExit(1)

print(f"\n✓ Loaded {N_PRODUCTS} products, {len(CATEGORIES)} categories")


# ════════════════════════════════════════════════════════════
# Step 1 — Load CF factors (from 02) and CBF embeddings (from 03)
# ════════════════════════════════════════════════════════════
print("\n[1/5] Loading CF factors and CBF embeddings...")

user_factors = np.load(MODELS_DIR / "cf_user_factors.npy")
item_factors = np.load(MODELS_DIR / "cf_item_factors.npy")
with open(MODELS_DIR / "cf_mappings.pkl", "rb") as f:
    cf_maps = pickle.load(f)
user2idx, prod2idx_cf = cf_maps["user2idx"], cf_maps["prod2idx"]

embeddings = np.load(MODELS_DIR / "product_embeddings.npy")          # (33, dim), L2-normalised
embedding_ids = np.load(MODELS_DIR / "faiss_product_ids.npy")        # (33,) product ids, same order
emb_by_pid = {int(pid): embeddings[i] for i, pid in enumerate(embedding_ids)}

popularity = pd.read_csv(PROCESSED_DIR / "product_popularity.csv")
pop_norm = dict(zip(popularity["product_id"], popularity["popularity_norm"]))

train_df = pd.read_csv(PROCESSED_DIR / "synthetic_train.csv")
test_df  = pd.read_csv(PROCESSED_DIR / "synthetic_test.csv")

print(f"  CF factors:  user {user_factors.shape}, item {item_factors.shape}")
print(f"  CBF embeddings: {embeddings.shape}")
print(f"  Train rows: {len(train_df):,} | Test rows: {len(test_df):,}")


# ════════════════════════════════════════════════════════════
# Step 2 — Feature builder
# ════════════════════════════════════════════════════════════
print("\n[2/5] Building per-(user, candidate) feature vectors...")

def cf_score(user_id, pid):
    if user_id not in user2idx or pid not in prod2idx_cf:
        return 0.0
    return float(user_factors[user2idx[user_id]] @ item_factors[prod2idx_cf[pid]])


def cbf_score(user_taste_vec, pid):
    if user_taste_vec is None or pid not in emb_by_pid:
        return 0.0
    v = emb_by_pid[pid]
    return float(np.dot(user_taste_vec, v))   # both normalised -> cosine


def user_taste_centroid(known_pids):
    vecs = [emb_by_pid[p] for p in known_pids if p in emb_by_pid]
    if not vecs:
        return None
    c = np.mean(vecs, axis=0)
    norm = np.linalg.norm(c)
    return c / norm if norm > 0 else None


FEATURE_NAMES = (
    ["cf_score", "cbf_score", "cf_x_cbf", "popularity", "rating", "price_norm", "category_match"]
    + [f"cat_{c}" for c in CATEGORIES]
)
MAX_PRICE = max(p["price"] for p in products)


def build_features(user_id, candidate_pids, known_pids):
    taste = user_taste_centroid(known_pids)

    # User's dominant category from their known (train) interactions
    known_cats = [prod_by_id[p]["category"] for p in known_pids if p in prod_by_id]
    dominant_cat = pd.Series(known_cats).mode()[0] if known_cats else None

    rows = []
    for pid in candidate_pids:
        p = prod_by_id[pid]
        cat_onehot = [1.0 if p["category"] == c else 0.0 for c in CATEGORIES]
        cf = cf_score(user_id, pid)
        cbf = cbf_score(taste, pid)
        rows.append([
            cf,
            cbf,
            cf * cbf,                                   # interaction term
            pop_norm.get(pid, 0.0),
            p["rating"],
            p["price"] / MAX_PRICE,
            1.0 if p["category"] == dominant_cat else 0.0,
            *cat_onehot,
        ])
    return np.array(rows, dtype=np.float32)


# ════════════════════════════════════════════════════════════
# Step 3 — Build train/eval sets for the RANKER (split users 80/20)
# ════════════════════════════════════════════════════════════
print("\n[3/5] Building ranker training data...")

all_users = sorted(train_df["user_id"].unique())
np.random.shuffle(all_users)
split = int(len(all_users) * 0.8)
ranker_train_users = set(all_users[:split])
ranker_eval_users  = set(all_users[split:])
print(f"  Ranker train users: {len(ranker_train_users)} | eval users: {len(ranker_eval_users)}")


def build_dataset(user_ids):
    X_parts, y_parts, group_sizes, meta = [], [], [], []
    for user_id in user_ids:
        known    = set(train_df[train_df["user_id"] == user_id]["product_id"].tolist())
        relevant = set(test_df[test_df["user_id"] == user_id]["product_id"].tolist())
        candidates = [pid for pid in range(N_PRODUCTS) if pid not in known]
        if not candidates:
            continue
        X = build_features(user_id, candidates, known)
        y = np.array([1 if pid in relevant else 0 for pid in candidates], dtype=np.int32)
        X_parts.append(X)
        y_parts.append(y)
        group_sizes.append(len(candidates))
        meta.append((user_id, candidates, relevant))
    return np.vstack(X_parts), np.concatenate(y_parts), np.array(group_sizes), meta


X_train, y_train, groups_train, _          = build_dataset(sorted(ranker_train_users))
X_eval,  y_eval,  groups_eval,  eval_meta   = build_dataset(sorted(ranker_eval_users))

print(f"  Train: {X_train.shape[0]:,} rows across {len(groups_train)} groups "
      f"({y_train.sum():,} positives)")
print(f"  Eval:  {X_eval.shape[0]:,} rows across {len(groups_eval)} groups "
      f"({y_eval.sum():,} positives)")


# ════════════════════════════════════════════════════════════
# Step 4 — Train LightGBM LambdaMART
# ════════════════════════════════════════════════════════════
print("\n[4/5] Training LGBMRanker (objective=lambdarank)...")

ranker = lgb.LGBMRanker(
    objective="lambdarank",
    metric="ndcg",
    n_estimators=200,
    num_leaves=7,
    max_depth=4,
    learning_rate=0.03,
    min_child_samples=10,
    reg_lambda=1.0,
    verbose=-1,
)
ranker.fit(
    X_train, y_train,
    group=groups_train,
    eval_set=[(X_eval, y_eval)],
    eval_group=[groups_eval],
    eval_at=[10],
)

importances = dict(zip(FEATURE_NAMES, ranker.feature_importances_))
print("  Feature importances (gain):")
for name, imp in sorted(importances.items(), key=lambda x: -x[1])[:6]:
    print(f"    {name:<16s} {imp:>5d}")


# ════════════════════════════════════════════════════════════
# Step 5 — Evaluate all 4 systems on the SAME held-out users
# ════════════════════════════════════════════════════════════
print("\n[5/5] Evaluating Popularity / CF-only / CBF-only / Hybrid...")


def precision_recall_ndcg_at_k(ranked_ids, relevant_ids, k=10):
    top_k = ranked_ids[:k]
    hits = [1 if pid in relevant_ids else 0 for pid in top_k]
    precision = sum(hits) / k
    recall = sum(hits) / len(relevant_ids) if relevant_ids else 0.0
    dcg = sum(h / np.log2(i + 2) for i, h in enumerate(hits))
    ideal = [1] * min(len(relevant_ids), k) + [0] * max(0, k - len(relevant_ids))
    idcg = sum(h / np.log2(i + 2) for i, h in enumerate(ideal))
    ndcg = dcg / idcg if idcg > 0 else 0.0
    return precision, recall, ndcg


# Re-derive eval rows so we can slice per-user for each scoring method
row_offset = 0
hybrid_preds = ranker.predict(X_eval)

metrics = {m: {"p": [], "r": [], "n": []} for m in ["popularity", "cf", "cbf", "hybrid"]}

for (user_id, candidates, relevant), g in zip(eval_meta, groups_eval):
    X_user = X_eval[row_offset:row_offset + g]
    hpred  = hybrid_preds[row_offset:row_offset + g]
    row_offset += g

    if not relevant:
        continue

    # Column indices in FEATURE_NAMES: [cf_score, cbf_score, cf_x_cbf, popularity, ...]
    cf_col, cbf_col, pop_col = 0, 1, 3

    rankings = {
        "popularity": [c for c, _ in sorted(zip(candidates, X_user[:, pop_col]), key=lambda x: -x[1])],
        "cf":         [c for c, _ in sorted(zip(candidates, X_user[:, cf_col]),  key=lambda x: -x[1])],
        "cbf":        [c for c, _ in sorted(zip(candidates, X_user[:, cbf_col]), key=lambda x: -x[1])],
        "hybrid":     [c for c, _ in sorted(zip(candidates, hpred),              key=lambda x: -x[1])],
    }

    for method, ranked in rankings.items():
        p, r, n = precision_recall_ndcg_at_k(ranked, relevant, k=10)
        metrics[method]["p"].append(p)
        metrics[method]["r"].append(r)
        metrics[method]["n"].append(n)


print(f"\n  Evaluated on {len(eval_meta)} held-out users")
print(f"\n  {'Model':<28} {'Precision@10':>13} {'Recall@10':>11} {'NDCG@10':>9}")
print("  " + "-" * 64)
labels = {
    "popularity": "Popularity baseline",
    "cf":         "CF only (SVD)",
    "cbf":        "CBF only (FAISS/TF-IDF)",
    "hybrid":     "Hybrid (LightGBM LambdaMART)",
}
results_summary = {}
for key, label in labels.items():
    p = np.mean(metrics[key]["p"])
    r = np.mean(metrics[key]["r"])
    n = np.mean(metrics[key]["n"])
    results_summary[key] = {"precision": p, "recall": r, "ndcg": n}
    print(f"  {label:<28} {p:>13.4f} {r:>11.4f} {n:>9.4f}")

pop_p = results_summary["popularity"]["precision"]
hyb_p = results_summary["hybrid"]["precision"]
if pop_p > 0:
    uplift = (hyb_p - pop_p) / pop_p
    print(f"\n  Hybrid vs Popularity Precision@10 uplift: {uplift:+.1%}")


# ════════════════════════════════════════════════════════════
# Save model + results
# ════════════════════════════════════════════════════════════
ranker.booster_.save_model(str(MODELS_DIR / "hybrid_ranker.txt"))
with open(MODELS_DIR / "ranker_feature_names.pkl", "wb") as f:
    pickle.dump(FEATURE_NAMES, f)

results_df = pd.DataFrame(results_summary).T
results_df.to_csv(PROCESSED_DIR / "ranker_evaluation.csv")

print(f"\nSaved model → {MODELS_DIR / 'hybrid_ranker.txt'}")
print(f"Saved evaluation → {PROCESSED_DIR / 'ranker_evaluation.csv'}")

print("\n" + "=" * 60)
print("✅  04_hybrid_ranker.py COMPLETE")
print("=" * 60)
print("  All four sets of metrics above were computed from real model")
print("  predictions on synthetic persona-based data — none are hardcoded.")
print("  Note: small catalogue (33 items) means @10 metrics are naturally")
print("  higher than they would be on a 50k-item real catalogue.")
print("\n  Next: backend/app/ml/ranker/ loads hybrid_ranker.txt to serve")
print("  /recommend/{user_id} via the FastAPI backend.")
