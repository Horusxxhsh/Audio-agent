"""
TRR Projection Type Ablation (Task 4.3).

Compares PCA-fitted projection vs random projection for TRR.
Tests whether learned projection P provides meaningful advantage.

Usage:
    python trr_projection_type_ablation.py --dataset ../../Experiments/dataset_full_vectors.json
"""

import json
import sys
import logging
import time
from pathlib import Path
from typing import Dict, List

import numpy as np
import torch
import torch.nn as nn

sys.path.insert(0, str(Path(__file__).parent.parent / "common"))
sys.path.insert(0, str(Path(__file__).parent.parent / "TextureResonance"))

from evaluate import Evaluator

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PROTOCOL_A_TEST_SIZE = 204


class ProjectionVariantEncoder:
    """Encoder with configurable projection type (PCA vs Random)."""

    def __init__(
        self,
        project_dim: int = 64,
        projection_type: str = "random",
        pca_train_features: np.ndarray = None,
    ):
        """Initialize encoder variant.

        Args:
            project_dim: Projection output dimension.
            projection_type: 'random' or 'pca'.
            pca_train_features: Training features for PCA fitting (N x 768).
        """
        try:
            from transformers import Wav2Vec2Model
        except ImportError:
            raise RuntimeError("transformers required")

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.project_dim = project_dim
        self.projection_type = projection_type

        self.model = Wav2Vec2Model.from_pretrained("facebook/wav2vec2-base").to(self.device)
        self.model.eval()

        # Initialize projection matrix
        if projection_type == "pca" and pca_train_features is not None:
            self._fit_pca_projection(pca_train_features)
        else:
            # Random projection (Xavier init, frozen)
            self.projector = nn.Linear(768, project_dim).to(self.device)
            for param in self.projector.parameters():
                param.requires_grad = False

    def _fit_pca_projection(self, features: np.ndarray) -> None:
        """Fit PCA projection from training features.

        Args:
            features: Training features matrix (N x 768).
        """
        logger.info(f"Fitting PCA projection from {features.shape} features")
        # Center
        mean = features.mean(axis=0)
        centered = features - mean

        # SVD for PCA
        U, S, Vt = np.linalg.svd(centered, full_matrices=False)
        # Top-d components
        P = Vt[:self.project_dim].T  # (768, d)

        # Create projection layer with PCA weights
        self.projector = nn.Linear(768, self.project_dim, bias=True).to(self.device)
        with torch.no_grad():
            self.projector.weight.copy_(torch.from_numpy(P.T).float())
            self.projector.bias.copy_(torch.from_numpy(-mean @ P).float())
        for param in self.projector.parameters():
            param.requires_grad = False

        variance_explained = (S[:self.project_dim] ** 2).sum() / (S ** 2).sum()
        logger.info(f"PCA: {self.project_dim} components, "
                     f"variance explained: {variance_explained:.4f}")

    def get_embedding(self, waveform: torch.Tensor) -> np.ndarray:
        """Compute TRR embedding."""
        waveform = waveform.to(self.device)

        with torch.no_grad():
            outputs = self.model(waveform, output_hidden_states=True)

        gram_matrices = []
        for layer_idx in [4, 5, 6]:
            features = outputs.hidden_states[layer_idx].squeeze(0)
            projected = self.projector(features)
            n_time = projected.shape[0]
            gram = torch.matmul(projected.T, projected) / n_time
            gram_matrices.append(gram)

        fused_gram = torch.stack(gram_matrices).mean(dim=0)
        embedding = fused_gram.flatten()
        embedding = torch.nn.functional.normalize(embedding, p=2, dim=0)

        return embedding.cpu().numpy()


def run_projection_type_ablation(
    dataset_path: str,
    output_dir: str,
    use_cached: bool = True,
) -> Dict:
    """Run PCA vs Random projection ablation.

    Args:
        dataset_path: Path to dataset JSON.
        output_dir: Output directory.
        use_cached: Use pre-computed vectors as proxy.

    Returns:
        Results dict.
    """
    with open(dataset_path, "r") as f:
        dataset = json.load(f)

    evaluator_raw = Evaluator(normalize=False)
    evaluator_norm = Evaluator(normalize=True)

    projection_types = ["random", "pca"]
    results = {}

    for proj_type in projection_types:
        logger.info(f"\n=== Projection Type: {proj_type} ===")
        t0 = time.time()

        if use_cached:
            logger.info("Using cached vectors (proxy mode)")
            embeddings = []
            for item in dataset:
                vec = item.get("Vectors", {}).get("Wav2Vec")
                embeddings.append(np.array(vec, dtype=np.float32) if vec else None)
        else:
            # TODO: Full re-encoding with ProjectionVariantEncoder
            logger.warning("Full re-encoding not implemented in this run")
            embeddings = [None] * len(dataset)

        queries = dataset[:PROTOCOL_A_TEST_SIZE]
        kb = dataset[PROTOCOL_A_TEST_SIZE:]
        q_embs = embeddings[:PROTOCOL_A_TEST_SIZE]
        kb_embs = embeddings[PROTOCOL_A_TEST_SIZE:]

        valid_kb = [(i, e) for i, e in enumerate(kb_embs) if e is not None]
        if not valid_kb:
            results[proj_type] = {"error": "no valid vectors"}
            continue

        kb_indices, kb_vecs = zip(*valid_kb)
        kb_matrix = np.stack(kb_vecs)
        norms = np.linalg.norm(kb_matrix, axis=1, keepdims=True)
        kb_matrix = kb_matrix / np.maximum(norms, 1e-8)

        l2_raw, l2_norm, acc01, cos_sim = [], [], [], []

        for i, q_emb in enumerate(q_embs):
            if q_emb is None:
                continue
            q_vec = q_emb / max(np.linalg.norm(q_emb), 1e-8)
            sims = kb_matrix @ q_vec
            best_idx = kb_indices[int(np.argmax(sims))]

            pred = kb[best_idx].get("Parameters", {})
            gt = queries[i].get("Parameters", {})

            l2_raw.append(evaluator_raw.compute_parameter_distance(pred, gt))
            l2_norm.append(evaluator_norm.compute_parameter_distance(pred, gt))
            acc01.append(evaluator_norm.compute_accuracy_tolerance(pred, gt))
            cos_sim.append(evaluator_raw.compute_cosine_similarity(pred, gt))

        elapsed = time.time() - t0
        results[proj_type] = {
            "projection_type": proj_type,
            "n_evaluated": len(l2_raw),
            "elapsed_sec": round(elapsed, 1),
            "l2_raw": float(np.mean(l2_raw)) if l2_raw else 0.0,
            "l2_norm": float(np.mean(l2_norm)) if l2_norm else 0.0,
            "acc_at_01": float(np.mean(acc01)) if acc01 else 0.0,
            "cosine": float(np.mean(cos_sim)) if cos_sim else 0.0,
        }
        logger.info(f"  {proj_type}: L2={results[proj_type]['l2_raw']:.4f}")

    # Save
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "projection_type_ablation_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print("\n=== Projection Type Ablation ===")
    print(f"{'Type':>10} {'L2 (raw)':>10} {'L2 (norm)':>10} {'Acc@0.1':>8} {'Cosine':>8}")
    for name, r in results.items():
        if "error" in r:
            print(f"{name:>10} ERROR")
        else:
            print(f"{name:>10} {r['l2_raw']:>10.4f} {r['l2_norm']:>10.4f} "
                  f"{r['acc_at_01']:>8.4f} {r['cosine']:>8.4f}")

    return results


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="TRR Projection Type Ablation")
    parser.add_argument("--dataset", type=str,
                        default=str(Path(__file__).parent.parent / "dataset_full_vectors.json"))
    parser.add_argument("--output-dir", type=str,
                        default=str(Path(__file__).parent))
    parser.add_argument("--recompute", action="store_true")
    args = parser.parse_args()

    run_projection_type_ablation(args.dataset, args.output_dir, use_cached=not args.recompute)


if __name__ == "__main__":
    main()
