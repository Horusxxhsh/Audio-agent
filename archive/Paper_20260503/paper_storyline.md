# 论文故事线：Audio-Agent (顶级计算机期刊版)

## 目标期刊

**IEEE TASLP** (Transactions on Audio, Speech, and Language Processing) 或 **ACM TOMM** (Transactions on Multimedia)
*特点：强调理论深度、系统性的数学建模、以及详尽的实验分析（消融实验 + 主观听测）。*

## 标题 (Drafts)

1. **Bridging the Semantic Gap in Neural Audio Effects: A Neuro-Symbolic Framework with Retrieval-Augmented Generation**
    * *强调神经符号 (Neuro-Symbolic) 和语义鸿沟 (Semantic Gap)。*
2. **Audio-Agent: Interactive Timber Exploration via Large Language Models and Adaptive Preference Learning**
    * *强调交互性 (Interactive) 和自适应学习 (Adaptive)。*

---

## 1. 引言 (Introduction) - *约 1.5 页*

### 1.1 背景与挑战

- **参数空间的维度灾难**：现代 DSP 链（Compressor, EQ, Distortion 等）拥有高维、非线性的参数空间。
* **语义鸿沟 (The Semantic Gap)**：
  * **底层信号层**：数值参数 (e.g., Threshold: -20dB, Attack: 10ms)。
  * **高层感知层**：自然语言描述 (e.g., "Warm", "Punchy", "Dreamy Post-rock")。
  * *核心矛盾*：音乐家使用感知层语言，但工具只接受信号层输入。
* **由生成式 AI 带来的新问题**：
  * 端到端生成模型 (AudioLDM, MusicLM) 生成的音频不可编辑 (Non-editable)，无法集成到专业制作流程 (DAW) 中。
  * 现有的参数推断模型 (Parameter Inference) 往往是黑盒，且缺乏对“风格”的少样本泛化能力。

### 1.2 本文方法 (Overview)

- 我们提出了 **Audio-Agent**，一个**神经符号 (Neuro-Symbolic)** 系统。
* **符号层**：使用标准的 C++ DSP 算法，保证音质和可解释性。
* **神经层**：使用 LLM 作为推理核心，通过 RAG (Retrieval-Augmented Generation) 建立“语义-参数”映射。
* **核心贡献**：
    1. **双模态 RAG 机制**：结合文本（风格描述）和音频（声学特征）的检索增强，解决 LLM 在连续参数空间的“幻觉”问题。
    2. **自适应记忆回路 (Adaptive Memory Loop)**：一种基于用户反馈 (Accept/Edit/Reject) 的在线学习机制，使系统能个性化地收敛到用户的审美偏好。
    3. **可解释的 DSP 控制协议**：定义了一套通用的效果器参数 JSON 协议，实现了自然语言到底层信号处理的透明转换。

---

## 2. 相关工作 (Related Work)

- **智能音乐制作 (Intelligent Music Production, IMP)**：自动混音、EQ 匹配技术。*本工作区别：关注创造性的音色设计 (Timbre Design) 而非单纯的工程平衡。*
* **可微数字信号处理 (Differentiable DSP, DDSP)**：DDSP 及其变体。*本工作区别：不需要重新训练特定模型，直接利用预训练 LLM 的通用知识推理。*
* **基于提示的音频生成 (Prompt-to-Audio)**：AudioGen 等。*本工作区别：生成的是“控制信号”而非“波形”，保留了专业工作流的可编辑性。*

---

## 3. 问题形式化 (Problem Formulation) - *约 1 页*

*期刊论文需要明确的数学定义。*

定义效果器链函数 $f(\mathbf{x}, \theta)$，其中 $\mathbf{x}$ 是输入音频，$\theta \in \mathbb{R}^d$ 是 $d$ 维参数空间。
用户的意图由两部分组成：$I = \{T, A_{ref}\}$，其中 $T$ 是文本描述，$A_{ref}$ 是参考音频（可选）。
我们的目标是学习映射 $\mathcal{M}: I \rightarrow \theta^*$，使得感知距离 $D_{perceptual}(f(\mathbf{x}, \theta^*), \text{Target}) \rightarrow 0$。

由于直接训练 $\mathcal{M}$ 需要海量配对数据，我们将问题分解为**检索 (Retrieve)** 与 **推理 (Reason)** 两步：
$$ \theta^* = \text{LLM}(T, \text{RAG}(T, A_{ref}), \text{History}) $$

---

## 4. 系统架构与方法 (Methodology) - *约 3-4 页*

### 4.1 混合架构 (Hybrid Architecture)

- **C++ Client (JUCE)**: 负责实时音频处理、特征提取 (MFCC/Spectral)、UI 交互。
* **Python Agent**: 负责 RAG 检索、LLM 推理、向量数据库管理。

### 4.2 双模态知识检索 (Dual-Modal RAG)

*对应代码：`rag_system.py`*
* **知识库构建**：
  * $\mathcal{K}_{text}$：风格描述数据库（如 "Shoegaze: heavy reverb, fuzz distortion"）。
  * $\mathcal{K}_{audio}$：参数预设库，附带对应音频的 Wav2Vec2 嵌入向量。
* **检索算法**：
  * 输入查询 $q$，计算混合相似度分数：
    $$ S(q, d_i) = \alpha \cdot \text{Sim}_{cos}(\mathbf{e}_{text}(q), \mathbf{e}_{text}(d_i)) + \beta \cdot \text{Sim}_{cos}(\mathbf{e}_{audio}(q), \mathbf{e}_{audio}(d_i)) $$
  * 返回 Top-$k$ 个参数预设 $\{\theta_1, ..., \theta_k\}$ 作为上下文 (In-Context Learning Examples)。

### 4.3 提示工程与参数推理 (Prompting & Inference)

*对应代码：`llm.py`*
* **Chain-of-Thought (CoT)** 设计：
    1. **Decomposition**: 将文本解析为 `Tags` (e.g., [post-rock, ambient]), `Texture` (e.g., [shimmering, wide]), `Technique` (e.g., [tremolo picking]).
    2. **Mapping**: 根据 Tags 检索到的 Range 约束参数（例如 `Ambient` 意味着 `Reverb.size` $\in [0.7, 0.9]$）。
    3. **Refinement**: 根据 $A_{ref}$ 的听感微调数值。

### 4.4 自适应偏好学习 (Adaptive Preference Learning)

- **记忆更新规则**：
  * 用户反馈 $r \in \{+1, 0, -1\}$ (Accept/Edit/Reject)。
  * 对于 Accept 的样本，更新向量库及其权重，使其在后续检索中优先级更高。
  * 公式化描述长期记忆的权重衰减与强化机制。

---

## 5. 实验 (Experiments) - *约 3 页*

### 5.1 实验设置

- **数据集**：构建包含 50 种不同吉他音色风格（涵盖 Jazz, Metal, Ambient 等）的 "Text-Parameter" 配对数据集作为 Ground Truth。
* **基线模型 (Baselines)**：
    1. None-RAG LLM (直接问 GPT-4/DeepSeek)。
    2. Static Retrieval (传统关键词匹配)。
    3. Audio-Agent (Ours)。

### 5.2 客观评测 (Objective Metrics)

1. **参数一致性 (Parameter Consistency)**：输入语义相似的 Prompt，计算生成参数的方差（越低越稳定）。
2. **覆盖率 (Coverage)**：生成的参数在有效参数空间内的分布情况。
3. **检索准确率 (Retrieval Accuracy)**：RAG 模块检索到正确风格预设的 Top-k 准确率。

### 5.3 主观听测 (Subjective Evaluation / MOS Test)

*期刊论文的核心部分。*
* **任务**：邀请 20 位专业音乐制作人/吉他手。
* **流程**：播放生成的音频，针对以下指标打分 (1-5)：
  * **语义相关性 (Semantic Relevance)**：声音是否符合文本描述？
  * **音质 (Sound Quality)**：是否有数字失真或不自然的参数突变？
  * **可编辑性 (Editability)**：生成的参数是否便于后续微调？
* **结果分析**：对比 Audio-Agent 与基线模型在 MOS 分数上的显著性差异 (t-test)。

### 5.4 消融实验 (Ablation Study)

- **w/o Audio RAG**: 仅使用文本检索，观察对“音色细节”捕捉能力的下降。
* **w/o Memory**: 去除记忆模块，观察系统在多轮交互中是否无法收敛到用户偏好。

---

## 6. 讨论与结论 (Discussion & Conclusion)

- **优势**：解决了由自然语言到复杂 DSP 参数的映射难题，保留了专业工作流。
* **局限性**：依赖于 LLM 的推理能力，推理延迟目前还无法做到“实时调制 (Real-time Modulation)”。
* **未来工作**：引入轻量级模型实现端侧部署；扩展到更多种类的效果器（如合成器）。

---
