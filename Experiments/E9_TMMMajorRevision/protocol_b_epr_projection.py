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

from Experiments.E8_ExecutableNeighborhood.epr_projection import (
    METRIC_IMPL as EPR_METRIC_IMPL,
    kb_items_from_topk_rows,
    observed_numeric_ranges,
    projection_record,
)
from Experiments.E9_TMMMajorRevision.prepare_sota_vectors import load_dataset
from Experiments.E9_TMMMajorRevision.validity_audit import switch_metrics

DEFAULT_DATASET = "Data/External_1267_211/dataset/dataset_full_vectors_1267.json"
DEFAULT_TOPK = "Experiments/E9_TMMMajorRevision/outputs/unified_protocol/unified_topk_rows.json"
DEFAULT_OUT = "Experiments/E9_TMMMajorRevision/outputs/protocol_b_epr"
DEFAULT_SOURCE_METHODS = ["Wav2Vec", "FeatureNN", "CLAP", "PaSST", "PANNs", "TRR"]


def load_topk_rows(path: Path) -> list[dict[str, object]]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise ValueError(f"top-k rows must be a JSON array: {path}")
    return rows


def epr_rows_for_methods(
    topk_rows: Sequence[Mapping[str, object]],
    dataset: Sequence[dict],
    source_methods: Sequence[str],
    k: int,
    temperature: float,
) -> list[dict[str, object]]:
    kb_items = kb_items_from_topk_rows(dataset, topk_rows)
    ranges = observed_numeric_ranges(kb_items)
    wanted = {str(method) for method in source_methods}
    rows: list[dict[str, object]] = []
    for row in topk_rows:
        if row.get("status") != "ok" or str(row.get("method", "")) not in wanted:
            continue
        projected = projection_record(row, dataset, ranges, k=int(k), temperature=float(temperature))
        if projected.get("status") == "ok":
            query_idx = int(projected["query_idx"])
            pred_params = projected.get("prediction_parameters", {})
            gt_params = dataset[query_idx].get("Parameters", {})
            if isinstance(pred_params, Mapping) and isinstance(gt_params, Mapping):
                projected.update(switch_metrics(pred_params, gt_params))
        rows.append(projected)
    return rows


def _mean(values: Sequence[float]) -> float:
    return float(np.mean(values)) if values else float("nan")


def aggregate_epr_rows(rows: Sequence[Mapping[str, object]]) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for source in sorted({str(row.get("source_method", "")) for row in rows if row.get("status") == "ok"}):
        sub = [row for row in rows if row.get("status") == "ok" and str(row.get("source_method", "")) == source]
        out[source] = {
            "n": len(sub),
            "norm_l2": _mean([float(row["norm_l2"]) for row in sub]),
            "acc_at_0_1": _mean([float(row["acc_at_0_1"]) for row in sub]),
            "recall": _mean([float(row["recall"]) for row in sub]),
            "cosine": _mean([float(row["cosine"]) for row in sub]),
            "module": _mean([float(row["module"]) for row in sub]),
            "switch_precision": _mean([float(row["switch_precision"]) for row in sub if "switch_precision" in row]),
            "switch_recall": _mean([float(row["switch_recall"]) for row in sub if "switch_recall" in row]),
            "switch_f1": _mean([float(row["switch_f1"]) for row in sub if "switch_f1" in row]),
            "switch_accuracy": _mean([float(row["switch_accuracy"]) for row in sub if "switch_accuracy" in row]),
            "edit_cost": _mean([float(row["edit_cost"]) for row in sub]),
            "provenance_max_weight": _mean([float(row["provenance_max_weight"]) for row in sub]),
            "provenance_effective_exemplars": _mean([float(row["provenance_effective_exemplars"]) for row in sub]),
        }
    return out


def write_outputs(output_dir: Path, rows: Sequence[dict[str, object]], summary: Mapping[str, object], audit: Mapping[str, object]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "protocol_b_epr_rows.json").write_text(json.dumps(list(rows), indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "protocol_b_epr_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "protocol_b_epr_audit.json").write_text(json.dumps(audit, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    fields = sorted({key for row in rows for key in row.keys()} - {"prediction_parameters"})
    with (output_dir / "protocol_b_epr_rows.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: json.dumps(row.get(field), ensure_ascii=False) if isinstance(row.get(field), (list, dict)) else row.get(field) for field in fields})


def main() -> int:
    parser = argparse.ArgumentParser(description="Protocol-B EPR projection for each retrieval prior.")
    parser.add_argument("--dataset", default=DEFAULT_DATASET)
    parser.add_argument("--topk-json", default=DEFAULT_TOPK)
    parser.add_argument("--output-dir", default=DEFAULT_OUT)
    parser.add_argument("--methods", nargs="+", default=DEFAULT_SOURCE_METHODS)
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--temperature", type=float, default=0.05)
    args = parser.parse_args()
    dataset = load_dataset(Path(args.dataset))
    topk_rows = load_topk_rows(Path(args.topk_json))
    rows = epr_rows_for_methods(topk_rows, dataset, args.methods, k=args.k, temperature=args.temperature)
    summary = aggregate_epr_rows(rows)
    audit = {"metric_impl": EPR_METRIC_IMPL, "k": args.k, "temperature": args.temperature, "source_methods": args.methods}
    write_outputs(Path(args.output_dir), rows, summary, audit)
    print(f"wrote {Path(args.output_dir) / 'protocol_b_epr_summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
