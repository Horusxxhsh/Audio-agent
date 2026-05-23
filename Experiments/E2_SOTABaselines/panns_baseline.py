"""
PANNs Baseline Protocol-A Evaluation (Task 3.1).

Loads PANNs CNN14 encoder, extracts embeddings for KB and queries,
performs cosine retrieval, and evaluates under Protocol-A.

Usage:
    python panns_baseline.py --dataset ../dataset_full_vectors.json
"""

import json
import sys
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "common"))
from evaluate import Evaluator

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PROTOCOL_A_TEST_SIZE = 204


def extract_panns_embeddings(
    dataset: List[Dict],
    cache_path: Optional[str] = None,
) -> List[Optional[np.ndarray]]:
    """Extract PANNs embeddings for all dataset items.

    If cache exists, load from cache. Otherwise compute and save.

    Args:
        dataset: Full dataset list.
        cache_path: Optional cache file path.

    Returns:
        List of embedding arrays (or None for failed items).
    """
    if cache_path and Path(cache_path).exists():
        logger.info(f"Loading PANNs embeddings from cache: {cache_path}")
        data = np.load(cache_path, allow_pickle=True)
        return [data[str(i)] if str(i) in data else None for i in range(len(dataset))]

    # Import encoder
    # Resolve Windows-style paths to Linux paths
    base_audio_dir = Path("/home/xyh/code/Audio-agent/Data/Audio_Synthetic")

    def resolve_path(audio_path: str) -> Optional[Path]:
        """Convert Windows path to Linux path and check existence."""
        if not audio_path:
            return None
        # Try direct path first
        p = Path(audio_path)
        if p.exists():
            return p
        # Extract basename and try under base audio dir
        basename = audio_path.replace("\\", "/").split("/")[-1]
        if basename:
            candidate = base_audio_dir / basename
            if candidate.exists():
                return candidate
        return None

    try:
        from panns_encoder import PANNsEncoder
    except ImportError:
        logger.error("panns_encoder.py not found in current directory")
        raise

    encoder = PANNsEncoder()
    embeddings = []

    for i, item in enumerate(dataset):
        audio_path = item.get("AudioPath", "")
        resolved = resolve_path(audio_path)
        if not resolved:
            embeddings.append(None)
            continue

        try:
            emb = encoder.encode_audio(str(resolved))
            embeddings.append(emb)
        except Exception as e:
            logger.warning(f"Failed to encode item {i}: {e}")
            embeddings.append(None)

        if (i + 1) % 100 == 0:
            logger.info(f"  Encoded {i + 1}/{len(dataset)}")

    # Save cache
    if cache_path:
        save_dict = {str(i): e for i, e in enumerate(embeddings) if e is not None}
        np.savez_compressed(cache_path, **save_dict)
        logger.info(f"Saved PANNs embeddings cache to {cache_path}")

    return embeddings


def evaluate_retrieval(
    dataset: List[Dict],
    embeddings: List[Optional[np.ndarray]],
    normalize: bool = True,
) -> Dict:
    """Evaluate PANNs retrieval under Protocol-A.

    Args:
        dataset: Full dataset.
        embeddings: Pre-computed embeddings.
        normalize: Whether to use normalized metrics.

    Returns:
        Results dict.
    """
    evaluator = Evaluator(normalize=normalize)

    queries = dataset[:PROTOCOL_A_TEST_SIZE]
    kb = dataset[PROTOCOL_A_TEST_SIZE:]
    q_embs = embeddings[:PROTOCOL_A_TEST_SIZE]
    kb_embs = embeddings[PROTOCOL_A_TEST_SIZE:]

    # Build KB matrix
    valid_kb = [(i, e) for i, e in enumerate(kb_embs) if e is not None]
    if not valid_kb:
        return {"error": "no valid KB embeddings"}

    kb_indices, kb_vecs = zip(*valid_kb)
    kb_matrix = np.stack(kb_vecs)
    norms = np.linalg.norm(kb_matrix, axis=1, keepdims=True)
    kb_matrix = kb_matrix / np.maximum(norms, 1e-8)

    l2_errors, acc01_scores, cosine_scores, recall_scores, module_scores = (
        [], [], [], [], []
    )
    n_evaluated = 0

    for i, q_emb in enumerate(q_embs):
        if q_emb is None:
            continue

        q_vec = q_emb / max(np.linalg.norm(q_emb), 1e-8)
        sims = kb_matrix @ q_vec
        best_idx = kb_indices[int(np.argmax(sims))]

        pred = kb[best_idx].get("Parameters", {})
        gt = queries[i].get("Parameters", {})

        l2_errors.append(evaluator.compute_parameter_distance(pred, gt))
        acc01_scores.append(evaluator.compute_accuracy_tolerance(pred, gt))
        cosine_scores.append(evaluator.compute_cosine_similarity(pred, gt))
        recall_scores.append(evaluator.compute_parameter_recall(pred, gt))
        module_scores.append(evaluator.compute_module_consistency(pred, gt))
        n_evaluated += 1

    return {
        "method": "PANNs (CNN14)",
        "n_evaluated": n_evaluated,
        "n_total": PROTOCOL_A_TEST_SIZE,
        "normalize": normalize,
        "L2": float(np.mean(l2_errors)) if l2_errors else 0.0,
        "Acc@0.1": float(np.mean(acc01_scores)) if acc01_scores else 0.0,
        "Cosine": float(np.mean(cosine_scores)) if cosine_scores else 0.0,
        "Recall": float(np.mean(recall_scores)) if recall_scores else 0.0,
        "Module": float(np.mean(module_scores)) if module_scores else 0.0,
        "L2_std": float(np.std(l2_errors)) if l2_errors else 0.0,
    }


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="PANNs Baseline Protocol-A Evaluation")
    parser.add_argument("--dataset", type=str,
                        default=str(Path(__file__).parent.parent / "dataset_full_vectors.json"))
    parser.add_argument("--cache", type=str, default=None,
                        help="PANNs embedding cache path (.npz)")
    parser.add_argument("--output-dir", type=str, default=str(Path(__file__).parent))
    parser.add_argument("--normalized", action="store_true",
                        help="Use min-max normalized metrics")
    args = parser.parse_args()

    with open(args.dataset, "r") as f:
        dataset = json.load(f)
    logger.info(f"Loaded {len(dataset)} items")

    cache_path = args.cache or str(Path(args.output_dir) / "panns_embeddings_cache.npz")
    embeddings = extract_panns_embeddings(dataset, cache_path=cache_path)

    n_valid = sum(1 for e in embeddings if e is not None)
    logger.info(f"Valid embeddings: {n_valid}/{len(dataset)}")

    # Evaluate both raw and normalized
    results_raw = evaluate_retrieval(dataset, embeddings, normalize=False)
    results_norm = evaluate_retrieval(dataset, embeddings, normalize=True)

    results = {"raw": results_raw, "normalized": results_norm}

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "panns_baseline_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print("\n=== PANNs Baseline Protocol-A ===")
    for mode, r in results.items():
        print(f"\n[{mode}]")
        print(f"  N={r['n_evaluated']}, L2={r['L2']:.4f}, Acc@0.1={r['Acc@0.1']:.4f}, "
              f"Cos={r['Cosine']:.4f}, Recall={r['Recall']:.4f}, Module={r['Module']:.4f}")

    logger.info(f"Results saved to {out / 'panns_baseline_results.json'}")


if __name__ == "__main__":
    main()
