from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from Experiments.E7_HardSplit.run_hard_split_retrieval import (
    load_dataset,
    load_requested_query_indices,
)
from Experiments.common.evaluate import Evaluator
from Experiments.common.parameter_space import topk_parameter_neighborhood_recall


VECTOR_METHODS = {
    "TRR": "TRR",
    "Wav2Vec": "Wav2Vec",
    "FeatureNN": "FeatureNN",
    "CLAP": "CLAP",
    "PaSST": "PaSST",
    "PANNs": "PANNs",
}
DEFAULT_DATASET = "Data/External_1267_211/dataset/dataset_full_vectors_1267.json"
DEFAULT_SPLIT = "Experiments/tmm/splits/tmm_external1267_audio_grouped/seed0/test.txt"
DEFAULT_OUT = "Experiments/E8_ExecutableNeighborhood/outputs/topk"
OUTPUT_FIELDS = [
    "method",
    "query_idx",
    "query_name",
    "status",
    "coverage",
    "skip_reason",
    "candidate_count",
    "metric_impl",
    "top1_name",
    "top1_norm_l2",
    "top1_acc_at_0_1",
    "top1_recall",
    "top1_cosine",
    "top1_module",
    "pnr_at_1",
    "pnr_at_3",
    "pnr_at_5",
    "topk_names",
    "topk_scores",
]
METRIC_IMPL = "legacy_evaluator_for_protocolA_compat"


def _get_vector(item: Dict[str, object], vector_key: str) -> Optional[np.ndarray]:
    vector, reason = _inspect_vector(item, vector_key)
    return vector if reason == "" else None


def _inspect_vector(item: Dict[str, object], vector_key: str) -> Tuple[Optional[np.ndarray], str]:
    vectors = item.get("Vectors", {})
    if not isinstance(vectors, dict):
        return None, "missing_vector"
    raw = vectors.get(vector_key)
    if raw is None:
        return None, "missing_vector"
    arr = np.asarray(raw, dtype=float).reshape(-1)
    if arr.size == 0:
        return None, "missing_vector"
    if not np.all(np.isfinite(arr)):
        return None, "nonfinite_vector"
    if float(np.linalg.norm(arr)) <= 0.0:
        return None, "zero_norm_vector"
    return arr, ""


def _normalize_vector(vector: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vector))
    if norm <= 0.0:
        raise ValueError("zero-norm vectors are invalid for cosine retrieval")
    return vector.astype(float) / norm


def _normalize_matrix(matrix: np.ndarray) -> np.ndarray:
    if matrix.size == 0:
        return matrix.astype(float)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    if np.any(norms <= 0.0):
        raise ValueError("zero-norm rows are invalid for cosine retrieval")
    return matrix.astype(float) / norms


def cosine_topk(query: np.ndarray, matrix: np.ndarray, k: int) -> List[Tuple[int, float]]:
    """Return row indices and cosine scores sorted from best to worst."""
    if k <= 0:
        return []
    matrix = np.asarray(matrix, dtype=float)
    if matrix.size == 0 or matrix.shape[0] == 0:
        return []
    if matrix.ndim != 2:
        raise ValueError("matrix must be two-dimensional")
    query = np.asarray(query, dtype=float).reshape(-1)
    if query.shape[0] != matrix.shape[1]:
        raise ValueError(f"query dim {query.shape[0]} does not match matrix dim {matrix.shape[1]}")
    scores = np.dot(_normalize_matrix(matrix), _normalize_vector(query))
    order = np.argsort(-scores, kind="mergesort")[: min(k, matrix.shape[0])]
    return [(int(idx), float(scores[idx])) for idx in order]


def topk_record(
    method: str,
    query_idx: int,
    query_item: Dict[str, object],
    candidates: Sequence[Tuple[Dict[str, object], float]],
    threshold: float,
) -> Dict[str, object]:
    gt = query_item.get("Parameters", {})
    topk_params = [candidate.get("Parameters", {}) for candidate, _ in candidates]
    top1_item = candidates[0][0] if candidates else {}
    top1_params = top1_item.get("Parameters", {}) if candidates else {}
    norm_eval = Evaluator(normalize=True)
    raw_eval = Evaluator(normalize=False)

    row: Dict[str, object] = {
        "method": method,
        "query_idx": int(query_idx),
        "query_name": str(query_item.get("SongName", "")),
        "status": "ok",
        "coverage": 1.0,
        "skip_reason": "",
        "candidate_count": len(candidates),
        "metric_impl": METRIC_IMPL,
        "top1_name": str(top1_item.get("SongName", "")) if candidates else "",
        "top1_norm_l2": norm_eval.compute_parameter_distance(top1_params, gt) if candidates else None,
        "top1_acc_at_0_1": norm_eval.compute_accuracy_tolerance(top1_params, gt, tolerance=0.1) if candidates else None,
        "top1_recall": norm_eval.compute_parameter_recall(top1_params, gt, threshold=0.1) if candidates else None,
        "top1_cosine": norm_eval.compute_cosine_similarity(top1_params, gt) if candidates else None,
        "top1_module": raw_eval.compute_module_consistency(top1_params, gt) if candidates else None,
        "pnr_at_1": topk_parameter_neighborhood_recall(topk_params[:1], gt, threshold=threshold),
        "pnr_at_3": topk_parameter_neighborhood_recall(topk_params[:3], gt, threshold=threshold),
        "pnr_at_5": topk_parameter_neighborhood_recall(topk_params[:5], gt, threshold=threshold),
        "topk_names": [str(candidate.get("SongName", "")) for candidate, _ in candidates],
        "topk_scores": [float(score) for _, score in candidates],
        "topk_candidates": [
            {
                "name": str(candidate.get("SongName", "")),
                "score": float(score),
                "parameters": candidate.get("Parameters", {}),
            }
            for candidate, score in candidates
        ],
    }
    row["pnr_at_k"] = topk_parameter_neighborhood_recall(topk_params, gt, threshold=threshold)
    return row


def skipped_record(
    method: str,
    query_idx: int,
    query_item: Dict[str, object],
    skip_reason: str,
) -> Dict[str, object]:
    return {
        "method": method,
        "query_idx": int(query_idx),
        "query_name": str(query_item.get("SongName", "")),
        "status": "skipped",
        "coverage": 0.0,
        "skip_reason": skip_reason,
        "candidate_count": 0,
        "metric_impl": METRIC_IMPL,
        "top1_name": "",
        "top1_norm_l2": None,
        "top1_acc_at_0_1": None,
        "top1_recall": None,
        "top1_cosine": None,
        "top1_module": None,
        "pnr_at_1": 0,
        "pnr_at_3": 0,
        "pnr_at_5": 0,
        "pnr_at_k": 0,
        "topk_names": [],
        "topk_scores": [],
        "topk_candidates": [],
    }


def _index_kb(
    kb_items: Sequence[Dict[str, object]],
    vector_key: str,
) -> Tuple[List[Dict[str, object]], np.ndarray, Dict[str, int]]:
    pairs: List[Tuple[Dict[str, object], np.ndarray]] = []
    stats = {
        "candidate_pool_size": len(kb_items),
        "indexed_kb_items": 0,
        "zero_norm_kb_vectors": 0,
    }
    for item in kb_items:
        vector, reason = _inspect_vector(item, vector_key)
        if reason == "zero_norm_vector":
            stats["zero_norm_kb_vectors"] += 1
        if vector is not None:
            pairs.append((item, vector))
    if not pairs:
        return [], np.empty((0, 0), dtype=float), stats
    dims = {int(vector.shape[0]) for _, vector in pairs}
    if len(dims) != 1:
        raise ValueError(f"{vector_key} has inconsistent KB embedding dimensions: {sorted(dims)}")
    stats["indexed_kb_items"] = len(pairs)
    return [item for item, _ in pairs], np.asarray([vector for _, vector in pairs], dtype=float), stats


def _new_method_audit(expected_queries: int, kb_stats: Dict[str, int]) -> Dict[str, int]:
    return {
        "expected_queries": expected_queries,
        "ok_rows": 0,
        "skipped_rows": 0,
        "missing_query_vectors": 0,
        "dim_mismatch_query_vectors": 0,
        "zero_norm_query_vectors": 0,
        "indexed_kb_items": int(kb_stats["indexed_kb_items"]),
        "zero_norm_kb_vectors": int(kb_stats["zero_norm_kb_vectors"]),
        "candidate_pool_size": int(kb_stats["candidate_pool_size"]),
    }


def dump_topk(
    dataset_path: Path,
    split_file: Path,
    output_dir: Path,
    k: int,
    threshold: float,
) -> List[Dict[str, object]]:
    dataset = load_dataset(dataset_path)
    query_indices = load_requested_query_indices(dataset, split_file)
    query_index_set = set(query_indices)
    kb_items = [item for idx, item in enumerate(dataset) if idx not in query_index_set]
    rows: List[Dict[str, object]] = []
    audit: Dict[str, Dict[str, int]] = {}

    for method, vector_key in VECTOR_METHODS.items():
        indexed_items, matrix, kb_stats = _index_kb(kb_items, vector_key)
        method_audit = _new_method_audit(len(query_indices), kb_stats)
        audit[method] = method_audit
        expected_dim = matrix.shape[1] if matrix.ndim == 2 and matrix.shape[0] else None
        for query_idx in query_indices:
            query_item = dataset[query_idx]
            query_vector, vector_reason = _inspect_vector(query_item, vector_key)
            if vector_reason:
                skip_reason = f"{vector_reason.replace('_vector', '')}_query_vector"
                if vector_reason == "missing_vector":
                    method_audit["missing_query_vectors"] += 1
                elif vector_reason == "zero_norm_vector":
                    method_audit["zero_norm_query_vectors"] += 1
                rows.append(skipped_record(method, query_idx, query_item, skip_reason))
                method_audit["skipped_rows"] += 1
                continue
            if expected_dim is None:
                rows.append(skipped_record(method, query_idx, query_item, "no_indexed_kb_items"))
                method_audit["skipped_rows"] += 1
                continue
            if int(query_vector.shape[0]) != int(expected_dim):
                rows.append(skipped_record(method, query_idx, query_item, "dim_mismatch_query_vector"))
                method_audit["dim_mismatch_query_vectors"] += 1
                method_audit["skipped_rows"] += 1
                continue
            ranked = cosine_topk(query_vector, matrix, k=k)
            candidates = [(indexed_items[item_idx], score) for item_idx, score in ranked]
            if not candidates:
                rows.append(skipped_record(method, query_idx, query_item, "no_retrieval_candidates"))
                method_audit["skipped_rows"] += 1
                continue
            rows.append(topk_record(method, query_idx, query_item, candidates, threshold=threshold))
            method_audit["ok_rows"] += 1

    write_outputs(output_dir, rows, audit)
    return rows


def _csv_value(value: object) -> object:
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return value


def write_outputs(output_dir: Path, rows: Sequence[Dict[str, object]], audit: Dict[str, object]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "topk_retrieval_metrics.json"
    csv_path = output_dir / "topk_retrieval_metrics.csv"
    audit_path = output_dir / "topk_retrieval_audit.json"

    json_path.write_text(json.dumps(list(rows), indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    audit_path.write_text(json.dumps(audit, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")

    fields = list(OUTPUT_FIELDS)
    extra = sorted({key for row in rows for key in row.keys()} - set(fields))
    extra = [key for key in extra if key != "topk_candidates"]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields + extra)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _csv_value(row.get(key)) for key in fields + extra})


def main() -> int:
    parser = argparse.ArgumentParser(description="Dump Protocol-A top-k executable-neighborhood retrieval rows.")
    parser.add_argument("--dataset", default=DEFAULT_DATASET, help="Dataset JSON path.")
    parser.add_argument("--split-file", default=DEFAULT_SPLIT, help="Protocol-A query-name split file.")
    parser.add_argument("--output-dir", default=DEFAULT_OUT, help="Directory for JSON array, CSV, and audit outputs.")
    parser.add_argument("--k", type=int, default=5, help="Number of retrieved neighbors per query.")
    parser.add_argument("--threshold", type=float, default=0.10, help="Normalized parameter RMSE threshold for PNR.")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    dump_topk(Path(args.dataset), Path(args.split_file), output_dir, k=args.k, threshold=args.threshold)
    print(f"wrote {output_dir / 'topk_retrieval_metrics.csv'}")
    print(f"wrote {output_dir / 'topk_retrieval_metrics.json'}")
    print(f"wrote {output_dir / 'topk_retrieval_audit.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
