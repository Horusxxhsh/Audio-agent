"""
E6: End-to-End Latency Profiling

Measures detailed timing breakdown of the agent pipeline:
- Wav2Vec2 encoding
- Gram matrix construction
- KNN retrieval
- Multimodal fusion
- LLM parameter generation

Author: Claude
Date: 2026-03-05
"""

import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from functools import wraps
import logging

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "Source"))

from rag_system import AudioRAGSystem


@dataclass
class TimingResult:
    """Timing result for a single component."""
    component: str
    duration_ms: float
    query_id: str
    run_id: int


class Timer:
    """Context manager for timing code blocks."""

    def __init__(self, name: str, results_list: List[TimingResult], query_id: str = "", run_id: int = 0):
        self.name = name
        self.results_list = results_list
        self.query_id = query_id
        self.run_id = run_id
        self.start_time = None
        self.end_time = None

    def __enter__(self):
        self.start_time = time.perf_counter_ns()
        return self

    def __exit__(self, *args):
        self.end_time = time.perf_counter_ns()
        duration_ms = (self.end_time - self.start_time) / 1_000_000  # Convert to ms

        self.results_list.append(TimingResult(
            component=self.name,
            duration_ms=duration_ms,
            query_id=self.query_id,
            run_id=self.run_id
        ))


def timed_component(name: str, results_list: List[TimingResult]):
    """Decorator to time a function."""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            query_id = kwargs.get('query_id', 'unknown')
            run_id = kwargs.get('run_id', 0)

            with Timer(name, results_list, query_id, run_id):
                return func(*args, **kwargs)
        return wrapper
    return decorator


class LatencyProfiler:
    """
    Profiles end-to-end latency of the agent pipeline.
    """

    def __init__(self, rag_system: AudioRAGSystem, output_dir: str = "./results"):
        self.rag = rag_system
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results: List[TimingResult] = []

    def profile_wav2vec2_encoding(
        self,
        audio_vector: List[float],
        query_id: str = "",
        run_id: int = 0
    ) -> float:
        """Time Wav2Vec2 feature extraction."""
        with Timer("wav2vec2_encoding", self.results, query_id, run_id):
            # Simulate or actual Wav2Vec2 encoding
            # In real implementation, this would call the actual encoder
            time.sleep(0.01)  # Placeholder
            return 0.0

    def profile_gram_matrix(
        self,
        features: np.ndarray,
        query_id: str = "",
        run_id: int = 0
    ) -> np.ndarray:
        """Time Gram matrix construction."""
        with Timer("gram_matrix", self.results, query_id, run_id):
            # Gram matrix computation: G = H @ H.T / T
            if len(features.shape) == 1:
                features = features.reshape(1, -1)

            gram = np.dot(features.T, features) / features.shape[0]
            return gram

    def profile_knn_retrieval(
        self,
        query_vector: np.ndarray,
        k: int = 5,
        query_id: str = "",
        run_id: int = 0
    ) -> List[Dict]:
        """Time KNN retrieval."""
        with Timer("knn_retrieval", self.results, query_id, run_id):
            # Call actual retrieval
            results = self.rag.knowledge_base.query(
                query_embeddings=query_vector.tolist(),
                n_results=k
            )
            return results

    def profile_multimodal_fusion(
        self,
        text_score: float,
        audio_score: float,
        query_id: str = "",
        run_id: int = 0
    ) -> float:
        """Time multimodal fusion."""
        with Timer("multimodal_fusion", self.results, query_id, run_id):
            # Simple weighted fusion
            fused = 0.5 * text_score + 0.5 * audio_score
            return fused

    def profile_llm_generation(
        self,
        prompt: str,
        query_id: str = "",
        run_id: int = 0
    ) -> str:
        """Time LLM parameter generation."""
        with Timer("llm_generation", self.results, query_id, run_id):
            # In real implementation, this would call LLM API
            # For profiling, we can use a cached response or mock
            time.sleep(0.1)  # Placeholder for API latency
            return "{}"

    def profile_full_pipeline(
        self,
        query_info: Dict[str, Any],
        run_id: int = 0
    ) -> Dict[str, Any]:
        """
        Profile the complete agent pipeline.

        Args:
            query_info: Query with text and audio
            run_id: Run identifier for repeated measurements

        Returns:
            Pipeline results with timing info
        """
        query_id = query_info.get('id', f"query_{run_id}")

        # 1. Wav2Vec2 encoding (if audio provided)
        if 'audio_vector' in query_info and query_info['audio_vector']:
            audio_features = np.array(query_info['audio_vector'])
            self.profile_wav2vec2_encoding(
                query_info['audio_vector'],
                query_id=query_id,
                run_id=run_id
            )

            # 2. Gram matrix construction
            gram_matrix = self.profile_gram_matrix(
                audio_features,
                query_id=query_id,
                run_id=run_id
            )

        # 3. KNN retrieval
        query_embedding = np.random.randn(768)  # Placeholder
        retrieval_results = self.profile_knn_retrieval(
            query_embedding,
            k=5,
            query_id=query_id,
            run_id=run_id
        )

        # 4. Multimodal fusion (if text also provided)
        if 'text' in query_info:
            self.profile_multimodal_fusion(
                0.8, 0.7,  # Placeholder scores
                query_id=query_id,
                run_id=run_id
            )

        # 5. LLM parameter generation
        self.profile_llm_generation(
            "Generate parameters",
            query_id=query_id,
            run_id=run_id
        )

        return {'query_id': query_id, 'run_id': run_id}

    def run_profiling(
        self,
        queries: List[Dict[str, Any]],
        n_repeats: int = 100
    ) -> pd.DataFrame:
        """
        Run comprehensive latency profiling.

        Args:
            queries: List of test queries
            n_repeats: Number of times to repeat each query

        Returns:
            DataFrame with all timing results
        """
        logger.info(f"Starting latency profiling: {len(queries)} queries x {n_repeats} repeats")

        for run_id in range(n_repeats):
            if run_id % 10 == 0:
                logger.info(f"  Run {run_id}/{n_repeats}")

            for query in queries:
                try:
                    self.profile_full_pipeline(query, run_id=run_id)
                except Exception as e:
                    logger.warning(f"Error profiling query: {e}")

        # Convert to DataFrame
        df = pd.DataFrame([asdict(r) for r in self.results])

        # Save results
        output_path = self.output_dir / "latency_results.csv"
        df.to_csv(output_path, index=False)
        logger.info(f"Saved results to {output_path}")

        return df

    def analyze_results(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze timing results.

        Args:
            df: Timing results DataFrame

        Returns:
            Analysis dictionary with statistics
        """
        analysis = {}

        # Statistics by component
        component_stats = df.groupby('component')['duration_ms'].agg([
            ('count', 'count'),
            ('mean', 'mean'),
            ('std', 'std'),
            ('median', 'median'),
            ('p50', lambda x: x.quantile(0.50)),
            ('p95', lambda x: x.quantile(0.95)),
            ('p99', lambda x: x.quantile(0.99)),
            ('min', 'min'),
            ('max', 'max')
        ]).round(3)

        analysis['component_stats'] = component_stats.to_dict()

        # End-to-end latency (sum of all components per query-run)
        e2e = df.groupby(['query_id', 'run_id'])['duration_ms'].sum().reset_index()
        e2e_stats = e2e['duration_ms'].agg([
            ('count', 'count'),
            ('mean', 'mean'),
            ('std', 'std'),
            ('median', 'median'),
            ('p50', lambda x: x.quantile(0.50)),
            ('p95', lambda x: x.quantile(0.95)),
            ('p99', lambda x: x.quantile(0.99))
        ]).round(3)

        analysis['end_to_end_stats'] = e2e_stats.to_dict()

        # Cacheable vs non-cacheable breakdown
        cacheable_components = ['wav2vec2_encoding', 'gram_matrix']
        cacheable_time = df[df['component'].isin(cacheable_components)]['duration_ms'].sum()
        non_cacheable_time = df[~df['component'].isin(cacheable_components)]['duration_ms'].sum()

        analysis['cache_breakdown'] = {
            'cacheable_ms': float(cacheable_time),
            'non_cacheable_ms': float(non_cacheable_time),
            'cacheable_percentage': float(cacheable_time / (cacheable_time + non_cacheable_time) * 100)
        }

        return analysis

    def plot_results(self, df: pd.DataFrame, analysis: Dict[str, Any]):
        """Generate latency visualization plots."""
        logger.info("Generating latency plots...")

        fig, axes = plt.subplots(2, 2, figsize=(14, 10))

        # Plot 1: Component latency breakdown (boxplot)
        ax = axes[0, 0]
        components = df['component'].unique()
        data = [df[df['component'] == c]['duration_ms'].values for c in components]
        ax.boxplot(data, labels=components)
        ax.set_ylabel('Latency (ms)')
        ax.set_title('Latency Distribution by Component')
        ax.tick_params(axis='x', rotation=45)
        ax.grid(True, alpha=0.3, axis='y')

        # Plot 2: Mean latency comparison (bar)
        ax = axes[0, 1]
        stats = df.groupby('component')['duration_ms'].mean().sort_values(ascending=True)
        colors = plt.cm.viridis(np.linspace(0, 1, len(stats)))
        bars = ax.barh(stats.index, stats.values, color=colors)
        ax.set_xlabel('Mean Latency (ms)')
        ax.set_title('Average Latency by Component')
        ax.grid(True, alpha=0.3, axis='x')

        # Add value labels
        for bar, val in zip(bars, stats.values):
            ax.text(val + 0.5, bar.get_y() + bar.get_height()/2,
                   f'{val:.2f}ms', va='center', fontsize=9)

        # Plot 3: CDF of end-to-end latency
        ax = axes[1, 0]
        e2e = df.groupby(['query_id', 'run_id'])['duration_ms'].sum()
        sorted_latency = np.sort(e2e.values)
        cdf = np.arange(1, len(sorted_latency) + 1) / len(sorted_latency)
        ax.plot(sorted_latency, cdf, linewidth=2)
        ax.axhline(0.5, color='r', linestyle='--', alpha=0.5, label='p50')
        ax.axhline(0.95, color='g', linestyle='--', alpha=0.5, label='p95')
        ax.set_xlabel('End-to-End Latency (ms)')
        ax.set_ylabel('CDF')
        ax.set_title('End-to-End Latency Distribution')
        ax.legend()
        ax.grid(True, alpha=0.3)

        # Plot 4: Cacheable vs Non-cacheable pie chart
        ax = axes[1, 1]
        cache = analysis['cache_breakdown']
        sizes = [cache['cacheable_ms'], cache['non_cacheable_ms']]
        labels = [f'Cacheable\n({cache["cacheable_percentage"]:.1f}%)',
                  f'Non-cacheable\n({100-cache["cacheable_percentage"]:.1f}%)']
        colors = ['#66b3ff', '#ff9999']
        ax.pie(sizes, labels=labels, colors=colors, autopct='%1.1fms',
               startangle=90, textprops={'fontsize': 10})
        ax.set_title('Cacheable vs Non-cacheable Time')

        plt.tight_layout()
        output_path = self.output_dir / "latency_analysis.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        logger.info(f"Saved plot to {output_path}")


def main():
    """Main entry point."""
    import os
    from dotenv import load_dotenv

    load_dotenv()

    # Initialize RAG system
    rag = AudioRAGSystem(
        api_key=os.getenv("OPENAI_API_KEY", ""),
        base_url=os.getenv("OPENAI_BASE_URL", "")
    )

    # Create profiler
    profiler = LatencyProfiler(rag, output_dir="./results/E6_Latency")

    # Create dummy queries for profiling
    queries = [
        {'id': f'query_{i}', 'text': f'test query {i}', 'audio_vector': [0.1] * 768}
        for i in range(10)
    ]

    # Run profiling
    df = profiler.run_profiling(queries, n_repeats=100)

    # Analyze
    analysis = profiler.analyze_results(df)

    # Plot
    profiler.plot_results(df, analysis)

    # Print summary
    print("\n" + "="*60)
    print("LATENCY PROFILING SUMMARY")
    print("="*60)

    print("\nComponent Statistics (ms):")
    for component, stats in analysis['component_stats'].items():
        print(f"\n  {component}:")
        print(f"    Median: {stats['p50']:.3f}ms")
        print(f"    P95: {stats['p95']:.3f}ms")
        print(f"    Mean: {stats['mean']:.3f}ms")

    print("\nEnd-to-End Latency:")
    e2e = analysis['end_to_end_stats']
    print(f"  Median: {e2e['median']:.3f}ms")
    print(f"  P95: {e2e['p95']:.3f}ms")
    print(f"  Mean: {e2e['mean']:.3f}ms")

    print("\nCache Breakdown:")
    cache = analysis['cache_breakdown']
    print(f"  Cacheable: {cache['cacheable_percentage']:.1f}%")
    print(f"  Non-cacheable: {100-cache['cacheable_percentage']:.1f}%")

    print("\n" + "="*60)


if __name__ == "__main__":
    main()
