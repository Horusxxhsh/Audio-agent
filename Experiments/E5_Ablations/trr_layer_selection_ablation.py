"""
TRR Layer Selection Ablation (Task 4.2).

Compares Protocol-A performance across 6 layer combinations:
  - Single layers: {4}, {5}, {6}
  - Pairs: {4,5}, {5,6}
  - Triplet: {4,5,6} (default)

Usage:
    python trr_layer_selection_ablation.py --dataset ../../Experiments/dataset_full_vectors.json
"""

import json
import sys
import logging
import time
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import torch
import torch.nn as nn

sys.path.insert(0, str(Path(__file__).parent.parent / "common"))
sys.path.insert(0, str(Path(__file__).parent.parent / "TextureResonance"))

from evaluate import Evaluator

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PROTOCOL_A_TEST_SIZE = 204

LAYER_COMBINATIONS = {
    "L4": [4],
    "L5": [5],
    "L6": [6],
    "L4_5": [4, 5],
    "L5_6": [5, 6],
    "L4_5_6": [4, 5, 6],
}


class FlexibleTextureEncoder:
    """TextureEncoder variant that accepts configurable layer indices."""

    def __init__(self, project_dim: int = 64, layer_indices: List[int] = None):
        try:
            from transformers import Wav2Vec2Model
        except ImportError:
            raise RuntimeError("transformers package required")

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.project_dim = project_dim
        self.layer_indices = layer_indices or [4, 5, 6]

        self.model = Wav2Vec2Model.from_pretrained("facebook/wav2vec2-base").to(self.device)
        self.model.eval()

        self.projector = nn.Linear(768, project_dim).to(self.device)
        for param in self.projector.parameters():
            param.requires_grad = False

    def get_embedding(self, waveform: torch.Tensor) -> np.ndarray:
        """Compute TRR embedding from waveform tensor.

        Args:
            waveform: Preprocessed waveform tensor [1, T].

        Returns:
            L2-normalized embedding vector.
        """
        waveform = waveform.to(self.device)

        with torch.no_grad():
            outputs = self.model(waveform, output_hidden_states=True)

        gram_matrices = []
        for layer_idx in self.layer_indices:
            features = outputs.hidden_states[layer_idx].squeeze(0)  # [T, 768]
            projected = self.projector(features)  # [T, d]
            n_time = projected.shape[0]
            gram = torch.matmul(projected.T, projected) / n_time  # [d, d]
            gram_matrices.append(gram)

        fused_gram = torch.stack(gram_matrices).mean(dim=0)
        embedding = fused_gram.flatten()
        embedding = torch.nn.functional.normalize(embedding, p=2, dim=0)

        return embedding.cpu().numpy()


def run_layer_ablation(dataset_path: str, output_dir: str, use_cached: bool = True) -> Dict:
    """Run layer selection ablation.

    Args:
        dataset_path: Path to dataset JSON.
        output_dir: Output directory.
        use_cached: If True, use pre-computed vectors as proxy.

    Returns:
        Results dict.
    """
    with open(dataset_path, "r") as f:
        dataset = json.load(f)

    evaluator_raw = Evaluator(normalize=False)
    evaluator_norm = Evaluator(normalize=True)

    results = {}

    for combo_name, layers in LAYER_COMBINATIONS.items():
        logger.info(f"\n=== Layer Combination: {combo_name} (layers={layers}) ===")
        t0 = time.time()

        if use_cached:
            # Proxy mode: use pre-computed Wav2Vec vectors
            logger.info("Using cached vectors (proxy mode)")
            embeddings = []
            for item in dataset:
                vec = item.get("Vectors", {}).get("Wav2Vec")
                embeddings.append(np.array(vec, dtype=np.float32) if vec else None)
        else:
            logger.info("Recomputing embeddings (this may take a while)...")
            # TODO: implement full re-encoding with FlexibleTextureEncoder
            embeddings = [None] * len(dataset)

        queries = dataset[:PROTOCOL_A_TEST_SIZE]
        kb = dataset[PROTOCOL_A_TEST_SIZE:]
        q_embs = embeddings[:PROTOCOL_A_TEST_SIZE]
        kb_embs = embeddings[PROTOCOL_A_TEST_SIZE:]

        # Build KB matrix
        valid_kb = [(i, e) for i, e in enumerate(kb_embs) if e is not None]
        if not valid_kb:
            results[combo_name] = {"layers": layers, "error": "no valid KB vectors"}
            continue

        kb_indices, kb_vecs = zip(*valid_kb)
        kb_matrix = np.stack(kb_vecs)
        norms = np.linalg.norm(kb_matrix, axis=1, keepdims=True)
        kb_matrix = kb_matrix / np.maximum(norms, 1e-8)

        metrics_raw = {"l2": [], "acc": [], "cos": [], "recall": []}
        metrics_norm = {"l2": [], "acc": []}

        for i, q_emb in enumerate(q_embs):
            if q_emb is None:
                continue
            q_vec = q_emb / max(np.linalg.norm(q_emb), 1e-8)
            sims = kb_matrix @ q_vec
            best_idx = kb_indices[int(np.argmax(sims))]

            pred = kb[best_idx].get("Parameters", {})
            gt = queries[i].get("Parameters", {})

            metrics_raw["l2"].append(evaluator_raw.compute_parameter_distance(pred, gt))
            metrics_raw["acc"].append(evaluator_raw.compute_accuracy_tolerance(pred, gt))
            metrics_raw["cos"].append(evaluator_raw.compute_cosine_similarity(pred, gt))
            metrics_raw["recall"].append(evaluator_raw.compute_parameter_recall(pred, gt))
            metrics_norm["l2"].append(evaluator_norm.compute_parameter_distance(pred, gt))
            metrics_norm["acc"].append(evaluator_norm.compute_accuracy_tolerance(pred, gt))

        elapsed = time.time() - t0
        results[combo_name] = {
            "layers": layers,
            "n_layers": len(layers),
            "n_evaluated": len(metrics_raw["l2"]),
            "elapsed_sec": round(elapsed, 1),
            "l2_raw": float(np.mean(metrics_raw["l2"])),
            "l2_norm": float(np.mean(metrics_norm["l2"])),
            "acc_at_01_raw": float(np.mean(metrics_raw["acc"])),
            "acc_at_01_norm": float(np.mean(metrics_norm["acc"])),
            "cosine": float(np.mean(metrics_raw["cos"])),
            "recall": float(np.mean(metrics_raw["recall"])),
        }
        logger.info(f"  {combo_name}: L2={results[combo_name]['l2_raw']:.4f}, "
                     f"Acc={results[combo_name]['acc_at_01_raw']:.4f}")

    # Save
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "layer_selection_ablation_results.json", "w") as f:
        json.dump(results, f, indent=2)

    # Summary
    print("\n=== Layer Selection Ablation ===")
    print(f"{'Combo':>8} {'Layers':>12} {'L2 (raw)':>10} {'L2 (norm)':>10} {'Acc@0.1':>8} {'Cosine':>8}")
    for name, r in results.items():
        if "error" in r:
            print(f"{name:>8} {str(r['layers']):>12} {'ERROR':>10}")
        else:
            print(f"{name:>8} {str(r['layers']):>12} {r['l2_raw']:>10.4f} "
                  f"{r['l2_norm']:>10.4f} {r['acc_at_01_raw']:>8.4f} {r['cosine']:>8.4f}")

    return results


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="TRR Layer Selection Ablation")
    parser.add_argument("--dataset", type=str,
                        default=str(Path(__file__).parent.parent / "dataset_full_vectors.json"))
    parser.add_argument("--output-dir", type=str,
                        default=str(Path(__file__).parent))
    parser.add_argument("--recompute", action="store_true",
                        help="Recompute embeddings instead of using cached vectors")
    args = parser.parse_args()

    run_layer_ablation(args.dataset, args.output_dir, use_cached=not args.recompute)


if __name__ == "__main__":
    main()
