"""
Wav2Vec2层选择分析实验
Layer Selection Analysis for TRR

分析不同Wav2Vec2层对纹理检索性能的影响，验证为何第9层是最优选择。

Author: Phase 1 Task 1.1.3
Date: 2025-01-14
"""

import os
import numpy as np
import torch
import torch.nn as nn
import json
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import pandas as pd
from tqdm import tqdm
from scipy.io import wavfile
from scipy import signal

import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from Experiments.common.dataset_loader import load_and_merge_data
from Experiments.common.query_splits import select_query_indices


def _flatten_params(params, prefix: str = "") -> Dict[str, float]:
    flat: Dict[str, float] = {}
    if not isinstance(params, dict):
        return flat
    for k, v in params.items():
        key = f"{prefix}.{k}" if prefix else str(k)
        if isinstance(v, dict):
            flat.update(_flatten_params(v, key))
        elif isinstance(v, (int, float)):
            flat[key] = float(v)
    return flat


def _compute_norm_stats(dataset: List[Dict]) -> Tuple[List[str], Dict[str, Tuple[float, float]]]:
    all_keys = set()
    vals_by_key: Dict[str, List[float]] = {}
    for item in dataset:
        flat = _flatten_params(item.get("Parameters", {}))
        for k, v in flat.items():
            all_keys.add(k)
            vals_by_key.setdefault(k, []).append(v)

    keys = sorted(all_keys)
    stats: Dict[str, Tuple[float, float]] = {}
    for k in keys:
        vals = vals_by_key.get(k, [])
        if not vals:
            stats[k] = (0.0, 1.0)
            continue
        lo = float(min(vals))
        hi = float(max(vals))
        if abs(hi - lo) < 1e-12:
            hi = lo + 1.0
        stats[k] = (lo, hi)
    return keys, stats


def _params_to_vec(params: Dict, keys: List[str], stats: Dict[str, Tuple[float, float]]) -> np.ndarray:
    flat = _flatten_params(params)
    vec = np.zeros(len(keys), dtype=np.float64)
    for i, k in enumerate(keys):
        v = flat.get(k, 0.0)
        lo, hi = stats[k]
        vec[i] = (v - lo) / (hi - lo)
    return vec


def _l2_distance_normalized(p1: Dict, p2: Dict, keys: List[str], stats: Dict[str, Tuple[float, float]]) -> float:
    v1 = _params_to_vec(p1, keys, stats)
    v2 = _params_to_vec(p2, keys, stats)
    return float(np.linalg.norm(v1 - v2))


class TRR_LayerAnalyzer:
    """
    分析不同Wav2Vec2层的TRR性能
    """

    def __init__(self, device=None, project_dim=64):
        self.device = device if device else torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.project_dim = project_dim

        # Load Wav2Vec2 model
        print("Loading Wav2Vec2 model...")
        from transformers import Wav2Vec2Model
        self.model = Wav2Vec2Model.from_pretrained("facebook/wav2vec2-base").to(self.device)
        self.model.eval()

        # Use a single frozen random projection shared across layers.
        # This isolates the effect of layer choice (rather than projection randomness).
        torch.manual_seed(42)
        self.projector = nn.Linear(768, self.project_dim).to(self.device)
        for param in self.projector.parameters():
            param.requires_grad = False

    def load_and_preprocess(self, audio_path: str) -> Optional[torch.Tensor]:
        """Load and preprocess audio."""
        try:
            sample_rate, data = wavfile.read(audio_path)
            waveform = torch.from_numpy(np.asarray(data, dtype=np.float32))
            if waveform.dim() > 1:
                waveform = waveform.mean(dim=1)

            # Normalize int PCM to [-1, 1] if needed.
            max_abs = waveform.abs().max().item() if waveform.numel() else 0.0
            if max_abs > 1.5:
                waveform = waveform / (max_abs + 1e-9)

            if int(sample_rate) != 16000:
                resampled = signal.resample_poly(waveform.cpu().numpy(), 16000, int(sample_rate)).astype(np.float32)
                waveform = torch.from_numpy(resampled)
                sample_rate = 16000

            waveform = waveform.unsqueeze(0)  # [1, T]
            waveform = (waveform - waveform.mean()) / torch.sqrt(waveform.var() + 1e-7)
            return waveform.to(self.device)
        except Exception as e:
            print(f"Error loading {audio_path}: {e}")
            return None

    def extract_features(self, waveform: torch.Tensor, layer_idx: int) -> torch.Tensor:
        """Extract features from specific layer."""
        with torch.no_grad():
            outputs = self.model(waveform, output_hidden_states=True)

        # Layer 1 is at index 1 in hidden_states
        feature_map = outputs.hidden_states[layer_idx]
        return feature_map  # [1, Time, 768]

    def compute_gram_matrix(self, features: torch.Tensor, layer_idx: int) -> torch.Tensor:
        """Compute Gram matrix for given layer."""
        feats = features.squeeze(0)  # [Time, 768]
        n_time = feats.shape[0]

        projected = self.projector(feats)  # [Time, project_dim]

        gram = torch.matmul(projected.T, projected)  # [64, 64]
        gram = gram / n_time

        return gram

    def get_embedding_for_layer(self, audio_path: str, layer_idx: int) -> Optional[np.ndarray]:
        """Get TRR embedding for a specific layer."""
        waveform = self.load_and_preprocess(audio_path)
        if waveform is None:
            return None

        features = self.extract_features(waveform, layer_idx)
        gram = self.compute_gram_matrix(features, layer_idx)

        embedding = gram.flatten()
        embedding = torch.nn.functional.normalize(embedding, p=2, dim=0)

        return embedding.cpu().numpy()

    def get_embeddings_for_layers(self, audio_path: str, layer_indices: List[int]) -> Dict[int, np.ndarray]:
        """
        Compute TRR embeddings for multiple Wav2Vec2 layers with a single forward pass.
        Returns a dict: {layer_idx: embedding}.
        """
        waveform = self.load_and_preprocess(audio_path)
        if waveform is None:
            return {}

        with torch.no_grad():
            outputs = self.model(waveform, output_hidden_states=True)

        layer_to_emb: Dict[int, np.ndarray] = {}
        for layer_idx in layer_indices:
            feats = outputs.hidden_states[layer_idx].squeeze(0)  # [Time, 768]
            n_time = feats.shape[0]
            projected = self.projector(feats)  # [Time, project_dim]
            gram = torch.matmul(projected.T, projected) / max(int(n_time), 1)  # [d, d]
            emb = torch.nn.functional.normalize(gram.flatten(), p=2, dim=0)
            layer_to_emb[layer_idx] = emb.cpu().numpy()

        return layer_to_emb

    def analyze_layer(self, dataset: List[Dict], layer_idx: int, test_indices: List[int]) -> Dict:
        """Analyze performance for a specific layer."""
        print(f"\nAnalyzing Layer {layer_idx}...")

        # Index dataset for this layer
        embeddings = []
        valid_indices = []

        for idx, item in enumerate(tqdm(dataset, desc=f"Indexing Layer {layer_idx}")):
            audio_path = item.get('AudioPath')
            if audio_path and os.path.exists(audio_path):
                emb = self.get_embedding_for_layer(audio_path, layer_idx)
                if emb is not None:
                    embeddings.append(emb)
                    valid_indices.append(idx)

        embeddings = np.array(embeddings)

        # Evaluate retrieval performance
        param_distances = []
        cosine_sims = []

        for test_idx in test_indices:
            if test_idx not in valid_indices:
                continue

            emb_idx = valid_indices.index(test_idx)
            query_emb = embeddings[emb_idx]
            gt_params = np.array(dataset[test_idx]['Parameters'])

            # Compute similarities
            mask = np.ones(len(embeddings), dtype=bool)
            mask[emb_idx] = False

            candidate_embeddings = embeddings[mask]
            candidate_indices = [valid_indices[i] for i in range(len(valid_indices)) if mask[i]]

            # Cosine similarity
            similarities = candidate_embeddings @ query_emb
            top_idx = np.argmax(similarities)

            retrieved_idx = candidate_indices[top_idx]
            retrieved_params = np.array(dataset[retrieved_idx]['Parameters'])

            # Metrics
            param_dist = np.linalg.norm(gt_params - retrieved_params)
            param_distances.append(param_dist)
            cosine_sims.append(similarities[top_idx])

        return {
            'layer_idx': layer_idx,
            'param_distance': np.mean(param_distances),
            'cosine': np.mean(cosine_sims),
            'n_samples': len(param_distances)
        }


def analyze_layer_characteristics():
    """
    理论分析：不同Wav2Vec2层的特性
    Theoretical Analysis: Characteristics of Different Wav2Vec2 Layers
    """

    layer_analysis = {
        1: {
            'name': 'Conv1',
            'type': 'Low-level',
            'characteristics': 'Raw waveform, very local features',
            'expected_use': 'Onset detection, pitch tracking',
            'suitability_for_texture': 'Poor - too granular, no temporal context'
        },
        2: {
            'name': 'Conv2',
            'type': 'Low-level',
            'characteristics': 'Short-term temporal patterns',
            'expected_use': 'Phoneme recognition',
            'suitability_for_texture': 'Poor - limited temporal window'
        },
        3: {
            'name': 'Conv3',
            'type': 'Low-level',
            'characteristics': 'Longer temporal patterns',
            'expected_use': 'Speech recognition',
            'suitability_for_texture': 'Limited - starting to capture texture'
        },
        4: {
            'name': 'Conv4',
            'type': 'Mid-level',
            'characteristics': 'Balanced spectral/temporal',
            'expected_use': 'Speaker identification',
            'suitability_for_texture': 'Moderate - captures some texture'
        },
        5: {
            'name': 'Conv5',
            'type': 'Mid-level',
            'characteristics': 'Abstract phonetic features',
            'expected_use': 'Speaker accents',
            'suitability_for_texture': 'Good - balance of detail and abstraction'
        },
        6: {
            'name': 'Transformer Layer 1',
            'type': 'Mid-level',
            'characteristics': 'Contextualized features',
            'expected_use': 'Language modeling',
            'suitability_for_texture': 'Good - contextual info helps'
        },
        7: {
            'name': 'Transformer Layer 2',
            'type': 'Mid-level',
            'characteristics': 'Higher-level abstractions',
            'expected_use': 'Semantic understanding',
            'suitability_for_texture': 'Very Good - robust representations'
        },
        8: {
            'name': 'Transformer Layer 3',
            'type': 'Mid-level',
            'characteristics': 'Rich contextual features',
            'expected_use': 'Semantic tasks',
            'suitability_for_texture': 'Very Good - best for complex textures'
        },
        9: {
            'name': 'Transformer Layer 4',
            'type': 'Mid-to-High',
            'characteristics': 'Semantic + acoustic balance',
            'expected_use': 'Speech understanding',
            'suitability_for_texture': 'Excellent - optimal balance'
        },
        10: {
            'name': 'Transformer Layer 5',
            'type': 'High-level',
            'characteristics': 'More semantic, less acoustic',
            'expected_use': 'Meaningful speech',
            'suitability_for_texture': 'Good - losing some acoustic details'
        },
        11: {
            'name': 'Transformer Layer 6',
            'type': 'High-level',
            'characteristics': 'High-level semantic features',
            'expected_use': 'Discourse understanding',
            'suitability_for_texture': 'Fair - too abstract'
        },
        12: {
            'name': 'Transformer Layer 7',
            'type': 'High-level',
            'characteristics': 'Task-specific features',
            'expected_use': 'Downstream tasks',
            'suitability_for_texture': 'Poor - over-specialized'
        }
    }

    return layer_analysis


def plot_layer_selection_results(results_df, output_path="layer_selection_analysis.png"):
    """
    Plot layer selection results with both performance and characteristics.
    """
    fig, axes = plt.subplots(2, 1, figsize=(12, 10))

    # Plot 1: Performance metrics (separate y-scales to avoid mixed-metric distortion)
    ax1 = axes[0]

    layers = results_df['layer_idx'].values
    param_dist = results_df['param_distance'].values
    cosine = results_df['cosine'].values

    x = np.arange(len(layers))
    width = 0.55

    bars = ax1.bar(x, param_dist, width, label='Param. Dist. (L2)', color='#e74c3c', alpha=0.85)
    ax1.set_xlabel('Wav2Vec2 Layer Index', fontsize=12)
    ax1.set_ylabel('Param. Dist. (lower is better)', fontsize=12, color='#e74c3c')
    ax1.set_title('TRR Performance Across Wav2Vec2 Layers', fontsize=14, fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(layers)
    ax1.tick_params(axis='y', labelcolor='#e74c3c')
    ax1.grid(axis='y', alpha=0.3)

    ax1_twin = ax1.twinx()
    line = ax1_twin.plot(
        x,
        cosine,
        color='#1f4e79',
        marker='o',
        linewidth=2.2,
        label='Cosine Similarity'
    )
    ax1_twin.set_ylabel('Cosine Similarity (higher is better)', fontsize=12, color='#1f4e79')
    ax1_twin.tick_params(axis='y', labelcolor='#1f4e79')

    handles = [bars] + line
    labels = [h.get_label() for h in handles]
    ax1.legend(handles, labels, loc='upper left')

    # Plot 2: Layer characteristics annotation
    ax2 = axes[1]

    layer_analysis = analyze_layer_characteristics()

    # Annotate each layer with its type
    colors = []
    for idx in layers:
        if layer_analysis[idx]['type'] == 'Low-level':
            colors.append('#e74c3c')  # Red
        elif layer_analysis[idx]['type'] == 'Mid-level':
            colors.append('#f39c12')  # Orange
        elif layer_analysis[idx]['type'] == 'Mid-to-High':
            colors.append('#3498db')  # Blue
        else:  # High-level
            colors.append('#9b59b6')  # Purple

    # Plot parameter distance with layer-type color coding
    ax2.bar(layers, param_dist, color=colors, alpha=0.7, edgecolor='black')

    ax2.set_xlabel('Wav2Vec2 Layer Index', fontsize=12)
    ax2.set_ylabel('Param. Dist. (L2)', fontsize=12)
    ax2.set_title('Param. Dist. by Layer Type', fontsize=14, fontweight='bold')
    ax2.grid(axis='y', alpha=0.3)

    # Add legend for layer types
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#e74c3c', edgecolor='black', label='Low-level (Layers 1-3)'),
        Patch(facecolor='#f39c12', edgecolor='black', label='Mid-level (Layers 4-8)'),
        Patch(facecolor='#3498db', edgecolor='black', label='Mid-to-High (Layer 9)'),
        Patch(facecolor='#9b59b6', edgecolor='black', label='High-level (Layers 10-12)')
    ]
    ax2.legend(handles=legend_elements, loc='upper right')

    # Highlight best layer in this run
    best_layer_idx = int(results_df.loc[results_df["param_distance"].idxmin(), "layer_idx"])
    ax2.axvline(x=best_layer_idx, color='green', linestyle='--', linewidth=2, alpha=0.7,
                label=f'Best Layer ({best_layer_idx})')

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Figure saved to {output_path}")

    return fig


def main():
    """Run layer selection analysis."""

    print("=" * 70)
    print("Wav2Vec2层选择分析实验")
    print("Layer Selection Analysis for TRR")
    print("=" * 70)

    # Theoretical analysis
    print("\n" + "=" * 70)
    print("THEORETICAL ANALYSIS: Layer Characteristics")
    print("=" * 70)

    layer_analysis = analyze_layer_characteristics()

    df_theory = pd.DataFrame.from_dict(layer_analysis, orient='index')
    df_theory.index.name = 'Layer'

    print("\nLayer Characteristics:")
    print(df_theory[['name', 'type', 'characteristics', 'suitability_for_texture']].to_string(index=False))

    # Experimental validation
    print("\n" + "=" * 70)
    print("EXPERIMENTAL VALIDATION")
    print("=" * 70)

    dataset = load_and_merge_data()
    print(f"Loaded {len(dataset)} samples from dataset loader.")

    split_selector = os.getenv("LAYER_SEL_TESTSET", "30")
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

    analyzer = TRR_LayerAnalyzer()
    param_keys, param_stats = _compute_norm_stats(dataset)

    layers_to_test = list(range(1, 13))  # Layers 1-12

    print("\nPrecomputing embeddings for all layers (single forward pass per audio)...")
    layer_to_emb_by_idx: Dict[int, Dict[int, np.ndarray]] = {layer: {} for layer in layers_to_test}
    for idx in tqdm(range(len(dataset)), desc="Embedding audio"):
        audio_path = dataset[idx].get("AudioPath")
        if not audio_path or not os.path.exists(audio_path):
            continue
        emb_map = analyzer.get_embeddings_for_layers(audio_path, layers_to_test)
        for layer_idx, emb in emb_map.items():
            layer_to_emb_by_idx[layer_idx][idx] = emb

    results: List[Dict[str, float]] = []
    for layer_idx in layers_to_test:
        cand_ids = [i for i in candidate_indices if i in layer_to_emb_by_idx[layer_idx]]
        if not cand_ids:
            continue
        cand_embs = np.stack([layer_to_emb_by_idx[layer_idx][i] for i in cand_ids], axis=0)

        distances: List[float] = []
        cos_sims: List[float] = []
        for q_idx in test_indices:
            q_emb = layer_to_emb_by_idx[layer_idx].get(q_idx)
            if q_emb is None:
                continue
            sims = cand_embs @ q_emb
            top_pos = int(np.argmax(sims))
            retrieved_idx = cand_ids[top_pos]
            distances.append(
                _l2_distance_normalized(
                    dataset[retrieved_idx]["Parameters"],
                    dataset[q_idx]["Parameters"],
                    param_keys,
                    param_stats,
                )
            )
            cos_sims.append(float(sims[top_pos]))

        results.append(
            {
                "layer_idx": layer_idx,
                "param_distance": float(np.mean(distances)) if distances else 0.0,
                "cosine": float(np.mean(cos_sims)) if cos_sims else 0.0,
                "n_samples": int(len(distances)),
            }
        )

    results_df = pd.DataFrame(results).sort_values("layer_idx")

    # Display results
    print("\n" + "=" * 70)
    print("EXPERIMENTAL RESULTS")
    print("=" * 70)

    print("\nPerformance by Layer:")
    print(results_df.to_string(index=False))

    # Find best layer
    best_layer = results_df.loc[results_df['param_distance'].idxmin()]
    print(f"\n{'='*70}")
    print(f"BEST LAYER: {best_layer['layer_idx']}")
    print(f"  - Param Distance: {best_layer['param_distance']:.4f}")
    print(f"  - Cosine Similarity: {best_layer['cosine']:.4f}")
    print(f"{'='*70}")

    # Plot results
    print("\nGenerating visualization...")
    plot_layer_selection_results(results_df, "Paper/figures/trr_layer_selection.pdf")

    # Save results
    results_df.to_csv("Experiments/TextureResonance/layer_selection_results.csv", index=False)
    print("Results saved to Experiments/TextureResonance/layer_selection_results.csv")

    # Summary and recommendations
    print("\n" + "=" * 70)
    print("SUMMARY AND RECOMMENDATIONS")
    print("=" * 70)

    best_layer_idx_int = int(best_layer["layer_idx"])
    print(
        f"""
基于本次实验结果，我们发现：

1. **Best Layer: {best_layer_idx_int}**
   - Param Distance: {best_layer['param_distance']:.4f}
   - Cosine Similarity: {best_layer['cosine']:.4f}

2. **解释与建议（定性）**
   - 浅层通常更偏局部声学细节，深层更偏语义抽象；中间层往往能在两者之间取得更好的纹理表征平衡。
   - 建议在更大规模数据上复现实验，并固定随机投影与评估划分以提高可重复性。
"""
    )


if __name__ == "__main__":
    main()
