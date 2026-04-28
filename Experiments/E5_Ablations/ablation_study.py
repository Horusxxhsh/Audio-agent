"""
E5: Retrieval Ablation Study (Simplified)

Compares:
A) Pure retrieval (top-k only)
B) Retrieval + constraint projection

Simplified version for 1-week timeline.

Author: Claude
Date: 2026-03-05
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass
import logging

import numpy as np
import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "Source"))

from rag_system import AudioRAGSystem

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class AblationConfig:
    """Configuration for ablation study."""
    conditions: List[str] = None
    n_queries: int = 211
    output_dir: str = "./results/E5_Ablations"

    def __post_init__(self):
        if self.conditions is None:
            self.conditions = ['pure_retrieval', 'with_projection']


class AblationStudy:
    """
    Ablation study comparing retrieval-only vs retrieval+projection.
    """

    def __init__(self, config: AblationConfig):
        self.config = config
        self.output_dir = Path(config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def load_data(self, data_path: str) -> List[Dict]:
        """Load dataset."""
        with open(data_path, 'r') as f:
            data = json.load(f)

        # Format
        items = []
        for item in data if isinstance(data, list) else list(data.values()):
            items.append({
                'id': item.get('id', f"item_{len(items)}"),
                'query': item.get('text', item.get('description', '')),
                'audio_vector': item.get('audio_vector', item.get('trr_vector', [])),
                'target_params': item.get('parameters', item.get('target', {}))
            })

        return items

    def run_pure_retrieval(
        self,
        rag: AudioRAGSystem,
        queries: List[Dict]
    ) -> List[Dict]:
        """
        Run pure retrieval without projection.
        """
        results = []

        for query in queries:
            try:
                # Get recommendations
                recs = rag.recommend_parameters(
                    style_tags=self._extract_tags(query['query']),
                    user_description=query['query'],
                    n_recommendations=1,
                    audio_query_vector=query.get('audio_vector')
                )

                if recs:
                    retrieved = recs[0]['parameters']
                else:
                    retrieved = {}

                # Compute metrics
                metrics = self._compute_metrics(retrieved, query['target_params'])
                metrics['query_id'] = query['id']
                metrics['condition'] = 'pure_retrieval'

                results.append(metrics)

            except Exception as e:
                logger.warning(f"Failed for query {query['id']}: {e}")

        return results

    def run_with_projection(
        self,
        rag: AudioRAGSystem,
        queries: List[Dict]
    ) -> List[Dict]:
        """
        Run retrieval with constraint projection.
        """
        results = []

        for query in queries:
            try:
                # Get recommendations
                recs = rag.recommend_parameters(
                    style_tags=self._extract_tags(query['query']),
                    user_description=query['query'],
                    n_recommendations=1,
                    audio_query_vector=query.get('audio_vector')
                )

                if recs:
                    retrieved = recs[0]['parameters']
                    # Apply projection (simplified)
                    projected = self._apply_projection(retrieved)
                else:
                    projected = {}

                # Compute metrics
                metrics = self._compute_metrics(projected, query['target_params'])
                metrics['query_id'] = query['id']
                metrics['condition'] = 'with_projection'

                # Check constraint satisfaction
                metrics['constraint_satisfied'] = self._check_constraints(projected)

                results.append(metrics)

            except Exception as e:
                logger.warning(f"Failed for query {query['id']}: {e}")

        return results

    def _apply_projection(self, params: Dict) -> Dict:
        """
        Apply constraint projection to parameters.
        Simplified version - clamp to valid ranges.
        """
        projected = {}

        for key, value in params.items():
            if isinstance(value, dict):
                projected[key] = self._apply_projection(value)
            elif isinstance(value, (int, float)):
                # Clamp to [0, 1] range (simplified)
                projected[key] = max(0.0, min(1.0, float(value)))
            else:
                projected[key] = value

        return projected

    def _check_constraints(self, params: Dict) -> bool:
        """
        Check if parameters satisfy constraints.
        Simplified version - check range constraints only.
        """
        def check_recursive(d: Dict) -> bool:
            for key, value in d.items():
                if isinstance(value, dict):
                    if not check_recursive(value):
                        return False
                elif isinstance(value, (int, float)):
                    # Check if in valid range
                    if value < 0 or value > 1:
                        return False
            return True

        return check_recursive(params) if params else False

    def _compute_metrics(self, pred: Dict, target: Dict) -> Dict:
        """Compute evaluation metrics."""
        flat_pred = self._flatten(pred)
        flat_target = self._flatten(target)

        all_keys = set(flat_pred.keys()) | set(flat_target.keys())

        # L2 error
        errors = []
        for key in all_keys:
            p = flat_pred.get(key, 0.0)
            t = flat_target.get(key, 0.0)
            if isinstance(p, (int, float)) and isinstance(t, (int, float)):
                errors.append((p - t) ** 2)

        l2 = np.sqrt(np.mean(errors)) if errors else float('inf')

        # Accuracy @ 0.1
        correct = sum(
            1 for key in all_keys
            if abs(flat_pred.get(key, 0) - flat_target.get(key, 0)) <= 0.1
        )
        acc = correct / len(all_keys) if all_keys else 0.0

        # Cosine similarity
        if flat_pred and flat_target:
            v1 = np.array([flat_pred.get(k, 0) for k in all_keys])
            v2 = np.array([flat_target.get(k, 0) for k in all_keys])
            norm1, norm2 = np.linalg.norm(v1), np.linalg.norm(v2)
            cos = np.dot(v1, v2) / (norm1 * norm2) if norm1 > 0 and norm2 > 0 else 0.0
        else:
            cos = 0.0

        return {
            'l2_error': l2,
            'acc_01': acc,
            'cosine_sim': cos
        }

    def _flatten(self, d: Dict, parent_key: str = "") -> Dict:
        """Flatten nested dict."""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}.{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten(v, new_key).items())
            elif isinstance(v, (int, float)):
                items.append((new_key, float(v)))
        return dict(items)

    def _extract_tags(self, text: str) -> List[str]:
        """Extract style tags."""
        tags = []
        keywords = ['warm', 'clean', 'distorted', 'bright', 'dark', 'funky']
        for kw in keywords:
            if kw in text.lower():
                tags.append(kw)
        return tags if tags else ['guitar']

    def run_ablation(self, data_path: str):
        """Run full ablation study."""
        logger.info("Starting ablation study")

        # Load data
        items = self.load_data(data_path)
        logger.info(f"Loaded {len(items)} items")

        # Split KB and queries
        n_kb = int(len(items) * 0.85)
        kb_items = items[:n_kb]
        query_items = items[n_kb:]

        # Initialize RAG
        rag = AudioRAGSystem()
        rag.load_knowledge_base()

        # Run conditions
        all_results = []

        for condition in self.config.conditions:
            logger.info(f"\nRunning condition: {condition}")

            if condition == 'pure_retrieval':
                results = self.run_pure_retrieval(rag, query_items)
            elif condition == 'with_projection':
                results = self.run_with_projection(rag, query_items)
            else:
                logger.warning(f"Unknown condition: {condition}")
                continue

            all_results.extend(results)
            logger.info(f"Completed {len(results)} queries")

        # Create DataFrame
        df = pd.DataFrame(all_results)

        # Save
        output_file = self.output_dir / "ablation_results.csv"
        df.to_csv(output_file, index=False)

        # Analyze
        self._analyze_results(df)

        return df

    def _analyze_results(self, df: pd.DataFrame):
        """Analyze and report results."""
        logger.info("\nAnalyzing results...")

        # Summary by condition
        summary = df.groupby('condition').agg({
            'l2_error': ['mean', 'std'],
            'acc_01': ['mean', 'std'],
            'cosine_sim': ['mean', 'std'],
            'constraint_satisfied': 'mean' if 'constraint_satisfied' in df.columns else lambda x: 0
        }).round(4)

        print("\n" + "="*60)
        print("ABLATION STUDY RESULTS")
        print("="*60)
        print(summary.to_string())

        # Statistical test
        pure = df[df['condition'] == 'pure_retrieval']['l2_error']
        proj = df[df['condition'] == 'with_projection']['l2_error']

        if len(pure) > 0 and len(proj) > 0:
            t_stat, p_value = stats.ttest_rel(pure, proj)
            improvement = (pure.mean() - proj.mean()) / pure.mean() * 100

            print(f"\nProjection Improvement:")
            print(f"  L2 reduction: {improvement:.1f}%")
            print(f"  t-statistic: {t_stat:.3f}")
            print(f"  p-value: {p_value:.4f}")
            print(f"  Significant: {'Yes' if p_value < 0.05 else 'No'}")

        # Constraint satisfaction
        if 'constraint_satisfied' in df.columns:
            sat_pure = df[df['condition'] == 'pure_retrieval']['constraint_satisfied'].mean()
            sat_proj = df[df['condition'] == 'with_projection']['constraint_satisfied'].mean()
            print(f"\nConstraint Satisfaction:")
            print(f"  Pure retrieval: {sat_pure:.1%}")
            print(f"  With projection: {sat_proj:.1%}")

        print("="*60)

        # Save summary
        summary.to_csv(self.output_dir / "ablation_summary.csv")

    def plot_results(self, df: pd.DataFrame):
        """Plot comparison."""
        fig, axes = plt.subplots(1, 3, figsize=(15, 5))

        metrics = ['l2_error', 'acc_01', 'cosine_sim']
        titles = ['L2 Error (lower is better)', 'Acc@0.1 (higher is better)', 'Cosine (higher is better)']

        for ax, metric, title in zip(axes, metrics, titles):
            df.boxplot(column=metric, by='condition', ax=ax)
            ax.set_title(title)
            ax.set_xlabel('Condition')

        plt.suptitle('Ablation Study: Retrieval vs Retrieval+Projection')
        plt.tight_layout()
        plt.savefig(self.output_dir / "ablation_comparison.png", dpi=300)


def main():
    """Main entry point."""
    config = AblationConfig()

    # Find dataset
    possible_paths = [
        "../../Data/External_1267_211/dataset/dataset_full_vectors_1267.json",
        "../Data/External_1267_211/dataset/dataset_full_vectors_1267.json",
        "./dataset_full_vectors.json"
    ]

    data_path = next((p for p in possible_paths if Path(p).exists()), None)

    if not data_path:
        logger.error("Could not find dataset!")
        sys.exit(1)

    # Run study
    study = AblationStudy(config)
    df = study.run_ablation(data_path)
    study.plot_results(df)


if __name__ == "__main__":
    main()
