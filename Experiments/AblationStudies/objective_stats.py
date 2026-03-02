"""
Objective evaluation statistics for Protocol-A (per-query metrics CSV).

This script adds statistical rigor (CIs + paired permutation tests) without
changing any underlying experimental results.

Input:
  - per-query CSV dumped by direct_retrieval_comparison.py (--dump_csv)

Output:
  - JSON summary (machine-readable)
  - Markdown report (paper-ready)
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np


METRICS: List[str] = ["l2", "acc@0.1", "recall", "cosine", "module"]
LOWER_IS_BETTER = {"l2"}


@dataclass(frozen=True)
class MethodSeries:
    query_idx: np.ndarray  # shape (n,)
    values: Dict[str, np.ndarray]  # metric -> shape (n,)


def _read_per_query_csv(path: Path) -> Dict[str, MethodSeries]:
    rows: List[dict] = []
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(row)

    # (method, query_idx) -> metric dict
    table: Dict[Tuple[str, int], dict] = {}
    for r in rows:
        method = r["method"].strip()
        qidx = int(r["query_idx"])
        missing = int(r.get("missing", "0") or 0)
        if missing:
            # Skip missing retrievals for stats (should be 0 for Protocol-A).
            continue
        table[(method, qidx)] = r

    methods = sorted({m for (m, _) in table.keys()})
    query_idx = np.array(sorted({q for (_, q) in table.keys()}), dtype=int)

    by_method: Dict[str, MethodSeries] = {}
    for m in methods:
        vals: Dict[str, List[float]] = {k: [] for k in METRICS}
        missing_q = []
        for q in query_idx:
            r = table.get((m, int(q)))
            if r is None:
                missing_q.append(int(q))
                continue
            for k in METRICS:
                vals[k].append(float(r[k]))
        if missing_q:
            raise ValueError(f"Missing rows for method={m}: query_idx={missing_q[:10]} (count={len(missing_q)})")
        by_method[m] = MethodSeries(
            query_idx=query_idx,
            values={k: np.asarray(vals[k], dtype=float) for k in METRICS},
        )

    return by_method


def _bootstrap_ci_mean(x: np.ndarray, *, n_boot: int, seed: int, alpha: float) -> Tuple[float, float]:
    rng = np.random.default_rng(int(seed))
    n = int(x.shape[0])
    # (n_boot, n) resample indices
    idx = rng.integers(0, n, size=(int(n_boot), n))
    samples = x[idx].mean(axis=1)
    lo = float(np.quantile(samples, alpha / 2.0))
    hi = float(np.quantile(samples, 1.0 - alpha / 2.0))
    return lo, hi


def _bootstrap_ci_mean_diff(
    a: np.ndarray, b: np.ndarray, *, n_boot: int, seed: int, alpha: float
) -> Tuple[float, float]:
    if a.shape != b.shape:
        raise ValueError("a and b must have same shape for paired bootstrap.")
    rng = np.random.default_rng(int(seed))
    n = int(a.shape[0])
    idx = rng.integers(0, n, size=(int(n_boot), n))
    d = (a - b)
    samples = d[idx].mean(axis=1)
    lo = float(np.quantile(samples, alpha / 2.0))
    hi = float(np.quantile(samples, 1.0 - alpha / 2.0))
    return lo, hi


def _paired_permutation_pvalue(d: np.ndarray, *, n_perm: int, seed: int) -> float:
    """
    Two-sided paired permutation test via random sign-flipping.
    """
    rng = np.random.default_rng(int(seed))
    n = int(d.shape[0])
    obs = float(d.mean())
    signs = rng.choice(np.array([-1.0, 1.0], dtype=float), size=(int(n_perm), n), replace=True)
    perm_means = (signs * d).mean(axis=1)
    p = (float(np.sum(np.abs(perm_means) >= abs(obs))) + 1.0) / (float(n_perm) + 1.0)
    return float(p)


def _holm_bonferroni(pvals: List[float]) -> List[float]:
    """
    Holm-Bonferroni adjusted p-values (step-down), preserving original order.
    """
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    adj = [0.0] * m
    prev = 0.0
    for rank, i in enumerate(order):
        p_adj = (m - rank) * pvals[i]
        p_adj = min(1.0, max(p_adj, prev))
        adj[i] = p_adj
        prev = p_adj
    return adj


def main() -> None:
    ap = argparse.ArgumentParser(description="Compute CIs and paired permutation tests from per-query CSV.")
    ap.add_argument("--csv", type=str, required=True, help="Per-query CSV path (dump_csv output).")
    ap.add_argument("--out_json", type=str, required=True, help="Output JSON path.")
    ap.add_argument("--out_md", type=str, required=True, help="Output Markdown report path.")
    ap.add_argument("--n_boot", type=int, default=10000, help="Bootstrap resamples (default: 10000).")
    ap.add_argument("--n_perm", type=int, default=20000, help="Permutation samples (default: 20000).")
    ap.add_argument("--seed", type=int, default=42, help="RNG seed (default: 42).")
    args = ap.parse_args()

    csv_path = Path(args.csv)
    by_method = _read_per_query_csv(csv_path)

    methods = sorted(by_method.keys())
    n = int(next(iter(by_method.values())).query_idx.shape[0])

    # Method-level summaries
    method_summary = {}
    for m in methods:
        ms = by_method[m]
        method_summary[m] = {"n": n, "metrics": {}}
        for k in METRICS:
            x = ms.values[k]
            mean = float(x.mean())
            std = float(x.std(ddof=1)) if n > 1 else 0.0
            lo, hi = _bootstrap_ci_mean(x, n_boot=args.n_boot, seed=args.seed, alpha=0.05)
            method_summary[m]["metrics"][k] = {
                "mean": mean,
                "std": std,
                "ci95": [lo, hi],
            }

    # Pairwise comparisons vs TRR
    if "TRR" not in by_method:
        raise ValueError("Expected a method named 'TRR' in the CSV.")
    trr = by_method["TRR"]

    comparisons = []
    raw_pvals = []
    comp_keys = []
    for baseline in methods:
        if baseline == "TRR":
            continue
        base = by_method[baseline]
        for k in METRICS:
            a = trr.values[k]
            b = base.values[k]
            # Define signed difference so that positive = TRR better.
            if k in LOWER_IS_BETTER:
                # Lower is better => improvement means baseline - TRR > 0
                d = (b - a)
            else:
                d = (a - b)
            mean_diff = float(d.mean())
            lo, hi = _bootstrap_ci_mean_diff(d, np.zeros_like(d), n_boot=args.n_boot, seed=args.seed, alpha=0.05)
            p = _paired_permutation_pvalue(d, n_perm=args.n_perm, seed=args.seed)
            comparisons.append(
                {
                    "baseline": baseline,
                    "metric": k,
                    "n": n,
                    "mean_diff_signed": mean_diff,
                    "ci95_signed": [lo, hi],
                    "p_perm_two_sided": p,
                }
            )
            raw_pvals.append(p)
            comp_keys.append((baseline, k))

    adj_pvals = _holm_bonferroni(raw_pvals)
    for rec, p_adj in zip(comparisons, adj_pvals):
        rec["p_holm"] = float(p_adj)

    out = {
        "input_csv": str(csv_path),
        "n_queries": n,
        "methods": methods,
        "metrics": METRICS,
        "method_summary": method_summary,
        "comparisons_vs_trr": comparisons,
    }

    out_json = Path(args.out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(out, indent=2, sort_keys=True), encoding="utf-8")

    # Markdown report
    out_md = Path(args.out_md)
    out_md.parent.mkdir(parents=True, exist_ok=True)

    def fmt_ci(ci):
        return f"[{ci[0]:.4f}, {ci[1]:.4f}]"

    lines = []
    lines.append("# Protocol-A Objective Metrics: Confidence Intervals and Significance")
    lines.append("")
    lines.append(f"- Input CSV: `{csv_path}`")
    lines.append(f"- Queries: n={n} (paired across methods by `query_idx`)")  # avoid ambiguity on duplicate names
    lines.append(f"- Bootstrap resamples: {int(args.n_boot)} (seed={int(args.seed)})")
    lines.append(f"- Paired permutation samples: {int(args.n_perm)} (seed={int(args.seed)})")
    lines.append("")

    lines.append("## Per-Method 95% CIs (Mean Over Queries)")
    lines.append("")
    header = ["Method"] + [f"{k} (mean, 95% CI)" for k in METRICS]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("| " + " | ".join(["---"] * len(header)) + " |")
    for m in methods:
        row = [m]
        for k in METRICS:
            rec = method_summary[m]["metrics"][k]
            row.append(f"{rec['mean']:.4f}, {fmt_ci(rec['ci95'])}")
        lines.append("| " + " | ".join(row) + " |")

    lines.append("")
    lines.append("## TRR vs Baselines (Signed Improvements)")
    lines.append("")
    lines.append("Signed improvement is defined as:")
    lines.append("- For `l2`: `baseline - TRR` (positive means TRR reduces error).")
    lines.append("- For other metrics: `TRR - baseline` (positive means TRR increases the score).")
    lines.append("")

    header = ["Baseline", "Metric", "Mean Δ", "95% CI", "p (perm, 2-sided)", "p (Holm)"]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("| " + " | ".join(["---"] * len(header)) + " |")
    for rec in comparisons:
        lines.append(
            "| "
            + " | ".join(
                [
                    rec["baseline"],
                    rec["metric"],
                    f"{rec['mean_diff_signed']:.4f}",
                    fmt_ci(rec["ci95_signed"]),
                    f"{rec['p_perm_two_sided']:.3g}",
                    f"{rec['p_holm']:.3g}",
                ]
            )
            + " |"
        )

    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote JSON: {out_json}")
    print(f"Wrote MD:   {out_md}")


if __name__ == "__main__":
    main()
