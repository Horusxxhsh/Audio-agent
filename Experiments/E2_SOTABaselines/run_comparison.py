"""
SOTA Baseline Comparison: TRR vs CLAP vs PaSST vs PANNs

Run this to compare TRR against modern audio representations.

Author: Claude
Date: 2026-03-05
"""

import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import logging

import numpy as np
import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
import seaborn as sns

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "Source"))
sys.path.insert(0, str(Path(__file__).parent))

from rag_system import AudioRAGSystem
from clap_encoder import CLAPEncoder
from passt_encoder import PaSSTEncoder
from panns_encoder import PANNsEncoder


@dataclass
class ComparisonConfig:
    """Configuration for baseline comparison."""
    methods: List[str] = None  # ['trr', 'clap', 'passt', 'panns']
    dataset_path: str = ""
    output_dir: str = "./results/E2_SOTABaselines"
    batch_size: int = 8
    use_gpu: bool = True

    def __post_init__(self):
        if self.methods is None:
            self.methods = ['trr', 'clap', 'passt', 'panns']


class BaselineComparisonExperiment:
    """
    Compare TRR against SOTA audio representations.
    """

    def __init__(self, config: ComparisonConfig):
        self.config = config
        self.output_dir = Path(config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize encoders
        self.encoders = {}
        self._init_encoders()

        logger.info(f"Initialized comparison experiment")
        logger.info(f"Methods: {config.methods}")

    def _init_encoders(self):
        """Initialize all encoders."""
        for method in self.config.methods:
            try:
                if method == 'clap':
                    logger.info("Initializing CLAP...")
                    self.encoders[method] = CLAPEncoder()
                elif method == 'passt':
                    logger.info("Initializing PaSST...")
                    self.encoders[method] = PaSSTEncoder()
                elif method == 'panns':
                    logger.info("Initializing PANNs...")
                    self.encoders[method] = PANNsEncoder()
                elif method == 'trr':
                    logger.info("TRR will use existing RAG system")
                else:
                    logger.warning(f"Unknown method: {method}")
            except Exception as e:
                logger.error(f"Failed to initialize {method}: {e}")
                logger.warning(f"Skipping {method}")

    def load_dataset(self, data_path: str) -> List[Dict[str, Any]]:
        """
        Load dataset with audio files and ground truth.

        Args:
            data_path: Path to dataset JSON

        Returns:
            List of data items with audio paths and parameters
        """
        logger.info(f"Loading dataset from {data_path}")

        with open(data_path, 'r') as f:
            data = json.load(f)

        # Format items
        items = []
        for item in data if isinstance(data, list) else list(data.values()):
            items.append({
                'id': item.get('id', f"item_{len(items)}"),
                'audio_path': item.get('audio_path', item.get('audio_file', '')),
                'parameters': item.get('parameters', item.get('target', {})),
                'description': item.get('text', item.get('description', '')),
                'trr_vector': item.get('trr_vector', item.get('audio_vector', []))
            })

        logger.info(f"Loaded {len(items)} items")
        return items

    def compute_embeddings(
        self,
        items: List[Dict[str, Any]],
        method: str,
        cache_dir: Optional[Path] = None
    ) -> np.ndarray:
        """
        Compute embeddings for all items using specified method.

        Args:
            items: Dataset items
            method: Encoding method
            cache_dir: Directory to cache embeddings

        Returns:
            Embeddings array (N x D)
        """
        # Check cache
        if cache_dir:
            cache_file = cache_dir / f"{method}_embeddings.npy"
            if cache_file.exists():
                logger.info(f"Loading cached {method} embeddings")
                return np.load(cache_file)

        if method == 'trr':
            # Use existing TRR vectors
            embeddings = np.array([item['trr_vector'] for item in items])
        elif method in self.encoders:
            # Use encoder
            encoder = self.encoders[method]
            audio_paths = [item['audio_path'] for item in items if item['audio_path']]

            if not audio_paths:
                logger.error(f"No audio paths found for {method}")
                return np.array([])

            embeddings = encoder.encode_audio_batch(audio_paths)
        else:
            logger.error(f"No encoder for method: {method}")
            return np.array([])

        # Cache
        if cache_dir:
            cache_dir.mkdir(parents=True, exist_ok=True)
            np.save(cache_file, embeddings)

        return embeddings

    def evaluate_retrieval(
        self,
        query_embeddings: np.ndarray,
        kb_embeddings: np.ndarray,
        ground_truth: List[Dict],
        k: int = 1
    ) -> Dict[str, float]:
        """
        Evaluate retrieval performance.

        Args:
            query_embeddings: Query embeddings
            kb_embeddings: Knowledge base embeddings
            ground_truth: Ground truth parameters
            k: Top-k retrieval

        Returns:
            Metrics dictionary
        """
        from sklearn.metrics.pairwise import cosine_similarity

        # Compute similarities
        similarities = cosine_similarity(query_embeddings, kb_embeddings)

        # For each query, find top-k matches
        l2_errors = []
        acc_01 = []
        cos_sims = []

        for i, query_sim in enumerate(similarities):
            # Get top-k indices
            top_k_indices = np.argsort(query_sim)[-k:][::-1]

            # Use top-1 for metrics
            best_match_idx = top_k_indices[0]

            # Get retrieved parameters
            retrieved_params = ground_truth[best_match_idx]['parameters']
            target_params = ground_truth[i]['parameters']

            # Compute L2 error
            l2 = self._compute_l2(retrieved_params, target_params)
            l2_errors.append(l2)

            # Compute accuracy@0.1
            acc = self._compute_acc(retrieved_params, target_params, threshold=0.1)
            acc_01.append(acc)

            # Cosine similarity of parameter vectors
            cos = self._compute_cosine(retrieved_params, target_params)
            cos_sims.append(cos)

        return {
            'l2_mean': np.mean(l2_errors),
            'l2_std': np.std(l2_errors),
            'acc_01_mean': np.mean(acc_01),
            'cos_mean': np.mean(cos_sims),
            'n_queries': len(l2_errors)
        }

    def _compute_l2(self, pred: Dict, target: Dict) -> float:
        """Compute L2 error between parameter dictionaries."""
        flat_pred = self._flatten(pred)
        flat_target = self._flatten(target)

        all_keys = set(flat_pred.keys()) | set(flat_target.keys())
        errors = []

        for key in all_keys:
            p = flat_pred.get(key, 0.0)
            t = flat_target.get(key, 0.0)
            if isinstance(p, (int, float)) and isinstance(t, (int, float)):
                errors.append((p - t) ** 2)

        return np.sqrt(np.mean(errors)) if errors else float('inf')

    def _compute_acc(self, pred: Dict, target: Dict, threshold: float = 0.1) -> float:
        """Compute accuracy@threshold."""
        flat_pred = self._flatten(pred)
        flat_target = self._flatten(target)

        all_keys = set(flat_pred.keys()) | set(flat_target.keys())
        correct = 0
        total = 0

        for key in all_keys:
            p = flat_pred.get(key, 0.0)
            t = flat_target.get(key, 0.0)
            if isinstance(p, (int, float)) and isinstance(t, (int, float)):
                if abs(p - t) <= threshold:
                    correct += 1
                total += 1

        return correct / total if total > 0 else 0.0

    def _compute_cosine(self, pred: Dict, target: Dict) -> float:
        """Compute cosine similarity."""
        flat_pred = self._flatten(pred)
        flat_target = self._flatten(target)

        all_keys = sorted(set(flat_pred.keys()) | set(flat_target.keys()))
        v1 = np.array([flat_pred.get(k, 0.0) for k in all_keys])
        v2 = np.array([flat_target.get(k, 0.0) for k in all_keys])

        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return np.dot(v1, v2) / (norm1 * norm2)

    def _flatten(self, d: Dict, parent_key: str = "") -> Dict[str, float]:
        """Flatten nested dictionary."""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}.{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten(v, new_key).items())
            elif isinstance(v, (int, float)):
                items.append((new_key, float(v)))
        return dict(items)

    def run_comparison(self, data_path: str) -> pd.DataFrame:
        """
        Run full comparison across all methods.

        Args:
            data_path: Path to dataset

        Returns:
            Results DataFrame
        """
        logger.info("Starting baseline comparison")

        # Load data
        items = self.load_dataset(data_path)

        # Split into KB and queries (e.g., 85/15 split)
        n_kb = int(len(items) * 0.85)
        kb_items = items[:n_kb]
        query_items = items[n_kb:]

        logger.info(f"KB size: {len(kb_items)}, Queries: {len(query_items)}")

        # Cache directory
        cache_dir = self.output_dir / "embeddings"

        # Evaluate each method
        results = []

        for method in self.config.methods:
            logger.info(f"\n{'='*60}")
            logger.info(f"Evaluating: {method.upper()}")
            logger.info(f"{'='*60}")

            try:
                # Compute embeddings
                kb_emb = self.compute_embeddings(kb_items, method, cache_dir)
                query_emb = self.compute_embeddings(query_items, method, cache_dir)

                if len(kb_emb) == 0 or len(query_emb) == 0:
                    logger.warning(f"No embeddings for {method}, skipping")
                    continue

                # Evaluate
                metrics = self.evaluate_retrieval(
                    query_emb, kb_emb, kb_items, k=1
                )

                metrics['method'] = method
                results.append(metrics)

                logger.info(f"Results: L2={metrics['l2_mean']:.4f}, "
                          f"Acc@0.1={metrics['acc_01_mean']:.4f}, "
                          f"Cos={metrics['cos_mean']:.4f}")

            except Exception as e:
                logger.error(f"Failed to evaluate {method}: {e}")
                import traceback
                traceback.print_exc()

        # Create DataFrame
        df = pd.DataFrame(results)

        # Save
        output_file = self.output_dir / "baseline_comparison.csv"
        df.to_csv(output_file, index=False)
        logger.info(f"\nResults saved to {output_file}")

        return df

    def statistical_test(self, df: pd.DataFrame, baseline: str = 'trr'):
        """
        Perform statistical tests against baseline.
        """
        if baseline not in df['method'].values:
            logger.warning(f"Baseline {baseline} not in results")
            return

        baseline_row = df[df['method'] == baseline].iloc[0]

        logger.info(f"\n{'='*60}")
        logger.info(f"Statistical Tests (baseline: {baseline})")
        logger.info(f"{'='*60}")

        for _, row in df.iterrows():
            if row['method'] == baseline:
                continue

            # Note: This would need per-query results for proper testing
            # Simplified version here
            improvement = (baseline_row['l2_mean'] - row['l2_mean']) / baseline_row['l2_mean'] * 100

            logger.info(f"\n{row['method']} vs {baseline}:")
            logger.info(f"  L2 improvement: {improvement:+.1f}%")
            logger.info(f"  Better: {'Yes' if improvement > 0 else 'No'}")

    def plot_comparison(self, df: pd.DataFrame):
        """
        Create comparison plots.
        """
        fig, axes = plt.subplots(1, 3, figsize=(15, 5))

        metrics = ['l2_mean', 'acc_01_mean', 'cos_mean']
        titles = ['L2 Error (lower is better)', 'Accuracy@0.1 (higher is better)', 'Cosine Similarity (higher is better)']

        for ax, metric, title in zip(axes, metrics, titles):
            df_sorted = df.sort_values(metric, ascending=(metric == 'l2_mean'))
            colors = ['#2ecc71' if m == 'trr' else '#3498db' for m in df_sorted['method']]

            ax.bar(df_sorted['method'], df_sorted[metric], color=colors)
            ax.set_ylabel(metric)
            ax.set_title(title)
            ax.grid(True, alpha=0.3, axis='y')

            # Add value labels
            for i, (idx, row) in enumerate(df_sorted.iterrows()):
                ax.text(i, row[metric], f'{row[metric]:.3f}',
                       ha='center', va='bottom', fontsize=9)

        plt.tight_layout()
        output_file = self.output_dir / "baseline_comparison.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        logger.info(f"Plot saved to {output_file}")


def main():
    """Main entry point."""
    config = ComparisonConfig(
        methods=['trr', 'clap', 'passt', 'panns'],
        batch_size=8,
        use_gpu=True
    )

    # Find dataset
    possible_paths = [
        "../../Data/External_1267_211/dataset/dataset_full_vectors_1267.json",
        "../Data/External_1267_211/dataset/dataset_full_vectors_1267.json",
        "./dataset_full_vectors.json"
    ]

    data_path = None
    for path in possible_paths:
        if Path(path).exists():
            data_path = path
            break

    if not data_path:
        logger.error("Could not find dataset file!")
        sys.exit(1)

    # Run experiment
    experiment = BaselineComparisonExperiment(config)
    df = experiment.run_comparison(data_path)

    # Statistical tests
    experiment.statistical_test(df, baseline='trr')

    # Plot
    experiment.plot_comparison(df)

    # Print summary
    print("\n" + "="*60)
    print("BASELINE COMPARISON SUMMARY")
    print("="*60)
    print(df.to_string(index=False))
    print("="*60)


if __name__ == "__main__":
    main()
