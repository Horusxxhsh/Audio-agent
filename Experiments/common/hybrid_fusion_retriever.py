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
        """构建文本表示：Protocol-C 使用 Style + Feature，不使用 SongName。"""
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
            score_norm: 分数归一化方式（none/zscore/minmax）
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

        def normalize(scores: np.ndarray, mode: str) -> np.ndarray:
            if mode == "none":
                return scores
            if mode == "zscore":
                sigma = float(np.std(scores))
                if sigma < 1e-12:
                    return np.zeros_like(scores)
                return (scores - float(np.mean(scores))) / sigma
            if mode == "minmax":
                lo = float(np.min(scores))
                hi = float(np.max(scores))
                if hi - lo < 1e-12:
                    return np.zeros_like(scores)
                return (scores - lo) / (hi - lo)
            raise ValueError(f"Unknown score_norm: {score_norm}")

        def top_margin(scores: np.ndarray) -> float:
            if len(scores) < 2:
                return 0.0
            top2 = np.sort(scores)[-2:]
            return float(top2[-1] - top2[-2])

        text_scores_scaled = normalize(text_scores, score_norm) * float(text_scale)
        audio_scores_scaled = normalize(audio_scores, score_norm) * float(audio_scale)

        if adaptive_alpha_mode == "confidence":
            margin_delta = top_margin(text_scores_scaled) - top_margin(audio_scores_scaled)
            conf = 1.0 / (1.0 + np.exp(-float(confidence_temperature) * margin_delta))
            alpha = float(alpha_min) + (float(alpha_max) - float(alpha_min)) * float(conf)

        # 4. 加权融合
        # 现在两个分数的量纲相似，可以直接加权
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
                'type': 'hybrid_fusion',
                'alpha': alpha
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
                score_norm,
                text_scale,
                audio_scale,
                adaptive_alpha_mode,
                alpha_min,
                alpha_max,
                confidence_temperature,
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
