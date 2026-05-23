"""
Layer-5 Gram vs mean-pool confound analysis (CR-1).

Reads existing P0 TRR mechanism ablation results and produces a formal
statistical comparison that answers: "Does TRR's advantage come from the
Gram matrix itself, or from selecting layer 5?"

Key confound:
- gram_l5_d64 improves over mean_pool_l5 (layer 5 only), but
  gram_l456_d64 is nearly identical to mean_pool_l456 (multi-layer).

This script does NOT re-run experiments. It reads existing CSV results
and performs:
  1. Per-layer mean-pool vs Gram comparison
  2. Delta computation (Gram improvement)
  3. Wilcoxon signed-rank tests on per-query norm_l2 values
  4. Bootstrap 95% confidence intervals
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
from scipy import stats


@dataclass
class LayerAblationResult:
    """Single row of the Layer-5 confound ablation output."""
    layer: List[int]          # e.g. [5], [4], [4, 5, 6]
    method: str               # "mean_pool" | "gram"
    project_dim: int         # 0 for mean_pool, 64 for Gram
    norm_l2_mean: float
    norm_l2_ci_lower: float  # bootstrap 95% CI
    norm_l2_ci_upper: float
    improvement_vs_mean: float  # positive = Gram better (mean_pool_L2 - gram_L2)
    wilcoxon_p: float       # Gram vs mean-pool at same layer (NaN if unpaired)
    n_queries: int          # must be 204


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_summary(summary_path: str) -> Dict[str, dict]:
    """Load the summary CSV into a dict keyed by variant name."""
    result: Dict[str, dict] = {}
    with open(summary_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            result[row["variant"]] = row
    return result


def load_per_query(per_query_path: str) -> Dict[str, List[float]]:
    """Load per-query norm_l2 values keyed by variant name."""
    result: Dict[str, List[float]] = {}
    with open(per_query_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            result.setdefault(row["variant"], []).append(float(row["norm_l2"]))
    return result


# ---------------------------------------------------------------------------
# Statistical helpers
# ---------------------------------------------------------------------------

def bootstrap_ci(values: List[float], n_bootstrap: int = 10000,
                 seed: int = 42, ci: float = 0.95) -> Tuple[float, float]:
    """Compute bootstrap confidence interval for the mean."""
    rng = np.random.RandomState(seed)
    n = len(values)
    means = np.empty(n_bootstrap)
    for i in range(n_bootstrap):
        sample = rng.choice(values, size=n, replace=True)
        means[i] = sample.mean()
    alpha = 1 - ci
    lower = np.percentile(means, 100 * alpha / 2)
    upper = np.percentile(means, 100 * (1 - alpha / 2))
    return float(lower), float(upper)


def wilcoxon_signed_rank(x: List[float], y: List[float]) -> float:
    """
    Two-sided Wilcoxon signed-rank test.

    x = mean_pool norm_l2, y = gram norm_l2.
    Returns p-value. NaN if lengths differ.
    """
    if len(x) != len(y):
        return float("nan")
    try:
        _, p = stats.wilcoxon(np.array(x), np.array(y))
        return float(p)
    except Exception:
        return float("nan")


# ---------------------------------------------------------------------------
# Confound mapping: which variants form a comparison pair?
# ---------------------------------------------------------------------------

# Pairs where both mean-pool and Gram cover the same layer set.
# Format: (layer_list, mean_pool_variant, gram_variant, project_dim)
COMPARISON_PAIRS: List[Tuple[List[int], str, str, int]] = [
    ([5], "mean_pool_l5", "gram_l5_d64", 64),
    ([4, 5, 6], "mean_pool_l456", "gram_l456_d64", 64),
]

# Gram-only variants (no mean-pool counterpart at the same layer set)
GRAM_ONLY: List[Tuple[List[int], str, int]] = [
    ([4], "gram_l4_d64", 64),
    ([6], "gram_l6_d64", 64),
]


def build_results(summary: Dict[str, dict],
                  per_query: Dict[str, List[float]],
                  n_bootstrap: int = 10000) -> List[LayerAblationResult]:
    """Build the full list of LayerAblationResult objects."""
    results: List[LayerAblationResult] = []

    # Track all variants processed to avoid duplicates
    processed: set = set()

    # --- Paired comparisons (mean_pool + Gram at same layer set) ---
    for layers, mp_variant, gr_variant, proj_dim in COMPARISON_PAIRS:
        # Mean-pool result
        mp_row = summary[mp_variant]
        mp_mean = float(mp_row["norm_l2_mean"])
        mp_vals = per_query[mp_variant]
        mp_ci = bootstrap_ci(mp_vals, n_bootstrap)
        n = len(mp_vals)

        # Gram result
        gr_row = summary[gr_variant]
        gr_mean = float(gr_row["norm_l2_mean"])
        gr_vals = per_query[gr_variant]
        gr_ci = bootstrap_ci(gr_vals, n_bootstrap)

        # Delta: positive = Gram better (lower L2 distance)
        delta = mp_mean - gr_mean

        # Wilcoxon: paired on 204 queries
        p_val = wilcoxon_signed_rank(mp_vals, gr_vals)

        results.append(LayerAblationResult(
            layer=layers,
            method="mean_pool",
            project_dim=0,
            norm_l2_mean=mp_mean,
            norm_l2_ci_lower=mp_ci[0],
            norm_l2_ci_upper=mp_ci[1],
            improvement_vs_mean=0.0,  # baseline
            wilcoxon_p=float("nan"),  # not applicable for baseline
            n_queries=n,
        ))
        results.append(LayerAblationResult(
            layer=layers,
            method="gram",
            project_dim=proj_dim,
            norm_l2_mean=gr_mean,
            norm_l2_ci_lower=gr_ci[0],
            norm_l2_ci_upper=gr_ci[1],
            improvement_vs_mean=delta,
            wilcoxon_p=p_val,
            n_queries=n,
        ))
        processed.add(mp_variant)
        processed.add(gr_variant)

    # --- Gram-only variants (no mean-pool counterpart) ---
    for layers, gr_variant, proj_dim in GRAM_ONLY:
        gr_row = summary[gr_variant]
        gr_mean = float(gr_row["norm_l2_mean"])
        gr_vals = per_query[gr_variant]
        gr_ci = bootstrap_ci(gr_vals, n_bootstrap)
        n = len(gr_vals)

        results.append(LayerAblationResult(
            layer=layers,
            method="gram",
            project_dim=proj_dim,
            norm_l2_mean=gr_mean,
            norm_l2_ci_lower=gr_ci[0],
            norm_l2_ci_upper=gr_ci[1],
            improvement_vs_mean=float("nan"),
            wilcoxon_p=float("nan"),
            n_queries=n,
        ))
        processed.add(gr_variant)

    return results


# ---------------------------------------------------------------------------
# CSV output
# ---------------------------------------------------------------------------

CSV_FIELDS = [
    "layer", "method", "project_dim", "norm_l2_mean",
    "norm_l2_ci_lower", "norm_l2_ci_upper",
    "improvement_vs_mean", "wilcoxon_p", "n_queries",
]


def layer_to_str(layers: List[int]) -> str:
    """Convert layer list to string for CSV output."""
    return "+".join(str(l) for l in layers)


def write_csv(results: List[LayerAblationResult], output_path: str) -> None:
    """Write results to CSV."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for r in results:
            row = asdict(r)
            # Convert layer list to string
            row["layer"] = layer_to_str(r.layer)
            writer.writerow(row)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Layer-5 Gram vs mean-pool confound analysis")
    parser.add_argument(
        "--summary",
        default=str(Path(__file__).parent / "outputs" / "p0_trr_mechanism" /
                     "p0_trr_mechanism_summary.csv"),
        help="Path to summary CSV")
    parser.add_argument(
        "--per-query",
        default=str(Path(__file__).parent / "outputs" / "p0_trr_mechanism" /
                     "p0_trr_mechanism_per_query.csv"),
        help="Path to per-query CSV")
    parser.add_argument(
        "--output",
        default=str(Path(__file__).parent / "outputs" / "layer5_confound" /
                     "layer5_confound_results.csv"),
        help="Output CSV path")
    parser.add_argument(
        "--n-bootstrap", type=int, default=10000,
        help="Number of bootstrap samples")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    summary = load_summary(args.summary)
    per_query = load_per_query(args.per_query)

    results = build_results(summary, per_query, args.n_bootstrap)
    write_csv(results, args.output)

    # Print summary
    print(f"Layer-5 Confound Analysis")
    print(f"{'=' * 60}")
    for r in results:
        layers_str = layer_to_str(r.layer)
        delta_str = f"+{r.improvement_vs_mean:.4f}" if not np.isnan(r.improvement_vs_mean) else "N/A"
        p_str = f"{r.wilcoxon_p:.6f}" if not np.isnan(r.wilcoxon_p) else "N/A"
        print(f"  Layer {layers_str:>7s} | {r.method:>10s} | "
              f"Norm.L2 = {r.norm_l2_mean:.4f} "
              f"[{r.norm_l2_ci_lower:.4f}, {r.norm_l2_ci_upper:.4f}] | "
              f"Delta = {delta_str} | p = {p_str}")

    print(f"\nOutput: {args.output}")
    print(f"Total rows: {len(results)}")


if __name__ == "__main__":
    main()
