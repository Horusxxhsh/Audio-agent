from __future__ import annotations

import math
from typing import Dict, List, Sequence

from Experiments.common.evaluate import Evaluator


def _distance(evaluator: Evaluator, left: Dict, right: Dict) -> float:
    return evaluator.compute_parameter_distance(left.get("Parameters", {}), right.get("Parameters", {}))


def _normalized_flat_vectors(dataset: Sequence[Dict], evaluator: Evaluator) -> List[Dict[str, float]]:
    vectors: List[Dict[str, float]] = []
    for item in dataset:
        flat = evaluator._flatten_params(item.get("Parameters", {}))
        vectors.append({key: evaluator._normalize_value(key, value) for key, value in flat.items()})
    return vectors


def _normalized_distance(left: Dict[str, float], right: Dict[str, float], evaluator: Evaluator) -> float:
    keys = set(left.keys()) | set(right.keys())
    if not keys:
        return 0.0
    total = 0.0
    for key in keys:
        missing_value = evaluator._normalize_value(key, 0.0)
        diff = left.get(key, missing_value) - right.get(key, missing_value)
        total += diff * diff
    return math.sqrt(total / len(keys))


def _connected_components(dataset: Sequence[Dict], threshold: float) -> List[List[int]]:
    evaluator = Evaluator(normalize=True)
    flat_vectors = _normalized_flat_vectors(dataset, evaluator)
    n = len(dataset)
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        root_a = find(a)
        root_b = find(b)
        if root_a != root_b:
            parent[root_b] = root_a

    for i in range(n):
        for j in range(i + 1, n):
            dist = _normalized_distance(flat_vectors[i], flat_vectors[j], evaluator)
            if dist <= threshold or math.isclose(dist, threshold, abs_tol=1e-12):
                union(i, j)

    grouped: Dict[int, List[int]] = {}
    for idx in range(n):
        grouped.setdefault(find(idx), []).append(idx)
    return [members for _, members in sorted(grouped.items(), key=lambda pair: min(pair[1]))]


def build_parameter_cluster_split(
    dataset: Sequence[Dict],
    requested_query_indices: Sequence[int],
    threshold: float,
) -> Dict[str, object]:
    if not requested_query_indices:
        raise ValueError("requested_query_indices must not be empty")

    clusters = _connected_components(dataset, threshold)
    index_to_cluster = {
        member: cluster_id
        for cluster_id, members in enumerate(clusters)
        for member in members
    }

    selected_clusters = set()
    test_indices: List[int] = []
    removed_query_count = 0
    for idx in requested_query_indices:
        cluster_id = index_to_cluster[idx]
        if cluster_id in selected_clusters:
            removed_query_count += 1
            continue
        selected_clusters.add(cluster_id)
        test_indices.append(idx)

    kb_indices = [
        idx
        for idx in range(len(dataset))
        if index_to_cluster[idx] not in selected_clusters
    ]

    cluster_summary = [
        {
            "cluster_id": cluster_id,
            "members": members,
            "names": [str(dataset[idx].get("SongName", f"preset_{idx}")) for idx in members],
        }
        for cluster_id, members in enumerate(clusters)
    ]

    return {
        "threshold": threshold,
        "test_indices": test_indices,
        "kb_indices": kb_indices,
        "clusters": cluster_summary,
        "removed_query_count": removed_query_count,
        "cluster_count": len(clusters),
    }
