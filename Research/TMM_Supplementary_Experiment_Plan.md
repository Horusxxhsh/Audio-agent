# IEEE TMM Revision: 补充实验方案详细设计

## 文档信息
- **目标期刊**: IEEE Transactions on Multimedia (TMM)
- **稿件ID**: #8159
- **修订类型**: Major Revision 补充实验
- **总预算**: 10-15天

---

## 实验总览

| 实验编号 | 实验名称 | 目的 | 预算 | 对应审稿人关切 |
|---------|---------|------|------|---------------|
| E1 | AEM 学习曲线 | 证明记忆机制随交互改善性能 | 2-3天 | Agent claim |
| E2 | CLAP/PaSST/PANNs 基线对比 | 回应 C1 新颖性质疑 | 3-4天 | C1: 新颖性 |
| E3 | 真实噪声 Protocol-C | 用真实音频退化替代 embedding 加噪 | 2-3天 | C4: 真实场景 |
| E4 | 指标与感知相关性 | 建立参数指标与听测评分的相关性 | 1-2天 | C3: 感知相关性 |
| E5 | Retrieval-only vs Retrieval+Projection | 证明检索是核心，projection 有边际增益 | 1-2天 | Agent claim |
| E6 | 端到端延迟分析 | 提供真实的部署时延预算 | 1天 | C6: 延迟 |

---

## 实验1: AEM (Adaptive Executable Memory) 学习曲线

### 1.1 实验名称与目的

**名称**: Adaptive Executable Memory (AEM) Learning Curve Analysis

**目的**:
- 证明记忆机制随用户交互次数增加而改善检索性能
- 支撑论文中关于 "Adaptive" 和 "Personalization" 的核心 claim
- 提供定量证据表明系统能够从用户反馈中学习并收敛到用户偏好

**对应审稿关切**: 支撑 Agent claim（自适应能力）

### 1.2 详细协议

#### 输入
- **知识库**: 1,267 个参数预设（与 Protocol-A 一致）
- **测试查询**: N=50 个 held-out queries（从 211 中分层采样）
- **记忆大小条件**: [0, 5, 10, 20, 50] 条记忆
- **交互轮次**: 每条件 10 轮迭代

#### 实验步骤

**Step 1: 初始化**
```python
def initialize_experiment():
    """初始化实验环境"""
    rag = AudioRAGSystem(api_key=..., base_url=...)
    initialize_knowledge_base(rag)  # 加载 1267 个预设
    simulator = UserSimulator(rag)

    # 清空记忆
    rag.chroma_client.delete_collection("user_preference_memory")
    rag.memory_collection = rag._get_or_create_collection("user_preference_memory")

    return rag, simulator
```

**Step 2: 模拟用户反馈累积**
```python
def simulate_interaction_turn(
    rag: AudioRAGSystem,
    simulator: UserSimulator,
    query: str,
    target_params: Dict[str, Any],
    audio_vector: List[float],
    learning_rate: float = 0.6
) -> Dict[str, Any]:
    """
    模拟单轮交互

    Returns:
        {
            "retrieved_params": 检索到的参数,
            "l2_error_before": 用户微调前的 L2 误差,
            "l2_error_after": 用户微调后的 L2 误差,
            "source_modality": 检索来源 (kb/memory)
        }
    """
    # 1. 检索推荐
    recommendations = rag.recommend_parameters(
        style_tags=extract_style_tags(query),
        user_description=query,
        n_recommendations=1,
        audio_query_vector=audio_vector
    )

    if not recommendations:
        return None

    retrieved_params = recommendations[0]['parameters']
    source = recommendations[0].get('source_modality', 'kb')

    # 2. 计算当前误差
    l2_error_before = simulator.calculate_l2_error(retrieved_params, target_params)

    # 3. 模拟用户微调
    tweaked_params = simulator.simulate_tweak(
        retrieved_params, target_params, learning_rate
    )

    # 4. 保存到记忆
    rag.save_to_memory(
        query=query,
        parameters=tweaked_params,
        audio_vector=audio_vector,
        metadata={"turn": turn_number, "query_id": query_id}
    )

    # 5. 计算微调后误差
    l2_error_after = simulator.calculate_l2_error(tweaked_params, target_params)

    return {
        "retrieved_params": retrieved_params,
        "tweaked_params": tweaked_params,
        "l2_error_before": l2_error_before,
        "l2_error_after": l2_error_after,
        "source_modality": source
    }
```

**Step 3: 不同记忆大小的对比实验**
```python
def run_memory_size_experiment(
    memory_sizes: List[int] = [0, 5, 10, 20, 50],
    n_queries: int = 50,
    n_turns_per_query: int = 10
) -> Dict[int, List[Dict]]:
    """
    运行不同记忆大小的对比实验

    对于每个 memory_size:
    - 重置记忆库
    - 为每个 query 运行 n_turns 轮交互
    - 记录每轮的 L2 误差
    """
    results = {}

    for mem_size in memory_sizes:
        print(f"\n{'='*60}")
        print(f"Testing with max_memory_size = {mem_size}")
        print(f"{'='*60}")

        rag, simulator = initialize_experiment()

        # 限制记忆库大小（模拟有限记忆）
        if mem_size > 0:
            rag.memory_limit = mem_size  # 需要添加到 AudioRAGSystem

        size_results = []

        for query_idx, test_query in enumerate(test_queries[:n_queries]):
            query_results = []

            for turn in range(1, n_turns_per_query + 1):
                result = simulate_interaction_turn(
                    rag, simulator,
                    test_query['query'],
                    test_query['target_params'],
                    test_query['audio_vector']
                )

                if result:
                    result['turn'] = turn
                    result['query_id'] = query_idx
                    result['memory_size'] = mem_size
                    query_results.append(result)

            size_results.extend(query_results)

        results[mem_size] = size_results

    return results
```

**Step 4: 统计显著性检验**
```python
def compute_statistical_significance(
    results: Dict[int, List[Dict]]
) -> pd.DataFrame:
    """
    计算不同记忆大小 vs 无记忆基线的统计显著性

    使用配对 t 检验（paired t-test）:
    - H0: 记忆大小 X 的 L2 误差均值 = 无记忆基线的 L2 误差均值
    - H1: 记忆大小 X 的 L2 误差均值 < 无记忆基线

    多重比较校正: Holm-Bonferroni
    """
    baseline_errors = [r['l2_error_before'] for r in results[0]]

    significance_results = []

    for mem_size in [5, 10, 20, 50]:
        test_errors = [r['l2_error_before'] for r in results[mem_size]]

        # 配对 t 检验
        t_stat, p_value = scipy.stats.ttest_rel(baseline_errors, test_errors)

        # 效应量 (Cohen's d)
        cohens_d = compute_cohens_d(baseline_errors, test_errors)

        significance_results.append({
            "memory_size": mem_size,
            "mean_l2_baseline": np.mean(baseline_errors),
            "mean_l2_with_memory": np.mean(test_errors),
            "improvement_pct": (1 - np.mean(test_errors) / np.mean(baseline_errors)) * 100,
            "t_statistic": t_stat,
            "p_value_raw": p_value,
            "cohens_d": cohens_d
        })

    # Holm-Bonferroni 校正
    p_values = [r['p_value_raw'] for r in significance_results]
    reject, p_corrected, _, _ = multipletests(p_values, method='holm')

    for i, r in enumerate(significance_results):
        r['p_value_holm'] = p_corrected[i]
        r['significant'] = reject[i]

    return pd.DataFrame(significance_results)
```

#### 输出
- **逐 query CSV**: `aem_learning_curve_per_query.csv`
  - 字段: `query_id`, `memory_size`, `turn`, `l2_error_before`, `l2_error_after`, `source_modality`
- **统计报告**: `aem_significance_report.csv`
  - 字段: `memory_size`, `mean_l2`, `improvement_pct`, `p_value_holm`, `cohens_d`
- **可视化**: `aem_learning_curve.png` (L2 误差随记忆大小和轮次变化)

### 1.3 预期结果

**假设**:
1. 无记忆基线 (0条): L2 误差保持恒定（约 0.35-0.40）
2. 随着记忆大小增加，L2 误差单调递减
3. 50条记忆条件下，L2 误差相比基线降低 20-30%
4. 所有非零记忆条件 vs 基线均达到统计显著性 (p < 0.05, Holm校正后)

**图表类型**:
- 主图: 折线图，X轴=记忆大小，Y轴=平均L2误差，误差条=95% CI
- 副图: 学习曲线，X轴=交互轮次，Y轴=L2误差，不同颜色=不同记忆大小

### 1.4 资源需求

**计算资源**:
- GPU: 不需要（仅检索，无模型推理）
- CPU: 8核以上
- 内存: 16GB+
- 存储: 5GB（用于缓存和结果）

**时间预算**:
- 实现: 1天
- 运行: 0.5天（50 queries × 5 conditions × 10 turns = 2,500 次检索）
- 分析: 0.5天
- **总计: 2天**

**数据需求**:
- 现有 1,267 个知识库预设
- 50 个测试查询（从 211 held-out 中分层采样）

### 1.5 代码框架

```python
# File: Experiments/AEM/memory_learning_curve.py

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from typing import Dict, List, Any
from dataclasses import dataclass
from scipy import stats
from statsmodels.stats.multitest import multipletests

from rag_system import AudioRAGSystem, initialize_knowledge_base
from simulate_user_feedback import UserSimulator


@dataclass
class AEMConfig:
    """AEM 实验配置"""
    memory_sizes: List[int] = None
    n_queries: int = 50
    n_turns: int = 10
    learning_rate: float = 0.6
    similarity_threshold: float = 0.90
    output_dir: str = "Experiments/AEM/results"

    def __post_init__(self):
        if self.memory_sizes is None:
            self.memory_sizes = [0, 5, 10, 20, 50]


class AEMExperiment:
    """AEM 学习曲线实验主类"""

    def __init__(self, config: AEMConfig):
        self.config = config
        self.rag = None
        self.simulator = None

    def setup(self):
        """初始化 RAG 系统和模拟器"""
        self.rag = AudioRAGSystem(
            api_key=os.environ.get("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com"
        )
        initialize_knowledge_base(self.rag)
        self.simulator = UserSimulator(self.rag)

    def reset_memory(self):
        """重置记忆库"""
        try:
            self.rag.chroma_client.delete_collection("user_preference_memory")
        except:
            pass
        self.rag.memory_collection = self.rag._get_or_create_collection(
            "user_preference_memory"
        )

    def run_single_query_session(
        self,
        query: str,
        target_params: Dict[str, Any],
        audio_vector: np.ndarray,
        max_memory: int
    ) -> List[Dict]:
        """运行单个查询的多轮交互会话"""
        results = []

        for turn in range(1, self.config.n_turns + 1):
            # 检索
            recs = self.rag.recommend_parameters(
                style_tags=[],
                user_description=query,
                n_recommendations=1,
                audio_query_vector=audio_vector.tolist()
            )

            if not recs:
                continue

            retrieved = recs[0]
            l2_before = self.simulator.calculate_l2_error(
                retrieved['parameters'], target_params
            )

            # 模拟用户微调
            tweaked = self.simulator.simulate_tweak(
                retrieved['parameters'], target_params,
                self.config.learning_rate
            )

            # 保存到记忆
            self.rag.save_to_memory(query, tweaked, audio_vector.tolist())

            # 如果超过记忆限制，删除最旧的
            # (需要实现记忆限制逻辑)

            results.append({
                'turn': turn,
                'l2_error': l2_before,
                'source': retrieved.get('source_modality', 'kb')
            })

        return results

    def run_experiment(self) -> Dict[int, pd.DataFrame]:
        """运行完整实验"""
        all_results = {}

        # 加载测试查询
        test_queries = self._load_test_queries(self.config.n_queries)

        for mem_size in self.config.memory_sizes:
            print(f"\n[Memory Size: {mem_size}]")
            self.setup()
            self.reset_memory()

            size_results = []

            for q_idx, query_data in enumerate(test_queries):
                session_results = self.run_single_query_session(
                    query_data['query'],
                    query_data['target_params'],
                    query_data['audio_vector'],
                    mem_size
                )

                for r in session_results:
                    r['query_id'] = q_idx
                    r['memory_size'] = mem_size

                size_results.extend(session_results)

            all_results[mem_size] = pd.DataFrame(size_results)

        return all_results

    def analyze(self, results: Dict[int, pd.DataFrame]) -> pd.DataFrame:
        """统计分析"""
        # 计算每记忆大小的平均 L2
        summary = []

        for mem_size, df in results.items():
            mean_l2 = df['l2_error'].mean()
            std_l2 = df['l2_error'].std()
            ci_low, ci_high = stats.t.interval(
                0.95, len(df)-1, loc=mean_l2, scale=stats.sem(df['l2_error'])
            )

            summary.append({
                'memory_size': mem_size,
                'mean_l2': mean_l2,
                'std_l2': std_l2,
                'ci_95_low': ci_low,
                'ci_95_high': ci_high,
                'n_samples': len(df)
            })

        summary_df = pd.DataFrame(summary)

        # 与基线比较
        baseline = results[0]['l2_error'].mean()
        summary_df['improvement_pct'] = (
            (baseline - summary_df['mean_l2']) / baseline * 100
        )

        # 统计检验
        baseline_errors = results[0]['l2_error'].values
        p_values = []

        for mem_size in self.config.memory_sizes[1:]:
            test_errors = results[mem_size]['l2_error'].values
            _, p = stats.ttest_rel(baseline_errors, test_errors)
            p_values.append(p)

        # Holm 校正
        reject, p_corrected, _, _ = multipletests(p_values, method='holm')
        summary_df['p_value_holm'] = [np.nan] + p_corrected.tolist()
        summary_df['significant'] = [False] + reject.tolist()

        return summary_df

    def plot(self, results: Dict[int, pd.DataFrame], summary: pd.DataFrame):
        """生成可视化"""
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))

        # 图1: 记忆大小 vs L2 误差
        ax1 = axes[0]
        ax1.errorbar(
            summary['memory_size'],
            summary['mean_l2'],
            yerr=[summary['mean_l2'] - summary['ci_95_low'],
                  summary['ci_95_high'] - summary['mean_l2']],
            marker='o', linewidth=2, capsize=5
        )
        ax1.set_xlabel('Memory Size (Number of Stored Preferences)')
        ax1.set_ylabel('Mean L2 Error')
        ax1.set_title('AEM Learning Curve: Retrieval Performance vs Memory Size')
        ax1.grid(True, alpha=0.3)

        # 图2: 学习曲线（按轮次）
        ax2 = axes[1]
        for mem_size in [0, 10, 50]:
            df = results[mem_size]
            turn_means = df.groupby('turn')['l2_error'].mean()
            ax2.plot(turn_means.index, turn_means.values,
                    marker='o', label=f'Memory={mem_size}')
        ax2.set_xlabel('Interaction Turn')
        ax2.set_ylabel('Mean L2 Error')
        ax2.set_title('Convergence Over Interaction Turns')
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(f"{self.config.output_dir}/aem_learning_curve.png", dpi=300)

    def _load_test_queries(self, n: int) -> List[Dict]:
        """加载测试查询"""
        # 从 held-out pool 中分层采样
        pass


def main():
    config = AEMConfig(
        memory_sizes=[0, 5, 10, 20, 50],
        n_queries=50,
        n_turns=10
    )

    exp = AEMExperiment(config)
    results = exp.run_experiment()
    summary = exp.analyze(results)
    exp.plot(results, summary)

    # 保存结果
    summary.to_csv(f"{config.output_dir}/aem_summary.csv", index=False)
    for mem_size, df in results.items():
        df.to_csv(f"{config.output_dir}/aem_memory_{mem_size}.csv", index=False)

    print("\n" + "="*60)
    print("AEM Experiment Complete")
    print("="*60)
    print(summary)


if __name__ == "__main__":
    main()
```

---

## 实验2: CLAP/PaSST/PANNs 基线对比

### 2.1 实验名称与目的

**名称**: SOTA Audio Embedding Baseline Comparison (CLAP, PaSST, PANNs)

**目的**:
- 回应审稿人 C1 关于方法新颖性的质疑
- 证明 TRR 在现代表征学习方法中的优势
- 在公平对比协议下与 SOTA 音频表征方法竞争

**对应审稿关切**: C1 (新颖性), R3 (强基线)

### 2.2 详细协议

#### 输入
- **知识库**: 1,267 个音频样本及其参数
- **测试集**: 211 held-out queries
- **对比方法**:
  - CLAP (Contrastive Language-Audio Pretraining) - LAION 版本
  - PaSST (Patchout faSt Spectrogram Transformer) - ImageNet 预训练
  - PANNs (Pretrained Audio Neural Networks) - CNN14 架构
  - TRR (Ours) - 作为对比基准
  - Wav2Vec-RAG - 现有基线
  - Text-RAG - 现有基线

#### 模型变体与 Pooling 策略

**CLAP 变体**:
- `CLAP-large` (630M 参数) - 主要对比
- Pooling 策略: mean pooling (默认)

**PaSST 变体**:
- `PaSST-S` (基于 DeiT-S)
- Pooling 策略:
  - Global mean pooling
  - Attention-based pooling (CLS token)

**PANNs 变体**:
- `PANNs-CNN14` (官方实现)
- Pooling 策略:
  - Global average pooling
  - Attention pooling

#### 公平对比协议

**统一设置**:
1. **输入音频**: 统一使用 16kHz, mono, 10s 片段
2. **检索方式**: Top-1 KNN (cosine similarity)
3. **评估指标**: 与 Protocol-A 完全一致 (L2, Acc@0.1, Recall, Cosine, Module)
4. **数据集划分**: 与 TRR 完全相同的 held-out 211 queries

**预计算缓存策略**:
```python
# 统一的缓存命名规范
cache_patterns = {
    "CLAP": "{audio_path}.clap.npy",
    "PaSST": "{audio_path}.passt.npy",
    "PANNs": "{audio_path}.panns.npy",
    "TRR": "{audio_path}.trr.npy",
    "Wav2Vec": "{audio_path}.w2v.npy"
}
```

#### 实验步骤

**Step 1: Embedding 预计算**
```python
def precompute_embeddings(
    audio_paths: List[str],
    method: str,
    batch_size: int = 32
) -> Dict[str, np.ndarray]:
    """
    预计算所有音频的 embedding

    Args:
        audio_paths: 音频文件路径列表
        method: 'CLAP' | 'PaSST' | 'PANNs'
        batch_size: 批处理大小

    Returns:
        路径到 embedding 的映射
    """
    if method == "CLAP":
        model = load_clap_model("laion/clap-htsat-unfused")
    elif method == "PaSST":
        model = load_passt_model("passt-s")
    elif method == "PANNs":
        model = load_panns_model("CNN14")

    embeddings = {}

    for batch in chunks(audio_paths, batch_size):
        # 加载音频
        waveforms = [load_audio(p, sr=16000, duration=10.0) for p in batch]

        # 提取 embedding
        batch_embeddings = model.encode(waveforms)

        # 保存缓存
        for path, emb in zip(batch, batch_embeddings):
            cache_path = get_cache_path(path, method)
            np.save(cache_path, emb)
            embeddings[path] = emb

    return embeddings
```

**Step 2: KNN 检索评估**
```python
def evaluate_retrieval_method(
    method: str,
    knowledge_base: List[Dict],
    test_queries: List[Dict],
    k: int = 1
) -> pd.DataFrame:
    """
    评估单一检索方法

    Returns:
        逐 query 结果 DataFrame
    """
    # 构建 KNN 索引
    retriever = EmbeddingKNNRetriever(
        name=method,
        dataset=knowledge_base,
        get_embedding=make_audio_cache_getter(f".{method.lower()}.npy"),
        normalize=True
    )

    results = []

    for query in test_queries:
        # 检索 Top-k
        neighbors = retriever.retrieve(query, k=k)

        if not neighbors:
            continue

        # 使用 Top-1 的参数作为预测
        predicted_params = neighbors[0]['Parameters']
        ground_truth = query['Parameters']

        # 计算指标
        metrics = compute_parameter_metrics(predicted_params, ground_truth)

        results.append({
            'query_id': query['SongName'],
            'method': method,
            'l2': metrics['l2'],
            'acc_at_0_1': metrics['acc@0.1'],
            'recall': metrics['recall'],
            'cosine': metrics['cosine'],
            'module': metrics['module']
        })

    return pd.DataFrame(results)
```

**Step 3: 统计比较**
```python
def compare_methods_statistically(
    results: Dict[str, pd.DataFrame]
) -> pd.DataFrame:
    """
    方法间的统计比较

    使用配对检验比较 TRR vs 每个基线
    """
    trr_results = results['TRR']
    comparisons = []

    for method in ['CLAP', 'PaSST', 'PANNs', 'Wav2Vec', 'Text']:
        if method not in results:
            continue

        method_results = results[method]

        # 配对 t 检验 (L2)
        t_stat, p_val = stats.ttest_rel(
            method_results['l2'],
            trr_results['l2']
        )

        # 效应量
        cohens_d = compute_cohens_d(method_results['l2'], trr_results['l2'])

        # 95% CI
        diff = method_results['l2'] - trr_results['l2']
        ci_low, ci_high = stats.t.interval(
            0.95, len(diff)-1, loc=np.mean(diff),
            scale=stats.sem(diff)
        )

        comparisons.append({
            'comparison': f'{method} vs TRR',
            'metric': 'L2',
            'mean_diff': np.mean(diff),
            'ci_95_low': ci_low,
            'ci_95_high': ci_high,
            't_statistic': t_stat,
            'p_value': p_val,
            'cohens_d': cohens_d
        })

    # Holm 校正
    p_values = [c['p_value'] for c in comparisons]
    reject, p_corrected, _, _ = multipletests(p_values, method='holm')

    for i, c in enumerate(comparisons):
        c['p_value_holm'] = p_corrected[i]
        c['significant'] = reject[i]

    return pd.DataFrame(comparisons)
```

#### 输出
- **逐 query CSV**: `sota_baseline_per_query.csv`
  - 字段: `query_id`, `method`, `l2`, `acc_at_0_1`, `recall`, `cosine`, `module`
- **汇总表**: `sota_baseline_summary.csv`
  - 各方法的均值和 95% CI
- **统计检验表**: `sota_baseline_significance.csv`
  - TRR vs 各基线的配对检验结果
- **可视化**: `sota_baseline_comparison.png` (雷达图或柱状图)

### 2.3 预期结果

**假设**:
1. TRR 在 L2 指标上优于所有基线方法
2. CLAP 作为最强的通用音频表征，性能接近但略逊于 TRR
3. PaSST 和 PANNs 在纹理敏感任务上表现不如 TRR
4. 所有 TRR 优势均达到统计显著性 (p < 0.05, Holm校正)

**图表类型**:
- 主图: 分组柱状图，展示各方法的五个指标
- 副图: 配对差异图 (TRR - Baseline)，带 95% CI

### 2.4 资源需求

**计算资源**:
- GPU: RTX 3090 或同等 (用于预计算 CLAP/PaSST/PANNs embeddings)
- CPU: 8核以上
- 内存: 32GB+
- 存储: 20GB (embedding 缓存)

**时间预算**:
- 环境配置: 0.5天
- Embedding 预计算: 1天 (1,267 + 211 = 1,478 个音频)
- 检索评估: 0.5天
- 统计分析: 0.5天
- 论文表格: 0.5天
- **总计: 3天**

**依赖包**:
```
torch>=2.0.0
transformers>=4.30.0
laion-clap>=1.1.4  # CLAP
passt>=0.1.0       # PaSST
panns-inference    # PANNs
librosa>=0.10.0
soundfile>=0.12.0
```

### 2.5 代码框架

```python
# File: Experiments/SOTABaselines/sota_comparison.py

import torch
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass
import pandas as pd
from pathlib import Path

# 可选导入，缺失时跳过
try:
    import laion_clap
    HAS_CLAP = True
except ImportError:
    HAS_CLAP = False

try:
    import passt
    HAS_PASST = True
except ImportError:
    HAS_PASST = False

try:
    import panns_inference
    HAS_PANNS = True
except ImportError:
    HAS_PANNS = False


@dataclass
class EmbeddingExtractor:
    """统一的 Embedding 提取器接口"""
    name: str
    model: Any
    device: str = "cuda" if torch.cuda.is_available() else "cpu"

    def encode(self, audio_paths: List[str]) -> np.ndarray:
        """提取音频 embedding"""
        raise NotImplementedError


class CLAPExtractor(EmbeddingExtractor):
    """CLAP Embedding 提取器"""

    def __init__(self, model_name: str = "laion/clap-htsat-unfused"):
        if not HAS_CLAP:
            raise ImportError("laion-clap not installed")

        import laion_clap
        model = laion_clap.CLAP_Module(
            enable_fusion=False,
            amodel='HTSAT-base'
        )
        model.load_ckpt()  # 加载预训练权重

        super().__init__("CLAP", model)

    def encode(self, audio_paths: List[str]) -> np.ndarray:
        """CLAP 使用 48kHz 采样率"""
        embeddings = self.model.get_audio_embedding_from_filelist(
            x=audio_paths,
            use_tqdm=True
        )
        return embeddings


class PaSSTExtractor(EmbeddingExtractor):
    """PaSST Embedding 提取器"""

    def __init__(self, model_name: str = "passt-s"):
        if not HAS_PASST:
            raise ImportError("passt not installed")

        # 加载 PaSST 模型
        from passt import get_model
        model = get_model(
            arch="passt_s_swa_p16_128_ap476",
            n_classes=527,  # AudioSet 类别数
            s_patchout_t=40,
            s_patchout_f=4
        )
        model.eval()

        super().__init__("PaSST", model)

    def encode(self, audio_paths: List[str]) -> np.ndarray:
        """PaSST 使用 mel-spectrogram 输入"""
        embeddings = []

        for path in audio_paths:
            # 加载音频并计算 mel-spectrogram
            wav, sr = librosa.load(path, sr=32000, mono=True)
            mel = librosa.feature.melspectrogram(
                y=wav, sr=sr, n_mels=128,
                n_fft=2048, hop_length=512
            )
            mel_db = librosa.power_to_db(mel, ref=np.max)

            # 转换为 tensor
            mel_tensor = torch.from_numpy(mel_db).unsqueeze(0).unsqueeze(0)
            mel_tensor = mel_tensor.to(self.device)

            # 前向传播
            with torch.no_grad():
                output = self.model(mel_tensor)
                # 使用 mean pooling
                emb = output.mean(dim=1).cpu().numpy()

            embeddings.append(emb[0])

        return np.array(embeddings)


class PANNsExtractor(EmbeddingExtractor):
    """PANNs Embedding 提取器"""

    def __init__(self, model_name: str = "CNN14"):
        if not HAS_PANNS:
            raise ImportError("panns-inference not installed")

        from panns_inference import AudioTagging
        model = AudioTagging(checkpoint_path=None, device=self.device)

        super().__init__("PANNs", model)

    def encode(self, audio_paths: List[str]) -> np.ndarray:
        """PANNs 使用 32kHz 采样率"""
        embeddings = []

        for path in audio_paths:
            # PANNs 自带音频加载
            (audio, _) = librosa.load(path, sr=32000, mono=True)

            # 前向传播
            with torch.no_grad():
                output = self.model.inference(audio)
                # 使用 embedding 层输出
                emb = output['embedding'].cpu().numpy()

            embeddings.append(emb[0])

        return np.array(embeddings)


def run_sota_comparison(
    knowledge_base_path: str,
    test_queries_path: str,
    output_dir: str
) -> Dict[str, pd.DataFrame]:
    """
    运行 SOTA 基线对比实验

    自动检测可用依赖，缺失时跳过对应方法
    """
    # 加载数据
    kb = load_knowledge_base(knowledge_base_path)
    test_queries = load_test_queries(test_queries_path)

    results = {}

    # 定义要测试的方法
    methods = []

    if HAS_CLAP:
        methods.append(("CLAP", CLAPExtractor()))
    else:
        print("[Warning] CLAP not available, skipping...")

    if HAS_PASST:
        methods.append(("PaSST", PaSSTExtractor()))
    else:
        print("[Warning] PaSST not available, skipping...")

    if HAS_PANNS:
        methods.append(("PANNs", PANNsExtractor()))
    else:
        print("[Warning] PANNs not available, skipping...")

    # 总是包含的基线
    methods.extend([
        ("TRR", TRRRetriever(kb)),
        ("Wav2Vec", Wav2VecRetriever(kb)),
        ("Text", TextRetriever(kb))
    ])

    # 运行评估
    for name, retriever in methods:
        print(f"\n[Evaluating {name}...]")
        df = evaluate_retrieval_method(name, kb, test_queries)
        results[name] = df

        # 保存逐 query 结果
        df.to_csv(f"{output_dir}/{name}_per_query.csv", index=False)

    # 统计比较
    comparison = compare_methods_statistically(results)
    comparison.to_csv(f"{output_dir}/statistical_comparison.csv", index=False)

    return results


if __name__ == "__main__":
    results = run_sota_comparison(
        knowledge_base_path="Data/knowledge_base.json",
        test_queries_path="Data/test_queries_211.json",
        output_dir="Experiments/SOTABaselines/results"
    )
```

---

## 实验3: 真实噪声 Protocol-C 重设计

### 3.1 实验名称与目的

**名称**: Real-World Audio Degradation Protocol-C

**目的**:
- 回应审稿人 C4 关于真实场景验证的关切
- 用真实音频退化替代简单的 embedding 加噪
- 验证自适应融合在真实退化条件下的表现

**对应审稿关切**: C4 (真实场景验证)

### 3.2 详细协议

#### 退化类型定义

| 退化类型 | 实现方式 | 参数设置 | 模拟场景 |
|---------|---------|---------|---------|
| AWGN | 直接加噪 | SNR = [20, 10, 5] dB | 环境噪声 |
| MP3压缩 | ffmpeg 编码 | 64kbps, 32kbps | 低码率传输 |
| 混响 | RIR 卷积 | Room size: small/medium/large | 室内声学 |
| 截断 | 时间裁剪 | 0.5s, 1.0s 片段 | 不完整输入 |

#### 输入
- **原始音频**: 211 held-out query 音频
- **退化参数**: 每种退化类型的 3 个严重程度级别
- **测试条件**: 单模态 (仅音频) vs 自适应融合

#### 实验步骤

**Step 1: 音频退化实现**
```python
import librosa
import soundfile as sf
import subprocess
from scipy import signal

class AudioDegrader:
    """音频退化处理器"""

    @staticmethod
    def add_awgn(audio: np.ndarray, sr: int, snr_db: float) -> np.ndarray:
        """添加加性高斯白噪声"""
        signal_power = np.mean(audio ** 2)
        noise_power = signal_power / (10 ** (snr_db / 10))
        noise = np.random.normal(0, np.sqrt(noise_power), len(audio))
        return audio + noise

    @staticmethod
    def mp3_compress(input_path: str, output_path: str, bitrate: str = "64k") -> str:
        """MP3 压缩退化"""
        cmd = [
            "ffmpeg", "-y", "-i", input_path,
            "-codec:a", "libmp3lame", "-b:a", bitrate,
            "-ac", "1", "-ar", "16000",
            output_path
        ]
        subprocess.run(cmd, check=True, capture_output=True)

        # 重新加载
        audio, sr = librosa.load(output_path, sr=16000, mono=True)
        return audio

    @staticmethod
    def add_reverb(audio: np.ndarray, sr: int, room_size: str = "medium") -> np.ndarray:
        """添加混响 (使用 RIR)"""
        # 加载预录制的 RIR 或使用人工 RIR
        rir_paths = {
            "small": "Data/RIR/small_room.wav",
            "medium": "Data/RIR/medium_room.wav",
            "large": "Data/RIR/large_room.wav"
        }

        rir, _ = librosa.load(rir_paths[room_size], sr=sr, mono=True)

        # 卷积
        reverberant = signal.convolve(audio, rir, mode='full')[:len(audio)]

        # 混合干/湿信号
        wet_gain = 0.3
        return (1 - wet_gain) * audio + wet_gain * reverberant

    @staticmethod
    def truncate(audio: np.ndarray, sr: int, duration: float) -> np.ndarray:
        """时间截断"""
        samples = int(duration * sr)

        if len(audio) <= samples:
            return audio

        # 随机起始位置
        max_start = len(audio) - samples
        start = np.random.randint(0, max_start)

        return audio[start:start + samples]
```

**Step 2: 退化 → 重新编码 → Gram 矩阵**
```python
def process_degraded_audio(
    original_path: str,
    degradation_type: str,
    severity: str,
    output_dir: str
) -> Dict[str, Any]:
    """
    处理退化音频并提取 TRR 特征

    Pipeline: 退化 -> 保存 -> 重新加载 -> Wav2Vec2 -> Gram 矩阵
    """
    # 加载原始音频
    audio, sr = librosa.load(original_path, sr=16000, mono=True)

    # 应用退化
    degrader = AudioDegrader()

    if degradation_type == "AWGN":
        snr_map = {"low": 20, "medium": 10, "high": 5}
        degraded = degrader.add_awgn(audio, sr, snr_map[severity])

    elif degradation_type == "MP3":
        bitrate_map = {"low": "128k", "medium": "64k", "high": "32k"}
        temp_path = f"{output_dir}/temp.mp3"
        degraded = degrader.mp3_compress(
            original_path, temp_path, bitrate_map[severity]
        )

    elif degradation_type == "Reverb":
        degraded = degrader.add_reverb(audio, sr, severity)

    elif degradation_type == "Truncate":
        duration_map = {"low": 2.0, "medium": 1.0, "high": 0.5}
        degraded = degrader.truncate(audio, sr, duration_map[severity])

    # 保存退化音频
    degraded_path = f"{output_dir}/{degradation_type}_{severity}.wav"
    sf.write(degraded_path, degraded, sr)

    # 重新编码 -> Wav2Vec2 -> Gram 矩阵
    trr_vector = compute_trr_from_audio(degraded_path)

    return {
        "original_path": original_path,
        "degraded_path": degraded_path,
        "degradation_type": degradation_type,
        "severity": severity,
        "trr_vector": trr_vector
    }
```

**Step 3: 单模态 vs 自适应融合对比**
```python
def evaluate_under_degradation(
    test_queries: List[Dict],
    knowledge_base: List[Dict],
    degradation_configs: List[Dict]
) -> pd.DataFrame:
    """
    在退化条件下评估检索性能

    对比:
    - Audio-only (单模态)
    - Adaptive Fusion (自适应融合)
    """
    results = []

    for query in test_queries:
        for config in degradation_configs:
            # 生成退化音频
            degraded = process_degraded_audio(
                query['audio_path'],
                config['type'],
                config['severity'],
                "temp/"
            )

            # 1. Audio-only 检索
            audio_only_result = retrieve_audio_only(
                degraded['trr_vector'],
                knowledge_base
            )

            # 2. 自适应融合检索
            # 模拟文本描述（可能模糊或不匹配）
            text_query = generate_conflicting_text(query, config['type'])

            fusion_result = retrieve_adaptive_fusion(
                text_query,
                degraded['trr_vector'],
                knowledge_base
            )

            # 计算指标
            gt_params = query['parameters']

            results.append({
                'query_id': query['id'],
                'degradation_type': config['type'],
                'severity': config['severity'],
                'method': 'Audio-only',
                'l2': compute_l2(audio_only_result, gt_params),
                'fusion_weight': 1.0  # 纯音频
            })

            results.append({
                'query_id': query['id'],
                'degradation_type': config['type'],
                'severity': config['severity'],
                'method': 'Adaptive-Fusion',
                'l2': compute_l2(fusion_result, gt_params),
                'fusion_weight': fusion_result.get('alpha', 0.5)
            })

    return pd.DataFrame(results)
```

#### 输出
- **逐 query CSV**: `protocol_c_real_degradation.csv`
- **汇总表**: 按退化类型和严重程度的性能汇总
- **可视化**:
  - 热力图: 退化类型 × 严重程度 vs L2 误差
  - 对比图: Audio-only vs Adaptive-Fusion

### 3.3 预期结果

**假设**:
1. 随着退化严重程度增加，Audio-only 性能显著下降
2. Adaptive Fusion 在所有退化条件下均优于 Audio-only
3. 在 MP3 压缩和截断条件下，融合策略会自动降低音频权重
4. 在 AWGN 条件下，融合策略仍能保持较高音频权重（因为 TRR 对噪声有一定鲁棒性）

### 3.4 资源需求

**计算资源**:
- GPU: 用于 Wav2Vec2 特征提取
- 存储: 10GB (退化音频缓存)

**时间预算**: 2-3天

---

## 实验4: 指标与感知相关性分析

### 4.1 实验名称与目的

**名称**: Objective-Perceptual Metric Correlation Analysis

**目的**:
- 回应审稿人 C3 关于参数指标与感知质量相关性的关切
- 建立参数空间指标与听测评分的定量关系
- 识别"感知无关"的参数误差类型

**对应审稿关切**: C3 (感知相关性)

### 4.2 详细协议

#### 输入
- **听测数据**: MUSHRA 实验原始评分 (26 participants × N queries)
- **参数指标**: L2, Acc@0.1, Recall, Cosine, Module
- **音频指标**: FAD (Fréchet Audio Distance)

#### 实验步骤

**Step 1: 数据准备**
```python
def prepare_correlation_data(
    mushra_path: str,
    metrics_path: str
) -> pd.DataFrame:
    """
    合并听测评分和参数指标

    Returns:
        DataFrame with columns:
        - query_id, participant_id, rating
        - l2, acc_at_0_1, recall, cosine, module
        - fad
    """
    # 加载 MUSHRA 数据
    mushra_df = pd.read_csv(mushra_path)

    # 加载参数指标
    metrics_df = pd.read_csv(metrics_path)

    # 合并
    merged = mushra_df.merge(
        metrics_df,
        on=['query_id', 'method'],
        how='inner'
    )

    return merged
```

**Step 2: 相关性计算**
```python
def compute_correlations(df: pd.DataFrame) -> pd.DataFrame:
    """
    计算参数指标与听测评分的相关性

    使用:
    - Spearman (非参数，单调关系)
    - Pearson (线性关系)
    """
    metrics = ['l2', 'acc_at_0_1', 'recall', 'cosine', 'module', 'fad']

    results = []

    for metric in metrics:
        # Spearman
        spearman_r, spearman_p = stats.spearmanr(
            df[metric],
            df['rating']
        )

        # Pearson
        pearson_r, pearson_p = stats.pearsonr(
            df[metric],
            df['rating']
        )

        # 95% CI (Fisher z-transform)
        spearman_ci = fisher_z_ci(spearman_r, len(df))
        pearson_ci = fisher_z_ci(pearson_r, len(df))

        results.append({
            'metric': metric,
            'spearman_r': spearman_r,
            'spearman_p': spearman_p,
            'spearman_ci_low': spearman_ci[0],
            'spearman_ci_high': spearman_ci[1],
            'pearson_r': pearson_r,
            'pearson_p': pearson_p,
            'pearson_ci_low': pearson_ci[0],
            'pearson_ci_high': pearson_ci[1]
        })

    return pd.DataFrame(results)
```

**Step 3: 混合效应模型**
```python
def fit_mixed_effects_model(df: pd.DataFrame) -> Dict:
    """
    拟合混合效应模型

    Model: rating ~ metric + (1|participant) + (1|query)
    """
    import statsmodels.api as sm
    import statsmodels.formula.api as smf

    # 标准化指标
    df['l2_z'] = (df['l2'] - df['l2'].mean()) / df['l2'].std()

    # 拟合模型
    model = smf.mixedlm(
        "rating ~ l2_z + acc_at_0_1 + cosine",
        df,
        groups=df["participant_id"],
        re_formula="~1"
    )

    result = model.fit()

    return {
        'params': result.params,
        'pvalues': result.pvalues,
        'conf_int': result.conf_int(),
        'aic': result.aic,
        'bic': result.bic
    }
```

**Step 4: 识别感知无关误差**
```python
def identify_perceptually_irrelevant_errors(
    df: pd.DataFrame,
    rating_threshold: float = 10.0  # MUSHRA 分数差异阈值
) -> pd.DataFrame:
    """
    识别感知无关的参数误差

    找出: 参数差异大但听测评分接近的样本对
    """
    irrelevant_cases = []

    # 按 query 分组
    for query_id, group in df.groupby('query_id'):
        if len(group) < 2:
            continue

        # 比较所有方法对
        for i, row1 in group.iterrows():
            for j, row2 in group.iterrows():
                if i >= j:
                    continue

                rating_diff = abs(row1['rating'] - row2['rating'])
                l2_diff = abs(row1['l2'] - row2['l2'])

                # 参数差异大但评分接近
                if l2_diff > 0.5 and rating_diff < rating_threshold:
                    irrelevant_cases.append({
                        'query_id': query_id,
                        'method_1': row1['method'],
                        'method_2': row2['method'],
                        'l2_diff': l2_diff,
                        'rating_diff': rating_diff,
                        'l2_1': row1['l2'],
                        'l2_2': row2['l2']
                    })

    return pd.DataFrame(irrelevant_cases)
```

#### 输出
- **相关性表**: 各指标与听测评分的 Spearman/Pearson 相关
- **混合效应模型结果**: 固定效应估计和显著性
- **感知无关误差案例**: 需要单独讨论的异常样本

### 4.3 预期结果

**假设**:
1. FAD 与听测评分相关性最高 (|r| > 0.6)
2. Acc@0.1 与听测评分呈中等正相关 (r ~ 0.4-0.5)
3. L2 与听测评分呈中等负相关 (r ~ -0.4)
4. 存在 10-15% 的案例显示大参数差异但小感知差异

### 4.4 资源需求

**时间预算**: 1-2天

---

## 实验5: Retrieval-only vs Retrieval+Projection 消融

### 5.1 实验名称与目的

**名称**: Retrieval vs Retrieval+Projection Ablation Study

**目的**:
- 支撑 Agent claim，证明检索是核心贡献
- 量化 Projection/Constraint Repair 的边际增益
- 报告约束满足率（可行性）

**对应审稿关切**: Agent claim (检索核心性)

### 5.2 详细协议

#### 测试条件

| 条件 | 描述 | 目的 |
|-----|------|-----|
| (a) Pure Retrieval | 仅检索，无后处理 | 证明检索本身有效 |
| (b) Retrieval + Simple Projection | 检索 + 简单投影 | 边际增益 |
| (c) Retrieval + Constraint Repair | 检索 + 约束修复 | 完整系统 |

#### 实验步骤

**Step 1: 定义三种条件**
```python
class RetrievalCondition:
    """检索条件基类"""

    def process(self, retrieved_params: Dict) -> Dict:
        raise NotImplementedError


class PureRetrieval(RetrievalCondition):
    """纯检索，无后处理"""

    def process(self, retrieved_params: Dict) -> Dict:
        return retrieved_params


class SimpleProjection(RetrievalCondition):
    """简单投影：将参数裁剪到有效范围"""

    def __init__(self, param_ranges: Dict[str, Tuple[float, float]]):
        self.param_ranges = param_ranges

    def process(self, retrieved_params: Dict) -> Dict:
        projected = {}
        for key, value in retrieved_params.items():
            if key in self.param_ranges:
                min_val, max_val = self.param_ranges[key]
                projected[key] = np.clip(value, min_val, max_val)
            else:
                projected[key] = value
        return projected


class ConstraintRepair(RetrievalCondition):
    """约束修复：处理模块间依赖关系"""

    def __init__(self, constraints: List[Constraint]):
        self.constraints = constraints

    def process(self, retrieved_params: Dict) -> Dict:
        # 先简单投影
        params = SimpleProjection(PARAM_RANGES).process(retrieved_params)

        # 应用约束修复
        for constraint in self.constraints:
            if not constraint.is_satisfied(params):
                params = constraint.repair(params)

        return params
```

**Step 2: 约束满足率计算**
```python
def compute_constraint_satisfaction_rate(
    predictions: List[Dict],
    constraints: List[Constraint]
) -> Dict[str, float]:
    """
    计算约束满足率

    Returns:
        {
            'overall_satisfaction': 总体满足率,
            'per_constraint': 各约束的满足率
        }
    """
    total = len(predictions)

    # 总体满足（所有约束都满足）
    fully_satisfied = sum(
        1 for p in predictions
        if all(c.is_satisfied(p) for c in constraints)
    )

    # 各约束满足率
    per_constraint = {}
    for constraint in constraints:
        satisfied = sum(
            1 for p in predictions
            if constraint.is_satisfied(p)
        )
        per_constraint[constraint.name] = satisfied / total

    return {
        'overall_satisfaction': fully_satisfied / total,
        'per_constraint': per_constraint
    }
```

**Step 3: 对比评估**
```python
def run_ablation_experiment(
    test_queries: List[Dict],
    knowledge_base: List[Dict],
    conditions: List[RetrievalCondition]
) -> pd.DataFrame:
    """运行消融实验"""

    results = []

    for condition in conditions:
        condition_results = []

        for query in test_queries:
            # 检索
            retrieved = retrieve_top_k(query, knowledge_base, k=1)[0]

            # 应用条件处理
            predicted = condition.process(retrieved['parameters'])

            # 计算指标
            metrics = compute_parameter_metrics(predicted, query['parameters'])

            condition_results.append({
                'query_id': query['id'],
                'condition': condition.__class__.__name__,
                **metrics
            })

        results.extend(condition_results)

        # 计算约束满足率
        predictions = [r['parameters'] for r in condition_results]
        satisfaction = compute_constraint_satisfaction_rate(
            predictions, CONSTRAINTS
        )

        print(f"{condition.__class__.__name__}:")
        print(f"  Constraint Satisfaction: {satisfaction['overall_satisfaction']:.2%}")

    return pd.DataFrame(results)
```

#### 输出
- **性能对比表**: 三种条件的 L2, Acc@0.1, Recall 等指标
- **约束满足率表**: 各条件的约束满足情况
- **边际增益分析**: (b)-(a) 和 (c)-(b) 的增益量化

### 5.3 预期结果

**假设**:
1. Pure Retrieval 已能达到较好的性能（L2 ~ 0.35）
2. Simple Projection 带来边际改善（L2 降低 5-10%）
3. Constraint Repair 主要提升约束满足率（从 85% 到 98%+）
4. 检索是核心，后处理提供可行性和边际精度提升

### 5.4 资源需求

**时间预算**: 1-2天

---

## 实验6: 端到端延迟分析

### 6.1 实验名称与目的

**名称**: End-to-End Latency Profiling

**目的**:
- 回应审稿人 C6 关于系统延迟的关切
- 提供真实的部署时延预算
- 区分在线计算和可缓存部分
- 提供优化策略建议

**对应审稿关切**: C6 (延迟分析)

### 6.2 详细协议

#### 测量模块

| 模块 | 描述 | 是否可缓存 |
|-----|------|----------|
| Wav2Vec2 前向 | 音频编码 | 否（输入相关） |
| Gram 构造 | TRR 特征计算 | 否（输入相关） |
| KNN 检索 | 向量检索 | 否（输入相关） |
| Fusion | 多模态融合 | 否（输入相关） |
| LLM 调用 | 参数生成/修复 | 部分可缓存 |
| DSP 渲染 | 音频渲染 | 否（输出验证） |

#### 实验步骤

**Step 1: 分模块延迟测量**
```python
import time
from contextlib import contextmanager
from typing import Dict, List
import statistics

@contextmanager
def timer(name: str, timings: Dict[str, List[float]]):
    """计时上下文管理器"""
    start = time.perf_counter()
    yield
    elapsed = (time.perf_counter() - start) * 1000  # ms
    timings.setdefault(name, []).append(elapsed)


def profile_end_to_end_latency(
    test_queries: List[Dict],
    n_repetitions: int = 100,
    n_warmup: int = 10
) -> Dict[str, Dict[str, float]]:
    """
    测量端到端延迟

    Returns:
        {
            'module_name': {
                'median_ms': ...,
                'p95_ms': ...,
                'p99_ms': ...,
                'mean_ms': ...,
                'std_ms': ...
            }
        }
    """
    timings = {}

    # Warmup
    for _ in range(n_warmup):
        _ = run_single_inference(test_queries[0], timings)

    # 正式测量
    for _ in range(n_repetitions):
        query = random.choice(test_queries)
        _ = run_single_inference(query, timings)

    # 统计
    stats = {}
    for module, times in timings.items():
        sorted_times = sorted(times)
        n = len(sorted_times)

        stats[module] = {
            'median_ms': statistics.median(sorted_times),
            'p95_ms': sorted_times[int(n * 0.95)],
            'p99_ms': sorted_times[int(n * 0.99)],
            'mean_ms': statistics.mean(sorted_times),
            'std_ms': statistics.stdev(sorted_times) if n > 1 else 0,
            'n_samples': n
        }

    return stats


def run_single_inference(query: Dict, timings: Dict) -> Dict:
    """单次推理，记录各模块时间"""

    # 1. 音频加载
    with timer("audio_load", timings):
        audio = load_audio(query['audio_path'])

    # 2. Wav2Vec2 前向
    with timer("wav2vec_forward", timings):
        features = wav2vec_encode(audio)

    # 3. Gram 矩阵构造
    with timer("gram_construction", timings):
        trr_vector = compute_gram_matrix(features)

    # 4. KNN 检索
    with timer("knn_retrieval", timings):
        neighbors = knn_search(trr_vector, k=5)

    # 5. 融合
    with timer("fusion", timings):
        fused = adaptive_fusion(query['text'], neighbors)

    # 6. LLM 调用
    with timer("llm_call", timings):
        params = llm_generate(fused)

    # 7. 约束修复
    with timer("constraint_repair", timings):
        repaired = constraint_repair(params)

    return repaired
```

**Step 2: 缓存策略分析**
```python
def analyze_caching_opportunities(
    test_queries: List[Dict]
) -> Dict[str, float]:
    """
    分析可缓存部分的潜在收益

    可缓存:
    - 知识库 embeddings (预计算)
    - LLM 输出（对于重复查询）
    """

    # 知识库预计算节省
    kb_size = len(knowledge_base)
    trr_time_per_sample = 50  # ms，假设值
    total_precompute_time = kb_size * trr_time_per_sample / 1000  # seconds

    # LLM 缓存命中率分析
    query_hashes = [hash(q['text']) for q in test_queries]
    unique_queries = len(set(query_hashes))
    cache_hit_rate = 1 - (unique_queries / len(test_queries))

    llm_time_saved = cache_hit_rate * stats['llm_call']['median_ms']

    return {
        'kb_precompute_time_s': total_precompute_time,
        'llm_cache_hit_rate': cache_hit_rate,
        'llm_time_saved_ms': llm_time_saved,
        'optimized_e2e_median_ms': (
            stats['e2e']['median_ms'] - llm_time_saved
        )
    }
```

**Step 3: ANN 索引优化分析**
```python
def compare_ann_vs_exact_knn(
    test_queries: List[Dict],
    nlist_values: List[int] = [10, 50, 100],
    nprobe_values: List[int] = [1, 5, 10]
) -> pd.DataFrame:
    """
    对比精确 KNN 和 ANN (Faiss IVF)

    评估: 速度 vs 精度 trade-off
    """
    results = []

    # 精确 KNN 基线
    exact_time, exact_recall = measure_exact_knn(test_queries)

    for nlist in nlist_values:
        for nprobe in nprobe_values:
            # 构建 Faiss IVF 索引
            index = build_ivf_index(knowledge_base, nlist=nlist)

            # 测量
            ann_time, ann_recall = measure_ann_knn(
                test_queries, index, nprobe=nprobe
            )

            results.append({
                'nlist': nlist,
                'nprobe': nprobe,
                'search_time_ms': ann_time,
                'speedup_vs_exact': exact_time / ann_time,
                'recall_at_1': ann_recall,
                'recall_degradation': exact_recall - ann_recall
            })

    return pd.DataFrame(results)
```

#### 输出
- **延迟分解表**: 各模块的 median/p95/p99
- **端到端延迟**: 完整流程的时间预算
- **优化建议表**: 缓存和 ANN 的潜在收益

### 6.3 预期结果

**假设**:
1. 端到端 median 延迟: 200-500ms (不含 LLM)
2. LLM 调用: 500-2000ms (API 依赖)
3. Wav2Vec2 + Gram: 50-100ms
4. KNN 检索: 5-10ms (精确) / 1-2ms (ANN)
5. ANN 可实现 5-10x 加速，Recall@1 > 95%

### 6.4 资源需求

**时间预算**: 1天

---

## 实验执行时间表

```
Week 1:
  Day 1-2: E1 (AEM 学习曲线)
  Day 3-4: E2 (SOTA 基线) - 环境配置 + Embedding 预计算
  Day 5:   E2 (SOTA 基线) - 评估 + 分析

Week 2:
  Day 1-2: E3 (真实噪声 Protocol-C)
  Day 3:   E4 (指标相关性)
  Day 4:   E5 (消融实验)
  Day 5:   E6 (延迟分析)

Week 3:
  Day 1-2: 论文表格和图表制作
  Day 3-5: 论文修订 + 审稿回应更新
```

---

## 与审稿人 Concern 的对应关系汇总

| 实验 | 对应审稿关切 | 核心证据 |
|-----|-------------|---------|
| E1 AEM 学习曲线 | Agent claim | 记忆大小 vs L2 误差曲线，统计显著性 |
| E2 SOTA 基线 | C1 (新颖性) | TRR vs CLAP/PaSST/PANNs 对比表 |
| E3 真实噪声 | C4 (真实场景) | 4种退化类型的融合性能对比 |
| E4 指标相关性 | C3 (感知相关性) | Spearman/Pearson 相关表，混合效应模型 |
| E5 消融实验 | Agent claim | Retrieval-only vs +Projection 对比 |
| E6 延迟分析 | C6 (延迟) | 分模块延迟表，优化策略 |

---

## 风险与缓解策略

| 风险 | 可能性 | 影响 | 缓解策略 |
|-----|-------|------|---------|
| CLAP/PaSST 依赖安装失败 | 中 | 高 | 提供 Docker 镜像，可选依赖设计 |
| 新基线性能优于 TRR | 中 | 高 | 聚焦"参数空间对齐任务"的边界界定 |
| 听测数据量不足 | 低 | 中 | 明确报告样本量和统计功效 |
| 延迟测量波动大 | 中 | 低 | 增加重复次数，报告 p95/p99 |
| 实验时间超预期 | 中 | 中 | 并行执行独立实验，优先核心实验 |

---

## 验收标准

每个实验完成后需检查:

1. **可复现性**: 一键运行脚本，固定随机种子
2. **统计严谨性**: 95% CI，配对检验，多重比较校正
3. **文档完整性**: 逐 query CSV，汇总表，可视化
4. **论文可用性**: 结果可直接用于论文表格和图表
5. **代码质量**: 符合项目代码规范，有类型提示和文档

---

*文档版本: 1.0*
*创建日期: 2026-03-05*
*最后更新: 2026-03-05*
