"""
Derived analysis for Protocol-A per-query retrieval metrics.

This script keeps the canonical Protocol-A CSV as the single source of truth and
derives paper-facing diagnostics:
  - per-baseline win/loss/tie counts for TRR
  - signed-delta summaries for each metric
  - representative gain/failure cases ranked by L2 delta
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, Iterable, List, Mapping


METRICS: List[str] = ["l2", "acc@0.1", "recall", "cosine", "module"]
LOWER_IS_BETTER = {"l2"}
EPSILON = 1e-12


def read_per_query_csv(path: Path) -> Dict[str, Dict[int, dict]]:
    rows_by_method: Dict[str, Dict[int, dict]] = {}
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if int(row.get("missing", "0") or 0):
                continue
            method = row["method"].strip()
            query_idx = int(row["query_idx"])
            rows_by_method.setdefault(method, {})[query_idx] = row
    return rows_by_method


def signed_delta(trr_value: float, baseline_value: float, metric: str) -> float:
    if metric in LOWER_IS_BETTER:
        return baseline_value - trr_value
    return trr_value - baseline_value


def classify_delta(delta: float, eps: float = EPSILON) -> str:
    if delta > eps:
        return "win"
    if delta < -eps:
        return "loss"
    return "tie"


def _percentile(sorted_values: List[float], q: float) -> float:
    if not sorted_values:
        raise ValueError("Cannot compute percentiles of an empty list.")
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    position = (len(sorted_values) - 1) * q
    lower = int(position)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = position - lower
    return float(sorted_values[lower] * (1.0 - weight) + sorted_values[upper] * weight)


def summarize_metric_deltas(deltas: Iterable[float]) -> dict:
    values = sorted(float(x) for x in deltas)
    n = len(values)
    if n == 0:
        raise ValueError("Cannot summarize empty deltas.")
    wins = sum(1 for x in values if x > EPSILON)
    losses = sum(1 for x in values if x < -EPSILON)
    ties = n - wins - losses
    return {
        "n": n,
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "mean": float(sum(values) / n),
        "median": _percentile(values, 0.5),
        "p25": _percentile(values, 0.25),
        "p75": _percentile(values, 0.75),
        "min": float(values[0]),
        "max": float(values[-1]),
    }


def _case_record(query_idx: int, trr_row: Mapping[str, str], baseline_row: Mapping[str, str], delta_l2: float) -> dict:
    return {
        "query_idx": int(query_idx),
        "query_name": trr_row["query_name"],
        "trr_retrieved": trr_row["retrieved_name"],
        "baseline_retrieved": baseline_row["retrieved_name"],
        "delta_l2": float(delta_l2),
        "trr_l2": float(trr_row["l2"]),
        "baseline_l2": float(baseline_row["l2"]),
    }


def analyze_pairwise(rows_by_method: Mapping[str, Mapping[int, Mapping[str, str]]], baseline: str, *, top_k: int) -> dict:
    if "TRR" not in rows_by_method:
        raise ValueError("Expected TRR rows in Protocol-A CSV.")
    if baseline not in rows_by_method:
        raise ValueError(f"Baseline {baseline!r} not found.")

    trr_rows = rows_by_method["TRR"]
    baseline_rows = rows_by_method[baseline]
    shared_query_idx = sorted(set(trr_rows).intersection(baseline_rows))

    metric_deltas: Dict[str, List[float]] = {metric: [] for metric in METRICS}
    l2_cases: List[dict] = []

    for query_idx in shared_query_idx:
        trr_row = trr_rows[query_idx]
        baseline_row = baseline_rows[query_idx]
        for metric in METRICS:
            delta = signed_delta(float(trr_row[metric]), float(baseline_row[metric]), metric)
            metric_deltas[metric].append(delta)
        l2_cases.append(
            _case_record(
                query_idx=query_idx,
                trr_row=trr_row,
                baseline_row=baseline_row,
                delta_l2=signed_delta(float(trr_row["l2"]), float(baseline_row["l2"]), "l2"),
            )
        )

    return {
        "baseline": baseline,
        "n_shared_queries": len(shared_query_idx),
        "metric_summaries": {
            metric: summarize_metric_deltas(deltas) for metric, deltas in metric_deltas.items()
        },
        "top_gains_l2": sorted(l2_cases, key=lambda row: row["delta_l2"], reverse=True)[:top_k],
        "top_failures_l2": sorted(l2_cases, key=lambda row: row["delta_l2"])[:top_k],
    }


def analyze_protocol_a(csv_path: Path, *, top_k: int) -> dict:
    rows_by_method = read_per_query_csv(csv_path)
    if "TRR" not in rows_by_method:
        raise ValueError("Protocol-A CSV must contain TRR rows.")

    trr_rows = rows_by_method["TRR"]
    unique_query_names = len({row["query_name"] for row in trr_rows.values()})
    baselines = sorted(method for method in rows_by_method if method != "TRR")

    return {
        "input_csv": str(csv_path),
        "query_count": len(trr_rows),
        "unique_query_names": unique_query_names,
        "baselines": [analyze_pairwise(rows_by_method, baseline, top_k=top_k) for baseline in baselines],
    }


def format_markdown(report: Mapping[str, object]) -> str:
    lines: List[str] = []
    lines.append("# Protocol-A Derived Analysis")
    lines.append("")
    lines.append(f"- Input CSV: `{report['input_csv']}`")
    lines.append(f"- Paired query count (TRR rows): {int(report['query_count'])}")
    lines.append(f"- Unique `query_name` labels in TRR rows: {int(report['unique_query_names'])}")
    lines.append("- Pairing is performed by `query_idx`; one query label is reused in the CSV, so label-level uniqueness is lower than row count.")
    lines.append("")

    for baseline_report in report["baselines"]:
        baseline = baseline_report["baseline"]
        lines.append(f"## TRR vs {baseline}")
        lines.append("")
        lines.append(f"- Shared paired queries: {int(baseline_report['n_shared_queries'])}")
        lines.append("")
        lines.append("| Metric | Wins | Losses | Ties | MeanΔ | MedianΔ | P25 | P75 | Min | Max |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
        for metric in METRICS:
            summary = baseline_report["metric_summaries"][metric]
            lines.append(
                "| {metric} | {wins} | {losses} | {ties} | {mean:.4f} | {median:.4f} | {p25:.4f} | {p75:.4f} | {minv:.4f} | {maxv:.4f} |".format(
                    metric=metric,
                    wins=summary["wins"],
                    losses=summary["losses"],
                    ties=summary["ties"],
                    mean=summary["mean"],
                    median=summary["median"],
                    p25=summary["p25"],
                    p75=summary["p75"],
                    minv=summary["min"],
                    maxv=summary["max"],
                )
            )
        lines.append("")

        lines.append("### Largest TRR Gains by L2")
        lines.append("")
        lines.append("| query_idx | Query | TRR retrieved | Baseline retrieved | ΔL2 | TRR L2 | Baseline L2 |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- |")
        for row in baseline_report["top_gains_l2"]:
            lines.append(
                f"| {row['query_idx']} | {row['query_name']} | {row['trr_retrieved']} | {row['baseline_retrieved']} | {row['delta_l2']:.4f} | {row['trr_l2']:.4f} | {row['baseline_l2']:.4f} |"
            )
        lines.append("")

        lines.append("### Largest TRR Failures by L2")
        lines.append("")
        lines.append("| query_idx | Query | TRR retrieved | Baseline retrieved | ΔL2 | TRR L2 | Baseline L2 |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- |")
        for row in baseline_report["top_failures_l2"]:
            lines.append(
                f"| {row['query_idx']} | {row['query_name']} | {row['trr_retrieved']} | {row['baseline_retrieved']} | {row['delta_l2']:.4f} | {row['trr_l2']:.4f} | {row['baseline_l2']:.4f} |"
            )
        lines.append("")

    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Protocol-A per-query derived analysis artifacts.")
    parser.add_argument("--csv", required=True, help="Path to protocolA_per_query_metrics.csv")
    parser.add_argument("--out_json", required=True, help="Output JSON path")
    parser.add_argument("--out_md", required=True, help="Output Markdown path")
    parser.add_argument("--top_k", type=int, default=5, help="Number of gain/failure cases per baseline")
    args = parser.parse_args()

    report = analyze_protocol_a(Path(args.csv), top_k=int(args.top_k))

    out_json = Path(args.out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")

    out_md = Path(args.out_md)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(format_markdown(report), encoding="utf-8")


if __name__ == "__main__":
    main()
