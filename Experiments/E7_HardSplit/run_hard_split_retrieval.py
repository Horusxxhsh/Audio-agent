from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from Experiments.common.evaluate import Evaluator
from Experiments.common.hard_split import build_parameter_cluster_split


VECTOR_METHODS = {
    "TRR": "TRR",
    "Wav2Vec": "Wav2Vec",
    "FeatureNN": "FeatureNN",
    "CLAP": "CLAP",
    "PaSST": "PaSST",
    "PANNs": "PANNs",
}


def _ordered_keys(rows: List[Dict[str, object]]) -> List[str]:
    preferred = [
        "method",
        "n",
        "norm_l2",
        "l2",
        "acc_at_0_1",
        "recall",
        "cosine",
        "module",
        "coverage",
        "missing_query_vectors",
        "indexed_kb_items",
        "candidate_pool_size",
    ]
    keys = {key for row in rows for key in row.keys()}
    ordered = [key for key in preferred if key in keys]
    ordered.extend(sorted(keys - set(ordered)))
    return ordered


def write_outputs(output_dir: Path, results: List[Dict[str, object]], audit: Dict[str, object]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    result_keys = _ordered_keys(results)

    (output_dir / "hard_split_results.json").write_text(
        json.dumps(results, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "hard_split_audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output_dir / "hard_split_results.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=result_keys)
        writer.writeheader()
        writer.writerows(results)


def load_dataset(path: Path) -> List[Dict[str, object]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Dataset JSON must contain a list of records")
    return data


def load_requested_query_indices(dataset: Sequence[Dict[str, object]], split_file: Path) -> List[int]:
    requested_names = [
        line.strip()
        for line in split_file.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    name_to_indices: Dict[str, List[int]] = {}
    for idx, item in enumerate(dataset):
        name = str(item.get("SongName", ""))
        name_to_indices.setdefault(name, []).append(idx)

    indices: List[int] = []
    missing_names: List[str] = []
    for name in requested_names:
        candidates = name_to_indices.get(name, [])
        if not candidates:
            missing_names.append(name)
            continue
        indices.append(candidates.pop(0))

    if missing_names:
        raise ValueError(f"Split file contains names missing from dataset: {missing_names[:5]}")
    return indices


def _get_vector(item: Dict[str, object], vector_key: str) -> Optional[np.ndarray]:
    vectors = item.get("Vectors", {})
    if not isinstance(vectors, dict):
        return None
    raw = vectors.get(vector_key)
    if raw is None:
        return None
    arr = np.asarray(raw, dtype=np.float32).reshape(-1)
    if arr.size == 0:
        return None
    return arr


def _normalize_matrix(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms <= 0] = 1.0
    return matrix / norms


def _top1_by_cosine(query_vec: np.ndarray, kb_vectors: np.ndarray, kb_items: Sequence[Dict[str, object]]) -> Dict[str, object]:
    q = query_vec.astype(np.float32).reshape(1, -1)
    q = _normalize_matrix(q)[0]
    sims = np.dot(kb_vectors, q)
    return kb_items[int(np.argmax(sims))]


def _mean(values: Iterable[float]) -> float:
    vals = list(values)
    if not vals:
        return float("nan")
    return float(sum(vals) / len(vals))


def evaluate_method(
    method: str,
    vector_key: str,
    test_items: Sequence[Dict[str, object]],
    kb_items: Sequence[Dict[str, object]],
) -> Dict[str, object]:
    kb_pairs: List[Tuple[Dict[str, object], np.ndarray]] = []
    for item in kb_items:
        vec = _get_vector(item, vector_key)
        if vec is not None:
            kb_pairs.append((item, vec))

    indexed_kb_items = len(kb_pairs)
    if indexed_kb_items == 0:
        return {
            "method": method,
            "n": 0,
            "norm_l2": None,
            "l2": None,
            "acc_at_0_1": None,
            "recall": None,
            "cosine": None,
            "module": None,
            "coverage": 0.0,
            "missing_query_vectors": len(test_items),
            "indexed_kb_items": 0,
            "candidate_pool_size": len(kb_items),
        }

    kb_dims = {int(vec.shape[0]) for _, vec in kb_pairs}
    if len(kb_dims) != 1:
        raise ValueError(f"{method} has inconsistent KB embedding dimensions: {sorted(kb_dims)}")

    kb_matrix = _normalize_matrix(np.asarray([vec for _, vec in kb_pairs], dtype=np.float32))
    kb_indexed_items = [item for item, _ in kb_pairs]
    raw_eval = Evaluator(normalize=False)
    norm_eval = Evaluator(normalize=True)

    l2_values: List[float] = []
    norm_l2_values: List[float] = []
    acc_values: List[float] = []
    recall_values: List[float] = []
    cosine_values: List[float] = []
    module_values: List[float] = []
    missing_query_vectors = 0

    expected_dim = next(iter(kb_dims))
    for query_item in test_items:
        query_vec = _get_vector(query_item, vector_key)
        if query_vec is None or int(query_vec.shape[0]) != expected_dim:
            missing_query_vectors += 1
            continue
        retrieved = _top1_by_cosine(query_vec, kb_matrix, kb_indexed_items)
        pred = retrieved.get("Parameters", {})
        gt = query_item.get("Parameters", {})
        l2_values.append(raw_eval.compute_parameter_distance(pred, gt))
        norm_l2_values.append(norm_eval.compute_parameter_distance(pred, gt))
        acc_values.append(norm_eval.compute_accuracy_tolerance(pred, gt, tolerance=0.1))
        recall_values.append(norm_eval.compute_parameter_recall(pred, gt, threshold=0.1))
        cosine_values.append(norm_eval.compute_cosine_similarity(pred, gt))
        module_values.append(raw_eval.compute_module_consistency(pred, gt))

    n = len(norm_l2_values)
    coverage = n / len(test_items) if test_items else 0.0
    return {
        "method": method,
        "n": n,
        "norm_l2": _mean(norm_l2_values) if n else None,
        "l2": _mean(l2_values) if n else None,
        "acc_at_0_1": _mean(acc_values) if n else None,
        "recall": _mean(recall_values) if n else None,
        "cosine": _mean(cosine_values) if n else None,
        "module": _mean(module_values) if n else None,
        "coverage": coverage,
        "missing_query_vectors": missing_query_vectors,
        "indexed_kb_items": indexed_kb_items,
        "candidate_pool_size": len(kb_items),
    }


def run_hard_split(
    dataset_path: Path,
    split_file: Path,
    threshold: float,
) -> Tuple[List[Dict[str, object]], Dict[str, object]]:
    dataset = load_dataset(dataset_path)
    requested_query_indices = load_requested_query_indices(dataset, split_file)
    split = build_parameter_cluster_split(dataset, requested_query_indices, threshold)
    test_indices = [int(idx) for idx in split["test_indices"]]
    kb_indices = [int(idx) for idx in split["kb_indices"]]
    test_items = [dataset[idx] for idx in test_indices]
    kb_items = [dataset[idx] for idx in kb_indices]

    results = [
        evaluate_method(method, vector_key, test_items, kb_items)
        for method, vector_key in VECTOR_METHODS.items()
    ]
    audit = {
        "dataset_path": str(dataset_path),
        "split_file": str(split_file),
        "threshold": threshold,
        "requested_query_count": len(requested_query_indices),
        "test_count": len(test_indices),
        "kb_count": len(kb_indices),
        "removed_query_count": split["removed_query_count"],
        "cluster_count": split["cluster_count"],
        "selected_query_names": [str(dataset[idx].get("SongName", "")) for idx in test_indices],
    }
    return results, audit


def main() -> int:
    parser = argparse.ArgumentParser(description="Run parameter-cluster hard split retrieval evaluation.")
    parser.add_argument(
        "--dataset",
        default="Data/External_1267_211/dataset/dataset_full_vectors_1267.json",
        help="Dataset JSON path.",
    )
    parser.add_argument(
        "--split-file",
        default="Experiments/tmm/splits/tmm_external1267_audio_grouped/seed0/test.txt",
        help="Protocol-A compatible query-name split file.",
    )
    parser.add_argument("--threshold", type=float, default=0.02, help="Normalized parameter RMSE cluster threshold.")
    parser.add_argument("--output-dir", default="Experiments/E7_HardSplit", help="Directory for JSON/CSV outputs.")
    args = parser.parse_args()

    results, audit = run_hard_split(Path(args.dataset), Path(args.split_file), args.threshold)
    output_dir = Path(args.output_dir)
    write_outputs(output_dir, results, audit)
    print(f"wrote {output_dir / 'hard_split_results.json'}")
    print(f"wrote {output_dir / 'hard_split_results.csv'}")
    print(f"wrote {output_dir / 'hard_split_audit.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
