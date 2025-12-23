# 顶级期刊核心贡献点梳理 (Key Contributions for Top-Tier Journal)

本文针对智能音乐制作 (Intelligent Music Production, IMP) 中存在的“语义鸿沟”与“参数致幻”问题，提出了一套完整的 Neuro-Symbolic Audio Agent 解决方案。结合最新的实验数据，我们将核心贡献总结为以下四点：

## 1. 框架创新: Neuro-Symbolic 桥接“语义鸿沟”
> **Methodological Contribution: Retrieval-Augmented Neuro-Symbolic Control**

*   **问题**: 现有的音频生成模型 (如 MusicLM) 多为端到端生成，产生不可编辑的波形；而传统的 DSP 控制方法依赖复杂的工程规则，缺乏灵活性。
*   **贡献**: 我们提出了首个 **Neuro-Symbolic（神经符号）** 框架，将 LLM 的语义理解能力（Agent）与 DSP 的高保真信号处理能力（Tool）解耦并桥接。
*   **创新性**: 
    *   **可编辑性 (Editability)**: 不同于黑盒生成，我们的输出是透明的 DSP 参数 (JSON)，用户可以无缝修改。
    *   **通用性 (Generality)**: 该框架不依赖特定的 DSP 算法，通过简单的 API 定义即可适配不同的效果器链。

## 2. 核心算法: 基于 Gram Matrix 的纹理共振检索 (TRR)
> **Theoretical Contribution: Texture Resonance Retrieval via Gram Matrix**

*   **问题**: 传统的音频检索 (如 CLAP, MusicCaps) 广泛使用时间维度的均值池化 (Mean Pooling)。我们从理论上证明了这种操作会导致 **"Timbre Ambiguity" (音色歧义)**——即动态纹理特征（如失真的颗粒感）在均值化后丢失。
*   **贡献**: 受图像风格迁移启发，我们首次将 **Gram Matrix (二阶特征相关性)** 引入音频参数检索任务。
    *   $$ G_{ij} = \sum_t F_{it} F_{jt} $$
    *   该矩阵并不捕捉“何时发生了什么”，而是捕捉“整体的纹理质感”，从而实现了对复杂音色（如 Distortion, Metal）的精准锁定。
*   **实证**: 实验显示，TRR 方法在复杂音色上的 **Active Parameter Recall (有效参数召回率)** 提升了近 10%。

## 3. 融合机制: 动态不确定性加权 (Dynamic Uncertainty Weighting)
> **Algorithmic Contribution: Uncertainty-Aware Modality Fusion**

*   **问题**: 多模态 RAG (Text + Audio) 面临“模态互斥”挑战。有时用户的文本描述模糊 (e.g., "Make it sound good")，有时参考音频质量低劣。静态的权重分配 (Fixed Weighting) 无法应对这种动态变化。
*   **贡献**: 我们设计了 **Dynamic $\alpha$ Gateway** 机制。
    *   该机制并不简单的拼接向量，而是实时计算输入模态的 **"Information Entropy" (信息熵/不确定性)**。
    *   当检测到文本模糊词（Vague Tokens）时，系统自动降低文本权重，转而依赖音频纹理特征。
*   **实证**: 在 Robustness 实验 (RQ3) 中，即使移除有效的文本提示，系统仍能凭借该机制保持高精度的检索性能。

## 4. 评估体系: 参数空间的立体化评价标准
> **Evaluation Contribution: Multi-dimensional Metric Protocol**

*   **问题**: 缺乏衡量“参数生成质量”的公认标准。传统的 L2 Distance 无法反映“听感方向”的正确性。
*   **贡献**: 我们建立了一套针对参数化音频生成的 **立体化评估协议**：
    *   **Cosine Similarity**: 衡量参数调节方向的一致性（"Directional Fidelity"）。
    *   **Active Parameter Recall**: 衡量稀疏参数空间下的关键特征命中率（"Sparse Feature Activation"）。
*   **价值**: 这套指标体系补全了现有研究仅关注 L2 误差的不足，为后续 Neuro-Symbolic Audio 研究提供了更严谨的量化标准。
