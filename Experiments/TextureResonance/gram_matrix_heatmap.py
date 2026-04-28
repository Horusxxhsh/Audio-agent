"""
Gram Matrix Heatmap Visualization (Task 7.2).

Generates representative Gram matrix heatmaps for selected query presets,
showing the second-order co-activation structure captured by TRR.

Usage:
    python gram_matrix_heatmap.py --dataset ../../Experiments/dataset_full_vectors.json
"""

import json
import sys
import logging
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def reconstruct_gram_from_vec(
    vec: np.ndarray,
    project_dim: int = 32,
) -> np.ndarray:
    """Reconstruct Gram matrix from flattened L2-normalized TRR vector.

    The TRR pipeline: Gram (d x d) -> flatten -> L2-normalize.
    We reverse: un-flatten to (d x d). Note that L2 normalization
    is not invertible for magnitude, but the pattern structure is preserved.

    Args:
        vec: Flattened TRR vector.
        project_dim: Projection dimension used in encoding.

    Returns:
        Gram matrix (d x d).
    """
    expected_dim = project_dim * project_dim
    if len(vec) != expected_dim:
        # Try to infer project_dim
        d = int(np.sqrt(len(vec)))
        if d * d == len(vec):
            project_dim = d
        else:
            logger.warning(f"Vector dim {len(vec)} is not a perfect square, "
                           f"using first {expected_dim} elements")
            vec = vec[:expected_dim]

    gram = vec.reshape(project_dim, project_dim)
    return gram


def select_representative_queries(
    dataset: List[Dict],
    n_samples: int = 6,
) -> List[int]:
    """Select diverse representative queries by style.

    Args:
        dataset: Full dataset.
        n_samples: Number of samples to select.

    Returns:
        List of dataset indices.
    """
    style_groups: Dict[str, List[int]] = {}
    for i, item in enumerate(dataset[:204]):  # Protocol-A test set
        style = item.get("Style", "Unknown")
        if not isinstance(style, str):
            style = "Unknown"
        if style not in style_groups:
            style_groups[style] = []
        style_groups[style].append(i)

    # Select one from each unique style, up to n_samples
    selected = []
    sorted_styles = sorted(style_groups.keys(), key=lambda s: -len(style_groups[s]))
    for style in sorted_styles:
        if len(selected) >= n_samples:
            break
        indices = style_groups[style]
        # Pick the first with valid vector
        for idx in indices:
            vec = dataset[idx].get("Vectors", {}).get("Wav2Vec")
            if vec is not None:
                selected.append(idx)
                break

    return selected


def plot_gram_heatmaps(
    grams: List[np.ndarray],
    titles: List[str],
    output_path: str,
) -> None:
    """Generate a grid of Gram matrix heatmaps.

    Args:
        grams: List of Gram matrices.
        titles: Subplot titles.
        output_path: Output PDF path.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        logger.error("matplotlib required for plotting")
        raise

    n = len(grams)
    ncols = min(3, n)
    nrows = (n + ncols - 1) // ncols

    fig, axes = plt.subplots(nrows, ncols, figsize=(4 * ncols, 3.5 * nrows))
    if n == 1:
        axes = np.array([axes])
    axes = axes.flatten()

    for i, (gram, title) in enumerate(zip(grams, titles)):
        ax = axes[i]
        im = ax.imshow(gram, cmap="viridis", aspect="equal", interpolation="nearest")
        ax.set_title(title, fontsize=10, fontweight="bold")
        ax.set_xlabel("Channel $j$", fontsize=9)
        ax.set_ylabel("Channel $i$", fontsize=9)
        ax.tick_params(labelsize=7)
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

    # Hide unused axes
    for j in range(n, len(axes)):
        axes[j].set_visible(False)

    fig.suptitle("TRR Gram Matrix Heatmaps (Representative Queries)",
                 fontsize=13, fontweight="bold")
    fig.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"Gram heatmap figure saved to {output_path}")


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Gram Matrix Heatmap Visualization")
    parser.add_argument("--dataset", type=str,
                        default=str(Path(__file__).parent.parent / "dataset_full_vectors.json"))
    parser.add_argument("--output-dir", type=str, default=None,
                        help="Output directory (default: Paper/figures/)")
    parser.add_argument("--n-samples", type=int, default=6)
    parser.add_argument("--project-dim", type=int, default=32,
                        help="Projection dim used in TRR (must match encoding)")
    args = parser.parse_args()

    with open(args.dataset, "r") as f:
        dataset = json.load(f)
    logger.info(f"Loaded {len(dataset)} items")

    # Select representative queries
    indices = select_representative_queries(dataset, n_samples=args.n_samples)
    logger.info(f"Selected {len(indices)} representative queries: {indices}")

    grams = []
    titles = []
    for idx in indices:
        item = dataset[idx]
        vec = np.array(item["Vectors"]["Wav2Vec"], dtype=np.float32)
        gram = reconstruct_gram_from_vec(vec, project_dim=args.project_dim)
        grams.append(gram)

        style = item.get("Style", "Unknown")
        song = item.get("SongName", f"Query {idx}")
        titles.append(f"{song}\n({style})")

    out_dir = args.output_dir or str(Path(__file__).parent.parent.parent / "Paper" / "figures")
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    output_path = str(Path(out_dir) / "gram_matrix_examples.pdf")

    plot_gram_heatmaps(grams, titles, output_path)


if __name__ == "__main__":
    main()
