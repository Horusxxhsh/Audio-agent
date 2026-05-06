from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from Experiments.E7_HardSplit.run_hard_split_retrieval import load_dataset, load_requested_query_indices
from Experiments.E8_ExecutableNeighborhood.topk_retrieval_dump import cosine_topk
from Experiments.common.evaluate import Evaluator
from Experiments.common.parameter_space import topk_parameter_neighborhood_recall
from Experiments.E9_TMMMajorRevision.validity_audit import switch_metrics

DEFAULT_DATASET = "Data/External_1267_211/dataset/dataset_full_vectors_1267.json"
DEFAULT_SPLIT = "Experiments/tmm/splits/tmm_external1267_audio_grouped/seed0/test.txt"
DEFAULT_OUT = "Experiments/E9_TMMMajorRevision/outputs/unified_protocol"
DEFAULT_METHODS = {"Wav2Vec": "Wav2Vec", "FeatureNN": "FeatureNN", "CLAP": "CLAP", "PaSST": "PaSST", "PANNs": "PANNs", "TRR": "TRR"}
METRIC_IMPL = "protocol_ab_unified_evaluator_v1"


def _has_vector(item: Mapping[str, object], key: str) -> bool:
    vectors = item.get("Vectors", {})
    vec = vectors.get(key) if isinstance(vectors, Mapping) else None
    return isinstance(vec, list) and len(vec) > 0


def _vector(item: Mapping[str, object], key: str) -> np.ndarray | None:
    if not _has_vector(item, key):
        return None
    arr = np.asarray(item["Vectors"][key], dtype=float).reshape(-1)
    if arr.size == 0 or not np.all(np.isfinite(arr)) or float(np.linalg.norm(arr)) <= 0:
        return None
    return arr


def vector_coverage(dataset: Sequence[Mapping[str, object]], query_indices: Sequence[int], methods: Mapping[str, str] | None = None) -> dict[str, dict[str, int]]:
    methods = methods or DEFAULT_METHODS
    qset = {int(idx) for idx in query_indices}
    kb_indices = [idx for idx in range(len(dataset)) if idx not in qset]
    return {
        method: {
            "query_ok": sum(1 for idx in qset if _has_vector(dataset[idx], key)),
            "query_total": len(qset),
            "kb_ok": sum(1 for idx in kb_indices if _has_vector(dataset[idx], key)),
            "kb_total": len(kb_indices),
        }
        for method, key in methods.items()
    }


def _index_kb(kb_items: Sequence[Mapping[str, object]], vector_key: str) -> tuple[list[Mapping[str, object]], np.ndarray]:
    pairs = [(item, _vector(item, vector_key)) for item in kb_items]
    pairs = [(item, vec) for item, vec in pairs if vec is not None]
    if not pairs:
        return [], np.empty((0, 0), dtype=float)
    dims = {int(vec.shape[0]) for _, vec in pairs}
    if len(dims) != 1:
        raise ValueError(f"inconsistent vector dimensions for {vector_key}: {sorted(dims)}")
    return [item for item, _ in pairs], np.asarray([vec for _, vec in pairs], dtype=float)


def _format_threshold(threshold: float) -> str:
    return f"{float(threshold):.2f}".replace(".", "_")


def topk_record(method: str, query_idx: int, query_item: Mapping[str, object], candidates: Sequence[tuple[Mapping[str, object], float]], pnr_thresholds: Sequence[float]) -> dict[str, object]:
    norm_eval = Evaluator(normalize=True)
    raw_eval = Evaluator(normalize=False)
    gt = query_item.get("Parameters", {})
    top1 = candidates[0][0] if candidates else {}
    top1_params = top1.get("Parameters", {}) if isinstance(top1, Mapping) else {}
    topk_params = [candidate.get("Parameters", {}) for candidate, _ in candidates]
    row: dict[str, object] = {
        "method": method,
        "query_idx": int(query_idx),
        "query_name": str(query_item.get("SongName", "")),
        "status": "ok",
        "metric_impl": METRIC_IMPL,
        "top1_name": str(top1.get("SongName", "")) if isinstance(top1, Mapping) else "",
        "top1_norm_l2": norm_eval.compute_parameter_distance(top1_params, gt),
        "top1_acc_at_0_1": norm_eval.compute_accuracy_tolerance(top1_params, gt, tolerance=0.1),
        "top1_recall": norm_eval.compute_parameter_recall(top1_params, gt, threshold=0.1),
        "top1_cosine": norm_eval.compute_cosine_similarity(top1_params, gt),
        "top1_module": raw_eval.compute_module_consistency(top1_params, gt),
        "topk_names": [str(candidate.get("SongName", "")) for candidate, _ in candidates],
        "topk_scores": [float(score) for _, score in candidates],
        "topk_candidates": [
            {"name": str(candidate.get("SongName", "")), "score": float(score), "parameters": candidate.get("Parameters", {})}
            for candidate, score in candidates
        ],
    }
    row.update({f"top1_{key}": value for key, value in switch_metrics(top1_params, gt).items()})
    for threshold in pnr_thresholds:
        suffix = _format_threshold(threshold)
        for k in (1, 5, 10):
            row[f"pnr_at_{k}_t{suffix}"] = topk_parameter_neighborhood_recall(topk_params[:k], gt, threshold=float(threshold))
    return row


def skipped_record(method: str, query_idx: int, query_item: Mapping[str, object], reason: str) -> dict[str, object]:
    return {
        "method": method,
        "query_idx": int(query_idx),
        "query_name": str(query_item.get("SongName", "")),
        "status": "skipped",
        "skip_reason": reason,
        "metric_impl": METRIC_IMPL,
        "topk_candidates": [],
    }


def dump_unified_topk(
    dataset: Sequence[Mapping[str, object]],
    query_indices: Sequence[int],
    kb_indices: Sequence[int] | None = None,
    methods: Mapping[str, str] | None = None,
    k: int = 10,
    pnr_thresholds: Sequence[float] = (0.05, 0.10, 0.15),
) -> list[dict[str, object]]:
    methods = methods or DEFAULT_METHODS
    qset = {int(idx) for idx in query_indices}
    kb_source_indices = [idx for idx in (kb_indices if kb_indices is not None else range(len(dataset))) if int(idx) not in qset]
    kb_items = [dataset[int(idx)] for idx in kb_source_indices]
    rows: list[dict[str, object]] = []
    for method, key in methods.items():
        indexed, matrix = _index_kb(kb_items, key)
        expected_dim = matrix.shape[1] if matrix.ndim == 2 and matrix.shape[0] else None
        for query_idx in query_indices:
            query = dataset[int(query_idx)]
            qvec = _vector(query, key)
            if qvec is None:
                rows.append(skipped_record(method, int(query_idx), query, "missing_or_invalid_query_vector"))
                continue
            if expected_dim is None:
                rows.append(skipped_record(method, int(query_idx), query, "no_indexed_kb_items"))
                continue
            if int(qvec.shape[0]) != int(expected_dim):
                rows.append(skipped_record(method, int(query_idx), query, "dim_mismatch_query_vector"))
                continue
            ranked = cosine_topk(qvec, matrix, k=k)
            candidates = [(indexed[idx], score) for idx, score in ranked]
            rows.append(topk_record(method, int(query_idx), query, candidates, pnr_thresholds))
    return rows


def _mean(values: Sequence[float]) -> float:
    return float(np.mean(values)) if values else float("nan")


def aggregate_topk_rows(rows: Sequence[Mapping[str, object]], pnr_thresholds: Sequence[float]) -> dict[str, dict[str, float]]:
    methods = sorted({str(row.get("method", "")) for row in rows if row.get("status") == "ok"})
    out: dict[str, dict[str, float]] = {}
    for method in methods:
        sub = [row for row in rows if row.get("status") == "ok" and str(row.get("method", "")) == method]
        def mean_field(field: str) -> float:
            return _mean([float(row[field]) for row in sub if field in row])

        record: dict[str, float] = {
            "n": len(sub),
            "norm_l2": _mean([float(row["top1_norm_l2"]) for row in sub]),
            "acc_at_0_1": _mean([float(row["top1_acc_at_0_1"]) for row in sub]),
            "recall": _mean([float(row["top1_recall"]) for row in sub]),
            "cosine": _mean([float(row["top1_cosine"]) for row in sub]),
            "module": _mean([float(row["top1_module"]) for row in sub]),
            "switch_precision": mean_field("top1_switch_precision"),
            "switch_recall": mean_field("top1_switch_recall"),
            "switch_f1": mean_field("top1_switch_f1"),
            "switch_accuracy": mean_field("top1_switch_accuracy"),
        }
        for threshold in pnr_thresholds:
            suffix = _format_threshold(threshold)
            for k in (1, 5, 10):
                field = f"pnr_at_{k}_t{suffix}"
                record[field] = _mean([float(row[field]) for row in sub if field in row])
        out[method] = record
    return out


def write_outputs(output_dir: Path, rows: Sequence[dict[str, object]], summary: Mapping[str, object], audit: Mapping[str, object]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "unified_topk_rows.json").write_text(json.dumps(list(rows), indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "unified_topk_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "unified_topk_audit.json").write_text(json.dumps(audit, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    fields = sorted({key for row in rows for key in row.keys()} - {"topk_candidates"})
    with (output_dir / "unified_topk_rows.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: json.dumps(row.get(field), ensure_ascii=False) if isinstance(row.get(field), (list, dict)) else row.get(field) for field in fields})


def main() -> int:
    parser = argparse.ArgumentParser(description="Unified Protocol-A top-k and PNR exporter.")
    parser.add_argument("--dataset", default=DEFAULT_DATASET)
    parser.add_argument("--split-file", default=DEFAULT_SPLIT)
    parser.add_argument("--output-dir", default=DEFAULT_OUT)
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--pnr-thresholds", type=float, nargs="+", default=[0.05, 0.10, 0.15])
    args = parser.parse_args()
    dataset = load_dataset(Path(args.dataset))
    query_indices = load_requested_query_indices(dataset, Path(args.split_file))
    rows = dump_unified_topk(dataset, query_indices, k=args.k, pnr_thresholds=args.pnr_thresholds)
    summary = aggregate_topk_rows(rows, pnr_thresholds=args.pnr_thresholds)
    audit = {"metric_impl": METRIC_IMPL, "coverage": vector_coverage(dataset, query_indices), "k": args.k, "pnr_thresholds": args.pnr_thresholds}
    write_outputs(Path(args.output_dir), rows, summary, audit)
    print(f"wrote {Path(args.output_dir) / 'unified_topk_summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
