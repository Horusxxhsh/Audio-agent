"""
E4: Metric-Perception Correlation Analysis (Simplified)

Correlates parameter-space metrics with listening test scores.
Simplified version for 1-week timeline - uses Spearman/Pearson only.

Author: Claude
Date: 2026-03-05
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
import seaborn as sns

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class CorrelationConfig:
    """Configuration for correlation analysis."""
    mushra_data_path: str = ""
    parameter_metrics_path: str = ""
    output_dir: str = "./results/E4_MetricCorrelation"


class MetricPerceptionCorrelation:
    """
    Analyzes correlation between objective metrics and subjective ratings.
    """

    def __init__(self, config: CorrelationConfig):
        self.config = config
        self.output_dir = Path(config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def load_mushra_data(self, path: str) -> pd.DataFrame:
        """
        Load MUSHRA listening test data.

        Expected format: CSV with columns
        - participant_id
        - query_id
        - condition (e.g., 'reference', 'trr', 'musicgen')
        - rating (0-100)
        """
        logger.info(f"Loading MUSHRA data from {path}")

        if path.endswith('.csv'):
            df = pd.read_csv(path)
        elif path.endswith('.json'):
            with open(path, 'r') as f:
                data = json.load(f)
            df = pd.DataFrame(data)
        else:
            raise ValueError(f"Unsupported file format: {path}")

        logger.info(f"Loaded {len(df)} ratings")
        return df

    def load_parameter_metrics(self, path: str) -> pd.DataFrame:
        """
        Load parameter-space metrics for each query.

        Expected format: CSV with columns
        - query_id
        - l2_error
        - acc_01
        - cosine_sim
        - recall
        """
        logger.info(f"Loading parameter metrics from {path}")

        df = pd.read_csv(path)
        logger.info(f"Loaded metrics for {len(df)} queries")
        return df

    def compute_correlations(
        self,
        mushra_df: pd.DataFrame,
        metrics_df: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Compute correlations between metrics and ratings.

        Simplified version: Spearman and Pearson only.
        (Full version would include mixed effects models)
        """
        # Merge dataframes on query_id
        merged = mushra_df.merge(metrics_df, on='query_id', how='inner')

        if len(merged) == 0:
            logger.error("No matching query_ids found!")
            return {}

        logger.info(f"Merged data: {len(merged)} records")

        # Get unique conditions
        conditions = merged['condition'].unique()
        logger.info(f"Conditions: {conditions}")

        # Compute correlations for each condition
        results = {}

        for condition in conditions:
            cond_data = merged[merged['condition'] == condition]

            if len(cond_data) < 10:
                logger.warning(f"Insufficient data for {condition}")
                continue

            results[condition] = {}

            # For each metric
            metric_cols = ['l2_error', 'acc_01', 'cosine_sim', 'recall']

            for metric in metric_cols:
                if metric not in cond_data.columns:
                    continue

                ratings = cond_data['rating'].values
                metric_vals = cond_data[metric].values

                # Remove NaN
                mask = ~(np.isnan(ratings) | np.isnan(metric_vals))
                ratings_clean = ratings[mask]
                metric_clean = metric_vals[mask]

                if len(ratings_clean) < 5:
                    continue

                # Spearman correlation
                spearman_r, spearman_p = stats.spearmanr(ratings_clean, metric_clean)

                # Pearson correlation
                pearson_r, pearson_p = stats.pearsonr(ratings_clean, metric_clean)

                results[condition][metric] = {
                    'spearman_r': float(spearman_r),
                    'spearman_p': float(spearman_p),
                    'pearson_r': float(pearson_r),
                    'pearson_p': float(pearson_p),
                    'n_samples': len(ratings_clean),
                    'significant': spearman_p < 0.05 or pearson_p < 0.05
                }

        return results

    def identify_perception_independent_errors(
        self,
        merged_df: pd.DataFrame,
        rating_threshold: float = 70.0,
        error_threshold: float = 0.5
    ) -> pd.DataFrame:
        """
        Identify cases where high parameter error doesn't affect perception.

        These are "perception-independent" errors.
        """
        # Find cases with high rating but high error
        high_rating = merged_df['rating'] >= rating_threshold
        high_error = merged_df['l2_error'] >= error_threshold

        perception_independent = merged_df[high_rating & high_error]

        logger.info(f"Found {len(perception_independent)} perception-independent cases")

        return perception_independent[['query_id', 'condition', 'rating', 'l2_error', 'acc_01']]

    def plot_correlations(self, results: Dict[str, Any], merged_df: pd.DataFrame):
        """Create correlation visualization."""
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))

        conditions = list(results.keys())
        metrics = ['l2_error', 'acc_01', 'cosine_sim', 'recall']

        for idx, (metric, ax) in enumerate(zip(metrics, axes.flat)):
            # Prepare data for plotting
            corr_data = []
            for cond in conditions:
                if metric in results[cond]:
                    corr_data.append({
                        'condition': cond,
                        'spearman': abs(results[cond][metric]['spearman_r']),
                        'pearson': abs(results[cond][metric]['pearson_r'])
                    })

            if not corr_data:
                continue

            df = pd.DataFrame(corr_data)

            x = np.arange(len(df))
            width = 0.35

            ax.bar(x - width/2, df['spearman'], width, label='Spearman', alpha=0.8)
            ax.bar(x + width/2, df['pearson'], width, label='Pearson', alpha=0.8)

            ax.set_ylabel('|Correlation|')
            ax.set_title(f'{metric.upper()} vs Rating')
            ax.set_xticks(x)
            ax.set_xticklabels(df['condition'], rotation=45)
            ax.legend()
            ax.grid(True, alpha=0.3, axis='y')

        plt.tight_layout()
        output_file = self.output_dir / "correlation_analysis.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        logger.info(f"Plot saved to {output_file}")

    def generate_report(self, results: Dict[str, Any]) -> str:
        """Generate text report of correlation analysis."""
        report = []
        report.append("=" * 60)
        report.append("Metric-Perception Correlation Analysis")
        report.append("=" * 60)

        for condition, metrics in results.items():
            report.append(f"\n{condition.upper()}")
            report.append("-" * 40)

            for metric, stats in metrics.items():
                sig_marker = "***" if stats['significant'] else ""
                report.append(f"\n{metric}:")
                report.append(f"  Spearman: r={stats['spearman_r']:.3f}, "
                            f"p={stats['spearman_p']:.4f} {sig_marker}")
                report.append(f"  Pearson:  r={stats['pearson_r']:.3f}, "
                            f"p={stats['pearson_p']:.4f} {sig_marker}")
                report.append(f"  N={stats['n_samples']}")

        report.append("\n" + "=" * 60)
        report.append("*** p < 0.05 (significant)")

        return "\n".join(report)

    def run_analysis(self):
        """Run full correlation analysis."""
        logger.info("Starting correlation analysis")

        # Load data
        mushra_df = self.load_mushra_data(self.config.mushra_data_path)
        metrics_df = self.load_parameter_metrics(self.config.parameter_metrics_path)

        # Compute correlations
        results = self.compute_correlations(mushra_df, metrics_df)

        if not results:
            logger.error("Analysis failed - no results")
            return

        # Identify perception-independent errors
        merged = mushra_df.merge(metrics_df, on='query_id', how='inner')
        pi_errors = self.identify_perception_independent_errors(merged)

        # Save results
        results_file = self.output_dir / "correlation_results.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)

        pi_file = self.output_dir / "perception_independent_errors.csv"
        pi_errors.to_csv(pi_file, index=False)

        # Generate report
        report = self.generate_report(results)
        report_file = self.output_dir / "correlation_report.txt"
        with open(report_file, 'w') as f:
            f.write(report)

        # Plot
        self.plot_correlations(results, merged)

        # Print report
        print("\n" + report)

        logger.info("Analysis complete!")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--mushra-data', required=True, help='Path to MUSHRA data')
    parser.add_argument('--metrics-data', required=True, help='Path to parameter metrics')
    parser.add_argument('--output-dir', default='./results/E4_MetricCorrelation')
    args = parser.parse_args()

    config = CorrelationConfig(
        mushra_data_path=args.mushra_data,
        parameter_metrics_path=args.metrics_data,
        output_dir=args.output_dir
    )

    analyzer = MetricPerceptionCorrelation(config)
    analyzer.run_analysis()


if __name__ == "__main__":
    main()
