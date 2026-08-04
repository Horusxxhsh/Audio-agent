"""
Per-Parameter Error Distribution Analysis (Task 5.2).

Generates per-parameter and per-module error breakdown for Protocol-A,
producing grouped bar charts and detailed statistics.

Usage:
    python per_param_analysis.py --dataset ../../Experiments/dataset_full_vectors.json
"""

import json
import sys
import logging
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(Path(__file__).parent.parent / "common"))
from evaluate import Evaluator, load_param_ranges
from Experiments.E7_HardSplit.run_hard_split_retrieval import load_requested_query_indices

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_SPLIT = REPO_ROOT / "Experiments" / "tmm" / "splits" / "tmm_external1267_audio_grouped" / "seed0" / "test.txt"

MODULE_NAMES = [
    "CompressorOn", "CompressorOff",
    "DriverOn", "DriverOff",
    "ScreamerOn", "ScreamerOff",
    "ReverbOn", "ReverbOff",
    "DelayOn", "DelayOff",
    "ChorusOn", "ChorusOff",
    "FlangerOn", "FlangerOff",
    "PhaserOn", "PhaserOff",
    "EqualiserOn", "EqualiserOff",
]


def flatten_params_with_keys(params: Dict) -> Dict[str, float]:
    """Flatten nested parameter dict to dot-separated keys."""
    flat = {}
    for module, sub in params.items():
        if isinstance(sub, dict):
            for key, val in sub.items():
                try:
                    flat[f"{module}.{key}"] = float(val)
                except (ValueError, TypeError):
                    continue
        else:
            try:
                flat[module] = float(sub)
            except (ValueError, TypeError):
                continue
    return flat


def compute_per_param_errors(
    dataset: List[Dict],
    query_indices: List[int],
    vector_key: str = "TRR",
) -> Dict[str, List[float]]:
    """Compute per-parameter absolute error for TRR retrieval.

    Args:
        dataset: Full dataset list.
        method_name: Method name for logging.

    Returns:
        Dict mapping param key -> list of absolute errors.
    """
    query_set = {int(i) for i in query_indices}
    queries = [dataset[i] for i in query_indices]
    kb = [item for i, item in enumerate(dataset) if i not in query_set]

    # Build KB embedding matrix
    kb_vecs = []
    kb_valid_idx = []
    for i, item in enumerate(kb):
        vec = item.get("Vectors", {}).get(vector_key)
        if vec is not None:
            kb_vecs.append(np.array(vec, dtype=np.float32))
            kb_valid_idx.append(i)
    kb_matrix = np.stack(kb_vecs)
    norms = np.linalg.norm(kb_matrix, axis=1, keepdims=True)
    kb_matrix = kb_matrix / np.maximum(norms, 1e-8)

    per_param_errors = defaultdict(list)

    for q in queries:
        q_vec = q.get("Vectors", {}).get(vector_key)
        if q_vec is None:
            continue
        q_vec = np.array(q_vec, dtype=np.float32)
        q_vec = q_vec / max(np.linalg.norm(q_vec), 1e-8)

        sims = kb_matrix @ q_vec
        best_kb_idx = kb_valid_idx[int(np.argmax(sims))]

        gt = flatten_params_with_keys(q.get("Parameters", {}))
        pred = flatten_params_with_keys(kb[best_kb_idx].get("Parameters", {}))

        all_keys = set(gt.keys()) | set(pred.keys())
        for key in all_keys:
            gt_val = gt.get(key, 0.0)
            pred_val = pred.get(key, 0.0)
            per_param_errors[key].append(abs(gt_val - pred_val))

    return dict(per_param_errors)


def compute_normalized_per_param_errors(
    per_param_errors: Dict[str, List[float]],
    param_ranges: Dict,
) -> Dict[str, List[float]]:
    """Normalize per-parameter errors by DSP physical ranges.

    Args:
        per_param_errors: Raw per-parameter errors.
        param_ranges: Loaded param_ranges.json.

    Returns:
        Normalized per-parameter errors in [0, 1].
    """
    normalized = {}
    for key, errors in per_param_errors.items():
        parts = key.split(".")
        if len(parts) == 2:
            module, param = parts
            if module in param_ranges and param in param_ranges[module]:
                rng = param_ranges[module][param]
                lo, hi = rng["min"], rng["max"]
                span = hi - lo
                if span > 0:
                    normalized[key] = [e / span for e in errors]
                    continue
        normalized[key] = errors  # fallback: no range found
    return normalized


def aggregate_by_module(
    per_param_errors: Dict[str, List[float]],
) -> Dict[str, Dict[str, float]]:
    """Aggregate per-parameter errors by module.

    Returns:
        Dict[module_name] -> {mean, median, std, max, n_params}.
    """
    module_errors = defaultdict(list)
    for key, errors in per_param_errors.items():
        module = key.split(".")[0] if "." in key else key
        module_errors[module].extend(errors)

    result = {}
    for module, errs in sorted(module_errors.items()):
        arr = np.array(errs)
        result[module] = {
            "mean": float(np.mean(arr)),
            "median": float(np.median(arr)),
            "std": float(np.std(arr)),
            "max": float(np.max(arr)),
            "n_errors": len(errs),
        }
    return result


def generate_report(
    per_param_raw: Dict[str, List[float]],
    per_param_norm: Dict[str, List[float]],
    module_stats_raw: Dict[str, Dict],
    module_stats_norm: Dict[str, Dict],
    output_path: str,
) -> None:
    """Generate markdown analysis report.

    Args:
        per_param_raw: Raw per-parameter errors.
        per_param_norm: Normalized per-parameter errors.
        module_stats_raw: Raw module-level stats.
        module_stats_norm: Normalized module-level stats.
        output_path: Report save path.
    """
    lines = ["# Per-Parameter Error Distribution Analysis\n"]
    lines.append("## Module-Level Summary (Raw)\n")
    lines.append("| Module | Mean | Median | Std | Max | N |")
    lines.append("|--------|------|--------|-----|-----|---|")
    for mod, s in module_stats_raw.items():
        lines.append(
            f"| {mod} | {s['mean']:.4f} | {s['median']:.4f} | "
            f"{s['std']:.4f} | {s['max']:.4f} | {s['n_errors']} |"
        )

    lines.append("\n## Module-Level Summary (Normalized)\n")
    lines.append("| Module | Mean | Median | Std | Max | N |")
    lines.append("|--------|------|--------|-----|-----|---|")
    for mod, s in module_stats_norm.items():
        lines.append(
            f"| {mod} | {s['mean']:.4f} | {s['median']:.4f} | "
            f"{s['std']:.4f} | {s['max']:.4f} | {s['n_errors']} |"
        )

    # Top-10 hardest parameters (by normalized mean error)
    lines.append("\n## Top-10 Hardest Parameters (by Normalized Mean Error)\n")
    lines.append("| Parameter | Mean (norm) | Mean (raw) | N |")
    lines.append("|-----------|-------------|------------|---|")
    param_means = {
        k: (float(np.mean(v)), float(np.mean(per_param_raw.get(k, v))))
        for k, v in per_param_norm.items()
    }
    sorted_params = sorted(param_means.items(), key=lambda x: -x[1][0])
    for key, (mn, mr) in sorted_params[:10]:
        lines.append(f"| {key} | {mn:.4f} | {mr:.4f} | {len(per_param_norm[key])} |")

    # Top-10 easiest parameters
    lines.append("\n## Top-10 Easiest Parameters (by Normalized Mean Error)\n")
    lines.append("| Parameter | Mean (norm) | Mean (raw) | N |")
    lines.append("|-----------|-------------|------------|---|")
    for key, (mn, mr) in sorted_params[-10:]:
        lines.append(f"| {key} | {mn:.4f} | {mr:.4f} | {len(per_param_norm[key])} |")

    with open(output_path, "w") as f:
        f.write("\n".join(lines) + "\n")
    logger.info(f"Report saved to {output_path}")


def generate_matplotlib_figure(
    module_stats_norm: Dict[str, Dict],
    output_path: str,
) -> None:
    """Generate per-module error bar chart.

    Args:
        module_stats_norm: Normalized module-level stats.
        output_path: Figure save path (PDF).
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        matplotlib.rcParams["pdf.fonttype"] = 42
        matplotlib.rcParams["ps.fonttype"] = 42
        matplotlib.rcParams["font.size"] = 16
        matplotlib.rcParams["axes.titlesize"] = 17
        matplotlib.rcParams["axes.labelsize"] = 16
        matplotlib.rcParams["xtick.labelsize"] = 12
        matplotlib.rcParams["ytick.labelsize"] = 12
        import matplotlib.pyplot as plt
    except ImportError:
        logger.warning("matplotlib not available, skipping figure generation")
        return

    modules = list(module_stats_norm.keys())
    means = [module_stats_norm[m]["mean"] for m in modules]
    stds = [module_stats_norm[m]["std"] for m in modules]

    fig, ax = plt.subplots(figsize=(6.5, 2.8))
    x_pos = np.arange(len(modules))
    bars = ax.bar(x_pos, means, yerr=stds, capsize=3, color="#4C72B0", alpha=0.8)

    ax.set_xlabel("Module", fontsize=9)
    ax.set_ylabel("Normalized Mean Absolute Error", fontsize=9)
    ax.set_title("Per-Module Parameter Error Distribution (Protocol-A, TRR)", fontsize=10)
    ax.set_xticks(x_pos)
    ax.set_xticklabels(modules, rotation=45, ha="right", fontsize=9)
    ymax = max([m + s for m, s in zip(means, stds)] + [0.05]) * 1.08
    ax.set_ylim(0, max(1.0, ymax))
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"Figure saved to {output_path}")


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Per-Parameter Error Analysis")
    parser.add_argument("--dataset", type=str,
                        default=str(Path(__file__).parent.parent / "dataset_full_vectors.json"))
    parser.add_argument("--output-dir", type=str,
                        default=str(Path(__file__).parent))
    parser.add_argument("--split-file", type=str, default=str(DEFAULT_SPLIT),
                        help="Protocol-A query split file")
    parser.add_argument("--vector-key", type=str, default="TRR",
                        help="Cached vector key to evaluate, default: TRR")
    parser.add_argument("--figure-dir", type=str, default=None,
                        help="Directory for figure output (default: Paper/figures/)")
    args = parser.parse_args()

    with open(args.dataset, "r") as f:
        dataset = json.load(f)
    logger.info(f"Loaded {len(dataset)} items from {args.dataset}")

    query_indices = load_requested_query_indices(dataset, Path(args.split_file))
    logger.info(f"Loaded {len(query_indices)} query indices from {args.split_file}")

    # Compute raw errors
    per_param_raw = compute_per_param_errors(dataset, query_indices, vector_key=args.vector_key)
    logger.info(f"Computed errors for {len(per_param_raw)} parameters")

    # Normalize
    param_ranges_path = Path(__file__).parent.parent / "common" / "param_ranges.json"
    param_ranges = load_param_ranges(str(param_ranges_path))
    per_param_norm = compute_normalized_per_param_errors(per_param_raw, param_ranges)

    # Module aggregation
    module_stats_raw = aggregate_by_module(per_param_raw)
    module_stats_norm = aggregate_by_module(per_param_norm)

    # Report
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    generate_report(per_param_raw, per_param_norm, module_stats_raw, module_stats_norm,
                    str(out / "per_param_analysis_report.md"))

    # Save JSON
    results = {
        "per_param_raw": {k: {"mean": float(np.mean(v)), "std": float(np.std(v))}
                          for k, v in per_param_raw.items()},
        "per_param_norm": {k: {"mean": float(np.mean(v)), "std": float(np.std(v))}
                           for k, v in per_param_norm.items()},
        "module_stats_raw": module_stats_raw,
        "module_stats_norm": module_stats_norm,
    }
    with open(out / "per_param_analysis_results.json", "w") as f:
        json.dump(results, f, indent=2)

    # Figure
    fig_dir = args.figure_dir or str(Path(__file__).parent.parent.parent / "Paper" / "figures")
    Path(fig_dir).mkdir(parents=True, exist_ok=True)
    generate_matplotlib_figure(module_stats_norm, str(Path(fig_dir) / "per_param_error_dist.pdf"))


if __name__ == "__main__":
    main()
