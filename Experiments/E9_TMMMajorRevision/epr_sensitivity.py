from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from Experiments.E8_ExecutableNeighborhood.epr_projection import (
    _candidate_params,
    _candidate_score,
    _evaluate_projection,
    kb_items_from_topk_rows,
    observed_numeric_ranges,
    softmax_weights,
    weighted_projection,
)
from Experiments.E9_TMMMajorRevision.prepare_sota_vectors import load_dataset
from Experiments.E9_TMMMajorRevision.protocol_b_epr_projection import load_topk_rows
from Experiments.E9_TMMMajorRevision.validity_audit import switch_metrics

DEFAULT_DATASET = "Data/External_1267_211/dataset/dataset_full_vectors_1267.json"
DEFAULT_TOPK = "Experiments/E9_TMMMajorRevision/outputs/unified_protocol/unified_topk_rows.json"
DEFAULT_OUT = "Experiments/E9_TMMMajorRevision/outputs/epr_sensitivity"


def _weights(scores: Sequence[float], mode: str, temperature: float) -> list[float]:
    if mode == "softmax":
        return softmax_weights(scores, temperature=float(temperature))
    if mode == "uniform":
        if not scores:
            return []
        return [1.0 / len(scores)] * len(scores)
    raise ValueError(f"unsupported weighting mode: {mode}")


def epr_sensitivity_rows(
    topk_rows: Sequence[Mapping[str, object]],
    dataset: Sequence[dict],
    source_method: str = "TRR",
    ks: Sequence[int] = (1, 3, 5, 10),
    temperatures: Sequence[float] = (0.01, 0.05, 0.10),
    weighting_modes: Sequence[str] = ("softmax", "uniform"),
) -> list[dict[str, object]]:
    kb_items = kb_items_from_topk_rows(dataset, topk_rows)
    ranges = observed_numeric_ranges(kb_items)
    source_rows = [
        row
        for row in topk_rows
        if row.get("status") == "ok" and str(row.get("method", "")) == str(source_method)
    ]
    rows: list[dict[str, object]] = []
    for mode in weighting_modes:
        for k in ks:
            for temperature in temperatures:
                per_query = []
                for row in source_rows:
                    candidates = row.get("topk_candidates", [])
                    if not isinstance(candidates, list):
                        continue
                    selected = [candidate for candidate in candidates[: int(k)] if isinstance(candidate, Mapping)]
                    if not selected:
                        continue
                    scores = [_candidate_score(candidate) for candidate in selected]
                    weights = _weights(scores, mode=mode, temperature=float(temperature))
                    candidate_params = [_candidate_params(candidate) for candidate in selected]
                    pred_params, provenance = weighted_projection(candidate_params, weights, ranges)
                    query_idx = int(row["query_idx"])
                    gt_params = dataset[query_idx].get("Parameters", {})
                    metrics = _evaluate_projection(pred_params, gt_params if isinstance(gt_params, Mapping) else {})
                    metrics.update(switch_metrics(pred_params, gt_params if isinstance(gt_params, Mapping) else {}))
                    per_query.append((metrics, provenance))
                if not per_query:
                    continue
                rows.append(
                    {
                        "source_method": str(source_method),
                        "k": int(k),
                        "temperature": float(temperature),
                        "weighting": mode,
                        "n": len(per_query),
                        "norm_l2": sum(float(m["norm_l2"]) for m, _ in per_query) / len(per_query),
                        "recall": sum(float(m["recall"]) for m, _ in per_query) / len(per_query),
                        "cosine": sum(float(m["cosine"]) for m, _ in per_query) / len(per_query),
                        "legacy_module_jaccard": sum(float(m["legacy_module_jaccard"]) for m, _ in per_query) / len(per_query),
                        "switch_f1": sum(float(m["switch_f1"]) for m, _ in per_query) / len(per_query),
                        "switch_accuracy": sum(float(m["switch_accuracy"]) for m, _ in per_query) / len(per_query),
                        "provenance_effective_exemplars": sum(float(p["effective_exemplars"]) for _, p in per_query) / len(per_query),
                        "provenance_max_weight": sum(float(p["max_weight"]) for _, p in per_query) / len(per_query),
                    }
                )
    return rows


def write_outputs(output_dir: Path, rows: Sequence[dict[str, object]]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "epr_sensitivity_summary.json").write_text(json.dumps(list(rows), indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    fields = sorted({key for row in rows for key in row.keys()})
    with (output_dir / "epr_sensitivity_summary.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Protocol-B EPR sensitivity over K, temperature, and weighting.")
    parser.add_argument("--dataset", default=DEFAULT_DATASET)
    parser.add_argument("--topk-json", default=DEFAULT_TOPK)
    parser.add_argument("--output-dir", default=DEFAULT_OUT)
    parser.add_argument("--source-method", default="TRR")
    parser.add_argument("--ks", type=int, nargs="+", default=[1, 3, 5, 10])
    parser.add_argument("--temperatures", type=float, nargs="+", default=[0.01, 0.05, 0.10])
    parser.add_argument("--weighting-modes", nargs="+", default=["softmax", "uniform"])
    args = parser.parse_args()
    dataset = load_dataset(Path(args.dataset))
    topk_rows = load_topk_rows(Path(args.topk_json))
    rows = epr_sensitivity_rows(topk_rows, dataset, args.source_method, args.ks, args.temperatures, args.weighting_modes)
    write_outputs(Path(args.output_dir), rows)
    print(f"wrote {Path(args.output_dir) / 'epr_sensitivity_summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
