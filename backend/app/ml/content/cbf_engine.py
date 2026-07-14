"""
Content-Based Filtering Engine
FAISS ANN search + TF-IDF for similar products and semantic search.
"""
import numpy as np
import pickle
import logging
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)
MODELS_DIR = Path(__file__).parent.parent.parent.parent / "data/processed/models"


class ContentBasedEngine:
    def __init__(self):
        self.faiss_index = None
        self.product_ids: Optional[np.ndarray] = None
        self.embeddings: Optional[np.ndarray] = None
        self.tfidf = None
        self.tfidf_matrix = None
        self.dept_centroids: dict = {}
        self._st_model = None          # lazy-loaded sentence transformer
        self.loaded = False

    def load(self):
        try:
            import faiss
            import scipy.sparse as sp

            self.faiss_index = faiss.read_index(
                str(MODELS_DIR / "faiss_product_index.bin")
            )
            self.product_ids = np.load(MODELS_DIR / "faiss_product_ids.npy")
            self.embeddings  = np.load(
                MODELS_DIR / "product_embeddings.npy"
            ).astype(np.float32)

            with open(MODELS_DIR / "tfidf_vectorizer.pkl", "rb") as f:
                self.tfidf = pickle.load(f)
            self.tfidf_matrix = sp.load_npz(MODELS_DIR / "tfidf_matrix.npz")

            with open(MODELS_DIR / "department_centroids.pkl", "rb") as f:
                self.dept_centroids = pickle.load(f)

            self.loaded = True
            logger.info(
                f"CBF engine ready: {self.faiss_index.ntotal} products in FAISS"
            )
        except Exception as exc:
            logger.warning(f"CBF engine load failed: {exc}. Running degraded.")
            self.loaded = False

    # ------------------------------------------------------------------
    # Similar products (product detail page widget)
    # ------------------------------------------------------------------
    def get_similar_products(
        self,
        product_id: int,
        n: int = 10,
        exclude_ids: Optional[List[int]] = None,
    ) -> List[dict]:
        if not self.loaded:
            return []

        exclude = set(exclude_ids or [])
        exclude.add(product_id)

        prod_list = self.product_ids.tolist()
        if product_id not in prod_list:
            return []

        p_idx = prod_list.index(product_id)
        query = self.embeddings[p_idx : p_idx + 1]

        k = min(n + len(exclude) + 10, self.faiss_index.ntotal)
        distances, indices = self.faiss_index.search(query, k)

        results = []
        for idx, dist in zip(indices[0], distances[0]):
            if idx < 0 or idx >= len(self.product_ids):
                continue
            pid = int(self.product_ids[idx])
            if pid not in exclude:
                results.append(
                    {
                        "product_id": pid,
                        "cbf_score": float(dist),
                        "source": "content_based",
                    }
                )
            if len(results) >= n:
                break
        return results

    # ------------------------------------------------------------------
    # Semantic search (search page)
    # ------------------------------------------------------------------
    def search_by_text(self, query: str, n: int = 20) -> List[dict]:
        if not self.loaded:
            return []
        try:
            emb = self._embed_query(query)
            distances, indices = self.faiss_index.search(emb, n)
            return [
                {
                    "product_id": int(self.product_ids[i]),
                    "cbf_score": float(d),
                    "source": "semantic_search",
                }
                for i, d in zip(indices[0], distances[0])
                if i >= 0 and i < len(self.product_ids)
            ]
        except Exception as exc:
            logger.warning(f"Semantic search failed: {exc}. Falling back to TF-IDF.")
            return self._tfidf_search(query, n)

    def _embed_query(self, query: str) -> np.ndarray:
        """Embed a text query using sentence-transformers (lazy load)."""
        if self._st_model is None:
            from sentence_transformers import SentenceTransformer
            self._st_model = SentenceTransformer("all-MiniLM-L6-v2")
        emb = self._st_model.encode(
            [query.lower()], normalize_embeddings=True
        ).astype(np.float32)
        return emb

    def _tfidf_search(self, query: str, n: int) -> List[dict]:
        if self.tfidf is None or self.tfidf_matrix is None:
            return []
        from sklearn.metrics.pairwise import cosine_similarity

        q_vec = self.tfidf.transform([query.lower()])
        sims  = cosine_similarity(q_vec, self.tfidf_matrix).flatten()
        top   = np.argpartition(sims, -n)[-n:]
        top   = top[np.argsort(sims[top])[::-1]]
        return [
            {
                "product_id": int(self.product_ids[i]),
                "cbf_score": float(sims[i]),
                "source": "tfidf_search",
            }
            for i in top
            if i < len(self.product_ids)
        ]

    # ------------------------------------------------------------------
    # Category browsing (home feed rails)
    # ------------------------------------------------------------------
    def get_category_products(self, department: str, n: int = 20) -> List[dict]:
        if not self.loaded or department not in self.dept_centroids:
            return []
        centroid = np.array(
            self.dept_centroids[department], dtype=np.float32
        ).reshape(1, -1)
        distances, indices = self.faiss_index.search(centroid, n)
        return [
            {
                "product_id": int(self.product_ids[i]),
                "cbf_score": float(d),
                "source": "category",
            }
            for i, d in zip(indices[0], distances[0])
            if i >= 0 and i < len(self.product_ids)
        ]


_cbf_engine: Optional[ContentBasedEngine] = None


def get_cbf_engine() -> ContentBasedEngine:
    global _cbf_engine
    if _cbf_engine is None:
        _cbf_engine = ContentBasedEngine()
        _cbf_engine.load()
    return _cbf_engine
