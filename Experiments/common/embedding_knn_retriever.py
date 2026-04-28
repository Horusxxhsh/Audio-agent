from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np


def _safe_load_embedding(path: str) -> Optional[np.ndarray]:
    try:
        arr = np.load(path)
        if arr is None:
            return None
        arr = np.asarray(arr, dtype=np.float32).reshape(-1)
        if arr.size == 0:
            return None
        return arr
    except Exception:
        return None


def _l2_normalize(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=np.float32).reshape(-1)
    n = float(np.linalg.norm(x))
    if n <= 0:
        return x
    return (x / n).astype(np.float32, copy=False)


@dataclass(frozen=True)
class KNNIndexStats:
    name: str
    total_items: int
    indexed_items: int
    embedding_dim: Optional[int]
    missing_embeddings: int


class EmbeddingKNNRetriever:
    """
    Generic cosine KNN retriever over cached 1-D embeddings.

    Expected dataset item schema:
    - SongName: str
    - AudioPath: str (path to *.wav)  [required for cache-based baselines]
    - Parameters: dict
    """

    def __init__(
        self,
        *,
        name: str,
        dataset: Sequence[Dict[str, Any]],
        get_embedding: Callable[[Dict[str, Any]], Optional[np.ndarray]],
        normalize: bool = True,
        verbose: bool = True,
    ) -> None:
        self.name = name
        self._get_embedding = get_embedding
        self._normalize = bool(normalize)
        self._verbose = bool(verbose)

        embeddings: List[np.ndarray] = []
        items: List[Dict[str, Any]] = []
        emb_dim: Optional[int] = None
        missing = 0

        for item in dataset:
            emb = get_embedding(item)
            if emb is None:
                missing += 1
                continue
            emb = np.asarray(emb, dtype=np.float32).reshape(-1)
            if emb.size == 0:
                missing += 1
                continue
            if self._normalize:
                emb = _l2_normalize(emb)
            if emb_dim is None:
                emb_dim = int(emb.shape[0])
            embeddings.append(emb)
            items.append(item)

        self._items = items
        self._embeddings = np.asarray(embeddings, dtype=np.float32) if embeddings else np.empty((0, 0), dtype=np.float32)
        self.stats = KNNIndexStats(
            name=self.name,
            total_items=len(dataset),
            indexed_items=len(items),
            embedding_dim=emb_dim,
            missing_embeddings=missing,
        )

        if self._verbose:
            print(
                f"[{self.name}] Indexed {self.stats.indexed_items}/{self.stats.total_items} items "
                f"(missing={self.stats.missing_embeddings}, dim={self.stats.embedding_dim})"
            )

    @property
    def is_available(self) -> bool:
        return bool(self._embeddings.size) and len(self._items) > 0

    def retrieve(self, query_item: Dict[str, Any], k: int = 1) -> List[Dict[str, Any]]:
        if not self.is_available:
            return []

        q = self._get_embedding(query_item)
        if q is None:
            return []

        q = np.asarray(q, dtype=np.float32).reshape(-1)
        if q.size == 0:
            return []

        if self._normalize:
            q = _l2_normalize(q)

        # Cosine similarity = dot product for unit-normalized vectors.
        sims = np.dot(self._embeddings, q)
        if sims.ndim != 1 or sims.size == 0:
            return []

        kk = max(0, int(k))
        if kk <= 0:
            return []

        kk = min(kk, int(sims.shape[0]))
        top_idx = np.argsort(sims)[::-1][:kk]
        return [self._items[int(i)] for i in top_idx]


def make_audio_cache_getter(suffix: str) -> Callable[[Dict[str, Any]], Optional[np.ndarray]]:
    """
    Build an embedding getter that loads cached embeddings from:
      <AudioPath><suffix>
    where AudioPath is expected to point to an existing *.wav file.
    """

    def _get(item: Dict[str, Any]) -> Optional[np.ndarray]:
        audio_path = item.get("AudioPath")
        if not audio_path:
            return None
        if not os.path.exists(audio_path):
            return None
        cache_path = str(audio_path) + str(suffix)
        return _safe_load_embedding(cache_path)

    return _get


class CLAPRetriever(EmbeddingKNNRetriever):
    def __init__(self, dataset: Sequence[Dict[str, Any]], *, verbose: bool = True) -> None:
        super().__init__(
            name="CLAP",
            dataset=dataset,
            get_embedding=make_audio_cache_getter(".clap.npy"),
            normalize=True,
            verbose=verbose,
        )


class PaSSTRetriever(EmbeddingKNNRetriever):
    def __init__(self, dataset: Sequence[Dict[str, Any]], *, verbose: bool = True) -> None:
        super().__init__(
            name="PaSST",
            dataset=dataset,
            get_embedding=make_audio_cache_getter(".passt.npy"),
            normalize=True,
            verbose=verbose,
        )


class PANNsRetriever(EmbeddingKNNRetriever):
    def __init__(self, dataset: Sequence[Dict[str, Any]], *, verbose: bool = True) -> None:
        super().__init__(
            name="PANNs",
            dataset=dataset,
            get_embedding=make_audio_cache_getter(".panns.npy"),
            normalize=True,
            verbose=verbose,
        )

