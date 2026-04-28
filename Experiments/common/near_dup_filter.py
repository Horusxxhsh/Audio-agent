"""Near-duplicate filter for guitar effect preset datasets.

Identifies near-duplicate preset pairs based on parameter-space fingerprinting.
Outputs pairs list and filtered dataset for sensitivity analysis.

Usage:
    python near_dup_filter.py --dataset path/to/dataset.json --threshold 0.02 --output near_dup_pairs.json
"""

import json
import math
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Set, Tuple

logger = logging.getLogger(__name__)


def flatten_params(params: Dict, prefix: str = "") -> Dict[str, float]:
    """Recursively flatten nested parameter dict to float dict.

    Args:
        params: Nested parameter dictionary.
        prefix: Key prefix for recursion.

    Returns:
        Flat dict {dotted_key: float_value}.
    """
    flat: Dict[str, float] = {}
    for k, v in params.items():
        key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            flat.update(flatten_params(v, key))
        elif isinstance(v, (int, float)):
            flat[key] = float(v)
        elif isinstance(v, str):
            try:
                flat[key] = float(v)
            except ValueError:
                pass
    return flat


def compute_l2_distance(v1: Dict[str, float], v2: Dict[str, float]) -> float:
    """Compute L2 (Euclidean) distance between two flat parameter vectors.

    Args:
        v1: First flat parameter dict.
        v2: Second flat parameter dict.

    Returns:
        L2 distance (float).
    """
    all_keys = set(v1.keys()) | set(v2.keys())
    if not all_keys:
        return 0.0
    sq_sum = sum((v1.get(k, 0.0) - v2.get(k, 0.0)) ** 2 for k in all_keys)
    return math.sqrt(sq_sum)


def find_near_duplicates(
    dataset: List[Dict],
    threshold: float = 0.02,
) -> List[Tuple[int, int, float, str, str]]:
    """Find near-duplicate pairs in dataset by parameter L2 distance.

    Args:
        dataset: List of preset dicts with 'Parameters' and 'SongName' keys.
        threshold: L2 distance threshold below which two presets
                   are considered near-duplicates.

    Returns:
        List of (idx_i, idx_j, distance, name_i, name_j) tuples.
    """
    logger.info(f"Scanning {len(dataset)} presets for near-duplicates (threshold={threshold})")

    # Pre-flatten all parameter vectors
    flat_vectors = []
    for item in dataset:
        params = item.get("Parameters", {})
        flat_vectors.append(flatten_params(params))

    pairs: List[Tuple[int, int, float, str, str]] = []
    n = len(dataset)
    for i in range(n):
        for j in range(i + 1, n):
            dist = compute_l2_distance(flat_vectors[i], flat_vectors[j])
            if dist <= threshold:
                name_i = dataset[i].get("SongName", f"preset_{i}")
                name_j = dataset[j].get("SongName", f"preset_{j}")
                pairs.append((i, j, dist, name_i, name_j))

    logger.info(f"Found {len(pairs)} near-duplicate pairs")
    return pairs


def get_indices_to_remove(
    pairs: List[Tuple[int, int, float, str, str]],
    strategy: str = "keep_first",
) -> Set[int]:
    """Determine which indices to remove from near-duplicate pairs.

    Args:
        pairs: Output of find_near_duplicates.
        strategy: 'keep_first' keeps the lower-index item in each pair.

    Returns:
        Set of indices to remove.
    """
    to_remove: Set[int] = set()
    for i, j, dist, name_i, name_j in pairs:
        if strategy == "keep_first":
            to_remove.add(j)
        else:
            to_remove.add(j)
    return to_remove


def filter_dataset(
    dataset: List[Dict],
    indices_to_remove: Set[int],
) -> List[Dict]:
    """Return dataset with near-duplicate items removed.

    Args:
        dataset: Original dataset list.
        indices_to_remove: Indices to exclude.

    Returns:
        Filtered dataset list.
    """
    filtered = [item for idx, item in enumerate(dataset) if idx not in indices_to_remove]
    logger.info(f"Filtered dataset: {len(dataset)} -> {len(filtered)} items "
                f"(removed {len(indices_to_remove)})")
    return filtered


def main() -> None:
    """CLI entry point for near-duplicate detection."""
    parser = argparse.ArgumentParser(description="Near-duplicate preset filter")
    parser.add_argument("--dataset", type=str, required=True,
                        help="Path to dataset JSON file")
    parser.add_argument("--threshold", type=float, default=0.02,
                        help="L2 distance threshold for near-dup detection (default: 0.02)")
    parser.add_argument("--output", type=str, default="near_dup_pairs.json",
                        help="Output file for near-dup pairs (default: near_dup_pairs.json)")
    parser.add_argument("--filtered-output", type=str, default=None,
                        help="If set, save filtered dataset to this path")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        logger.error(f"Dataset file not found: {dataset_path}")
        return

    with open(dataset_path, "r") as f:
        dataset = json.load(f)

    pairs = find_near_duplicates(dataset, threshold=args.threshold)

    # Save pairs report
    pairs_report = {
        "threshold": args.threshold,
        "total_presets": len(dataset),
        "near_duplicate_count": len(pairs),
        "pairs": [
            {
                "idx_i": i,
                "idx_j": j,
                "distance": round(dist, 6),
                "name_i": name_i,
                "name_j": name_j,
            }
            for i, j, dist, name_i, name_j in pairs
        ],
    }

    output_path = Path(args.output)
    with open(output_path, "w") as f:
        json.dump(pairs_report, f, indent=2)
    logger.info(f"Near-duplicate pairs saved to {output_path}")

    if args.filtered_output:
        indices_to_remove = get_indices_to_remove(pairs)
        filtered = filter_dataset(dataset, indices_to_remove)
        with open(args.filtered_output, "w") as f:
            json.dump(filtered, f, indent=2)
        logger.info(f"Filtered dataset saved to {args.filtered_output}")

    # Summary
    print(f"\n=== Near-Duplicate Analysis ===")
    print(f"Total presets: {len(dataset)}")
    print(f"Near-duplicate pairs: {len(pairs)} (threshold L2 <= {args.threshold})")
    if pairs:
        print(f"\nTop 10 closest pairs:")
        sorted_pairs = sorted(pairs, key=lambda x: x[2])
        for i, j, dist, name_i, name_j in sorted_pairs[:10]:
            print(f"  [{i}] {name_i} <-> [{j}] {name_j}  (L2={dist:.6f})")


if __name__ == "__main__":
    main()
