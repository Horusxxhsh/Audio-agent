"""
t-SNE Visualization: TRR vs Wav2Vec2 Mean-Pooled (Task 7.1).

Generates a side-by-side t-SNE scatter plot comparing TRR Gram-based
embeddings against Wav2Vec2 mean-pooled embeddings, colored by style label.

Usage:
    python trr_tsne_visualization.py --dataset ../../Experiments/dataset_full_vectors.json
"""

import json
import sys
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Style label color palette (colorblind-friendly)
STYLE_COLORS = {
    "Blues": "#1f77b4",
    "Jazz": "#ff7f0e",
    "Rock": "#2ca02c",
    "Metal": "#d62728",
    "Clean": "#9467bd",
    "Ambient": "#8c564b",
    "Funk": "#e377c2",
    "Country": "#7f7f7f",
    "Pop": "#bcbd22",
    "Other": "#17becf",
}

DEFAULT_COLOR = "#aaaaaa"


def get_style_label(item: Dict) -> str:
    """Extract a simplified style label from item metadata.

    Args:
        item: Dataset item dict.

    Returns:
        Style label string.
    """
    style = item.get("Style", "")
    if isinstance(style, list):
        style_lower = " ".join(str(x) for x in style).lower()
    elif isinstance(style, str):
        style_lower = style.lower()
    else:
        return "Other"
    for key in STYLE_COLORS:
        if key.lower() in style_lower:
            return key
    return "Other"


def build_embedding_matrices(
    dataset: List[Dict],
) -> Tuple[np.ndarray, np.ndarray, List[str]]:
    """Build TRR and mean-pooled embedding matrices from cached vectors.

    TRR embeddings are read from cached `Vectors["TRR"]` entries, while
    mean-pooled Wav2Vec2 embeddings are read from cached `Vectors["Wav2Vec"]`
    entries. Records missing either vector are excluded so the two panels
    are drawn over the same item set.

    Args:
        dataset: Full dataset list.

    Returns:
        trr_matrix: (N, D_trr) TRR embedding matrix.
        mp_matrix: (N, D_mp) Mean-pooled embedding matrix.
        labels: Style labels per item.
    """
    trr_vecs = []
    mp_vecs = []
    labels = []
    valid_indices = []

    for i, item in enumerate(dataset):
        vectors = item.get("Vectors", {})
        trr_vec = vectors.get("TRR") if isinstance(vectors, dict) else None
        wav_vec = vectors.get("Wav2Vec") if isinstance(vectors, dict) else None
        if trr_vec is not None and wav_vec is not None and len(trr_vec) == 4096 and len(wav_vec) == 768:
            trr_vecs.append(np.array(trr_vec, dtype=np.float32))
            mp_vecs.append(np.array(wav_vec, dtype=np.float32))
            labels.append(get_style_label(item))
            valid_indices.append(i)

    trr_matrix = np.stack(trr_vecs)
    mp_matrix = np.stack(mp_vecs)
    logger.info(f"TRR matrix: {trr_matrix.shape}")
    logger.info(f"Wav2Vec matrix: {mp_matrix.shape}")
    # Apply L2 normalization
    norms = np.linalg.norm(mp_matrix, axis=1, keepdims=True)
    mp_matrix = mp_matrix / np.maximum(norms, 1e-8)

    return trr_matrix, mp_matrix, labels


def compute_tsne(
    matrix: np.ndarray,
    perplexity: float = 30.0,
    n_iter: int = 1000,
    random_state: int = 42,
) -> np.ndarray:
    """Compute t-SNE 2D embedding.

    Args:
        matrix: Input matrix (N, D).
        perplexity: t-SNE perplexity.
        n_iter: Number of iterations.
        random_state: Random seed.

    Returns:
        2D coordinates (N, 2).
    """
    try:
        from sklearn.manifold import TSNE
    except ImportError:
        logger.error("scikit-learn required for t-SNE. Install: pip install scikit-learn")
        raise

    kwargs = {
        "n_components": 2,
        "perplexity": min(perplexity, matrix.shape[0] - 1),
        "random_state": random_state,
        "metric": "cosine",
        "init": "random",
    }
    import inspect
    if "max_iter" in inspect.signature(TSNE).parameters:
        kwargs["max_iter"] = n_iter
    else:
        kwargs["n_iter"] = n_iter
    tsne = TSNE(**kwargs)
    return tsne.fit_transform(matrix)


def plot_tsne_comparison(
    trr_coords: np.ndarray,
    mp_coords: np.ndarray,
    labels: List[str],
    output_path: str,
) -> None:
    """Generate side-by-side t-SNE scatter plot.

    Args:
        trr_coords: (N, 2) TRR t-SNE coordinates.
        mp_coords: (N, 2) Mean-pooled t-SNE coordinates.
        labels: Style labels per point.
        output_path: Output PDF path.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        matplotlib.rcParams["pdf.fonttype"] = 42
        matplotlib.rcParams["ps.fonttype"] = 42
        matplotlib.rcParams["font.size"] = 17
        matplotlib.rcParams["axes.titlesize"] = 18
        matplotlib.rcParams["legend.fontsize"] = 8
        import matplotlib.pyplot as plt
        from matplotlib.lines import Line2D
    except ImportError:
        logger.error("matplotlib required for plotting")
        raise

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(6.8, 3.0))

    unique_labels = sorted(set(labels))
    markers = ["o", "s", "^", "D", "v", "P", "X", "h", "8", "*"]
    for i, label in enumerate(unique_labels):
        mask = [l == label for l in labels]
        color = STYLE_COLORS.get(label, DEFAULT_COLOR)
        marker = markers[i % len(markers)]

        idx = np.where(mask)[0]
        ax1.scatter(trr_coords[idx, 0], trr_coords[idx, 1],
                    c=color, marker=marker, s=12, alpha=0.6, edgecolors="none")
        ax2.scatter(mp_coords[idx, 0], mp_coords[idx, 1],
                    c=color, marker=marker, s=12, alpha=0.6, edgecolors="none")

    ax1.set_title("TRR (Gram Matrix Embedding)", fontsize=10, fontweight="bold")
    ax2.set_title("Wav2Vec2 Mean-Pooled", fontsize=10, fontweight="bold")

    for ax in [ax1, ax2]:
        ax.set_xticks([])
        ax.set_yticks([])
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    # Legend
    legend_elements = [
        Line2D([0], [0], marker=markers[i % len(markers)], color="w",
               markerfacecolor=STYLE_COLORS.get(l, DEFAULT_COLOR),
               markersize=8, label=l)
        for i, l in enumerate(unique_labels)
    ]
    fig.legend(handles=legend_elements, loc="lower center",
               ncol=min(len(unique_labels), 5), fontsize=8,
               frameon=False, bbox_to_anchor=(0.5, -0.02))

    fig.suptitle("t-SNE Comparison: TRR vs Wav2Vec2 Mean-Pooled Embeddings",
                 fontsize=10, fontweight="bold", y=1.02)
    fig.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"t-SNE figure saved to {output_path}")


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="t-SNE Visualization")
    parser.add_argument("--dataset", type=str,
                        default=str(Path(__file__).parent.parent / "dataset_full_vectors.json"))
    parser.add_argument("--output-dir", type=str, default=None,
                        help="Output directory (default: Paper/figures/)")
    parser.add_argument("--perplexity", type=float, default=30.0)
    parser.add_argument("--max-items", type=int, default=None,
                        help="Limit items for faster computation")
    args = parser.parse_args()

    with open(args.dataset, "r") as f:
        dataset = json.load(f)
    logger.info(f"Loaded {len(dataset)} items")

    if args.max_items and args.max_items < len(dataset):
        dataset = dataset[:args.max_items]
        logger.info(f"Truncated to {len(dataset)} items")

    trr_matrix, mp_matrix, labels = build_embedding_matrices(dataset)

    logger.info("Computing t-SNE for TRR embeddings...")
    trr_coords = compute_tsne(trr_matrix, perplexity=args.perplexity)

    logger.info("Computing t-SNE for mean-pooled embeddings...")
    mp_coords = compute_tsne(mp_matrix, perplexity=args.perplexity)

    out_dir = args.output_dir or str(Path(__file__).parent.parent.parent / "Paper" / "figures")
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    output_path = str(Path(out_dir) / "trr_vs_wav2vec_tsne.pdf")

    plot_tsne_comparison(trr_coords, mp_coords, labels, output_path)


if __name__ == "__main__":
    main()
