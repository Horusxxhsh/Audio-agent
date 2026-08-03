"""
Fusion Weight可视化分析
Fusion Weight Visualization and Analysis

分析uncertainty-aware fusion的权重分布，识别成功和失败案例。

Author: Phase 1 Task 1.2.2
Date: 2025-01-14
"""

import os
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import json
import pandas as pd
from scipy import stats
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity as sklearn_cosine

from Experiments.common.dataset_loader import load_and_merge_data
from Experiments.common.evaluate import Evaluator
from Experiments.common.query_splits import select_query_indices


class FusionWeightAnalyzer:
    """
    分析Dual-Modal Fusion的权重分布
    """

    def __init__(self, beta=2.0, top_k=5):
        self.beta = beta
        self.top_k = top_k

    def compute_entropy(self, scores: np.ndarray) -> float:
        """
        计算Shannon entropy

        Args:
            scores: 归一化相似度分数 [K]

        Returns:
            entropy: H = -sum(p * log(p))
        """
        # Convert scores to a probability distribution via softmax.
        s = scores.astype(np.float64)
        s = s - np.max(s)
        p = np.exp(s)
        p = p / (np.sum(p) + 1e-12)

        entropy = -np.sum(p * np.log(p + 1e-12))
        return entropy

    def compute_weights(self, text_scores: np.ndarray, audio_scores: np.ndarray) -> Dict[str, float]:
        """
        计算fusion weights

        Args:
            text_scores: Text-RAG的top-K相似度 [K]
            audio_scores: Audio-RAG的top-K相似度 [K]

        Returns:
            weights: {
                'w_text': float,
                'w_audio': float,
                'u_text': float,
                'u_audio': float,
                'u_text_norm': float,
                'u_audio_norm': float
            }
        """
        # Compute entropy
        u_text = self.compute_entropy(text_scores)
        u_audio = self.compute_entropy(audio_scores)

        # Normalize to [0, 1]
        u_max = np.log(self.top_k)
        u_text_norm = u_text / u_max
        u_audio_norm = u_audio / u_max

        # Compute weights (exponential decay)
        w_text = np.exp(-self.beta * u_text_norm)
        w_audio = np.exp(-self.beta * u_audio_norm)

        # Normalize
        Z = w_text + w_audio
        w_text = w_text / Z
        w_audio = w_audio / Z

        return {
            'w_text': w_text,
            'w_audio': w_audio,
            'u_text': u_text,
            'u_audio': u_audio,
            'u_text_norm': u_text_norm,
            'u_audio_norm': u_audio_norm
        }

    def analyze_query_categories(
        self,
        dataset: List[Dict],
        retrieval_results: Dict
    ) -> pd.DataFrame:
        """
        分析不同query类型的fusion行为

        Args:
            dataset: 完整数据集
            retrieval_results: 检索结果 {
                'query_idx': {
                    'text_scores': [K],
                    'audio_scores': [K],
                    'text_best': params,
                    'audio_best': params,
                    'fused': params,
                    'ground_truth': params,
                    'text_distance': float,
                    'audio_distance': float,
                    'fused_distance': float
                }
            }

        Returns:
            DataFrame with analysis
        """
        results = []

        for query_idx, data in retrieval_results.items():
            text_scores = np.array(data['text_scores'])
            audio_scores = np.array(data['audio_scores'])

            weights = self.compute_weights(text_scores, audio_scores)

            # Categorize query
            category = self._categorize_query(weights, data)

            result = {
                'query_idx': query_idx,
                'w_text': weights['w_text'],
                'w_audio': weights['w_audio'],
                'u_text_norm': weights['u_text_norm'],
                'u_audio_norm': weights['u_audio_norm'],
                'category': category,
                'text_distance': data['text_distance'],
                'audio_distance': data['audio_distance'],
                'fused_distance': data['fused_distance'],
                'improvement': data['text_distance'] - data['fused_distance']
            }
            results.append(result)

        return pd.DataFrame(results)

    def _categorize_query(self, weights: Dict, data: Dict) -> str:
        """
        分类query类型

        Categories:
        - 'text_dominant': Text权重 > 0.7
        - 'audio_dominant': Audio权重 > 0.7
        - 'balanced': 两个权重都在 [0.3, 0.7]
        - 'conflict': 两者都确信但方向矛盾 (u < 0.3 但distance都很大)
        - 'uncertain': 两者都不确定 (u > 0.7)
        """
        w_text = weights['w_text']
        u_text = weights['u_text_norm']
        u_audio = weights['u_audio_norm']

        if w_text > 0.7:
            return 'text_dominant'
        elif weights['w_audio'] > 0.7:
            return 'audio_dominant'
        elif 0.3 <= w_text <= 0.7:
            # Check for conflict
            if u_text < 0.3 and u_audio < 0.3:
                # Both confident but...
                # Check if they point in different directions
                text_dist = data['text_distance']
                audio_dist = data['audio_distance']
                if text_dist > 0.2 and audio_dist > 0.2:
                    # Both far from ground truth → likely contradiction
                    return 'conflict'
            return 'balanced'
        elif u_text > 0.7 and u_audio > 0.7:
            return 'uncertain'
        else:
            return 'other'

    def plot_weight_distribution(
        self,
        df: pd.DataFrame,
        output_path: str = "fusion_weight_distribution.png"
    ):
        """
        绘制fusion weight分布（小样本友好版本）
        """
        import matplotlib

        matplotlib.rcParams["pdf.fonttype"] = 42
        matplotlib.rcParams["ps.fonttype"] = 42
        matplotlib.rcParams["font.size"] = 14
        matplotlib.rcParams["axes.titlesize"] = 15
        matplotlib.rcParams["axes.labelsize"] = 14
        matplotlib.rcParams["xtick.labelsize"] = 12
        matplotlib.rcParams["ytick.labelsize"] = 12
        matplotlib.rcParams["legend.fontsize"] = 11

        fig, axes = plt.subplots(1, 2, figsize=(8.5, 3.4))

        # Plot 1: Weight vs uncertainty
        ax1 = axes[0]
        categories = df['category'].unique()
        colors = {
            'text_dominant': '#3498db',
            'audio_dominant': '#e74c3c',
            'balanced': '#2ecc71',
            'conflict': '#f39c12',
            'uncertain': '#9b59b6',
            'other': '#95a5a6'
        }

        for cat in categories:
            subset = df[df['category'] == cat]
            ax1.scatter(
                subset['u_text_norm'],
                subset['w_text'],
                label=cat,
                color=colors.get(cat, '#95a5a6'),
                alpha=0.6,
                s=60
            )

        if len(df) >= 2:
            coef = np.polyfit(df['u_text_norm'], df['w_text'], deg=1)
            x_fit = np.linspace(df['u_text_norm'].min(), df['u_text_norm'].max(), 100)
            y_fit = coef[0] * x_fit + coef[1]
            ax1.plot(x_fit, y_fit, linestyle='--', color='black', linewidth=1.4, label='Linear trend')

        ax1.axhline(y=0.5, color='gray', linestyle=':', linewidth=1.0)
        ax1.set_xlabel('Text uncertainty (normalized entropy)', fontsize=14)
        ax1.set_ylabel('Text weight $w_{text}$', fontsize=14)
        ax1.set_title(f'Fusion Weight vs. Uncertainty (N={len(df)})', fontsize=15, fontweight='bold')
        ax1.legend(fontsize=11)
        ax1.grid(True, alpha=0.3)

        # Plot 2: Per-query objective comparison (clearer than tiny-sample histograms)
        ax2 = axes[1]
        query_ids = np.arange(len(df))
        ax2.plot(query_ids, df['text_distance'], marker='o', linewidth=1.6, label='Text-only', color='#1f77b4')
        ax2.plot(query_ids, df['audio_distance'], marker='s', linewidth=1.6, label='Audio-only', color='#ff7f0e')
        ax2.plot(query_ids, df['fused_distance'], marker='^', linewidth=1.8, label='Fusion', color='#2ca02c')
        ax2.set_xlabel('Query index', fontsize=14)
        ax2.set_ylabel('Param. Dist.', fontsize=14)
        ax2.set_title('Per-query Param. Dist. Comparison', fontsize=15, fontweight='bold')
        ax2.set_xticks(query_ids)
        ax2.grid(True, alpha=0.3)
        ax2.legend(fontsize=11)

        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Figure saved to {output_path}")

        return fig

    def plot_failure_cases(
        self,
        df: pd.DataFrame,
        output_path: str = "fusion_failure_analysis.png"
    ):
        """
        分析和可视化fusion失败案例
        """
        # Identify failures: fusion worse than both modalities
        failures = df[
            (df['fused_distance'] > df['text_distance']) &
            (df['fused_distance'] > df['audio_distance'])
        ]

        if len(failures) == 0:
            print("No failure cases detected!")
            return None

        print(f"\nAnalyzing {len(failures)} failure cases...")

        fig, axes = plt.subplots(2, 2, figsize=(14, 10))

        # Plot 1: Uncertainty characteristics of failures
        ax1 = axes[0, 0]

        import matplotlib as _mpl

        _mpl.rcParams["pdf.fonttype"] = 42
        _mpl.rcParams["ps.fonttype"] = 42
        _mpl.rcParams["font.size"] = 16
        _mpl.rcParams["axes.titlesize"] = 17
        _mpl.rcParams["axes.labelsize"] = 16
        _mpl.rcParams["xtick.labelsize"] = 13
        _mpl.rcParams["ytick.labelsize"] = 13
        _mpl.rcParams["legend.fontsize"] = 13

        # Compare failures vs. successes
        successes = df[
            (df['fused_distance'] <= df['text_distance']) |
            (df['fused_distance'] <= df['audio_distance'])
        ]

        ax1.scatter(
            successes['u_text_norm'],
            successes['u_audio_norm'],
            alpha=0.3,
            color='green',
            label=f'Successes (n={len(successes)})',
            s=50
        )
        ax1.scatter(
            failures['u_text_norm'],
            failures['u_audio_norm'],
            alpha=0.8,
            color='red',
            label=f'Failures (n={len(failures)})',
            s=80,
            edgecolors='black',
            linewidths=1.5
        )

        ax1.set_xlabel('Text Uncertainty', fontsize=11)
        ax1.set_ylabel('Audio Uncertainty', fontsize=11)
        ax1.set_title('Failure Case Analysis: Uncertainty Space', fontsize=13, fontweight='bold')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # Add low-uncertainty rectangle (conflict zone)
        ax1.axvspan(0, 0.3, alpha=0.1, color='red', label='Conflict Zone')

        # Plot 2: Weight distribution
        ax2 = axes[0, 1]

        bins = np.linspace(0, 1, 20)
        ax2.hist(
            successes['w_text'],
            bins=bins,
            alpha=0.5,
            color='green',
            label='Successes',
            density=True
        )
        ax2.hist(
            failures['w_text'],
            bins=bins,
            alpha=0.7,
            color='red',
            label='Failures',
            density=True
        )

        ax2.set_xlabel('Text Weight', fontsize=11)
        ax2.set_ylabel('Density', fontsize=11)
        ax2.set_title('Weight Distribution: Success vs. Failure', fontsize=13, fontweight='bold')
        ax2.legend()
        ax2.grid(axis='y', alpha=0.3)

        # Plot 3: Category breakdown
        ax3 = axes[1, 0]

        failure_cats = failures['category'].value_counts()
        success_cats = successes['category'].value_counts()

        x = np.arange(len(set(list(failure_cats.index) + list(success_cats.index))))
        width = 0.35

        all_cats = set(list(failure_cats.index) + list(success_cats.index))

        failure_counts = [failure_cats.get(cat, 0) for cat in all_cats]
        success_counts = [success_cats.get(cat, 0) for cat in all_cats]

        ax3.bar(x - width/2, success_counts, width, label='Successes', color='green', alpha=0.7)
        ax3.bar(x + width/2, failure_counts, width, label='Failures', color='red', alpha=0.7)

        ax3.set_xlabel('Category', fontsize=11)
        ax3.set_ylabel('Count', fontsize=11)
        ax3.set_title('Success/Failure by Category', fontsize=13, fontweight='bold')
        ax3.set_xticks(x)
        ax3.set_xticklabels(all_cats, rotation=45, ha='right')
        ax3.legend()
        ax3.grid(axis='y', alpha=0.3)

        # Plot 4: Distance comparison
        ax4 = axes[1, 1]

        ax4.scatter(
            failures['text_distance'],
            failures['audio_distance'],
            c=failures['fused_distance'],
            cmap='Reds',
            s=80,
            alpha=0.8,
            edgecolors='black',
            linewidths=1,
            label='Failures'
        )

        # Add colorbar
        cbar = plt.colorbar(ax4.collections[0], ax=ax4)
        cbar.set_label('Fused Distance', fontsize=10)

        # Add diagonal
        max_dist = max(failures['text_distance'].max(), failures['audio_distance'].max())
        ax4.plot([0, max_dist], [0, max_dist], 'k--', linewidth=2, label='Equal Performance')

        ax4.set_xlabel('Text Distance', fontsize=11)
        ax4.set_ylabel('Audio Distance', fontsize=11)
        ax4.set_title('Failure Case: Modality Performance', fontsize=13, fontweight='bold')
        ax4.legend()
        ax4.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Failure analysis figure saved to {output_path}")

        return fig, failures


def generate_mock_retrieval_results(n_queries=50, top_k=5, seed=42):
    """
    生成mock retrieval results用于演示
    """
    np.random.seed(seed)

    results = {}

    for i in range(n_queries):
        # Generate random similarity scores
        text_scores = np.random.rand(top_k)
        audio_scores = np.random.rand(top_k)

        # Normalize
        text_scores = text_scores / np.sum(text_scores)
        audio_scores = audio_scores / np.sum(audio_scores)

        # Generate mock parameter vectors (6-dim)
        text_best = np.random.rand(6)
        audio_best = np.random.rand(6)
        ground_truth = np.random.rand(6)

        # Fused (simple average for demo)
        fused = 0.5 * text_best + 0.5 * audio_best

        # Compute distances
        text_distance = np.linalg.norm(text_best - ground_truth)
        audio_distance = np.linalg.norm(audio_best - ground_truth)
        fused_distance = np.linalg.norm(fused - ground_truth)

        results[i] = {
            'text_scores': text_scores.tolist(),
            'audio_scores': audio_scores.tolist(),
            'text_best': text_best.tolist(),
            'audio_best': audio_best.tolist(),
            'fused': fused.tolist(),
            'ground_truth': ground_truth.tolist(),
            'text_distance': text_distance,
            'audio_distance': audio_distance,
            'fused_distance': fused_distance
        }

    return results


def main():
    """运行fusion weight可视化分析（基于本仓库数据）"""

    print("=" * 70)
    print("Fusion Weight可视化分析")
    print("Fusion Weight Visualization and Analysis")
    print("=" * 70)

    dataset = load_and_merge_data()
    print(f"\nLoaded {len(dataset)} samples from dataset loader.")

    split_selector = os.getenv("FUSION_TESTSET", "30")
    try:
        split_info = select_query_indices(dataset, split_selector=split_selector, default_split="30")
    except ValueError as exc:
        print(f"Warning: {exc}. Falling back to split=30.")
        split_info = select_query_indices(dataset, split_selector="30", default_split="30")
    test_indices = split_info.test_indices
    if split_info.used_random_fallback:
        print(
            "Warning: No named test samples were found for split "
            f"{split_info.split}; using random fallback size={len(test_indices)}."
        )
    else:
        print(
            f"Using split={split_info.split}: "
            f"matched {len(split_info.found_names)}/{len(split_info.requested_names)} query names."
        )
        if split_info.missing_names:
            print(f"Missing query names ({len(split_info.missing_names)}): {split_info.missing_names}")

    candidate_indices = [i for i in range(len(dataset)) if i not in set(test_indices)]
    print(f"Candidate set size={len(candidate_indices)}.")

    evaluator = Evaluator()

    def build_text(item: Dict) -> str:
        song_name = (item.get("SongName") or "").replace("_", " ")
        style = " ".join(item.get("Style", []) or [])
        return f"{song_name} {style}".strip()

    # Candidate text index (TF-IDF)
    cand_items = [dataset[i] for i in candidate_indices]
    corpus = [build_text(it) for it in cand_items]
    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf = vectorizer.fit_transform(corpus)

    # Candidate TRR vectors from cache
    def load_trr(audio_path: Optional[str]) -> Optional[np.ndarray]:
        if not audio_path:
            return None
        cache_path = audio_path + ".trr.npy"
        if os.path.exists(cache_path):
            try:
                return np.load(cache_path)
            except Exception:
                return None
        return None

    trr_dim = None
    for it in cand_items:
        v = load_trr(it.get("AudioPath"))
        if v is not None:
            trr_dim = int(v.shape[0])
            break
    trr_dim = trr_dim or 4096

    cand_trr_arr = np.stack(
        [
            (load_trr(it.get("AudioPath")) if load_trr(it.get("AudioPath")) is not None else np.zeros(trr_dim))
            for it in cand_items
        ],
        axis=0,
    ).astype(np.float64)

    def cosine_scores(query_vec: np.ndarray, mat: np.ndarray) -> np.ndarray:
        q = query_vec.astype(np.float64)
        q = q / (np.linalg.norm(q) + 1e-12)
        m = mat / (np.linalg.norm(mat, axis=1, keepdims=True) + 1e-12)
        return m @ q

    def minmax(x: np.ndarray) -> np.ndarray:
        lo = float(np.min(x))
        hi = float(np.max(x))
        if hi - lo < 1e-12:
            return np.zeros_like(x, dtype=np.float64)
        return (x - lo) / (hi - lo)

    top_k = 5
    betas = [0.5, 1.0, 2.0, 4.0]

    def run_for_beta(beta: float) -> Tuple[pd.DataFrame, Dict]:
        analyzer = FusionWeightAnalyzer(beta=beta, top_k=top_k)
        retrieval_results: Dict[str, Dict] = {}

        perf = {"text": [], "audio": [], "fusion": []}  # tuples (l2, acc, cos)

        for q_idx in test_indices:
            q_item = dataset[q_idx]
            q_text = build_text(q_item)

            q_vec = vectorizer.transform([q_text])
            text_scores_full = sklearn_cosine(q_vec, tfidf).flatten().astype(np.float64)

            q_trr = load_trr(q_item.get("AudioPath"))
            if q_trr is None:
                audio_scores_full = np.zeros(len(cand_items), dtype=np.float64)
            else:
                audio_scores_full = cosine_scores(q_trr, cand_trr_arr)

            text_topk = np.sort(text_scores_full)[-top_k:]
            audio_topk = np.sort(audio_scores_full)[-top_k:]
            weights = analyzer.compute_weights(text_topk, audio_topk)

            text_best_pos = int(np.argmax(text_scores_full))
            audio_best_pos = int(np.argmax(audio_scores_full))
            fused_scores = weights["w_text"] * minmax(text_scores_full) + weights["w_audio"] * minmax(audio_scores_full)
            fused_best_pos = int(np.argmax(fused_scores))

            text_best_idx = candidate_indices[text_best_pos]
            audio_best_idx = candidate_indices[audio_best_pos]
            fused_best_idx = candidate_indices[fused_best_pos]

            gt_params = q_item["Parameters"]

            def eval_one(retrieved_idx: int):
                rp = dataset[retrieved_idx]["Parameters"]
                return (
                    evaluator.compute_parameter_distance(rp, gt_params),
                    evaluator.compute_accuracy_tolerance(rp, gt_params, tolerance=0.1),
                    evaluator.compute_cosine_similarity(rp, gt_params),
                )

            text_m = eval_one(text_best_idx)
            audio_m = eval_one(audio_best_idx)
            fused_m = eval_one(fused_best_idx)
            perf["text"].append(text_m)
            perf["audio"].append(audio_m)
            perf["fusion"].append(fused_m)

            retrieval_results[str(q_idx)] = {
                "text_scores": text_topk.tolist(),
                "audio_scores": audio_topk.tolist(),
                "text_distance": float(text_m[0]),
                "audio_distance": float(audio_m[0]),
                "fused_distance": float(fused_m[0]),
            }

        df = analyzer.analyze_query_categories(dataset, retrieval_results)
        # Summaries for paper tables
        def mean(col: int, key: str) -> float:
            return float(np.mean([t[col] for t in perf[key]])) if perf[key] else 0.0

        summary = {
            "beta": beta,
            "w_text_mean": float(df["w_text"].mean()) if len(df) else 0.0,
            "w_text_std": float(df["w_text"].std()) if len(df) else 0.0,
            "w_text_min": float(df["w_text"].min()) if len(df) else 0.0,
            "w_text_max": float(df["w_text"].max()) if len(df) else 0.0,
            "l2_text": mean(0, "text"),
            "l2_audio": mean(0, "audio"),
            "l2_fusion": mean(0, "fusion"),
            "acc_text": mean(1, "text"),
            "acc_audio": mean(1, "audio"),
            "acc_fusion": mean(1, "fusion"),
            "cos_text": mean(2, "text"),
            "cos_audio": mean(2, "audio"),
            "cos_fusion": mean(2, "fusion"),
        }

        return df, summary

    beta_summaries: List[Dict] = []
    df_default: Optional[pd.DataFrame] = None
    for b in betas:
        print(f"\nRunning fusion analysis (beta={b})...")
        df_b, summary_b = run_for_beta(b)
        beta_summaries.append(summary_b)
        if abs(b - 2.0) < 1e-9:
            df_default = df_b

    beta_df = pd.DataFrame(beta_summaries)
    beta_df.to_csv("Experiments/Fusion/fusion_beta_sensitivity.csv", index=False)
    print("\nSaved beta sensitivity to Experiments/Fusion/fusion_beta_sensitivity.csv")

    df = df_default if df_default is not None else pd.DataFrame()

    print(f"\nAnalyzed {len(df)} queries")
    print("\nCategory Distribution:")
    print(df['category'].value_counts().to_string())

    # Plot weight distribution
    print("\nGenerating weight distribution visualization...")
    FusionWeightAnalyzer(beta=2.0, top_k=top_k).plot_weight_distribution(df, "Paper/figures/fusion_weight_distribution.pdf")

    # Plot failure analysis
    print("\nAnalyzing failure cases...")
    result = FusionWeightAnalyzer(beta=2.0, top_k=top_k).plot_failure_cases(df, "Experiments/Fusion/fusion_failure_analysis.pdf")

    if result:
        fig, failures = result
        print(f"\nFound {len(failures)} failure cases ({len(failures)/len(df)*100:.1f}%)")
        print("\nFailure Category Breakdown:")
        print(failures['category'].value_counts().to_string())

        print("\nFailure Statistics:")
        print(f"  Mean text uncertainty: {failures['u_text_norm'].mean():.3f}")
        print(f"  Mean audio uncertainty: {failures['u_audio_norm'].mean():.3f}")
        print(f"  Mean text weight: {failures['w_text'].mean():.3f}")

    # Save results
    df.to_csv("Experiments/Fusion/fusion_weight_analysis.csv", index=False)
    print("\nResults saved to Experiments/Fusion/fusion_weight_analysis.csv")

    # Summary
    print("\n" + "=" * 70)
    print("KEY FINDINGS")
    print("=" * 70)

    if len(df) > 0:
        n_text_dom = len(df[df['category']=='text_dominant'])
        n_audio_dom = len(df[df['category']=='audio_dominant'])
        n_balanced = len(df[df['category']=='balanced'])
        n_conflict = len(df[df['category']=='conflict'])
        n_uncertain = len(df[df['category']=='uncertain'])

        w_text_mean = df['w_text'].mean()
        w_text_std = df['w_text'].std()
        w_audio_mean = df['w_audio'].mean()
        w_audio_std = df['w_audio'].std()

        improv_mean = df['improvement'].mean()
        improv_pos = (df['improvement'] > 0).sum()
        improv_pos_pct = improv_pos/len(df)*100

        n_failures = len(df[(df['fused_distance'] > df['text_distance']) & (df['fused_distance'] > df['audio_distance'])])
        worst_cat = df.loc[df['improvement'].idxmin(), 'category'] if len(df) > 0 else 'N/A'

        print(f"""
1. **Query Categories**:
   - Text-dominant: {n_text_dom} queries
   - Audio-dominant: {n_audio_dom} queries
   - Balanced: {n_balanced} queries
   - Conflict: {n_conflict} queries
   - Uncertain: {n_uncertain} queries

2. **Average Weights**:
   - Text weight: {w_text_mean:.3f} ± {w_text_std:.3f}
   - Audio weight: {w_audio_mean:.3f} ± {w_audio_std:.3f}

3. **Fusion Performance**:
   - Mean improvement: {improv_mean:.4f}
   - Positive improvements: {improv_pos} ({improv_pos_pct:.1f}%)

4. **Failure Cases**:
   - Total failures: {n_failures}
   - Main failure category: {worst_cat}
        """)

    print("\n" + "=" * 70)
    print("NEXT STEPS")
    print("=" * 70)
    print("""
1. Review the generated visualizations:
   - fusion_weight_distribution.png: Overall weight analysis
   - fusion_failure_analysis.png: Failure case diagnosis

2. Analyze failure cases:
   - Are failures concentrated in specific categories?
   - Do failures correlate with certain uncertainty patterns?

3. Consider improvements:
   - If many 'conflict' failures: Add direction-aware fusion
   - If failures in balanced cases: Tune temperature parameter β
   - If high uncertainty failures: Improve individual modality quality
    """)


if __name__ == "__main__":
    main()
