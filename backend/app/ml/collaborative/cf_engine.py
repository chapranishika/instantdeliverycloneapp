"""
Collaborative Filtering Engine
Loads TruncatedSVD factors trained by ml_research/02_collaborative_filtering.py.

Artifact filenames match exactly what 02_collaborative_filtering.py saves:
  - cf_user_factors.npy
  - cf_item_factors.npy
  - cf_mappings.pkl   (keys: user2idx, idx2user, prod2idx, idx2prod)
"""
import numpy as np
import pickle
import logging
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)
MODELS_DIR = Path(__file__).parent.parent.parent.parent / "data/processed/models"


class CollaborativeFilteringEngine:
    def __init__(self):
        self.user_factors: Optional[np.ndarray] = None
        self.item_factors: Optional[np.ndarray] = None
        self.user2idx: dict = {}
        self.prod2idx: dict = {}
        self.idx2prod: dict = {}
        self.loaded = False

    def load(self):
        """Load SVD factors and mappings saved by 02_collaborative_filtering.py."""
        try:
            # These filenames MUST match what 02_collaborative_filtering.py saves
            self.user_factors = np.load(MODELS_DIR / "cf_user_factors.npy")
            self.item_factors = np.load(MODELS_DIR / "cf_item_factors.npy")
            with open(MODELS_DIR / "cf_mappings.pkl", "rb") as f:
                m = pickle.load(f)
            self.user2idx = m["user2idx"]
            self.prod2idx = m["prod2idx"]
            self.idx2prod = m["idx2prod"]
            self.loaded = True
            logger.info(
                f"CF engine ready: {len(self.user2idx)} users, "
                f"{len(self.prod2idx)} products, "
                f"k={self.user_factors.shape[1]} factors"
            )
        except Exception as exc:
            logger.warning(f"CF engine load failed: {exc}. Serving cold-start only.")
            self.loaded = False

    def get_user_recommendations(
        self,
        user_id: str,
        n: int = 20,
        exclude_product_ids: Optional[List[int]] = None,
    ) -> List[dict]:
        """
        Personalised recs for user_id.
        user_id is a string (e.g. session_id or email) — we skip CF and
        return an empty list if the user is not in the training set, letting
        the hybrid ranker fall back to CBF/popularity.
        """
        if not self.loaded:
            return []

        exclude = set(exclude_product_ids or [])

        if user_id not in self.user2idx:
            # Unknown user — return empty, caller will use CBF/popularity
            return []

        u_idx = self.user2idx[user_id]
        u_vec = self.user_factors[u_idx]

        # Score all products
        scores = (u_vec @ self.item_factors.T).astype(float)

        # Zero out excluded items
        for pid in exclude:
            if pid in self.prod2idx:
                scores[self.prod2idx[pid]] = -np.inf

        top_idx = np.argsort(scores)[::-1][:n * 2]
        results = []
        for idx in top_idx:
            if len(results) >= n:
                break
            pid = self.idx2prod.get(int(idx))
            if pid is not None and pid not in exclude:
                results.append({
                    "product_id": int(pid),
                    "cf_score": float(scores[idx]),
                    "source": "collaborative_filtering",
                })
        return results


_cf_engine: Optional[CollaborativeFilteringEngine] = None


def get_cf_engine() -> CollaborativeFilteringEngine:
    global _cf_engine
    if _cf_engine is None:
        _cf_engine = CollaborativeFilteringEngine()
        _cf_engine.load()
    return _cf_engine
