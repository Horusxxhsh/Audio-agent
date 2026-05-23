"""Holm-Bonferroni multiple-comparison correction for paired Wilcoxon tests.

Applies the Holm-Bonferroni step-down procedure within each metric group
(Norm.L2, Acc@0.1, Recall, Cosine, SwitchF1).  Each group has exactly 3
pairwise comparisons (TRR vs Wav2Vec, TRR vs FeatureNN, TRR vs PaSST).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class HolmCorrectedResult:
    """One comparison entry after Holm-Bonferroni correction."""
    metric: str
    baseline: str
    raw_p: float
    holm_corrected_p: float
    n_comparisons: int
    significant_raw: bool
    significant_corrected: bool
    alpha: float  # default 0.05


# ---------------------------------------------------------------------------
# Core algorithm
# ---------------------------------------------------------------------------

def holm_bonferroni(p_values: List[float], alpha: float = 0.05) -> List[float]:
    """Apply the Holm-Bonferroni step-down procedure.

    Given ``m`` raw p-values, sorts them as :math:`p_(1) <= p_(2) <= ... <= p_(m)`.
    The corrected p-value for the i-th smallest is
        ``min( (m + 1 - i) * p_(i), 1.0)``
    where i is 1-based.  Results are returned in the **original order** of
    ``p_values``.

    Args:
        p_values: list of raw p-values (all must be in [0, 1]).
        alpha: nominal significance level (used only for significance flags,
               not for the corrected p-values themselves).

    Returns:
        List of Holm-corrected p-values in the same order as ``p_values``.
    """
    if not p_values:
        return []

    m = len(p_values)
    # (sorted_index, raw_p) pairs, sorted by p ascending
    indexed = sorted(enumerate(p_values), key=lambda x: x[1])

    corrected = [0.0] * m
    prev_corrected = 0.0  # enforce non-decreasing monotonicity

    for rank, (orig_idx, p) in enumerate(indexed, start=1):
        raw_corrected = min(p * (m + 1 - rank), 1.0)
        # Step-up enforcement: corrected p-values must be non-decreasing
        corrected[orig_idx] = max(raw_corrected, prev_corrected)
        prev_corrected = corrected[orig_idx]

    return corrected


def apply_correction(
    significance_results: Dict[str, Dict[str, dict]],
    alpha: float = 0.05,
) -> Dict[str, List[HolmCorrectedResult]]:
    """Load raw Wilcoxon results and apply Holm-Bonferroni per metric group.

    Args:
        significance_results: dict of {metric -> {baseline -> result_dict}}
            matching the format produced by significance_test.py.
        alpha: significance level.

    Returns:
        dict of {metric -> list[HolmCorrectedResult]}.
    """
    output: Dict[str, List[HolmCorrectedResult]] = {}

    for metric, baselines in significance_results.items():
        raw_p_values: List[float] = []
        baseline_names: List[str] = []

        for baseline, res in baselines.items():
            p = res.get("p")
            if p is None:
                continue
            raw_p_values.append(p)
            baseline_names.append(baseline)

        if not raw_p_values:
            continue

        m = len(raw_p_values)
        corrected_p = holm_bonferroni(raw_p_values, alpha=alpha)

        entries: List[HolmCorrectedResult] = []
        for baseline, raw_p, corr_p in zip(baseline_names, raw_p_values, corrected_p):
            entries.append(HolmCorrectedResult(
                metric=metric,
                baseline=baseline,
                raw_p=raw_p,
                holm_corrected_p=corr_p,
                n_comparisons=m,
                significant_raw=raw_p < alpha,
                significant_corrected=corr_p < alpha,
                alpha=alpha,
            ))

        output[metric] = entries

    return output


# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------

def results_to_dict(results: Dict[str, List[HolmCorrectedResult]]) -> dict:
    """Convert results to a plain dict for JSON serialization."""
    payload = {}
    for metric, entries in results.items():
        payload[metric] = [asdict(e) for e in entries]
    return payload


def load_and_correct(
    input_path: str | Path,
    output_path: str | Path | None = None,
    alpha: float = 0.05,
) -> Dict[str, List[HolmCorrectedResult]]:
    """Load significance results JSON, apply correction, optionally save.

    Returns the corrected results dict.
    """
    input_path = Path(input_path)
    with open(input_path) as f:
        raw = json.load(f)
    results = apply_correction(raw, alpha=alpha)
    if output_path is not None:
        with open(output_path, "w") as f:
            json.dump(results_to_dict(results), f, indent=2)
    return results


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    results_path = (
        Path(__file__).resolve().parent
        / "outputs/unified_protocol/significance_results.json"
    )
    output_path = results_path.with_name("holm_bonferroni_results.json")
    results = load_and_correct(results_path, output_path)

    print("=" * 72)
    print("Holm-Bonferroni Correction Summary")
    print("=" * 72)
    for metric, entries in results.items():
        print(f"\nMetric: {metric}")
        print(
            f"  {'Baseline':<12} {'Raw p':<16} "
            f"{'Corrected p':<16} {'Sig(raw)':<10} {'Sig(corr)':<10}"
        )
        print(
            f"  {'-'*12} {'-'*14} {'-'*14} {'-'*10} {'-'*10}"
        )
        for e in entries:
            print(
                f"  {e.baseline:<12} {e.raw_p:<16.2e} "
                f"{e.holm_corrected_p:<16.2e} "
                f"{'yes' if e.significant_raw else 'no':<10} "
                f"{'yes' if e.significant_corrected else 'no':<10}"
            )
    print(f"\nSaved to {output_path}")
