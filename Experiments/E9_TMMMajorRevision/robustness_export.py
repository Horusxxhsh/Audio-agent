from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from Experiments.E7_HardSplit.run_hard_split_retrieval import load_dataset, load_requested_query_indices
from Experiments.E9_TMMMajorRevision.unified_protocol_export import DEFAULT_METHODS, aggregate_topk_rows, dump_unified_topk
from Experiments.E9_TMMMajorRevision.protocol_b_epr_projection import aggregate_epr_rows, epr_rows_for_methods
from Experiments.common.evaluate import Evaluator
from Experiments.common.hard_split import build_parameter_cluster_split

DEFAULT_DATASET = "Data/External_1267_211/dataset/dataset_full_vectors_1267.json"
DEFAULT_SPLIT = "Experiments/tmm/splits/tmm_external1267_audio_grouped/seed0/test.txt"
DEFAULT_OUT = "Experiments/E9_TMMMajorRevision/outputs/robustness"
CLAP_SHARED_METHODS = {"Wav2Vec": "Wav2Vec", "FeatureNN": "FeatureNN", "CLAP": "CLAP", "TRR": "TRR"}


def _has_vector(item: Mapping[str, object], key: str) -> bool:
    vectors = item.get("Vectors", {})
    vec = vectors.get(key) if isinstance(vectors, Mapping) else None
    return isinstance(vec, list) and len(vec) > 0


def available_methods(dataset: Sequence[Mapping[str, object]], query_indices: Sequence[int], methods: Mapping[str, str]) -> dict[str, str]:
    qset = {int(idx) for idx in query_indices}
    kb_indices = [idx for idx in range(len(dataset)) if idx not in qset]
    out = {}
    for method, key in methods.items():
        query_ok = any(0 <= idx < len(dataset) and _has_vector(dataset[idx], key) for idx in qset)
        kb_ok = any(_has_vector(dataset[idx], key) for idx in kb_indices)
        if query_ok and kb_ok:
            out[method] = key
    return out


def shared_subset_indices(
    dataset: Sequence[Mapping[str, object]],
    query_indices: Sequence[int],
    methods: Mapping[str, str],
    return_kb: bool = False,
) -> list[int] | tuple[list[int], list[int]]:
    qset = {int(idx) for idx in query_indices}
    query_subset = [
        int(idx)
        for idx in query_indices
        if all(0 <= int(idx) < len(dataset) and _has_vector(dataset[int(idx)], key) for key in methods.values())
    ]
    kb_subset = [
        int(idx)
        for idx in range(len(dataset))
        if idx not in qset and all(_has_vector(dataset[idx], key) for key in methods.values())
    ]
    if return_kb:
        return query_subset, kb_subset
    return query_subset


def bootstrap_mean_ci(values: Sequence[float], n_boot: int = 1000, seed: int = 42, alpha: float = 0.05) -> tuple[float, float]:
    xs = np.asarray(list(values), dtype=float)
    if xs.size == 0:
        return float("nan"), float("nan")
    if xs.size == 1:
        return float(xs[0]), float(xs[0])
    rng = np.random.default_rng(seed)
    samples = rng.choice(xs, size=(int(n_boot), xs.size), replace=True).mean(axis=1)
    low = float(np.quantile(samples, alpha / 2.0))
    high = float(np.quantile(samples, 1.0 - alpha / 2.0))
    return round(low, 10), round(high, 10)


def _numeric_summary(rows: Sequence[Mapping[str, object]]) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for method in sorted({str(row.get("method", "")) for row in rows if row.get("status") == "ok"}):
        values = [float(row["top1_norm_l2"]) for row in rows if row.get("status") == "ok" and str(row.get("method", "")) == method]
        low, high = bootstrap_mean_ci(values)
        out[method] = {"n": len(values), "norm_l2": float(np.mean(values)) if values else math.nan, "norm_l2_ci_low": low, "norm_l2_ci_high": high}
    return out


def run_shared_subset(dataset: Sequence[Mapping[str, object]], query_indices: Sequence[int], methods: Mapping[str, str]) -> dict[str, object]:
    query_subset, kb_subset = shared_subset_indices(dataset, query_indices, methods, return_kb=True)
    rows = dump_unified_topk(dataset, query_subset, kb_indices=kb_subset, methods=methods, k=10, pnr_thresholds=[0.10])
    top1_summary = aggregate_topk_rows(rows, pnr_thresholds=[0.10])
    epr_rows = epr_rows_for_methods(rows, dataset, source_methods=list(methods.keys()), k=5, temperature=0.05)
    return {
        "query_count": len(query_subset),
        "kb_count": len(kb_subset),
        "top1_summary": top1_summary,
        "epr_summary": aggregate_epr_rows(epr_rows),
        "summary": _numeric_summary(rows),
    }


def _threshold_key(threshold: float) -> str:
    return f"{float(threshold):.3f}"


def _near_duplicate_kb_indices(
    dataset: Sequence[Mapping[str, object]],
    query_indices: Sequence[int],
    threshold: float,
) -> list[int]:
    qset = {int(idx) for idx in query_indices}
    kb_indices = [idx for idx in range(len(dataset)) if idx not in qset]
    if float(threshold) <= 0:
        return kb_indices
    evaluator = Evaluator(normalize=True)
    query_params = [dataset[idx].get("Parameters", {}) for idx in qset]
    kept = []
    for kb_idx in kb_indices:
        params = dataset[kb_idx].get("Parameters", {})
        if all(evaluator.compute_parameter_distance(params, query_param) > float(threshold) for query_param in query_params):
            kept.append(kb_idx)
    return kept


def near_duplicate_sensitivity(
    dataset: Sequence[Mapping[str, object]],
    query_indices: Sequence[int],
    methods: Mapping[str, str],
    thresholds: Sequence[float],
    k: int = 10,
) -> dict[str, dict[str, dict[str, float]]]:
    out: dict[str, dict[str, dict[str, float]]] = {}
    for threshold in thresholds:
        kb_indices = _near_duplicate_kb_indices(dataset, query_indices, float(threshold))
        rows = dump_unified_topk(dataset, query_indices, kb_indices=kb_indices, methods=methods, k=k, pnr_thresholds=[0.10])
        summary = aggregate_topk_rows(rows, pnr_thresholds=[0.10])
        enriched: dict[str, dict[str, float]] = {}
        for method, record in summary.items():
            enriched[method] = dict(record)
            enriched[method]["kb_size"] = len(kb_indices)
        out[_threshold_key(float(threshold))] = enriched
    return out


def hard_split_sweep(
    dataset: Sequence[Mapping[str, object]],
    query_indices: Sequence[int],
    methods: Mapping[str, str],
    thresholds: Sequence[float],
    n_boot: int = 1000,
    seed: int = 42,
) -> dict[str, object]:
    out: dict[str, object] = {}
    for threshold in thresholds:
        split = build_parameter_cluster_split(dataset, query_indices, float(threshold))
        test_indices = [int(idx) for idx in split["test_indices"]]
        kb_indices = [int(idx) for idx in split["kb_indices"]]
        rows = dump_unified_topk(dataset, test_indices, kb_indices=kb_indices, methods=methods, k=10, pnr_thresholds=[0.10])
        summary = _numeric_summary(rows)
        for method, record in summary.items():
            values = [
                float(row["top1_norm_l2"])
                for row in rows
                if row.get("status") == "ok" and str(row.get("method", "")) == method
            ]
            low, high = bootstrap_mean_ci(values, n_boot=n_boot, seed=seed)
            record["norm_l2_ci_low"] = low
            record["norm_l2_ci_high"] = high
        out[_threshold_key(float(threshold))] = {
            "query_count": len(test_indices),
            "kb_count": len(kb_indices),
            "cluster_count": int(split["cluster_count"]),
            "removed_query_count": int(split["removed_query_count"]),
            "summary": summary,
        }
    return out


def _write_json_csv(base: Path, stem: str, payload: object) -> None:
    base.mkdir(parents=True, exist_ok=True)
    (base / f"{stem}.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    rows = []
    if isinstance(payload, Mapping):
        for group_key, group_value in payload.items():
            if isinstance(group_value, Mapping):
                for method, record in group_value.items():
                    if isinstance(record, Mapping) and "norm_l2" in record:
                        rows.append({"group": group_key, "method": method, **record})
                    elif isinstance(record, Mapping) and "summary" in record:
                        for method2, record2 in record["summary"].items():
                            rows.append({"group": group_key, "method": method2, **record2})
    if rows:
        fields = sorted({key for row in rows for key in row.keys()})
        with (base / f"{stem}.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)


def write_robustness_placeholder(dataset_path: Path, split_file: Path, output_dir: Path, methods: Mapping[str, str] | None = None) -> dict[str, object]:
    dataset = load_dataset(dataset_path)
    query_indices = load_requested_query_indices(dataset, split_file)
    methods = methods or available_methods(dataset, query_indices, DEFAULT_METHODS)
    shared = run_shared_subset(dataset, query_indices, methods)
    near_dup = near_duplicate_sensitivity(dataset, query_indices, methods, thresholds=[0.0, 0.005, 0.01, 0.02, 0.05], k=10)
    hard = hard_split_sweep(dataset, query_indices, methods, thresholds=[0.01, 0.02, 0.05], n_boot=1000, seed=42)
    payload = {
        "status": "ok",
        "note": "Robustness rows use the unified Protocol-A evaluator. PaSST/PANNs are included only if vectors are present in the dataset.",
        "near_duplicate": near_dup,
        "hard_split_sweep": hard,
        "shared_subset": shared,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "robustness_coverage_limited.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    _write_json_csv(output_dir / "near_duplicate_unified", "near_duplicate_summary", near_dup)
    _write_json_csv(output_dir / "shared_subset", "shared_subset_summary", {"shared": shared.get("summary", {})})
    _write_json_csv(output_dir / "hard_split_sweep", "hard_split_sweep_summary", hard)
    audit = {
        "dataset_path": str(dataset_path),
        "split_file": str(split_file),
        "query_count": len(query_indices),
        "methods": methods,
        "threshold_definition": "threshold=0.000 is no-filter canonical; threshold>0 removes KB candidates with normalized parameter RMSE <= threshold to any Protocol-A query.",
        "normalization": "Evaluator(normalize=True)",
        "random_seed": 42,
    }
    (output_dir / "robustness_audit.json").write_text(json.dumps(audit, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Robustness evidence exporter for TMM major revision.")
    parser.add_argument("--dataset", default=DEFAULT_DATASET)
    parser.add_argument("--split-file", default=DEFAULT_SPLIT)
    parser.add_argument("--output-dir", default=DEFAULT_OUT)
    args = parser.parse_args()
    payload = write_robustness_placeholder(Path(args.dataset), Path(args.split_file), Path(args.output_dir))
    print(f"wrote robustness payload with status={payload['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
