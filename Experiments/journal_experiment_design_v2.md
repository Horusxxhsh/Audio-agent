# 顶级期刊实验设计方案：Neuro-Symbolic Audio Agent with Texture Resonance

**论文题目建议**: 
> *Bridging the Timbre Gap: Neuro-Symbolic Audio Effect Production via Texture-Aware Dual-Modal RAG*
> (跨越音色鸿沟：基于纹理感知的双模态RAG神经符号化音频效果制作)

**核心创新点 (The "Delta")**:
1.  **架构创新**: 将神经符号化控制 (LLM -> DSP Parameters) 与双模态检索 (Text+Audio) 结合。
2.  **特征创新**: 提出 **Texture Resonance Retrieval (TRR)**，利用 Gram Matrix 解决传统均值向量无法捕捉音频“织体/纹理”的问题。
3.  **融合机制**: 动态不确定性加权 (Dynamic Uncertainty Weighting)，根据模态的噪声水平自适应调整检索权重。

---

## 1. 研究问题 (Research Questions)

为了满足顶级期刊（如 IEEE TASLP, JAES, AAAI）的要求，我们需要回答以下层层递进的问题：

*   **RQ1 (Effectiveness)**: 引入双模态 RAG 机制后，系统在参数预测准确性上是否显著优于单模态基线和零样本 LLM？
*   **RQ2 (Texture Validity)**: 提出的 TRR (纹理共振) 模块在处理复杂音色（如失真、调制效果）时，是否比传统声学特征向量（Vector Embedding）更具鲁棒性？
*   **RQ3 (Robustness)**: 在用户输入（文本模糊）或参考音频（包含噪声）质量受损的情况下，系统的动态融合机制能否保持性能稳定？
*   **RQ4 (Interpretability)**: 检索到的参考案例是否在听感和参数逻辑上具有可解释性（即“为什么检索到这个？”）？

---

## 2. 实验设置 (Experimental Setup)

### 2.1 数据集 (The "Golden Set")
*   **规模**: 扩大至 100+ 样本（推荐补充更多合成数据或真实数据）。
*   **标注**: 
    - **Input**: 文本描述 (Text Prompt) + 参考音频 (Reference Audio)。
    - **Ground Truth**: 专家级 DSP 参数设置 (JSON)。
    - **Metadata**: 风格 (Style)、情感 (Mood)、典型性评分。

### 2.2 基线模型 (Baselines)
我们将我们的最终设计 (**Ours: Texture-Aware Dual RAG**) 与以下 SOTA/基线进行对比：

| ID | 方法名称 | 检索机制 | 核心特征 | 备注 |
|:---|:---|:---|:---|:---|
| **B1** | **Zero-shot LLM** | 无 (Direct Generation) | 仅依赖 LLM 内部知识 | 代表通用大模型能力 |
| **B2** | **Text-RAG** | 文本相似度 (Sbert/TF-IDF) | 语义匹配 | 代表传统 NLP 检索增强 |
| **B3** | **Audio-Vector RAG** | 声学向量 (Wav2Vec2 Mean) | 声学内容匹配 | 代表传统音频检索 (MusicCaps等) |
| **Ours** | **Texture-RAG** | **Text + TRR (Gram Matrix)** | **语义 + 纹理共振** | **本文提出的最终方案** |

### 2.3 核心方法详解: Texture Resonance Retrieval (TRR)
**为何均值向量失效？**
传统的音频检索 (如 MusicCaps, CLAP) 通常对时间维度进行**均值池化 (Mean Pooling)**，即 $V = \frac{1}{T} \sum_{t=1}^{T} f(t)$。这种操作会抹平时间上的动态变化，导致一段“平稳的正弦波”和一段“快速调制的方波”在均值特征上极其相似。这对“音色/纹理”的区分是致命的。

**TRR 的解决方案 (Gram Matrix)**:
受图像风格迁移 (Style Transfer) 的启发，我们提出计算特征通道之间的**二阶相关性 (Second-order Correlation)**，即 **Gram Matrix**。

1.  **特征提取**: 输入音频 $A$，通过 Wav2Vec 2.0 提取中间层特征 $F \in \mathbb{R}^{C \times T}$ ($C$=通道数, $T$=时间步)。
2.  **纹理编码**: 计算 Gram 矩阵 $G = F \cdot F^T \in \mathbb{R}^{C \times C}$。
    *   $G_{ij}$ 代表第 $i$ 个特征通道和第 $j$ 个特征通道的共激活程度。
    *   **关键点**: 该矩阵的大小只与通道数有关，与时间 $T$ 无关（Time-Invariant），因此它是纯粹的“风格/纹理”描述符。
3.  **检索**: 将 $G$ 展平为向量，使用余弦相似度进行检索。

---

## 3. 实验设计 (Detailed Experiments)

### 3.1 实验一：主性能对比 (Main Performance)
*   **目的**: 回答 RQ1。
*   **方法**: 在标准测试集上运行 B1, B2, B3, Ours。
*   **指标**: 
    - **Parameter Distance (L2)**: 预测参数与 GT 的欧氏距离 (特定于 DSP 的归一化距离)。
    - **Feature Distance (FD)**: 生成音频与目标音频的声学特征距离 (如 MFCC/Log-Mel 距离)。
*   **预期结果**: Ours 应该在各项指标上取得最低误差 (SOTA)。

### 3.2 实验二：纹理感知有效性分析 (The "Texture Gap")
*   **目的**: 回答 RQ2。这是论文的核心亮点。
*   **方法**: 
    - 选取具有鲜明纹理差异的子集（如 Clean Jazz vs Distorted Metal）。
    - 对比 **B3 (Mean Vector)** 和 **Ours (TRR)** 的 Top-K 检索准确率。
*   **可视化**: 绘制 t-SNE 图，展示 TRR 特征空间中不同风格的聚类分离度显著优于 Mean Vector。
*   **预期结论**: 证明 Mean Vector 存在“平均化陷阱” (Averaging Pitfall)，而 TRR 能精准捕捉音色细节。

### 3.3 实验三：噪声鲁棒性消融 (Ablation under Noise)
*   **目的**: 回答 RQ3。验证双模态互补性。
*   **设置**: (基于我们之前的 run_ablation.py 逻辑)
    - **Scenario A (Vague Text)**: 输入文本变为 "Make it sound good"，强制系统依赖音频。
    - **Scenario B (Noisy Audio)**: 音频加入背景噪/强混响，强制系统依赖文本。
*   **对比**: Ours (Dynamic Alpha) vs Ours (Fixed Alpha)。
*   **预期结论**: Dynamic Alpha 能够在单一模态失效时自动“切换”注意力，保持性能不崩溃。

### 3.4 实验四：主观听测 (Subjective Evaluation - MUSHRA)
*   **目的**: 顶级期刊必备，验证“参数准”是否等于“听着好”。
*   **方法**: 
    - 邀请 10-20 名专业音乐人/音频工程师。
    - 盲测：播放 Target 音频，以及 B1, B3, Ours 生成的音频。
    - 评分维度：
        1. **Timbral Similarity** (音色相似度)
        2. **Musicality** (音乐性)
        3. **Overall Quality** (整体质量)
*   **统计分析**: 使用 Wilcoxon Signed-Rank Test 验证 Ours 的显著性优势 (p < 0.05)。

### 3.5 实验五：综合消融研究 (Comprehensive Ablation)
*   **目的**: 深入验证每个组件的贡献。
*   **A. 融合策略消融 (Fusion Strategy)**
    - **Ours (Dynamic)** vs **Static (α=0.5)** vs **Text-Only** vs **Audio-Only**
    - 验证动态权重在不同信噪比下的优越性。
*   **B. 纹理特征消融 (Texture Feature)**
    - **TRR (Gram Matrix)** vs **Basic (Mean Pooling)** vs **Global (Std Dev)**
    - 验证 Gram Matrix 对风格捕捉的必要性。
*   **C. 记忆模块消融 (Memory Loop)** (可选)
    - **With Feedback** vs **Without Feedback**
    - 在多轮交互场景下，验证系统是否能“越用越懂用户”。

---

## 4. 论文叙事逻辑 (Storyline)

1.  **Introdution**: 音乐人面临参数调整的困难 -> LLM 很有潜力但容易幻觉 -> RAG 是解法 -> 但传统 RAG 忽略了音频独特的“纹理”属性。
2.  **Problem**: 为什么 Mean Pooling 向量不够好？（因为它丢弃了空间相关性，无法区分“持续的平稳正弦波”和“快速变化的方波纹理”）。
3.  **Method**: 
    - 引入 **TRR**：用 Gram Matrix 捕捉特征及其相关性。
    - 引入 **Dual RAG**：结合语义理解和纹理匹配。
4.  **Experiments**: 
    - 证明比 Text-Only 准。
    - 证明比 Vector-Only 更懂“风格”。
    - 证明在模糊输入下更鲁棒。
    - 证明人耳听起来更好。
5.  **Conclusion**: Audio-Agent 开启了基于参考听感的精确音频设计新范式。

---

## 5. 执行计划 (Action Plan)

1.  **代码固化**: 确认 `trr_adapter.py` 和 `rag_system.py` 为最终版本代码。
2.  **数据扩充**: (可选) 利用合成脚本生成更多样化的 100 组数据用于支撑图表。
3.  **图表绘制**: 
    - 绘制 TRR vs Vector 的检索热力图 (Heatmap)。
    - 绘制消融实验的柱状图 (Bar Plot)。
4.  **论文填空**: 将上述实验结果填入 LaTeX 模板。
