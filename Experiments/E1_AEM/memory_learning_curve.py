"""
E1: AEM (Adaptive Executable Memory) Learning Curve Analysis

This experiment validates that the memory mechanism improves retrieval performance
over user interactions, supporting the core "Adaptive" claim of the Agent.

Author: Claude
Date: 2026-03-05
"""

import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
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

# Add Source to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "Source"))

from rag_system import AudioRAGSystem


@dataclass
class ExperimentConfig:
    """Configuration for AEM learning curve experiment."""
    memory_sizes: List[int] = None
    n_queries: int = 50
    n_turns_per_query: int = 10
    learning_rate: float = 0.6  # How much user tweaks toward target
    output_dir: str = "./results"
    api_key: str = ""
    base_url: str = ""

    def __post_init__(self):
        if self.memory_sizes is None:
            self.memory_sizes = [0, 5, 10, 20, 50]


@dataclass
class TurnResult:
    """Result from a single interaction turn."""
    turn: int
    query_id: str
    memory_size: int
    l2_error_before: float
    l2_error_after: float
    source_modality: str  # 'kb' or 'memory'
    retrieved_params: Dict[str, Any]
    tweaked_params: Dict[str, Any]


class UserSimulator:
    """Simulates user feedback on retrieved parameters."""

    def __init__(self, learning_rate: float = 0.6):
        self.learning_rate = learning_rate
        logger.info(f"UserSimulator initialized with learning_rate={learning_rate}")

    def calculate_l2_error(
        self,
        params: Dict[str, Any],
        target_params: Dict[str, Any]
    ) -> float:
        """
        Calculate L2 error between retrieved and target parameters.

        Args:
            params: Retrieved/tweaked parameters
            target_params: Ground truth target parameters

        Returns:
            L2 error (RMSE)
        """
        # Flatten nested dictionaries
        flat_pred = self._flatten_dict(params)
        flat_target = self._flatten_dict(target_params)

        # Get union of keys
        all_keys = set(flat_pred.keys()) | set(flat_target.keys())

        # Calculate L2
        squared_errors = []
        for key in all_keys:
            pred_val = flat_pred.get(key, 0.0)
            target_val = flat_target.get(key, 0.0)

            # Handle numeric values only
            if isinstance(pred_val, (int, float)) and isinstance(target_val, (int, float)):
                squared_errors.append((pred_val - target_val) ** 2)

        if not squared_errors:
            return float('inf')

        return np.sqrt(np.mean(squared_errors))

    def simulate_tweak(
        self,
        retrieved_params: Dict[str, Any],
        target_params: Dict[str, Any],
        learning_rate: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Simulate user tweaking parameters toward target.

        The user adjusts retrieved parameters partially toward target,
        with learning_rate controlling how much they adjust.

        Args:
            retrieved_params: Parameters from retrieval
            target_params: User's desired parameters
            learning_rate: How much to move toward target (0-1)

        Returns:
            Tweaked parameters
        """
        if learning_rate is None:
            learning_rate = self.learning_rate

        tweaked = {}
        for key, retrieved_val in retrieved_params.items():
            target_val = target_params.get(key)

            if target_val is None:
                tweaked[key] = retrieved_val
            elif isinstance(retrieved_val, (int, float)) and isinstance(target_val, (int, float)):
                # Linear interpolation toward target
                tweaked[key] = retrieved_val + learning_rate * (target_val - retrieved_val)
            elif isinstance(retrieved_val, dict) and isinstance(target_val, dict):
                # Recursively tweak nested dict
                tweaked[key] = self.simulate_tweak(retrieved_val, target_val, learning_rate)
            else:
                tweaked[key] = retrieved_val

        return tweaked

    def _flatten_dict(self, d: Dict[str, Any], parent_key: str = "") -> Dict[str, float]:
        """Flatten nested dictionary to dot-separated keys with numeric values."""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}.{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key).items())
            elif isinstance(v, (int, float)):
                items.append((new_key, float(v)))
        return dict(items)


class AEMLearningCurveExperiment:
    """
    Experiment to measure how AEM improves over interactions.
    """

    def __init__(self, config: ExperimentConfig):
        self.config = config
        self.simulator = UserSimulator(learning_rate=config.learning_rate)
        self.results: List[TurnResult] = []

        # Create output directory
        Path(config.output_dir).mkdir(parents=True, exist_ok=True)

        logger.info(f"AEMLearningCurveExperiment initialized")
        logger.info(f"  Memory sizes: {config.memory_sizes}")
        logger.info(f"  N queries: {config.n_queries}")
        logger.info(f"  N turns per query: {config.n_turns_per_query}")

    def load_test_queries(self, data_path: str) -> List[Dict[str, Any]]:
        """
        Load test queries from dataset.

        Args:
            data_path: Path to dataset file

        Returns:
            List of query dictionaries with 'query', 'audio_vector', 'target_params'
        """
        logger.info(f"Loading test queries from {data_path}")

        # Load dataset
        with open(data_path, 'r') as f:
            dataset = json.load(f)

        # Extract held-out queries (last 211 items typically)
        # For experiment, sample n_queries from held-out set
        all_queries = []

        # Assuming dataset has structure with held_out split
        if 'held_out' in dataset:
            held_out = dataset['held_out']
        else:
            # Use last portion as held-out
            split_idx = int(len(dataset) * 0.85)
            held_out = list(dataset.values())[split_idx:]

        # Sample n_queries
        if len(held_out) > self.config.n_queries:
            np.random.seed(42)
            indices = np.random.choice(len(held_out), self.config.n_queries, replace=False)
            sampled = [held_out[i] for i in indices]
        else:
            sampled = held_out

        # Format queries
        queries = []
        for item in sampled:
            query_info = {
                'query_id': item.get('id', f"query_{len(queries)}"),
                'text_query': item.get('text', item.get('description', '')),
                'audio_vector': item.get('audio_vector', item.get('trr_vector', [])),
                'target_params': item.get('parameters', item.get('target', {}))
            }
            queries.append(query_info)

        logger.info(f"Loaded {len(queries)} test queries")
        return queries

    def run_single_interaction_turn(
        self,
        rag: AudioRAGSystem,
        query_info: Dict[str, Any],
        turn_number: int
    ) -> Optional[TurnResult]:
        """
        Run a single interaction turn.

        Args:
            rag: Configured RAG system
            query_info: Query information
            turn_number: Current turn number

        Returns:
            TurnResult or None if failed
        """
        try:
            # Get recommendations
            recommendations = rag.recommend_parameters(
                style_tags=self._extract_style_tags(query_info['text_query']),
                user_description=query_info['text_query'],
                n_recommendations=1,
                audio_query_vector=query_info.get('audio_vector')
            )

            if not recommendations:
                logger.warning(f"No recommendations for query {query_info['query_id']}")
                return None

            rec = recommendations[0]
            retrieved_params = rec.get('parameters', {})
            source = rec.get('source_modality', 'kb')

            # Calculate error before tweak
            l2_before = self.simulator.calculate_l2_error(
                retrieved_params,
                query_info['target_params']
            )

            # Simulate user tweak
            tweaked_params = self.simulator.simulate_tweak(
                retrieved_params,
                query_info['target_params']
            )

            # Calculate error after tweak
            l2_after = self.simulator.calculate_l2_error(
                tweaked_params,
                query_info['target_params']
            )

            # Save to memory for next turn
            rag.save_to_memory(
                query=query_info['text_query'],
                parameters=tweaked_params,
                audio_vector=query_info.get('audio_vector', []),
                metadata={
                    'turn': turn_number,
                    'query_id': query_info['query_id'],
                    'l2_before': l2_before,
                    'l2_after': l2_after
                }
            )

            return TurnResult(
                turn=turn_number,
                query_id=query_info['query_id'],
                memory_size=len(rag.get_memory_entries()),
                l2_error_before=l2_before,
                l2_error_after=l2_after,
                source_modality=source,
                retrieved_params=retrieved_params,
                tweaked_params=tweaked_params
            )

        except Exception as e:
            logger.error(f"Error in turn {turn_number} for query {query_info['query_id']}: {e}")
            return None

    def run_memory_size_condition(
        self,
        memory_size: int,
        queries: List[Dict[str, Any]]
    ) -> List[TurnResult]:
        """
        Run experiment for a specific memory size condition.

        Args:
            memory_size: Maximum memory size (0 means no memory)
            queries: List of test queries

        Returns:
            List of TurnResults
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"Testing with max_memory_size = {memory_size}")
        logger.info(f"{'='*60}")

        # Initialize RAG system
        rag = AudioRAGSystem(
            api_key=self.config.api_key,
            base_url=self.config.base_url
        )

        # Load knowledge base
        rag.load_knowledge_base()

        # Clear and configure memory
        if hasattr(rag, 'memory_collection') and rag.memory_collection:
            try:
                rag.chroma_client.delete_collection("user_preference_memory")
            except:
                pass
        rag.memory_collection = rag._get_or_create_collection("user_preference_memory")

        # Set memory limit if applicable
        if hasattr(rag, 'max_memory_size'):
            rag.max_memory_size = memory_size

        results = []

        # Run interaction turns for each query
        for query_idx, query_info in enumerate(queries):
            logger.info(f"  Query {query_idx+1}/{len(queries)}: {query_info['query_id']}")

            for turn in range(1, self.config.n_turns_per_query + 1):
                result = self.run_single_interaction_turn(rag, query_info, turn)

                if result:
                    results.append(result)

                    # Log progress every few turns
                    if turn % 5 == 0:
                        logger.info(f"    Turn {turn}: L2 before={result.l2_error_before:.4f}, "
                                  f"after={result.l2_error_after:.4f}, source={result.source_modality}")

                # Small delay to avoid rate limiting
                time.sleep(0.1)

        return results

    def run_experiment(self, data_path: str) -> Dict[str, Any]:
        """
        Run the complete learning curve experiment.

        Args:
            data_path: Path to dataset

        Returns:
            Dictionary with all results and statistics
        """
        logger.info("Starting AEM Learning Curve Experiment")

        # Load queries
        queries = self.load_test_queries(data_path)

        # Run for each memory size condition
        all_results = {}
        for memory_size in self.config.memory_sizes:
            results = self.run_memory_size_condition(memory_size, queries)
            all_results[memory_size] = results

            # Save intermediate results
            self._save_results(results, f"memory_size_{memory_size}")

        # Analyze and save final results
        analysis = self.analyze_results(all_results)
        self._save_analysis(analysis)

        return analysis

    def analyze_results(
        self,
        all_results: Dict[int, List[TurnResult]]
    ) -> Dict[str, Any]:
        """
        Analyze learning curve results.

        Args:
            all_results: Dictionary mapping memory_size to list of TurnResults

        Returns:
            Analysis dictionary with statistics
        """
        logger.info("\nAnalyzing results...")

        analysis = {
            'memory_sizes': self.config.memory_sizes,
            'conditions': {},
            'learning_curves': {},
            'significance_tests': {}
        }

        # Analyze each condition
        for memory_size, results in all_results.items():
            if not results:
                continue

            df = pd.DataFrame([asdict(r) for r in results])

            # Overall statistics
            analysis['conditions'][memory_size] = {
                'n_turns': len(results),
                'mean_l2_before': df['l2_error_before'].mean(),
                'std_l2_before': df['l2_error_before'].std(),
                'mean_l2_after': df['l2_error_after'].mean(),
                'std_l2_after': df['l2_error_after'].std(),
                'memory_hit_rate': (df['source_modality'] == 'memory').mean()
            }

            # Learning curve (error over turns, averaged across queries)
            learning_curve = df.groupby('turn').agg({
                'l2_error_before': ['mean', 'std'],
                'l2_error_after': ['mean', 'std']
            }).reset_index()

            analysis['learning_curves'][memory_size] = learning_curve.to_dict()

        # Significance tests
        baseline_results = all_results.get(0, [])  # No memory
        for memory_size in self.config.memory_sizes:
            if memory_size == 0:
                continue

            memory_results = all_results.get(memory_size, [])
            if not baseline_results or not memory_results:
                continue

            # Get final turn errors for each query
            baseline_df = pd.DataFrame([asdict(r) for r in baseline_results])
            memory_df = pd.DataFrame([asdict(r) for r in memory_results])

            baseline_final = baseline_df[baseline_df['turn'] == self.config.n_turns_per_query]['l2_error_after']
            memory_final = memory_df[memory_df['turn'] == self.config.n_turns_per_query]['l2_error_after']

            # Paired t-test
            if len(baseline_final) == len(memory_final) and len(baseline_final) > 0:
                t_stat, p_value = stats.ttest_rel(baseline_final, memory_final)

                analysis['significance_tests'][f"memory_{memory_size}_vs_baseline"] = {
                    't_statistic': float(t_stat),
                    'p_value': float(p_value),
                    'significant': p_value < 0.05,
                    'baseline_mean': float(baseline_final.mean()),
                    'memory_mean': float(memory_final.mean()),
                    'improvement': float((baseline_final.mean() - memory_final.mean()) / baseline_final.mean() * 100)
                }

        return analysis

    def _extract_style_tags(self, text: str) -> List[str]:
        """Extract style tags from text query."""
        # Simple extraction - can be improved
        tags = []
        keywords = ['warm', 'clean', 'distorted', 'bright', 'dark', 'funky', 'blues', 'rock', 'metal']
        text_lower = text.lower()
        for kw in keywords:
            if kw in text_lower:
                tags.append(kw)
        return tags if tags else ['guitar']

    def _save_results(self, results: List[TurnResult], suffix: str):
        """Save results to CSV."""
        output_path = Path(self.config.output_dir) / f"aem_results_{suffix}.csv"
        df = pd.DataFrame([asdict(r) for r in results])
        df.to_csv(output_path, index=False)
        logger.info(f"Saved results to {output_path}")

    def _save_analysis(self, analysis: Dict[str, Any]):
        """Save analysis to JSON."""
        output_path = Path(self.config.output_dir) / "aem_analysis.json"
        with open(output_path, 'w') as f:
            json.dump(analysis, f, indent=2)
        logger.info(f"Saved analysis to {output_path}")

    def plot_learning_curves(self, analysis: Dict[str, Any]):
        """Generate learning curve plots."""
        logger.info("Generating learning curve plots...")

        fig, axes = plt.subplots(1, 2, figsize=(14, 5))

        # Plot 1: L2 Error over turns for each memory size
        ax = axes[0]
        for memory_size in self.config.memory_sizes:
            if memory_size not in analysis['learning_curves']:
                continue

            curve = analysis['learning_curves'][memory_size]
            turns = curve['turn']['l2_error_after']['mean'].keys()
            means = list(curve['turn']['l2_error_after']['mean'].values())
            stds = list(curve['turn']['l2_error_after']['std'].values())

            ax.plot(turns, means, marker='o', label=f'Memory size={memory_size}')
            ax.fill_between(turns,
                           [m - s for m, s in zip(means, stds)],
                           [m + s for m, s in zip(means, stds)],
                           alpha=0.2)

        ax.set_xlabel('Interaction Turn')
        ax.set_ylabel('L2 Error (RMSE)')
        ax.set_title('Learning Curve: Error Reduction Over Turns')
        ax.legend()
        ax.grid(True, alpha=0.3)

        # Plot 2: Final error comparison
        ax = axes[1]
        conditions = []
        means = []
        stds = []

        for memory_size in self.config.memory_sizes:
            if memory_size in analysis['conditions']:
                cond = analysis['conditions'][memory_size]
                conditions.append(f'{memory_size}')
                means.append(cond['mean_l2_after'])
                stds.append(cond['std_l2_after'])

        x = range(len(conditions))
        ax.bar(x, means, yerr=stds, capsize=5)
        ax.set_xticks(x)
        ax.set_xticklabels(conditions)
        ax.set_xlabel('Memory Size')
        ax.set_ylabel('Final L2 Error (RMSE)')
        ax.set_title('Final Error by Memory Size')
        ax.grid(True, alpha=0.3, axis='y')

        plt.tight_layout()
        output_path = Path(self.config.output_dir) / "aem_learning_curves.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        logger.info(f"Saved plot to {output_path}")


def main():
    """Main entry point."""
    import os
    from dotenv import load_dotenv

    # Load environment variables
    load_dotenv()

    # Configuration
    config = ExperimentConfig(
        memory_sizes=[0, 5, 10, 20, 50],
        n_queries=50,
        n_turns_per_query=10,
        learning_rate=0.6,
        output_dir="./results/E1_AEM",
        api_key=os.getenv("OPENAI_API_KEY", ""),
        base_url=os.getenv("OPENAI_BASE_URL", "")
    )

    # Create experiment
    experiment = AEMLearningCurveExperiment(config)

    # Find dataset path
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
    analysis = experiment.run_experiment(data_path)

    # Generate plots
    experiment.plot_learning_curves(analysis)

    # Print summary
    print("\n" + "="*60)
    print("EXPERIMENT SUMMARY")
    print("="*60)

    for memory_size, cond in analysis['conditions'].items():
        print(f"\nMemory size = {memory_size}:")
        print(f"  Mean L2 error: {cond['mean_l2_after']:.4f} ± {cond['std_l2_after']:.4f}")
        print(f"  Memory hit rate: {cond['memory_hit_rate']:.2%}")

    print("\nSignificance Tests:")
    for test_name, test_result in analysis['significance_tests'].items():
        print(f"\n  {test_name}:")
        print(f"    Improvement: {test_result['improvement']:.1f}%")
        print(f"    p-value: {test_result['p_value']:.4f}")
        print(f"    Significant: {test_result['significant']}")

    print("\n" + "="*60)


if __name__ == "__main__":
    main()
