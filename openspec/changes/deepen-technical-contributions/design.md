# 设计文档：深化技术贡献描述

## 上下文

本文档详细说明技术贡献深化的技术决策和方法。

**背景**：
- 当前论文技术内容完整，但描述相对简洁
- 期刊投稿需要更详细的技术描述和更多的图表
- 需要添加伪代码、流程图、示意图等来支撑技术贡献
- 用户将自行绘制图表，我负责提供占位符和详细说明

**约束**：
- 不能改变论文的核心技术贡献
- 必须保持学术严谨性和客观性
- 必须符合目标期刊的投稿要求
- 图表使用占位符，用户后续绘制

**利益相关者**：
- 论文作者（需要高质量的期刊论文）
- 审稿人（需要详细的技术描述以便评估）
- 读者（需要详细的技术描述以便理解和复现）

## 目标 / 非目标

### 目标
- 深化技术贡献的描述，使其符合期刊标准
- 添加伪代码，便于理解和复现
- 添加图表占位符，支撑技术贡献
- 扩展理论分析，提升论文深度
- 添加案例研究，展示方法有效性

### 非目标
- 改变论文的核心技术贡献
- 修改实验数据和结果
- 绘制实际的图表（用户负责）
- 改变论文的叙事逻辑（这是 `paper-writing-enhancement` 的目标）

## 决策

### 决策 1：添加详细的算法伪代码

**决策**：为每个主要算法添加详细的伪代码，包含输入、输出、步骤和复杂度分析。

**原因**：
- 伪代码可以帮助读者理解算法
- 伪代码便于复现和实现
- 期刊论文通常包含伪代码
- 伪代码可以展示算法的细节

**考虑的替代方案**：
- **不添加伪代码**：优点是节省篇幅；缺点是影响可读性和复现性
- **只添加关键算法的伪代码**：优点是工作量小；缺点是不够全面

**选择理由**：为每个主要算法添加详细的伪代码，符合期刊标准，提升论文质量。

**实施方法**：
1. 识别所有主要算法（TRR、双模态检索、参数生成等）
2. 为每个算法编写伪代码
3. 使用 algorithm 环境
4. 包含输入、输出、步骤
5. 添加复杂度分析

**示例**：

```latex
\begin{algorithm}[t]
\caption{Texture Resonance Encoding (TRR)}
\label{alg:trr_encoding}
\begin{algorithmic}
\REQUIRE Frame-level features $\mathbf{H} \in \mathbb{R}^{C \times T}$
\ENSURE Normalized Gram matrix $\mathbf{G}_{\text{norm}} \in \mathbb{R}^{C \times C}$

\STATE $\mathbf{G} \leftarrow \frac{1}{T} \mathbf{H}\mathbf{H}^\top$
\STATE $\mathbf{G}_{\text{norm}} \leftarrow \mathbf{G} / \|\mathbf{G}\|_F$
\RETURN $\mathbf{G}_{\text{norm}}$
\end{algorithmic}
\end{algorithm}
```

---

### 决策 2：添加图表占位符

**决策**：为所有需要的图表添加占位符，用户后续绘制。

**原因**：
- 图表可以直观地展示技术贡献
- 用户希望自行绘制图表
- 占位符可以确保论文结构完整
- 占位符可以提供清晰的绘制说明

**考虑的替代方案**：
- **不添加占位符**：优点是简单；缺点是影响论文完整性
- **使用简单文本描述**：优点是无占位符；缺点是不够直观

**选择理由**：添加占位符，确保论文结构完整，提供清晰的绘制说明。

**实施方法**：
1. 识别所有需要的图表（架构图、流程图、示意图等）
2. 为每个图表创建占位符
3. 使用 `\includegraphics` 命令，但注释掉
4. 添加详细的图表说明
5. 使用红色文字标注占位符

**示例**：

```latex
\begin{figure}[h]
\centering
%\includegraphics[width=0.9\textwidth]{figures/trr_feature_extraction.pdf}
\textcolor{red}{[Figure: TRR Feature Extraction Flow. This figure illustrates the complete process of extracting Texture Resonance features from audio input, including: (1) audio preprocessing at 16kHz, (2) Wav2Vec2 feature extraction from layer 9, (3) Gram matrix computation, (4) spectral normalization. The flow should show the data transformation at each step with clear labels.]}
\caption{Texture Resonance feature extraction pipeline. The process starts with audio preprocessing, extracts frame-level features using Wav2Vec2, computes the Gram matrix to capture second-order statistics, and applies spectral normalization for scale invariance.}
\label{fig:trr_pipeline}
\end{figure}
```

---

### 决策 3：扩展理论分析

**决策**：为每个主要方法添加理论分析，包括数学推导、理论保证和复杂度分析。

**原因**：
- 理论分析可以提升论文深度
- 期刊论文通常包含理论分析
- 理论分析可以支撑方法的有效性
- 理论分析可以展示方法的创新性

**考虑的替代方案**：
- **不添加理论分析**：优点是简单；缺点是深度不足
- **只添加简单的理论分析**：优点是工作量小；缺点是不够深入

**选择理由**：为每个主要方法添加详细的理论分析，符合期刊标准，提升论文深度。

**实施方法**：
1. 识别每个主要方法
2. 为每个方法添加理论分析
3. 包含数学推导
4. 包含理论保证（如果适用）
5. 包含复杂度分析

**示例**：

```latex
\subsection{Theoretical Analysis of TRR}

We provide a theoretical justification for the effectiveness of Texture Resonance Retrieval.

\textbf{Time-Invariance Property}. Since TRR aggregates feature correlations across time through the Gram matrix computation $\mathbf{G} = \frac{1}{T}\mathbf{H}\mathbf{H}^\top$, the representation is approximately invariant to temporal shifts. Formally, for any time-shifted feature matrix $\mathbf{H}'$ obtained by circularly shifting $\mathbf{H}$ by $\tau$ time steps, we have $\|\mathbf{G} - \mathbf{G}'\|_F \approx 0$ when $T \gg \tau$.

\textbf{Scale-Invariance Property}. The spectral normalization step $\mathbf{G}_{\text{norm}} = \mathbf{G} / \|\mathbf{G}\|_F$ ensures that the representation is invariant to global energy scaling. For any scaling factor $\alpha > 0$, we have $\text{TRR}(\alpha \mathbf{H}) = \text{TRR}(\mathbf{H})$.

\textbf{Complexity Analysis}. Computing the Gram matrix requires $\mathcal{O}(C^2 T)$ time and $\mathcal{O}(C^2)$ memory, where $C$ is the feature dimension and $T$ is the number of time frames. In practice, we cache TRR embeddings for database items, making retrieval efficient.
```

---

### 决策 4：添加详细的案例研究

**决策**：为多个案例添加详细的分析，包括参数对比表、特征可视化和检索结果对比。

**原因**：
- 案例研究可以展示方法的有效性
- 详细的案例研究可以提供深入的理解
- 期刊论文通常包含详细的案例研究
- 案例研究可以支撑方法的实用性

**考虑的替代方案**：
- **不添加案例研究**：优点是简单；缺点是缺乏实证支持
- **只添加简单的案例研究**：优点是工作量小；缺点是不够详细

**选择理由**：为多个案例添加详细的分析，符合期刊标准，提升论文质量。

**实施方法**：
1. 选择代表性案例（Stadium Rock, Tweed Breakup, Punk Rock Raw）
2. 为每个案例添加参数对比表
3. 为每个案例添加特征可视化占位符
4. 为每个案例添加检索结果对比图占位符
5. 为每个案例添加详细分析

**示例**：

```latex
\subsubsection{Case Study: Stadium Rock}

\paragraph{Ground Truth.} The "Stadium Rock" preset is characterized by a bright, clean tone with pronounced high-mid presence (centered around 2.5 kHz), achieved through subtle EQ adjustments and light compression.

\paragraph{Retrieval Results.} Table \ref{tab:stadium_rock_retrieval} shows the top-3 retrieved presets using different methods.

\begin{table}[h]
\centering
\caption{Retrieval results for "Stadium Rock" query}
\label{tab:stadium_rock_retrieval}
\begin{tabular}{llcc}
\toprule
\textbf{Method} & \textbf{Retrieved Preset} & \textbf{Similarity} & \textbf{Parameter Distance} \\
\midrule
Vector-RAG & Funk Clean & 0.82 & 18.51 \\
Vector-RAG & Jazz Clean & 0.78 & 22.34 \\
Vector-RAG & Pop Clean & 0.75 & 25.12 \\
\midrule
TRR (Ours) & Arena Rock & 0.89 & 8.01 \\
TRR (Ours) & Stadium Rock (exact) & 0.95 & 0.00 \\
TRR (Ours) & Live Rock & 0.86 & 10.23 \\
\bottomrule
\end{tabular}
\end{table}

\paragraph{Analysis.} Vector-RAG retrieves broadly similar clean tones (Funk Clean, Jazz Clean) that match overall brightness but miss the specific "stadium" presence profile. In contrast, TRR retrieves presets that preserve the co-activation patterns in upper-mid frequency channels, yielding a closer reference neighborhood.

\paragraph{Visualization.} Figure \ref{fig:stadium_rock_features} visualizes the feature representations of the ground truth and retrieved presets.

\begin{figure}[h]
\centering
%\includegraphics[width=0.9\textwidth]{figures/stadium_rock_features.pdf}
\textcolor{red}{[Figure: Feature visualization for Stadium Rock case study. This figure should show: (1) t-SNE visualization of feature embeddings, (2) TRR Gram matrix heatmaps for ground truth and retrieved presets, (3) Parameter radar charts comparing ground truth and retrieved presets. Include legend and axis labels.]}
\caption{Feature visualization for Stadium Rock case study. The t-SNE plot shows clustering of similar presets, Gram matrix heatmaps reveal co-activation patterns, and radar charts compare parameter configurations.}
\label{fig:stadium_rock_features}
\end{figure}
```

---

### 决策 5：添加附录

**决策**：创建附录，包含详细的算法伪代码、实验参数、额外实验结果等补充材料。

**原因**：
- 附录可以存放补充材料，不影响正文篇幅
- 期刊论文通常包含附录
- 附录可以提供更多细节
- 附录可以提升论文的完整性

**考虑的替代方案**：
- **不添加附录**：优点是简单；缺点是补充材料无处存放
- **将补充材料放在正文中**：优点是无需附录；缺点是影响正文篇幅

**选择理由**：创建附录，存放补充材料，符合期刊标准。

**实施方法**：
1. 创建附录章节
2. 添加详细的算法伪代码
3. 添加实验参数表
4. 添加额外实验结果
5. 添加代码片段示例
6. 添加数据集详细说明

**示例**：

```latex
\appendix

\section{Additional Algorithm Details}

\subsection{Complete TRR Algorithm}

\begin{algorithm}[t]
\caption{Complete Texture Resonance Retrieval Algorithm}
\label{alg:trr_complete}
\begin{algorithmic}
\REQUIRE Audio sample $a$, sample rate $sr=16000$, window size $w=25$ms, hop size $h=10$ms
\ENSURE TRR embedding $\mathbf{G}_{\text{norm}} \in \mathbb{R}^{768 \times 768}$

\STATE Preprocess audio: resample to 16kHz, normalize to [-1, 1]
\STATE Extract frame-level features: $\mathbf{H} \leftarrow \text{Wav2Vec2}_{\text{layer 9}}(a)$
\STATE Compute Gram matrix: $\mathbf{G} \leftarrow \frac{1}{T} \mathbf{H}\mathbf{H}^\top$
\STATE Normalize: $\mathbf{G}_{\text{norm}} \leftarrow \mathbf{G} / \|\mathbf{G}\|_F$
\RETURN $\mathbf{G}_{\text{norm}}$
\end{algorithmic}
\end{algorithm}

\section{Experimental Parameters}

Table \ref{tab:hyperparameters} lists all hyperparameters used in our experiments.

\begin{table}[h]
\centering
\caption{Hyperparameters used in experiments}
\label{tab:hyperparameters}
\begin{tabular}{llc}
\toprule
\textbf{Parameter} & \textbf{Value} & \textbf{Description} \\
\midrule
Sample rate & 16 kHz & Audio preprocessing sample rate \\
Window size & 25 ms & STFT window size \\
Hop size & 10 ms & STFT hop size \\
Wav2Vec2 layer & 9 & Feature extraction layer \\
Feature dimension & 768 & Wav2Vec2 feature dimension \\
Retrieval top-K & 5 & Number of retrieved candidates \\
Fusion weight $\alpha$ & 0.5 & Text-audio fusion weight \\
\bottomrule
\end{tabular}
\end{table}
```

---

## 风险 / 权衡

| 风险 | 权衡 | 缓解措施 |
|------|------|----------|
| 工作量超预期 | 可能延期 | 按P0→P1优先级分阶段执行 |
| 篇幅超限 | 需要删减 | 使用 Appendix 存放补充材料 |
| 图表绘制困难 | 影响进度 | 使用占位符，用户后续绘制 |
| 与其他变更冲突 | 重复工作 | 定期同步，确保修改不重叠 |

---

## 迁移计划

### 阶段 1：准备（0.5小时）
- 阅读 proposal.md，了解变更范围
- 阅读 tasks.md，了解任务清单
- 阅读 design.md，了解技术决策
- 备份原始论文文件

### 阶段 2：核心改进（15-20小时）
- 按顺序完成 P0 任务（Task 1-8）
- 每完成一个任务，更新 tasks.md 中的复选框
- 定期编译 LaTeX，确保无错误

### 阶段 3：次要改进（5-10小时）
- 完成 P1 任务（Task 9-12）
- 运行完整检查清单
- 最终验证

### 阶段 4：准备图表绘制（1小时）
- 列出所有需要绘制的图表
- 为每个图表提供详细说明
- 创建图表绘制清单

### 回滚计划
- 如果修改导致严重问题，可以从备份恢复
- 使用 Git 版本控制，可以随时回滚

---

## 待决问题

1. **目标期刊**：具体投哪个期刊？
   - 待决定：IEEE Transactions on Audio, Speech, and Language Processing? ACM Transactions on Multimedia Computing?
   - 影响：篇幅限制、格式要求

2. **图表绘制工具**：用户使用什么工具绘制图表？
   - 待决定：draw.io、Inkscape、Python (matplotlib)、MATLAB？
   - 影响：占位符的格式和说明

3. **附录篇幅**：附录是否有篇幅限制？
   - 待确认：查看期刊投稿指南
   - 可能的解决方案：使用在线补充材料

4. **伪代码详细程度**：伪代码需要多详细？
   - 待讨论：与作者协调
   - 建议：包含关键步骤，但不必过于详细

---

## 参考资料

- 目标期刊的投稿指南
- IEEE/ACM Transactions 论文范文
- 现有的实验数据和代码
- 技术审阅报告