"""Plot paper-facing TRR mechanism diagnostics from the P0 mechanism artifact."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SUMMARY = REPO_ROOT / "Experiments" / "E5_Ablations" / "outputs" / "p0_trr_mechanism" / "p0_trr_mechanism_summary.csv"
DEFAULT_OUT = REPO_ROOT / "Paper" / "figures" / "trr_layer_selection.pdf"


DISPLAY_ORDER = [
    "mean_pool_l5",
    "mean_pool_l456",
    "gram_no_projection_l5",
    "gram_l4_d64",
    "gram_l5_d64",
    "gram_l6_d64",
    "gram_l456_d32",
    "gram_l456_d64",
    "gram_l456_d64_no_l2",
]

DISPLAY_LABELS = {
    "mean_pool_l5": "Mean L5",
    "mean_pool_l456": "Mean L4-6",
    "gram_no_projection_l5": "Gram L5 full",
    "gram_l4_d64": "Gram L4 d64",
    "gram_l5_d64": "Gram L5 d64",
    "gram_l6_d64": "Gram L6 d64",
    "gram_l456_d32": "Gram L4-6 d32",
    "gram_l456_d64": "Gram L4-6 d64",
    "gram_l456_d64_no_l2": "Gram no L2",
}


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    by_name = {row["variant"]: row for row in rows}
    return [by_name[name] for name in DISPLAY_ORDER if name in by_name]


def main() -> int:
    parser = argparse.ArgumentParser(description="Plot TRR mechanism diagnostic figure.")
    parser.add_argument("--summary", default=str(DEFAULT_SUMMARY))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args()

    rows = load_rows(Path(args.summary))
    if not rows:
        raise SystemExit(f"No rows loaded from {args.summary}")

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels = [DISPLAY_LABELS.get(row["variant"], row["variant"]) for row in rows]
    values = [float(row["norm_l2_mean"]) for row in rows]
    colors = [
        "#6c757d" if row["family"] == "mean_pool" else "#2b8cbe" if row["l2_normalize"] == "True" else "#d95f0e"
        for row in rows
    ]

    fig, ax = plt.subplots(figsize=(10.5, 4.8))
    ax.bar(range(len(rows)), values, color=colors, alpha=0.88)
    ax.set_ylabel("Normalized L2 (lower is better)")
    ax.set_title("TRR Mechanism Diagnostic on 204-Query Split")
    ax.set_xticks(range(len(rows)))
    ax.set_xticklabels(labels, rotation=35, ha="right")
    ax.grid(axis="y", alpha=0.25)
    best_idx = min(range(len(values)), key=lambda i: values[i])
    ax.annotate(
        "best observed",
        xy=(best_idx, values[best_idx]),
        xytext=(best_idx, values[best_idx] + 0.018),
        ha="center",
        arrowprops={"arrowstyle": "->", "linewidth": 0.8},
        fontsize=9,
    )
    fig.tight_layout()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
