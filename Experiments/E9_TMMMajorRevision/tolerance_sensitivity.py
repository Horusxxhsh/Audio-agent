"""Tolerance Sensitivity Analysis (MA-2).

Compute Acc@τ and Recall@τ across τ ∈ {0.05, 0.10, 0.15, 0.20} for all methods,
using existing unified top-K results.  Acc@τ is top-1 accuracy at tolerance τ;
Recall@τ is top-10 recall at tolerance τ.

Acc@τ is derived from the stored top1_norm_l2 (RMSE distance) values.
Recall@τ for τ ∈ {0.05, 0.10, 0.15} comes from the existing PNR columns.
Recall@τ for τ = 0.20 is recomputed from topk_candidates using the
normalized RMSE distance against ground-truth parameters.
"""

from __future__ import annotations

import csv
import json
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Mapping, Sequence

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from Experiments.common.evaluate import Evaluator

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TOLERANCES = [0.05, 0.10, 0.15, 0.20]

UNIFIED_JSON = REPO_ROOT / "Experiments/E9_TMMMajorRevision/outputs/unified_protocol/unified_topk_rows.json"
DATASET_JSON = "Data/External_1267_211/dataset/dataset_full_vectors_1267.json"

OUTPUT_DIR = REPO_ROOT / "Experiments/E9_TMMMajorRevision/outputs/tolerance_sensitivity"

# PNR column names for recall@10 at each pre-computed tolerance
_PNR_RECALL_COLS = {
    0.05: "pnr_at_10_t0_05",
    0.10: "pnr_at_10_t0_10",
    0.15: "pnr_at_10_t0_15",
}


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class ToleranceSensitivityResult:
    method: str
    tolerance: float
    acc_at_tau: float
    recall_at_tau: float
    n_queries: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_unified_rows(path: Path = UNIFIED_JSON) -> list[dict]:
    with open(path) as f:
        return json.load(f)


def _load_ground_truth(dataset_path: str, query_indices: list[int]) -> dict[int, dict]:
    """Load ground-truth Parameters for given query indices from the dataset."""
    with open(dataset_path) as f:
        dataset = json.load(f)
    return {int(idx): dataset[int(idx)].get("Parameters", {}) for idx in query_indices}


def _compute_recall_at_tau_from_candidates(
    rows: Sequence[Mapping],
    gt_params_map: Mapping[int, Mapping],
    tolerance: float,
    k: int = 10,
) -> list[float]:
    """Compute per-query Recall@k@τ from candidate parameters.

    Returns a list of 0/1 values (one per row), 1 if at least one candidate
    has RMSE distance ≤ tolerance.
    """
    ev = Evaluator(normalize=True)
    results = []
    for row in rows:
        gt = gt_params_map.get(int(row["query_idx"]), {})
        candidates = row.get("topk_candidates", [])[:k]
        cand_params = [c.get("parameters", {}) for c in candidates]
        # Use the parameter_space function which already handles normalization
        from Experiments.common.parameter_space import topk_parameter_neighborhood_recall
        hit = topk_parameter_neighborhood_recall(cand_params, gt, threshold=tolerance, normalize=True)
        results.append(hit)
    return results


def _compute_acc_at_tau(norm_l2_values: list[float], tolerance: float) -> float:
    """Acc@τ = fraction of queries with top-1 RMSE ≤ τ."""
    if not norm_l2_values:
        return 0.0
    return sum(1 for d in norm_l2_values if d <= tolerance) / len(norm_l2_values)


def _compute_recall_at_tau_from_pnr(rows: Sequence[Mapping], tolerance: float) -> float:
    """Read Recall@10@τ from pre-computed PNR column."""
    col = _PNR_RECALL_COLS[tolerance]
    if not rows:
        return 0.0
    hits = sum(1 for r in rows if r.get(col, 0) == 1)
    return hits / len(rows)


# ---------------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------------

def run_tolerance_sensitivity(
    unified_json: Path = UNIFIED_JSON,
    dataset_path: str = DATASET_JSON,
    output_dir: Path = OUTPUT_DIR,
    tolerances: list[float] | None = None,
) -> list[ToleranceSensitivityResult]:
    """Compute Acc@τ and Recall@τ for all methods at given tolerances.

    Returns a list of ToleranceSensitivityResult objects and writes outputs
    to *output_dir*.
    """
    tolerances = tolerances or TOLERANCES
    rows = _load_unified_rows(unified_json)

    # Group by method (only ok rows)
    methods: dict[str, list[dict]] = {}
    for row in rows:
        if row.get("status") == "ok":
            methods.setdefault(row["method"], []).append(row)

    # Load ground truth for recomputing Recall@0.20
    query_indices = [int(r["query_idx"]) for r in rows if r.get("status") == "ok"]
    gt_map = _load_ground_truth(dataset_path, list(set(query_indices)))

    all_results: list[ToleranceSensitivityResult] = []

    for method in sorted(methods.keys()):
        method_rows = methods[method]
        n_queries = len(method_rows)
        if n_queries == 0:
            continue

        top1_norms = [r["top1_norm_l2"] for r in method_rows]

        # For τ=0.20, pre-compute Recall@10@0.20 from candidates
        recall_020_per_query = _compute_recall_at_tau_from_candidates(
            method_rows, gt_map, 0.20, k=10
        )
        recall_020 = sum(recall_020_per_query) / n_queries if n_queries else 0.0

        for tau in tolerances:
            acc = _compute_acc_at_tau(top1_norms, tau)

            if tau in _PNR_RECALL_COLS:
                recall = _compute_recall_at_tau_from_pnr(method_rows, tau)
            else:
                recall = recall_020

            all_results.append(ToleranceSensitivityResult(
                method=method,
                tolerance=tau,
                acc_at_tau=round(acc, 6),
                recall_at_tau=round(recall, 6),
                n_queries=n_queries,
            ))

    # Write outputs
    output_dir.mkdir(parents=True, exist_ok=True)

    # CSV output
    csv_path = output_dir / "tolerance_sensitivity_results.csv"
    fieldnames = ["method", "tolerance", "acc_at_tau", "recall_at_tau", "n_queries"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in all_results:
            writer.writerow(asdict(r))

    # JSON output
    json_path = output_dir / "tolerance_sensitivity_results.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump([asdict(r) for r in all_results], f, indent=2)

    # Plot sensitivity curves
    _plot_sensitivity(all_results, output_dir)

    return all_results


def _plot_sensitivity(
    results: list[ToleranceSensitivityResult],
    output_dir: Path,
) -> None:
    """Generate sensitivity curves: Acc@τ and Recall@τ vs tolerance."""
    methods = sorted({r.method for r in results})
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    colors = {"TRR": "#2ca02c", "Wav2Vec": "#1f77b4", "PaSST": "#ff7f0e",
              "FeatureNN": "#9467bd", "CLAP": "#d62728"}

    for ax, metric, ylabel in [(axes[0], "acc", "Acc@τ"),
                                (axes[1], "recall", "Recall@τ")]:
        for method in methods:
            method_results = [r for r in results if r.method == method]
            taus = [r.tolerance for r in method_results]
            values = [r.acc_at_tau if metric == "acc" else r.recall_at_tau
                      for r in method_results]
            ax.plot(taus, values, marker="o", label=method,
                    color=colors.get(method, "gray"), linewidth=2, markersize=6)
        ax.set_xlabel("Tolerance τ", fontsize=12)
        ax.set_ylabel(ylabel, fontsize=12)
        ax.set_title(ylabel + " vs Tolerance", fontsize=13)
        ax.legend(fontsize=9, loc="best")
        ax.grid(True, alpha=0.3)
        ax.set_xticks(TOLERANCES)
        ax.set_xticklabels([f"{t:.2f}" for t in TOLERANCES])

    fig.tight_layout()
    fig_path = output_dir / "sensitivity_curves.png"
    fig.savefig(fig_path, dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Tolerance Sensitivity Analysis")
    parser.add_argument("--unified-json", type=Path, default=UNIFIED_JSON)
    parser.add_argument("--dataset", type=str, default=DATASET_JSON)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--tolerances", type=float, nargs="+", default=TOLERANCES)
    args = parser.parse_args()

    results = run_tolerance_sensitivity(
        unified_json=args.unified_json,
        dataset_path=args.dataset,
        output_dir=args.output_dir,
        tolerances=args.tolerances,
    )

    print(f"Tolerance sensitivity analysis complete.")
    print(f"Methods: {sorted({r.method for r in results})}")
    print(f"Tolerances: {args.tolerances}")
    print(f"Total results: {len(results)}")
    for r in results:
        print(f"  {r.method} τ={r.tolerance}: Acc={r.acc_at_tau:.4f}  Recall={r.recall_at_tau:.4f}  n={r.n_queries}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
