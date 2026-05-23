from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Mapping, Optional, Sequence

import numpy as np

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

# Grid per the task specification
DEFAULT_KS = [3, 5, 10, 20]
DEFAULT_TEMPERATURES = [0.01, 0.05, 0.10, 0.20, 0.50]


@dataclass
class EPRGridResult:
    k: int
    temperature: float
    norm_l2: float
    acc_at_0_1: float
    recall: float
    cosine: float
    switch_f1: float
    n_eff: float
    max_wi: float
    n_queries: int  # must be 204


def _softmax_weights(scores: Sequence[float], temperature: float) -> List[float]:
    return softmax_weights(scores, temperature=float(temperature))


def epr_sensitivity_rows(
    topk_rows: Sequence[Mapping[str, object]],
    dataset: Sequence[dict],
    source_method: str = "TRR",
    ks: Sequence[int] = DEFAULT_KS,
    temperatures: Sequence[float] = DEFAULT_TEMPERATURES,
) -> list[EPRGridResult]:
    """Run EPR sensitivity grid over K x temperature. Softmax weighting only."""
    kb_items = kb_items_from_topk_rows(dataset, topk_rows)
    ranges = observed_numeric_ranges(kb_items)
    source_rows = [
        row
        for row in topk_rows
        if row.get("status") == "ok" and str(row.get("method", "")) == str(source_method)
    ]

    results: list[EPRGridResult] = []
    for k in ks:
        for temperature in temperatures:
            per_query_metrics: list[dict] = []
            per_query_provenance: list[dict] = []
            for row in source_rows:
                candidates = row.get("topk_candidates", [])
                if not isinstance(candidates, list):
                    continue
                selected = [c for c in candidates[: int(k)] if isinstance(c, Mapping)]
                if not selected:
                    continue
                scores = [_candidate_score(c) for c in selected]
                weights = _softmax_weights(scores, temperature=float(temperature))
                candidate_params = [_candidate_params(c) for c in selected]
                pred_params, provenance = weighted_projection(candidate_params, weights, ranges)
                query_idx = int(row["query_idx"])
                gt_params = dataset[query_idx].get("Parameters", {})
                metrics = _evaluate_projection(
                    pred_params, gt_params if isinstance(gt_params, Mapping) else {}
                )
                metrics.update(
                    switch_metrics(
                        pred_params, gt_params if isinstance(gt_params, Mapping) else {}
                    )
                )
                per_query_metrics.append(metrics)
                per_query_provenance.append(provenance)

            if not per_query_metrics:
                continue

            n = len(per_query_metrics)
            results.append(
                EPRGridResult(
                    k=int(k),
                    temperature=float(temperature),
                    norm_l2=float(np.mean([float(m["norm_l2"]) for m in per_query_metrics])),
                    acc_at_0_1=float(np.mean([float(m["acc_at_0_1"]) for m in per_query_metrics])),
                    recall=float(np.mean([float(m["recall"]) for m in per_query_metrics])),
                    cosine=float(np.mean([float(m["cosine"]) for m in per_query_metrics])),
                    switch_f1=float(np.mean([float(m["switch_f1"]) for m in per_query_metrics])),
                    n_eff=float(np.mean([float(p["effective_exemplars"]) for p in per_query_provenance])),
                    max_wi=float(np.mean([float(p["max_weight"]) for p in per_query_provenance])),
                    n_queries=n,
                )
            )
    return results


def results_to_dicts(results: Sequence[EPRGridResult]) -> list[dict]:
    return [asdict(r) for r in results]


def find_optimal(
    results: Sequence[EPRGridResult],
    primary_metric: str = "switch_f1",
) -> Optional[EPRGridResult]:
    """Identify the best grid point by primary metric (higher is better)."""
    if not results:
        return None
    return max(results, key=lambda r: getattr(r, primary_metric))


def write_outputs(output_dir: Path, results: Sequence[EPRGridResult]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = results_to_dicts(results)
    json_path = output_dir / "epr_sensitivity_summary.json"
    csv_path = output_dir / "epr_sensitivity_summary.csv"

    json_path.write_text(
        json.dumps(rows, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    fields = sorted({key for r in rows for key in r.keys()})
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def generate_heatmap(
    output_dir: Path,
    results: Sequence[EPRGridResult],
    metrics: Optional[Sequence[str]] = None,
) -> None:
    """Generate sensitivity heatmaps for each metric (K vs temperature)."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import seaborn as sns
    except ImportError:
        return

    if metrics is None:
        metrics = ["norm_l2", "acc_at_0_1", "recall", "cosine", "switch_f1", "n_eff", "max_wi"]

    ks = sorted({r.k for r in results})
    temps = sorted({r.temperature for r in results})

    fig, axes = plt.subplots(2, 4, figsize=(20, 10))
    fig.suptitle("EPR Sensitivity Heatmaps (K x Temperature)", fontsize=14)

    # Flatten axes list
    flat_axes = axes.flatten()
    for idx, metric in enumerate(metrics):
        ax = flat_axes[idx]
        pivot = {}
        for r in results:
            pivot.setdefault(r.k, {})[r.temperature] = getattr(r, metric)
        matrix = np.array(
            [pivot.get(k, {}).get(t, np.nan) for k in ks for t in temps],
        ).reshape(len(ks), len(temps))

        sns.heatmap(
            matrix,
            ax=ax,
            xticklabels=[f"{t}" for t in temps],
            yticklabels=[f"K={k}" for k in ks],
            cmap="YlOrRd",
            annot=True,
            fmt=".4f",
            cbar_kws={"shrink": 0.8},
        )
        ax.set_xlabel("Temperature")
        ax.set_ylabel("K")
        ax.set_title(metric)

    # Hide any unused subplots
    for idx in range(len(metrics), len(flat_axes)):
        flat_axes[idx].set_visible(False)

    fig.tight_layout()
    figpath = output_dir / "epr_sensitivity_heatmap.png"
    figpath.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(figpath), dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {figpath}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run EPR sensitivity grid (K x temperature), softmax-only."
    )
    parser.add_argument("--dataset", default=DEFAULT_DATASET)
    parser.add_argument("--topk-json", default=DEFAULT_TOPK)
    parser.add_argument("--output-dir", default=DEFAULT_OUT)
    parser.add_argument("--source-method", default="TRR")
    parser.add_argument("--ks", type=int, nargs="+", default=DEFAULT_KS)
    parser.add_argument("--temperatures", type=float, nargs="+", default=DEFAULT_TEMPERATURES)
    args = parser.parse_args()

    dataset = load_dataset(Path(args.dataset))
    topk_rows = load_topk_rows(Path(args.topk_json))

    results = epr_sensitivity_rows(
        topk_rows,
        dataset,
        args.source_method,
        args.ks,
        args.temperatures,
    )
    write_outputs(Path(args.output_dir), results)
    generate_heatmap(Path(args.output_dir), results)

    # Summary
    optimal = find_optimal(results)
    if optimal:
        print(f"Optimal config: K={optimal.k}, tau={optimal.temperature}")
        print(f"  switch_f1={optimal.switch_f1:.4f}  norm_l2={optimal.norm_l2:.4f}")
        print(f"  acc@0.1={optimal.acc_at_0_1:.4f}  cosine={optimal.cosine:.4f}")
        print(f"  n_eff={optimal.n_eff:.2f}  max_wi={optimal.max_wi:.4f}")
    print(f"Total configurations: {len(results)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
