"""Regenerate paper-facing E9 diagnostic figures from exported CSV/JSON artifacts."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO_ROOT / "Paper" / "figures"
NEAR_DUP = REPO_ROOT / "Experiments" / "E9_TMMMajorRevision" / "outputs" / "robustness" / "near_duplicate_unified" / "near_duplicate_summary.csv"
HARD_SPLIT = REPO_ROOT / "Experiments" / "E9_TMMMajorRevision" / "outputs" / "robustness" / "hard_split_sweep" / "hard_split_sweep_summary.json"
EPR = REPO_ROOT / "Experiments" / "E9_TMMMajorRevision" / "outputs" / "epr_sensitivity" / "epr_sensitivity_summary.csv"


def plot_robustness(out_dir: Path) -> None:
    import matplotlib.pyplot as plt

    with NEAR_DUP.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    methods = ["TRR", "Wav2Vec", "FeatureNN", "PaSST", "CLAP"]
    colors = {"TRR": "#1b9e77", "Wav2Vec": "#7570b3", "FeatureNN": "#666666", "PaSST": "#d95f02", "CLAP": "#e7298a"}

    fig, axes = plt.subplots(1, 2, figsize=(6.8, 2.6))
    ax = axes[0]
    markers = {"TRR": "o", "Wav2Vec": "s", "FeatureNN": "^", "PaSST": "D", "CLAP": "v"}
    for method in methods:
        sub = sorted([r for r in rows if r["method"] == method], key=lambda r: float(r["group"]))
        if not sub:
            continue
        ax.plot(
            [float(r["group"]) for r in sub],
            [float(r["norm_l2"]) for r in sub],
            marker=markers.get(method, "o"),
            label=method,
            color=colors.get(method),
        )
    ax.set_title("Near-Duplicate Removal")
    ax.set_xlabel("Removal threshold")
    ax.set_ylabel("Normalized L2 (lower is better)")
    ax.grid(alpha=0.25)

    hard = json.loads(HARD_SPLIT.read_text(encoding="utf-8"))
    ax = axes[1]
    for method in methods:
        xs, ys, yerr_low, yerr_high = [], [], [], []
        for tau, payload in sorted(hard.items(), key=lambda kv: float(kv[0])):
            entry = payload["summary"].get(method)
            if not entry:
                continue
            xs.append(float(tau))
            ys.append(float(entry["norm_l2"]))
            yerr_low.append(max(0.0, float(entry["norm_l2"]) - float(entry.get("norm_l2_ci_low", entry["norm_l2"]))))
            yerr_high.append(max(0.0, float(entry.get("norm_l2_ci_high", entry["norm_l2"])) - float(entry["norm_l2"])))
        if xs:
            ax.errorbar(xs, ys, yerr=[yerr_low, yerr_high], marker=markers.get(method, "o"), capsize=3, label=method, color=colors.get(method))
    ax.set_title("Parameter-Cluster Hard Split")
    ax.set_xlabel("Cluster threshold")
    ax.grid(alpha=0.25)
    axes[0].legend(loc="upper left", fontsize=8)
    fig.tight_layout()
    out = out_dir / "robustness_result_curves.pdf"
    fig.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out}")


def plot_epr(out_dir: Path) -> None:
    import matplotlib.pyplot as plt

    with EPR.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    fig, axes = plt.subplots(1, 2, figsize=(6.8, 2.6))
    temps = sorted({r["temperature"] for r in rows}, key=float)
    for temp in temps:
        sub = sorted([r for r in rows if r["temperature"] == temp], key=lambda r: int(r["k"]))
        axes[0].plot([int(r["k"]) for r in sub], [float(r["norm_l2"]) for r in sub], marker="o", label=f"$\\tau$={temp}")
        axes[1].plot([int(r["k"]) for r in sub], [float(r["n_eff"]) for r in sub], marker="s", label=f"$\\tau$={temp}")
    for ax in axes:
        ax.axvline(5, color="#444444", linestyle="--", linewidth=1.0, alpha=0.7)
        ax.set_xlabel("K")
        ax.grid(alpha=0.25)
        ax.legend(fontsize=8)
    axes[0].set_title("EPR Sensitivity (softmax weighting)")
    axes[0].set_ylabel("Normalized L2 (lower is better)")
    axes[1].set_title("Provenance Spread")
    axes[1].set_ylabel("Effective exemplars")
    fig.tight_layout()
    out = out_dir / "epr_sensitivity_result_curve.pdf"
    fig.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Regenerate E9 paper diagnostic figures.")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    args = parser.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    import matplotlib

    matplotlib.use("Agg")
    matplotlib.rcParams["pdf.fonttype"] = 42
    matplotlib.rcParams["ps.fonttype"] = 42
    matplotlib.rcParams["font.size"] = 9
    matplotlib.rcParams["axes.titlesize"] = 10
    matplotlib.rcParams["axes.labelsize"] = 9
    matplotlib.rcParams["xtick.labelsize"] = 8
    matplotlib.rcParams["ytick.labelsize"] = 8
    matplotlib.rcParams["legend.fontsize"] = 8
    plot_robustness(out_dir)
    plot_epr(out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
