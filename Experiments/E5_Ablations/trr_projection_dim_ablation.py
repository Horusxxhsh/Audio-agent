"""
TRR Projection Dimension Ablation (Task 4.1).

Compares Protocol-A performance across projection dims d ∈ {32, 64, 128, 256}.
Recomputes Gram matrix embeddings for each dimension, then evaluates retrieval.

Usage:
    python trr_projection_dim_ablation.py --dataset ../../Experiments/dataset_full_vectors.json
"""

import json
import sys
import logging
import time
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).parent.parent / "common"))
sys.path.insert(0, str(Path(__file__).parent.parent / "TextureResonance"))

from evaluate import Evaluator
from texture_encoder import TextureEncoder

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PROTOCOL_A_TEST_SIZE = 204
PROJECTION_DIMS = [32, 64, 128, 256]


def compute_embeddings_for_dim(
    dataset: List[Dict],
    project_dim: int,
) -> List[np.ndarray]:
    """Compute TRR embeddings for all items with given projection dim.

    Args:
        dataset: Dataset items with AudioPath.
        project_dim: Projection dimension d.

    Returns:
        List of embedding arrays (or None for failed items).
    """
    encoder = TextureEncoder(project_dim=project_dim)
    embeddings = []

    for i, item in enumerate(dataset):
        audio_path = item.get("AudioPath", "")
        if not Path(audio_path).exists():
            # Try relative path
            alt_path = Path(__file__).parent.parent.parent / "Data" / Path(audio_path).name
            if alt_path.exists():
                audio_path = str(alt_path)
            else:
                embeddings.append(None)
                continue

        try:
            emb = encoder.get_embedding(audio_path)
            embeddings.append(emb)
        except Exception as e:
            logger.warning(f"Failed to encode item {i}: {e}")
            embeddings.append(None)

        if (i + 1) % 50 == 0:
            logger.info(f"  Encoded {i + 1}/{len(dataset)} (dim={project_dim})")

    return embeddings


def evaluate_retrieval(
    queries: List[Dict],
    kb: List[Dict],
    q_embeddings: List,
    kb_embeddings: List,
) -> Dict[str, float]:
    """Evaluate cosine retrieval with given embeddings.

    Args:
        queries: Test query items.
        kb: Knowledge base items.
        q_embeddings: Query embeddings.
        kb_embeddings: KB embeddings.

    Returns:
        Metrics dict.
    """
    evaluator_raw = Evaluator(normalize=False)
    evaluator_norm = Evaluator(normalize=True)

    # Build KB matrix (filter None)
    valid_kb = [(i, emb) for i, emb in enumerate(kb_embeddings) if emb is not None]
    if not valid_kb:
        return {"l2_raw": 0.0, "l2_norm": 0.0, "acc_at_01": 0.0, "cosine": 0.0}

    kb_indices, kb_vecs = zip(*valid_kb)
    kb_matrix = np.stack(kb_vecs)
    # L2 normalize
    norms = np.linalg.norm(kb_matrix, axis=1, keepdims=True)
    kb_matrix = kb_matrix / np.maximum(norms, 1e-8)

    l2_raw, l2_norm, acc01, cos_sim = [], [], [], []

    for i, q_emb in enumerate(q_embeddings):
        if q_emb is None:
            continue

        q_vec = q_emb / max(np.linalg.norm(q_emb), 1e-8)
        sims = kb_matrix @ q_vec
        best_idx = kb_indices[int(np.argmax(sims))]

        pred_params = kb[best_idx].get("Parameters", {})
        gt_params = queries[i].get("Parameters", {})

        l2_raw.append(evaluator_raw.compute_parameter_distance(pred_params, gt_params))
        l2_norm.append(evaluator_norm.compute_parameter_distance(pred_params, gt_params))
        acc01.append(evaluator_norm.compute_accuracy_tolerance(pred_params, gt_params))
        cos_sim.append(evaluator_raw.compute_cosine_similarity(pred_params, gt_params))

    return {
        "l2_raw": float(np.mean(l2_raw)) if l2_raw else 0.0,
        "l2_norm": float(np.mean(l2_norm)) if l2_norm else 0.0,
        "acc_at_01": float(np.mean(acc01)) if acc01 else 0.0,
        "cosine": float(np.mean(cos_sim)) if cos_sim else 0.0,
        "n_evaluated": len(l2_raw),
    }


def main() -> None:
    """Run projection dimension ablation."""
    import argparse
    parser = argparse.ArgumentParser(description="TRR Projection Dim Ablation")
    parser.add_argument("--dataset", type=str,
                        default=str(Path(__file__).parent.parent / "dataset_full_vectors.json"))
    parser.add_argument("--output-dir", type=str,
                        default=str(Path(__file__).parent))
    parser.add_argument("--use-cached-vectors", action="store_true",
                        help="Use pre-computed Wav2Vec vectors instead of re-encoding")
    args = parser.parse_args()

    with open(args.dataset, "r") as f:
        dataset = json.load(f)

    results = {}
    for dim in PROJECTION_DIMS:
        logger.info(f"\n=== Projection Dim = {dim} ===")
        t0 = time.time()

        if args.use_cached_vectors:
            # Use existing Wav2Vec vectors as proxy (same for all dims in this mode)
            logger.info("Using cached vectors (proxy mode)")
            embeddings = []
            for item in dataset:
                vec = item.get("Vectors", {}).get("Wav2Vec")
                embeddings.append(np.array(vec, dtype=np.float32) if vec else None)
        else:
            embeddings = compute_embeddings_for_dim(dataset, dim)

        test_embs = embeddings[:PROTOCOL_A_TEST_SIZE]
        kb_embs = embeddings[PROTOCOL_A_TEST_SIZE:]
        queries = dataset[:PROTOCOL_A_TEST_SIZE]
        kb = dataset[PROTOCOL_A_TEST_SIZE:]

        metrics = evaluate_retrieval(queries, kb, test_embs, kb_embs)
        elapsed = time.time() - t0

        results[str(dim)] = {
            "projection_dim": dim,
            "embedding_dim": dim * dim,
            "elapsed_sec": round(elapsed, 1),
            **metrics,
        }
        logger.info(f"  d={dim}: L2={metrics['l2_raw']:.4f}, Acc={metrics['acc_at_01']:.4f}, "
                     f"Cosine={metrics['cosine']:.4f}")

    # Save
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "projection_dim_ablation_results.json", "w") as f:
        json.dump(results, f, indent=2)

    # Print summary table
    print("\n=== Projection Dimension Ablation ===")
    print(f"{'Dim':>6} {'Emb Size':>10} {'L2 (raw)':>10} {'L2 (norm)':>10} {'Acc@0.1':>8} {'Cosine':>8}")
    for dim_str, r in results.items():
        print(f"{r['projection_dim']:>6} {r['embedding_dim']:>10} {r['l2_raw']:>10.4f} "
              f"{r['l2_norm']:>10.4f} {r['acc_at_01']:>8.4f} {r['cosine']:>8.4f}")


if __name__ == "__main__":
    main()
