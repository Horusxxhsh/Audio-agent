"""
智能融合检索器
=============

基于实验发现的最佳实践：
1. 文本检索 (TF-IDF) 表现最好 (8.92)
2. 原始 TRR (Gram Matrix) 在音频方法中表现最好 (17.30)
3. 两者的智能融合可能带来最大改进

融合策略：
- 动态权重调整（基于音频质量）
- 分数归一化
- 多种融合模式（加权、投票、级联）
"""

import os
import numpy as np
from typing import List, Dict, Any, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity as sklearn_cosine

# Import components
try:
    from Experiments.TextureResonance.texture_encoder import TextureEncoder
    from Experiments.TextureResonance.texture_encoder import similarity_score
except ImportError:
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
    from Experiments.TextureResonance.texture_encoder import TextureEncoder, similarity_score


class HybridFusionRetriever:
    """
    智能融合检索器：文本 (TF-IDF) + 音频 (TRR Gram Matrix)

    融合模式：
    1. 'weighted': 加权融合分数 = α * text_score + (1-α) * audio_score
    2. 'voting': 投票融合（各自 top-k，然后合并重排序）
    3. 'cascade': 级联融合（先用文本筛选，再用音频精排）
    """

    def __init__(self, dataset: List[Dict[str, Any]], fusion_mode: str = 'weighted'):
        """
        Args:
            dataset: 知识库数据集
            fusion_mode: 融合模式 ('weighted', 'voting', 'cascade')
        """
        self.dataset = dataset
        self.fusion_mode = fusion_mode

        print(f"Initializing HybridFusionRetriever with mode: {fusion_mode}")

        # 初始化文本检索器
        self._init_text_retriever()

        # 初始化音频检索器 (TRR)
        self._init_audio_retriever()

    def _init_text_retriever(self):
        """初始化 TF-IDF 文本检索器"""
        self.corpus = []
        for item in self.dataset:
            text = self._build_text(item)
            self.corpus.append(text)

        self.vectorizer = TfidfVectorizer(stop_words='english')
        self.tfidf_matrix = self.vectorizer.fit_transform(self.corpus)
        print(f"  >> Text Retriever Ready ({len(self.dataset)} items)")

    def _build_text(self, item):
        """构建文本表示：仅使用 Style + Feature，不使用 SongName。"""
        style = " ".join(item.get('Style', []))
        feature = " ".join(item.get('Feature', []))
        return f"{style} {feature}".strip()

    def _init_audio_retriever(self):
        """初始化 TRR 音频检索器"""
        # 使用与原始 TRR 相同的 project_dim=64，以便复用缓存
        self.encoder = TextureEncoder(project_dim=64)
        self.embeddings = []
        self.valid_indices = []

        # 预计算嵌入
        for i, item in enumerate(self.dataset):
            audio_path = item.get('AudioPath')
            embedding = None

            # 1. 优先使用JSON中的缓存向量（与TRRRetriever一致）
            if 'Vectors' in item and item['Vectors'].get('TRR'):
                try:
                    embedding = np.array(item['Vectors']['TRR'])
                except:
                    pass

            # 2. 尝试从文件缓存加载
            if embedding is None and audio_path and os.path.exists(audio_path):
                cache_path = audio_path + ".trr.npy"
                if os.path.exists(cache_path):
                    try:
                        embedding = np.load(cache_path)
                    except:
                        embedding = None

                # 3. 从音频文件计算
                if embedding is None:
                    try:
                        embedding = self.encoder.get_embedding(audio_path)
                        if embedding is not None:
                            np.save(cache_path, embedding)
                    except Exception as e:
                        pass

            if embedding is not None:
                self.embeddings.append(embedding)
                self.valid_indices.append(i)
            else:
                # 对于没有音频的样本，使用零向量（稍后在融合时会处理）
                # 注意：这里使用 4096 维 (64*64)
                self.embeddings.append(np.zeros(4096))
                self.valid_indices.append(i)

        if self.embeddings:
            self.embeddings = np.array(self.embeddings)
            actual_dim = self.embeddings.shape[1]
            print(f"  >> Audio Retriever (TRR) Ready (dim={actual_dim})")

    def _compute_audio_quality(self, audio_path: Optional[str]) -> float:
        """
        计算音频质量分数（用于动态调整融合权重）

        质量指标：
        - 音频文件是否存在
        - 音频时长（过短质量低）
        - 音频方差（过低可能是静音）
        """
        if not audio_path or not os.path.exists(audio_path):
            return 0.0

        try:
            import soundfile as sf
            data, sr = sf.read(audio_path)

            # 检查时长（至少 0.5 秒）
            duration = len(data) / sr
            if duration < 0.5:
                return 0.3

            # 检查方差（过低可能是静音）
            variance = np.var(data)
            if variance < 0.001:
                return 0.2
            elif variance > 0.5:
                return 0.6  # 可能削波
            else:
                return 0.8  # 良好

        except:
            return 0.0

    def _normalize_scores(self, scores: np.ndarray, mode: str) -> np.ndarray:
        if mode == "none":
            return scores
        if scores.size == 0:
            return scores
        if mode == "zscore":
            mean = float(np.mean(scores))
            std = float(np.std(scores))
            if std <= 1e-12:
                return np.zeros_like(scores)
            return (scores - mean) / std
        if mode == "minmax":
            min_v = float(np.min(scores))
            max_v = float(np.max(scores))
            if max_v - min_v <= 1e-12:
                return np.zeros_like(scores)
            return (scores - min_v) / (max_v - min_v)
        raise ValueError(f"Unknown score normalization mode: {mode}")

    def _top2_margin(self, scores: np.ndarray) -> float:
        if scores.size == 0:
            return 0.0
        ranked = np.sort(scores)[::-1]
        if ranked.size == 1:
            return float(ranked[0])
        return float(ranked[0] - ranked[1])

    def _sigmoid_confidence(self, margin: float, temperature: float) -> float:
        if margin <= 0:
            return 0.0
        x = float(np.clip(margin * temperature, -20.0, 20.0))
        return float(1.0 / (1.0 + np.exp(-x)))

    def _compute_confidence_alpha(
        self,
        text_scores_scaled: np.ndarray,
        audio_scores_scaled: np.ndarray,
        alpha_min: float,
        alpha_max: float,
        confidence_temperature: float,
    ) -> Dict[str, float]:
        text_margin = self._top2_margin(text_scores_scaled)
        audio_margin = self._top2_margin(audio_scores_scaled)
        text_peak = float(np.max(text_scores_scaled)) if text_scores_scaled.size else 0.0
        audio_peak = float(np.max(audio_scores_scaled)) if audio_scores_scaled.size else 0.0

        # Confidence combines local rank sharpness (top1-top2 margin) and
        # absolute peak strength. This suppresses branches that have a winner
        # only by a tiny margin but whose overall scores are still weak.
        peak_temperature = max(1.0, float(confidence_temperature) * 0.35)
        text_conf = 0.0 if np.allclose(text_scores_scaled, text_scores_scaled[:1]) else (
            self._sigmoid_confidence(text_margin, confidence_temperature) *
            self._sigmoid_confidence(max(0.0, text_peak), peak_temperature)
        )
        audio_conf = 0.0 if np.allclose(audio_scores_scaled, audio_scores_scaled[:1]) else (
            self._sigmoid_confidence(audio_margin, confidence_temperature) *
            self._sigmoid_confidence(max(0.0, audio_peak), peak_temperature)
        )

        denom = text_conf + audio_conf
        if denom <= 1e-12:
            alpha = 0.5 * (alpha_min + alpha_max)
        else:
            alpha = text_conf / denom
            peak_gap = max(0.0, text_peak - audio_peak)
            weak_audio = max(0.0, text_conf - audio_conf)
            low_audio_peak = max(0.0, 1.5 - audio_peak)
            low_audio_margin = max(0.0, 0.35 - audio_margin)
            gap_bias = 0.22 * self._sigmoid_confidence(peak_gap, peak_temperature)
            weak_audio_bias = 0.20 * self._sigmoid_confidence(weak_audio, confidence_temperature)
            low_peak_bias = 0.18 * self._sigmoid_confidence(low_audio_peak, peak_temperature)
            low_margin_bias = 0.16 * self._sigmoid_confidence(low_audio_margin, confidence_temperature)
            alpha = float(np.clip(alpha + gap_bias + weak_audio_bias + low_peak_bias + low_margin_bias, alpha_min, alpha_max))

        return {
            "alpha": float(alpha),
            "text_margin": float(text_margin),
            "audio_margin": float(audio_margin),
            "text_peak": float(text_peak),
            "audio_peak": float(audio_peak),
            "peak_gap_bias": float(gap_bias if denom > 1e-12 else 0.0),
            "weak_audio_bias": float(weak_audio_bias if denom > 1e-12 else 0.0),
            "low_audio_peak_bias": float(low_peak_bias if denom > 1e-12 else 0.0),
            "low_audio_margin_bias": float(low_margin_bias if denom > 1e-12 else 0.0),
            "text_confidence": float(text_conf),
            "audio_confidence": float(audio_conf),
        }

    def retrieve_top_k_weighted(self, query_text: str, query_audio_path: Optional[str] = None,
                               query_trr_vector: Optional[List[float]] = None,
                               alpha: float = 0.5, k: int = 5,
                               score_norm: str = "none",
                               text_scale: float = 1.0,
                               audio_scale: float = 1.0,
                               adaptive_alpha_mode: str = "none",
                               alpha_min: float = 0.3,
                               alpha_max: float = 0.8,
                               confidence_temperature: float = 8.0) -> List[Dict]:
        """
        加权融合模式

        融合公式：
        final_score = α * text_score + (1-α) * audio_score

        Args:
            query_text: 查询文本
            query_audio_path: 查询音频路径（可选）
            query_trr_vector: 查询TRR向量（可选，直接使用JSON中的向量）
            alpha: 融合权重
            k: 返回结果数量
            score_norm: 分数归一化方式 ('none', 'zscore', 'minmax')
            text_scale: 文本分数缩放系数
            audio_scale: 音频分数缩放系数
        """
        # 1. 文本检索分数
        query_vec = self.vectorizer.transform([query_text])
        text_scores = sklearn_cosine(query_vec, self.tfidf_matrix).flatten()

        # 2. 音频检索分数（使用余弦相似度，与TRRRetriever一致）
        # 优先使用直接传入的TRR向量，其次使用音频路径计算
        if query_trr_vector is not None:
            # 直接使用传入的TRR向量
            query_emb = np.array(query_trr_vector)
            # 标准化query和embeddings（余弦相似度）
            query_norm = np.linalg.norm(query_emb)
            if query_norm > 0:
                query_emb_normalized = query_emb / query_norm
            else:
                query_emb_normalized = query_emb

            emb_norms = np.linalg.norm(self.embeddings, axis=1, keepdims=True)
            emb_norms[emb_norms == 0] = 1  # 避免除零
            embeddings_normalized = self.embeddings / emb_norms

            audio_scores = np.dot(embeddings_normalized, query_emb_normalized)
        elif query_audio_path and os.path.exists(query_audio_path):
            # 从音频路径计算TRR向量
            query_emb = self.encoder.get_embedding(query_audio_path)
            if query_emb is not None:
                # 标准化query和embeddings（余弦相似度）
                query_norm = np.linalg.norm(query_emb)
                if query_norm > 0:
                    query_emb_normalized = query_emb / query_norm
                else:
                    query_emb_normalized = query_emb

                emb_norms = np.linalg.norm(self.embeddings, axis=1, keepdims=True)
                emb_norms[emb_norms == 0] = 1  # 避免除零
                embeddings_normalized = self.embeddings / emb_norms

                audio_scores = np.dot(embeddings_normalized, query_emb_normalized)
            else:
                audio_scores = np.zeros(len(self.dataset))
        else:
            audio_scores = np.zeros(len(self.dataset))

        # 3. 分数校准
        # 默认保留原始行为；需要时可通过 score_norm / text_scale / audio_scale
        # 将文本与音频分数调整到更可比较的量级。
        text_scores_scaled = self._normalize_scores(text_scores, score_norm) * float(text_scale)
        audio_scores_scaled = self._normalize_scores(audio_scores, score_norm) * float(audio_scale)

        # 4. 加权融合
        # 现在两个分数的量纲相似，可以直接加权
        alpha_info = {
            "alpha": float(alpha),
            "text_margin": 0.0,
            "audio_margin": 0.0,
            "text_peak": 0.0,
            "audio_peak": 0.0,
            "peak_gap_bias": 0.0,
            "weak_audio_bias": 0.0,
            "low_audio_peak_bias": 0.0,
            "low_audio_margin_bias": 0.0,
            "text_confidence": 0.0,
            "audio_confidence": 0.0,
            "alpha_source": "fixed",
        }
        if adaptive_alpha_mode == "confidence":
            auto = self._compute_confidence_alpha(
                text_scores_scaled=text_scores_scaled,
                audio_scores_scaled=audio_scores_scaled,
                alpha_min=float(alpha_min),
                alpha_max=float(alpha_max),
                confidence_temperature=float(confidence_temperature),
            )
            alpha = auto["alpha"]
            alpha_info.update(auto)
            alpha_info["alpha_source"] = "confidence"

        final_scores = alpha * text_scores_scaled + (1 - alpha) * audio_scores_scaled

        # 调试输出：显示Top-5样本的分数详情（已关闭）
        if False:  # 调试开关
            top_5_indices = np.argsort(final_scores)[::-1][:5]
            print(f"    [DEBUG] Top-5样本 (α={alpha}):")
            for rank, idx in enumerate(top_5_indices):
                name = self.dataset[idx]['SongName']
                text_s = float(text_scores_scaled[idx])
                audio_s = float(audio_scores_scaled[idx])
                final_s = float(final_scores[idx])
                print(f"      {rank+1}. {name}: text={text_s:.4f}, audio={audio_s:.4f}, final={final_s:.4f}")

        # 6. 排序
        top_indices = np.argsort(final_scores)[::-1][:k]

        results = []
        for idx in top_indices:
            results.append({
                'params': self.dataset[idx]['Parameters'],
                'score': float(final_scores[idx]),
                'song_name': self.dataset[idx]['SongName'],
                'text_score': float(text_scores[idx]),
                'audio_score': float(audio_scores[idx]) if idx < len(audio_scores) else 0.0,
                'text_score_scaled': float(text_scores_scaled[idx]),
                'audio_score_scaled': float(audio_scores_scaled[idx]) if idx < len(audio_scores_scaled) else 0.0,
                'type': 'hybrid_fusion',
                'alpha': float(alpha),
                'alpha_source': alpha_info['alpha_source'],
                'text_margin': float(alpha_info['text_margin']),
                'audio_margin': float(alpha_info['audio_margin']),
                'text_peak': float(alpha_info['text_peak']),
                'audio_peak': float(alpha_info['audio_peak']),
                'peak_gap_bias': float(alpha_info['peak_gap_bias']),
                'weak_audio_bias': float(alpha_info['weak_audio_bias']),
                'low_audio_peak_bias': float(alpha_info['low_audio_peak_bias']),
                'low_audio_margin_bias': float(alpha_info['low_audio_margin_bias']),
                'text_confidence': float(alpha_info['text_confidence']),
                'audio_confidence': float(alpha_info['audio_confidence']),
                'score_norm': score_norm,
                'text_scale': float(text_scale),
                'audio_scale': float(audio_scale),
            })

        return results

    def retrieve_top_k_voting(self, query_text: str, query_audio_path: Optional[str],
                            k: int = 5) -> List[Dict]:
        """
        投票融合模式

        策略：
        1. 文本和音频各自检索 top-2k
        2. 合并去重
        3. 根据在两个列表中的排名重新排序
        """
        k_expanded = k * 2

        # 1. 文本检索 top-2k
        query_vec = self.vectorizer.transform([query_text])
        text_scores = sklearn_cosine(query_vec, self.tfidf_matrix).flatten()
        text_top_indices = np.argsort(text_scores)[::-1][:k_expanded]

        # 2. 音频检索 top-2k
        if query_audio_path and os.path.exists(query_audio_path):
            query_emb = self.encoder.get_embedding(query_audio_path)
            if query_emb is not None:
                audio_scores = np.dot(self.embeddings, query_emb)
                audio_top_indices = np.argsort(audio_scores)[::-1][:k_expanded]
            else:
                audio_top_indices = np.array([])
        else:
            audio_top_indices = np.array([])

        # 3. 合并和投票
        vote_scores = {}
        for rank, idx in enumerate(text_top_indices):
            vote_scores[idx] = vote_scores.get(idx, 0) + (k_expanded - rank)

        for rank, idx in enumerate(audio_top_indices):
            vote_scores[idx] = vote_scores.get(idx, 0) + (k_expanded - rank)

        # 4. 排序
        sorted_indices = sorted(vote_scores.keys(), key=lambda x: vote_scores[x], reverse=True)[:k]

        results = []
        for idx in sorted_indices:
            results.append({
                'params': self.dataset[idx]['Parameters'],
                'score': float(vote_scores[idx]),
                'song_name': self.dataset[idx]['SongName'],
                'type': 'hybrid_voting'
            })

        return results

    def retrieve_top_k_cascade(self, query_text: str, query_audio_path: Optional[str],
                             k: int = 5) -> List[Dict]:
        """
        级联融合模式

        策略：
        1. 文本检索筛选 top-3k
        2. 在候选集内用音频检索精排
        """
        k_expanded = k * 3

        # 1. 文本检索筛选
        query_vec = self.vectorizer.transform([query_text])
        text_scores = sklearn_cosine(query_vec, self.tfidf_matrix).flatten()
        candidate_indices = np.argsort(text_scores)[::-1][:k_expanded]

        # 2. 音频检索精排
        if query_audio_path and os.path.exists(query_audio_path):
            query_emb = self.encoder.get_embedding(query_audio_path)
            if query_emb is not None:
                # 只在候选集中计算音频分数
                candidate_embeddings = self.embeddings[candidate_indices]
                audio_scores = np.dot(candidate_embeddings, query_emb)

                # 根据音频分数排序
                reranked_indices = candidate_indices[np.argsort(audio_scores)[::-1][:k]]
            else:
                # 音频检索失败，返回文本检索结果
                reranked_indices = candidate_indices[:k]
        else:
            # 没有音频，返回文本检索结果
            reranked_indices = candidate_indices[:k]

        results = []
        for idx in reranked_indices:
            results.append({
                'params': self.dataset[idx]['Parameters'],
                'score': float(text_scores[idx]),
                'song_name': self.dataset[idx]['SongName'],
                'type': 'hybrid_cascade'
            })

        return results

    def retrieve_top_k(self, query_text: str, query_audio_path: Optional[str] = None,
                     query_trr_vector: Optional[List[float]] = None,
                     alpha: float = 0.5, k: int = 5,
                     score_norm: str = "none",
                     text_scale: float = 1.0,
                     audio_scale: float = 1.0,
                     adaptive_alpha_mode: str = "none",
                     alpha_min: float = 0.3,
                     alpha_max: float = 0.8,
                     confidence_temperature: float = 8.0) -> List[Dict]:
        """
        检索最相关的 k 个项目（统一接口）

        Args:
            query_text: 查询文本
            query_audio_path: 查询音频路径
            query_trr_vector: 查询TRR向量（直接使用JSON中的向量）
            alpha: 融合权重（仅用于 weighted 模式）
            k: 返回结果数量
        """
        if self.fusion_mode == 'weighted':
            return self.retrieve_top_k_weighted(
                query_text,
                query_audio_path,
                query_trr_vector,
                alpha,
                k,
                score_norm=score_norm,
                text_scale=text_scale,
                audio_scale=audio_scale,
                adaptive_alpha_mode=adaptive_alpha_mode,
                alpha_min=alpha_min,
                alpha_max=alpha_max,
                confidence_temperature=confidence_temperature,
            )
        elif self.fusion_mode == 'voting':
            return self.retrieve_top_k_voting(query_text, query_audio_path, k)
        elif self.fusion_mode == 'cascade':
            return self.retrieve_top_k_cascade(query_text, query_audio_path, k)
        else:
            raise ValueError(f"Unknown fusion mode: {self.fusion_mode}")


# 便捷函数
def create_weighted_fusion_retriever(dataset):
    """创建加权融合检索器"""
    return HybridFusionRetriever(dataset, fusion_mode='weighted')


def create_voting_fusion_retriever(dataset):
    """创建投票融合检索器"""
    return HybridFusionRetriever(dataset, fusion_mode='voting')


def create_cascade_fusion_retriever(dataset):
    """创建级联融合检索器"""
    return HybridFusionRetriever(dataset, fusion_mode='cascade')
