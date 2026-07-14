"""
Hybrid Ranker
LightGBM LambdaMART blends CF + CBF signals into a single ranked list.
Also handles A/B test routing.
"""
import hashlib
import json
import logging
import pickle
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)
MODELS_DIR = Path(__file__).parent.parent.parent.parent / "data/processed/models"


class HybridRanker:
    def __init__(self):
        self.lgb_model = None
        self.ab_config: dict = {}
        self.loaded = False

    def load(self):
        try:
            txt_path = MODELS_DIR / "hybrid_ranker.txt"
            pkl_path = MODELS_DIR / "lgb_ranker.pkl"
            
            if txt_path.exists():
                import lightgbm as lgb
                self.lgb_model = lgb.Booster(model_file=str(txt_path))
                logger.info(f"Loaded Hybrid ranker Booster model from {txt_path}")
            elif pkl_path.exists():
                with open(pkl_path, "rb") as f:
                    self.lgb_model = pickle.load(f)
                logger.info(f"Loaded Hybrid ranker pickle model from {pkl_path}")
            else:
                raise FileNotFoundError(f"Neither {txt_path} nor {pkl_path} found")

            with open(MODELS_DIR / "ab_config.json") as f:
                self.ab_config = json.load(f)
            self.loaded = True
            logger.info("Hybrid ranker loaded (LightGBM LambdaMART)")
        except Exception as exc:
            logger.warning(f"Hybrid ranker load failed: {exc}. Using weighted blend.")
            self.loaded = False

    # ------------------------------------------------------------------
    # A/B routing
    # ------------------------------------------------------------------
    def get_ab_variant(self, user_id: int) -> str:
        """Deterministic A/B bucket via hash — same user always same bucket."""
        if not self.ab_config:
            return "treatment_b"
        bucket = int(hashlib.md5(str(user_id).encode()).hexdigest(), 16) % 100
        cumulative = 0
        for variant, cfg in self.ab_config.get("variants", {}).items():
            cumulative += int(cfg["weight"] * 100)
            if bucket < cumulative:
                return variant
        return "treatment_b"

    # ------------------------------------------------------------------
    # Main ranking
    # ------------------------------------------------------------------
    def rank(
        self,
        user_id: int,
        cf_candidates: List[dict],
        cbf_candidates: List[dict],
        context: Optional[dict] = None,
    ) -> List[dict]:
        """
        Merge CF + CBF candidates and re-rank using LightGBM or fallback blend.
        context: {n_user_orders, hour_of_day, day_of_week, ...}
        """
        variant = self.get_ab_variant(user_id)
        context = context or {}

        # Merge candidates by product_id, keeping best score from each source
        merged = self._merge_candidates(cf_candidates, cbf_candidates)

        if not merged:
            return []

        if variant == "control":
            # Popularity-only: sort by pop_score
            return sorted(merged, key=lambda x: x.get("pop_score", 0), reverse=True)

        if variant == "treatment_a":
            # CF only
            return sorted(merged, key=lambda x: x.get("cf_score", 0), reverse=True)

        # treatment_b — LightGBM or weighted blend
        if self.loaded and self.lgb_model is not None:
            return self._lgb_rank(merged, context)
        else:
            return self._weighted_blend(merged, context)

    def _merge_candidates(
        self, cf_list: List[dict], cbf_list: List[dict]
    ) -> List[dict]:
        """Union of CF + CBF candidates, normalise scores to [0,1]."""
        by_pid: dict = {}

        def _norm_scores(lst: List[dict], key: str) -> None:
            vals = [x.get(key, 0.0) for x in lst]
            mn, mx = min(vals, default=0), max(vals, default=1)
            rng = mx - mn if mx > mn else 1.0
            for item, v in zip(lst, vals):
                item[key + "_norm"] = (v - mn) / rng

        _norm_scores(cf_list, "cf_score")
        _norm_scores(cbf_list, "cbf_score")

        for item in cf_list:
            pid = item["product_id"]
            by_pid[pid] = {**item, "cbf_score_norm": 0.0}

        for item in cbf_list:
            pid = item["product_id"]
            if pid in by_pid:
                by_pid[pid]["cbf_score"]      = item.get("cbf_score", 0.0)
                by_pid[pid]["cbf_score_norm"] = item.get("cbf_score_norm", 0.0)
            else:
                by_pid[pid] = {**item, "cf_score": 0.0, "cf_score_norm": 0.0}

        return list(by_pid.values())

    def _lgb_rank(self, candidates: List[dict], context: dict) -> List[dict]:
        hour = context.get("hour_of_day", 12)
        n_orders = context.get("n_user_orders", 0)

        rows = []
        for c in candidates:
            rows.append(
                {
                    "cf_score":          c.get("cf_score_norm", 0.0),
                    "pop_score":         c.get("pop_score", 0.0),
                    "log_pop_count":     np.log1p(c.get("pop_count", 0)),
                    "cbf_score":         c.get("cbf_score_norm", 0.0),
                    "user_n_purchases":  float(n_orders),
                    "user_avg_reorder":  float(context.get("avg_reorder", 0.3)),
                    "in_user_dept":      float(c.get("in_user_dept", 0)),
                    "hour_sin":          np.sin(2 * np.pi * hour / 24),
                    "hour_cos":          np.cos(2 * np.pi * hour / 24),
                }
            )

        X = pd.DataFrame(rows)
        # Keep only columns the model was trained on
        if hasattr(self.lgb_model, "feature_name"):
            model_cols = self.lgb_model.feature_name()
            # If the feature_name() method returns a callable (older versions), execute it
            if callable(model_cols):
                model_cols = model_cols()
        else:
            model_cols = getattr(self.lgb_model, "feature_name_", list(X.columns))
            
        for col in model_cols:
            if col not in X.columns:
                X[col] = 0.0
        X = X[[c for c in model_cols if c in X.columns]]

        scores = self.lgb_model.predict(X)
        for item, score in zip(candidates, scores):
            item["final_score"] = float(score)

        return sorted(candidates, key=lambda x: x["final_score"], reverse=True)

    def _weighted_blend(self, candidates: List[dict], context: dict) -> List[dict]:
        """Simple weighted blend fallback (no LightGBM)."""
        w_cf  = 0.55
        w_cbf = 0.30
        w_pop = 0.15
        for item in candidates:
            item["final_score"] = (
                w_cf  * item.get("cf_score_norm", 0.0)
                + w_cbf * item.get("cbf_score_norm", 0.0)
                + w_pop * item.get("pop_score", 0.0)
            )
        return sorted(candidates, key=lambda x: x["final_score"], reverse=True)


_ranker: Optional[HybridRanker] = None


def get_ranker() -> HybridRanker:
    global _ranker
    if _ranker is None:
        _ranker = HybridRanker()
        _ranker.load()
    return _ranker
