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
    kb_items_from_topk_rows,
    observed_numeric_ranges,
    project_to_observed_ranges,
    softmax_weights,
    enforce_mutually_exclusive_module_states,
)
from Experiments.common.parameter_space import blend_parameter_dicts
from Experiments.E9_TMMMajorRevision.prepare_sota_vectors import load_dataset
from Experiments.E9_TMMMajorRevision.protocol_b_epr_projection import load_topk_rows
from Experiments.E9_TMMMajorRevision.validity_audit import epr_validity_record

DEFAULT_DATASET = "Data/External_1267_211/dataset/dataset_full_vectors_1267.json"
DEFAULT_TOPK = "Experiments/E9_TMMMajorRevision/outputs/unified_protocol/unified_topk_rows.json"
DEFAULT_OUT = "Experiments/E9_TMMMajorRevision/outputs/validity_audit"


def validity_rows(
    topk_rows: Sequence[Mapping[str, object]],
    dataset: Sequence[dict],
    source_methods: Sequence[str],
    k: int = 5,
    temperature: float = 0.05,
) -> list[dict[str, object]]:
    kb_items = kb_items_from_topk_rows(dataset, topk_rows)
    ranges = observed_numeric_ranges(kb_items)
    wanted = {str(method) for method in source_methods}
    out = []
    for row in topk_rows:
        if row.get("status") != "ok" or str(row.get("method", "")) not in wanted:
            continue
        candidates = row.get("topk_candidates", [])
        if not isinstance(candidates, list):
            continue
        selected = [candidate for candidate in candidates[: int(k)] if isinstance(candidate, Mapping)]
        if not selected:
            continue
        scores = [_candidate_score(candidate) for candidate in selected]
        weights = softmax_weights(scores, temperature=float(temperature))
        candidate_params = [_candidate_params(candidate) for candidate in selected]
        pre = blend_parameter_dicts(candidate_params, weights)
        range_projected = project_to_observed_ranges(pre, ranges)
        post = enforce_mutually_exclusive_module_states(range_projected, candidate_params, weights)
        record = epr_validity_record(pre, post, ranges)
        out.append(
            {
                "source_method": str(row.get("method", "")),
                "query_idx": int(row["query_idx"]),
                "query_name": str(row.get("query_name", "")),
                "k": int(k),
                "temperature": float(temperature),
                **record,
            }
        )
    return out


def summarize_validity(rows: Sequence[Mapping[str, object]]) -> dict[str, dict[str, float]]:
    out = {}
    for method in sorted({str(row.get("source_method", "")) for row in rows}):
        sub = [row for row in rows if str(row.get("source_method", "")) == method]
        n = len(sub)
        if not n:
            continue
        out[method] = {
            "n": n,
            "validity_rate": sum(1 for row in sub if bool(row.get("post_valid"))) / n,
            "pre_validity_rate": sum(1 for row in sub if bool(row.get("pre_valid"))) / n,
            "range_repair_rate": sum(1 for row in sub if bool(row.get("range_repaired"))) / n,
            "switch_repair_rate": sum(1 for row in sub if bool(row.get("switch_repaired"))) / n,
            "repair_rate": sum(1 for row in sub if bool(row.get("range_repaired")) or bool(row.get("switch_repaired"))) / n,
        }
    return out


def write_outputs(output_dir: Path, rows: Sequence[dict[str, object]], summary: Mapping[str, object], audit: Mapping[str, object]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "validity_rows.json").write_text(json.dumps(list(rows), indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "validity_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "validity_audit.json").write_text(json.dumps(audit, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    fields = sorted({key for row in rows for key in row.keys()})
    with (output_dir / "validity_rows.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Protocol-B EPR validity and repair rates.")
    parser.add_argument("--dataset", default=DEFAULT_DATASET)
    parser.add_argument("--topk-json", default=DEFAULT_TOPK)
    parser.add_argument("--output-dir", default=DEFAULT_OUT)
    parser.add_argument("--methods", nargs="+", default=["Wav2Vec", "FeatureNN", "CLAP", "PaSST", "TRR"])
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--temperature", type=float, default=0.05)
    args = parser.parse_args()
    dataset = load_dataset(Path(args.dataset))
    topk_rows = load_topk_rows(Path(args.topk_json))
    rows = validity_rows(topk_rows, dataset, args.methods, k=args.k, temperature=args.temperature)
    summary = summarize_validity(rows)
    audit = {"k": args.k, "temperature": args.temperature, "methods": args.methods}
    write_outputs(Path(args.output_dir), rows, summary, audit)
    print(f"wrote {Path(args.output_dir) / 'validity_summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
