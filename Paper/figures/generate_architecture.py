"""Regenerate the paper's retrieval-grounded framework figure as a vector PDF.

Two-panel honest architecture:
  (a) Evaluated offline protocol (frozen E9 artifacts)
  (b) Implemented real-time plugin (Source/PluginAudioProcessor.cpp DSP order)

Output: Paper/figures/retrieval_grounded_pipeline.pdf
Fonts: Type 42 (TrueType) embedded, grayscale-safe.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
matplotlib.rcParams["pdf.fonttype"] = 42
matplotlib.rcParams["ps.fonttype"] = 42
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

OUT = Path(__file__).resolve().parent / "retrieval_grounded_pipeline.pdf"

DSP_MODULES = [
    "Compressor", "Equaliser", "Screamer", "Driver",
    "Delay", "Chorus", "Phaser", "Flanger", "Reverb",
]


def _box(ax, x, y, w, h, text, fc="#eef3fb", ec="#2f4f8f", ls="-", fs=15.0, bold=False, lw=1.4):
    ax.add_patch(
        FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0.25,rounding_size=0.8",
            fc=fc, ec=ec, lw=lw, ls=ls,
        )
    )
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fs, fontweight="bold" if bold else "normal", wrap=True)


def _arrow(ax, x1, y1, x2, y2, ls="-", color="#222222", lw=1.5):
    ax.add_patch(
        FancyArrowPatch(
            (x1, y1), (x2, y2),
            arrowstyle="-|>", mutation_scale=14,
            ls=ls, color=color, lw=lw,
            shrinkA=2, shrinkB=2,
        )
    )


def main() -> None:
    fig, ax = plt.subplots(figsize=(13.6, 6.4))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    # ---------------------------------------------------------------- (a)
    ax.text(1, 97.5, "(a) Evaluated offline protocol",
            fontsize=16, fontweight="bold", va="top")

    box_h, box_w = 11.0, 15.0
    y1, y2, y3 = 84.0, 68.0, 52.0

    # row 1: inputs -> TRR -> Top-K -> EPR
    _box(ax, 1, y1, 12, box_h, "Audio Reference", fc="#e8f5e9", ec="#2e7d32", bold=True)
    _box(ax, 20, y1, 17, box_h, "Cached TRR Descriptor\n(Gram of mid-level Wav2Vec2)",
         fc="#eef3fb", ec="#2f4f8f")
    _box(ax, 43, y1, 18, box_h, "Cosine Top-K Retrieval\n(1,063-preset KB)",
         fc="#eef3fb", ec="#2f4f8f")
    _box(ax, 67, y1, 17, box_h, "EPR-K5 Projection\n(softmax blend)",
         fc="#eef3fb", ec="#2f4f8f")

    # row 0: optional text
    _box(ax, 1, y2, 12, box_h, "Optional Text Query", fc="#f5f5f5", ec="#888888", ls="--")
    _arrow(ax, 13, y2 + box_h / 2, 20, y1 + box_h / 2, ls="--", color="#666666")

    _arrow(ax, 13, y1 + box_h / 2, 20, y1 + box_h / 2)
    _arrow(ax, 37, y1 + box_h / 2, 43, y1 + box_h / 2)
    _arrow(ax, 61, y1 + box_h / 2, 67, y1 + box_h / 2)

    # row 2: validity + parameter output
    _box(ax, 67, y2, 17, box_h, "Validity Check\n(range / finite / On-Off)",
         fc="#fff8e1", ec="#b26a00")
    _box(ax, 43, y3, 18, box_h, "Editable Parameter Vector\n(offline output)",
         fc="#e8f5e9", ec="#2e7d32", bold=True)
    _arrow(ax, 75.5, y1, 75.5, y2 + box_h)
    _arrow(ax, 67, y2 + box_h / 2, 61, y3 + box_h / 2)
    _arrow(ax, 13, y3 + box_h / 2, 43, y3 + box_h / 2, ls=":", color="#888888")

    ax.text(24, y2 + box_h / 2 + 1.2, "(audio reference optional; text not used in the\n"
            "reported objective protocol)", fontsize=15, color="#555555", ha="left", va="bottom")

    # ------------------------------------------------------------- bridge
    ax.plot([2, 98], [44.5, 44.5], ls=(0, (4, 3)), color="#333333", lw=1.2)
    ax.text(50, 45.4, "deployment bridge not validated (legacy file polling)",
            ha="center", va="bottom", fontsize=15, color="#333333", style="italic")

    # ---------------------------------------------------------------- (b)
    ax.text(1, 41.5, "(b) Implemented real-time plugin", fontsize=16,
            fontweight="bold", va="top")

    yb, bh = 22.0, 11.0
    n = len(DSP_MODULES) + 2
    span = 98.0
    bw = span / n - 0.6
    x = 1.0
    _box(ax, x, yb, bw + 1.2, bh, "Dry Guitar\nInput", fc="#e8f5e9", ec="#2e7d32", bold=True)
    x += bw + 1.2 + 0.6
    for i, mod in enumerate(DSP_MODULES):
        _box(ax, x, yb, bw, bh, mod, fc="#eef3fb", ec="#2f4f8f")
        _arrow(ax, x - 0.6, yb + bh / 2, x, yb + bh / 2)
        x += bw + 0.6
    _box(ax, x, yb, bw + 1.2, bh, "Processed\nAudio Output", fc="#e8f5e9", ec="#2e7d32", bold=True)
    _arrow(ax, x - 0.6, yb + bh / 2, x, yb + bh / 2)

    ax.text(1, 19.5,
            "The nine modules form a simplified subset of the implemented chain, which also "
            "includes input gating, gain staging, four wave-shaping stages, bit-crushing, "
            "cabinet impulse response, and limiting.",
            fontsize=15, color="#555555", ha="left", va="top")

    fig.savefig(OUT, dpi=300, bbox_inches="tight", transparent=False)
    plt.close(fig)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
