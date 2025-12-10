# Audio-Agent 详细实验设计方案

## 1. 实验目标
验证 **Audio-Agent** 是否比现有基线模型更有效地弥合了自然语言描述与复杂 DSP 参数空间之间的语义鸿沟，并评估其“双模态 RAG”和“自适应记忆”机制对系统性能的具体贡献。

## 2. 数据集构建 ("Ground Truth")
由于通过文本描述生成插件链参数没有现成的公开数据集，我们将构建一个名为 **"GuitarTone-50"** 的专用数据集。

*   **规模**: 50 种独特的吉他音色风格（例如："80s Hair Metal", "Dreamy Shoegaze", "Dry Funk", "Modern Djent"）。
*   **数据采集协议**:
    1.  **专家标注**: 由专业混音师在不使用 AI 辅助的情况下，使用 Audio-Agent 插件手动调节出每种风格的“黄金参数 (Golden Parameters)”。
    2.  **多模态配对**:
        *   **文本**: 每种风格配备 5 个富含变化性的描述（例如："Heavy distortion with scooped mids" vs "High gain metal tone, no mid frequencies"）。
        *   **音频**: 标准化的干声吉他 DI (Direct Injection) 轨道，经过“黄金参数”处理后生成的*参考音频 ($A_{ref}$)*。
        *   **参数**: 插件的完整 JSON 状态（包括箱头设置、单块链、箱体 IR、后处理 FX）。
*   **总样本量**: 50 种风格 × 5 条提示词 = 250 对“文本-参数”配对数据。

## 3. 基线模型 (Baselines)

1.  **Baseline A: Direct LLM (Zero-shot)**
    *   *方法*: 将描述 JSON 结构的系统提示词和用户文本提示词直接输入 GPT-4/DeepSeek。
    *   *假设*: 缺乏领域特定的“旋钮调节”直觉，可能会产生“幻觉”数值或生成通用的“安全”设置。

2.  **Baseline B: Text-Only RAG**
    *   *方法*: 仅基于文本嵌入 (OpenAI `text-embedding-3-small`) 的余弦相似度检索 Top-k 参数预设。
    *   *假设*: 对明确的风格名称表现良好，但对于抽象的声学描述（如 "warm", "punchy"）效果不佳，因为这些描述的文本差异可能很大。

3.  **Audio-Agent (Ours)**
    *   *方法*: 双模态 RAG (文本 + 音频嵌入) + 思维链 (CoT) 推理。

## 4. 评估指标 (Evaluation Metrics)

### 4.1 客观指标 (Objective Metrics)

*   **参数空间距离 (Normalized Parameter Distance)**:
    由于不同参数量纲不同（如频率 20-20k vs 增益 0-10），我们将所有参数归一化到 $[0, 1]$ 区间。
    $$ \mathcal{L}_{param} = \frac{1}{N} \sum ||\hat{\theta} - \theta_{GT}||_2 $$
    *注: 这是一个严格的指标。低分代表这就好，但高分不一定代表“声音不好”（存在多解性问题）。*

*   **音频特征距离 (Fréchet Audio Distance - FAD)**:
    使用预测参数 ($\hat{\theta}$) 生成音频，并与参考音频 ($A_{ref}$) 比较统计特征分布。
    *   FAD 越低，表示生成的音频听感越接近目标风格分布。

*   **检索召回率 (Retrieval Recall@k)**:
    正确风格的“Ground Truth”预设出现在 Top-k 检索结果中的比例。

### 4.2 主观听测 (Subjective Evaluation / MUSHRA)

*   **受试者**: 20 位评估者（10 位专业混音师 + 10 位吉他手）。
*   **盲测流程**: 试听以下样本：
    1.  **Reference**: “黄金音色”（专家制作）。
    2.  **Anchor**: 随机预设（低锚点）。
    3.  **Samples**: Baseline A, Baseline B, 和 Audio-Agent 的生成结果（盲测）。
*   **评分维度 (1-5 Likert Scale)**:
    1.  **语义保真度 (Semantic Fidelity)**: “声音是否符合‘梦幻自赏 (Dreamy Shoegaze)’的描述？”
    2.  **音质 (Sound Quality)**: “失真是否悦耳？是否存在怪异的数字伪影？”
    3.  **可编辑性 (Editability)**: (仅限混音师) “查看生成的参数，作为起步点是否合理？”

## 5. 实施路线图

### 第一阶段：数据策展 (Week 1)
*   [ ] 定义 50 种目标风格列表。
*   [ ] 录制/获取干声 DI 样本（清音电吉他）。
*   [ ] 工程师制作 50 个“黄金预设”并保存为 JSON。
*   [ ] 生成 `knowledge_base.json` (文本 + 音频向量数据库)。

### 第二阶段：RAG 与推理管道 (Week 2)
*   [ ] 实现 `rag_system.py` 双编码器检索。
*   [ ] 优化 LLM Prompt 以确保 JSON 格式合规。
*   [ ] 对 250 个评估提示词进行批量推理。

### 第三阶段：评估 (Week 3)
*   [ ] 编写计算客观指标的 Python 脚本。
*   [ ] 搭建简单的 MUSHRA 听测 Web 界面。
*   [ ] 收集并分析人工反馈数据。

## 6. 消融实验 (Ablation Studies)
*   **w/o Audio Branch**: 量化从“通过音频听感检索”获得的知识量，对比仅“通过文本标签检索”。
*   **w/o CoT**: 量化“推理 (Reasoning)”步骤相对于直接输出检索到的参数块的优势。
