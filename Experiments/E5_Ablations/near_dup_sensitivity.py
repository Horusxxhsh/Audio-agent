"""
E5: Near-Duplicate Sensitivity Analysis

Evaluates robustness of all retrieval methods under KB deduplication.
Tests whether TRR advantage holds when near-duplicate presets are removed.

Usage:
    python near_dup_sensitivity.py --dataset ../../Experiments/dataset_full_vectors.json
"""

import json
import sys
import logging
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, field

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "common"))
sys.path.insert(0, str(Path(__file__).parent.parent / "TextureResonance"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "Source"))

from evaluate import Evaluator
from near_dup_filter import find_near_duplicates, get_indices_to_remove, filter_dataset

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Protocol-A split: first 204 = test queries, rest = KB
PROTOCOL_A_TEST_SIZE = 204


@dataclass
class SensitivityConfig:
    """Configuration for near-duplicate sensitivity experiment."""
    dataset_path: str = ""
    thresholds: List[float] = field(default_factory=lambda: [0.005, 0.01, 0.02, 0.05])
    output_dir: str = "./results/E5_Ablations"
    normalize_metrics: bool = True


def split_protocol_a(dataset: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    """Split dataset into Protocol-A test queries and knowledge base.

    Args:
        dataset: Full dataset list.

    Returns:
        (test_queries, knowledge_base) tuple.
    """
    test_queries = dataset[:PROTOCOL_A_TEST_SIZE]
    knowledge_base = dataset[PROTOCOL_A_TEST_SIZE:]
    return test_queries, knowledge_base


def cosine_retrieval(
    query_vec: np.ndarray,
    kb_vectors: np.ndarray,
    kb_items: List[Dict],
) -> Dict:
    """Retrieve best match from KB by cosine similarity.

    Args:
        query_vec: Query embedding vector.
        kb_vectors: KB embedding matrix (N x D).
        kb_items: KB items list (same order as kb_vectors).

    Returns:
        Best matching KB item dict.
    """
    if query_vec is None or kb_vectors is None or len(kb_vectors) == 0:
        return {}
    # Cosine similarity (assumes L2-normalized vectors)
    sims = kb_vectors @ query_vec
    best_idx = int(np.argmax(sims))
    return kb_items[best_idx]


def extract_vectors(items: List[Dict], key: str = "Wav2Vec") -> np.ndarray:
    """Extract embedding vectors from dataset items.

    Args:
        items: Dataset items with Vectors field.
        key: Vector key name (e.g., 'Wav2Vec', 'TRR').

    Returns:
        numpy array of shape (N, D).
    """
    vectors = []
    for item in items:
        vec = item.get("Vectors", {}).get(key, [])
        if vec:
            vectors.append(np.array(vec, dtype=np.float32))
        else:
            vectors.append(None)
    # Filter None
    valid = [v for v in vectors if v is not None]
    if not valid:
        return np.array([])
    return np.stack(valid)


def run_sensitivity_analysis(config: SensitivityConfig) -> Dict:
    """Run near-duplicate sensitivity analysis.

    Args:
        config: Experiment configuration.

    Returns:
        Results dict with metrics per threshold.
    """
    # Load dataset
    with open(config.dataset_path, "r") as f:
        dataset = json.load(f)

    logger.info(f"Loaded {len(dataset)} presets")

    evaluator_raw = Evaluator(normalize=False)
    evaluator_norm = Evaluator(normalize=True)

    results = {"thresholds": {}}

    # Baseline: no dedup
    test_q, kb = split_protocol_a(dataset)
    baseline_metrics = _evaluate_retrieval(test_q, kb, evaluator_raw, evaluator_norm)
    results["baseline"] = {
        "kb_size": len(kb),
        "test_size": len(test_q),
        "metrics": baseline_metrics,
    }
    logger.info(f"Baseline: KB={len(kb)}, metrics={baseline_metrics}")

    # Per threshold
    for threshold in config.thresholds:
        logger.info(f"\n--- Threshold: {threshold} ---")

        # Find near-dups in KB only
        pairs = find_near_duplicates(kb, threshold=threshold)
        indices_to_remove = get_indices_to_remove(pairs)
        kb_filtered = filter_dataset(kb, indices_to_remove)

        dedup_metrics = _evaluate_retrieval(test_q, kb_filtered, evaluator_raw, evaluator_norm)

        results["thresholds"][str(threshold)] = {
            "pairs_found": len(pairs),
            "removed": len(indices_to_remove),
            "kb_size_after": len(kb_filtered),
            "metrics": dedup_metrics,
        }
        logger.info(f"  Removed {len(indices_to_remove)} items, KB: {len(kb)} -> {len(kb_filtered)}")
        logger.info(f"  Metrics: {dedup_metrics}")

    return results


def _evaluate_retrieval(
    queries: List[Dict],
    kb: List[Dict],
    evaluator_raw: Evaluator,
    evaluator_norm: Evaluator,
) -> Dict[str, float]:
    """Evaluate retrieval using Wav2Vec vectors.

    Args:
        queries: Test query items.
        kb: Knowledge base items.
        evaluator_raw: Raw metrics evaluator.
        evaluator_norm: Normalized metrics evaluator.

    Returns:
        Aggregated metrics dict.
    """
    kb_vecs = extract_vectors(kb, "Wav2Vec")
    if len(kb_vecs) == 0:
        logger.warning("No valid KB vectors found, returning zeros")
        return {"l2_raw": 0.0, "l2_norm": 0.0, "acc01": 0.0, "cosine": 0.0}

    # L2-normalize KB vectors
    norms = np.linalg.norm(kb_vecs, axis=1, keepdims=True)
    norms = np.maximum(norms, 1e-8)
    kb_vecs_normed = kb_vecs / norms

    l2_raw_list = []
    l2_norm_list = []
    acc01_list = []
    cosine_list = []

    for q in queries:
        q_vec = q.get("Vectors", {}).get("Wav2Vec")
        if q_vec is None:
            continue
        q_vec = np.array(q_vec, dtype=np.float32)
        q_vec_normed = q_vec / max(np.linalg.norm(q_vec), 1e-8)

        best_item = cosine_retrieval(q_vec_normed, kb_vecs_normed, kb)
        pred_params = best_item.get("Parameters", {})
        gt_params = q.get("Parameters", {})

        l2_raw_list.append(evaluator_raw.compute_parameter_distance(pred_params, gt_params))
        l2_norm_list.append(evaluator_norm.compute_parameter_distance(pred_params, gt_params))
        acc01_list.append(evaluator_raw.compute_accuracy_tolerance(pred_params, gt_params))
        cosine_list.append(evaluator_raw.compute_cosine_similarity(pred_params, gt_params))

    return {
        "l2_raw": float(np.mean(l2_raw_list)) if l2_raw_list else 0.0,
        "l2_norm": float(np.mean(l2_norm_list)) if l2_norm_list else 0.0,
        "acc_at_01": float(np.mean(acc01_list)) if acc01_list else 0.0,
        "cosine": float(np.mean(cosine_list)) if cosine_list else 0.0,
    }


def generate_report(results: Dict, output_path: Path) -> None:
    """Generate markdown report from sensitivity results.

    Args:
        results: Results dict from run_sensitivity_analysis.
        output_path: Path to write report.
    """
    lines = [
        "# Near-Duplicate Sensitivity Analysis Report\n",
        "## Baseline (No Deduplication)\n",
        f"- KB size: {results['baseline']['kb_size']}",
        f"- Test queries: {results['baseline']['test_size']}",
        f"- L2 (raw): {results['baseline']['metrics']['l2_raw']:.4f}",
        f"- L2 (normalized): {results['baseline']['metrics']['l2_norm']:.4f}",
        f"- Acc@0.1: {results['baseline']['metrics']['acc_at_01']:.4f}",
        f"- Cosine: {results['baseline']['metrics']['cosine']:.4f}",
        "",
        "## Sensitivity to Near-Duplicate Removal\n",
        "| Threshold | Pairs | Removed | KB Size | L2 (raw) | L2 (norm) | Acc@0.1 | Cosine |",
        "|-----------|-------|---------|---------|----------|-----------|---------|--------|",
    ]

    for th_str, th_data in results["thresholds"].items():
        m = th_data["metrics"]
        lines.append(
            f"| {th_str} | {th_data['pairs_found']} | {th_data['removed']} | "
            f"{th_data['kb_size_after']} | {m['l2_raw']:.4f} | {m['l2_norm']:.4f} | "
            f"{m['acc_at_01']:.4f} | {m['cosine']:.4f} |"
        )

    lines.extend([
        "",
        "## Analysis\n",
        "If metrics remain stable across thresholds, TRR is robust to near-duplicate removal.",
        "Significant degradation would indicate reliance on trivial KB matches.",
    ])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write("\n".join(lines))
    logger.info(f"Report saved to {output_path}")


def main() -> None:
    """CLI entry point."""
    import argparse
    parser = argparse.ArgumentParser(description="Near-Duplicate Sensitivity Analysis")
    parser.add_argument("--dataset", type=str,
                        default=str(Path(__file__).parent.parent / "dataset_full_vectors.json"))
    parser.add_argument("--output-dir", type=str,
                        default=str(Path(__file__).parent))
    args = parser.parse_args()

    config = SensitivityConfig(
        dataset_path=args.dataset,
        output_dir=args.output_dir,
    )

    results = run_sensitivity_analysis(config)

    # Save raw results
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_dir / "near_dup_sensitivity_results.json", "w") as f:
        json.dump(results, f, indent=2)

    generate_report(results, output_dir / "near_dup_sensitivity_report.md")


if __name__ == "__main__":
    main()
