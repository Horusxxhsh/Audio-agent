# 设计文档：论文写作风格和技术规范优化

## 上下文

本文档详细说明论文写作风格和技术规范优化的技术决策和方法。

**背景**：
- 论文在技术内容方面已经比较完整，但在写作风格和技术规范方面存在问题
- 这些问题影响论文的专业性和可读性，不符合顶级会议标准
- 需要进行系统性的改进，而不是零散的修改

**约束**：
- 不能改变论文的核心技术贡献和内容
- 必须保持学术严谨性和客观性
- 改进必须符合 ICLR、NeurIPS 等顶级会议的写作规范
- 与现有的 `paper-writing-enhancement` 变更互补，不冲突

**利益相关者**：
- 论文作者（需要高质量的论文发表）
- 审稿人（需要清晰、专业的论文）
- 读者（需要易于理解和阅读的论文）

## 目标 / 非目标

### 目标
- 提升论文的写作质量，达到顶级会议标准
- 改善论文的可读性和专业性
- 统一术语和格式，减少歧义
- 确保论文的完整性和规范性

### 非目标
- 改变论文的核心技术贡献
- 修改实验数据和结果
- 改变论文的叙事逻辑和论证深度（这是 `paper-writing-enhancement` 的目标）
- 增加新的技术内容或实验

## 决策

### 决策 1：将要点列表转换为流畅段落

**决策**：将论文中的所有要点列表（itemize/enumerate）转换为流畅的段落式叙述，除了 Methods 章节的材料列表。

**原因**：
- 学术写作规范要求使用流畅的散文，而非要点列表
- 要点列表适合用于计划阶段，不适合用于最终论文
- 段落式叙述更能展示逻辑流畅性和论证深度
- 顶级会议（ICLR、NeurIPS）的论文极少使用要点列表

**考虑的替代方案**：
- **保留要点列表**：优点是信息结构清晰；缺点是不符合学术写作规范，显得不够专业
- **部分转换为段落**：优点是工作量较小；缺点是不一致，影响整体效果

**选择理由**：完全转换为段落式叙述，符合学术写作规范，提升论文质量。

**实施方法**：
1. 识别所有 itemize 和 enumerate 环境
2. 将每个列表项转换为完整的句子
3. 使用过渡词（First, Second, Third, Moreover, However）连接句子
4. 确保逻辑流畅，信息完整

**示例**：

原文（itemize）：
```latex
\begin{itemize}
  \item \textbf{Parameter explosion}: a typical amplifier and effects chain involves 8--15 continuous parameters with non-linear interactions.
  \item \textbf{Semantic ambiguity}: descriptors such as ``breakup'' admit multiple valid interpretations across genres (smooth overdrive vs. harsh clipping vs. compressed saturation).
  \item \textbf{Lack of transferability}: a preset that works for one guitar--pedal--amp combination often fails for another.
\end{itemize}
```

修改后（段落）：
```latex
Navigating this challenge involves confronting three interrelated obstacles. First, a typical amplifier and effects chain involves 8--15 continuous parameters with non-linear interactions, creating a combinatorial explosion of possible configurations. Second, semantic descriptors such as ``breakup'' admit multiple valid interpretations across genres, ranging from smooth overdrive to harsh clipping or compressed saturation, making it difficult to translate perceptual intent into precise technical specifications. Third, presets exhibit limited transferability; a configuration that works for one guitar--pedal--amp combination often fails when applied to different equipment, necessitating time-consuming recalibration.
```

---

### 决策 2：统一术语和缩写定义

**决策**：在首次使用时明确定义所有缩写词，并在全文中使用一致的术语。

**原因**：
- 缩写词定义缺失会导致读者困惑
- 术语不一致会影响专业性和可读性
- 统一的术语有助于读者理解和记忆
- 符合学术写作规范

**考虑的替代方案**：
- **不定义缩写词**：优点是节省篇幅；缺点是影响可读性
- **在文末添加术语表**：优点是集中管理；缺点是读者需要来回翻阅

**选择理由**：在首次使用时定义，并在全文中使用一致的术语，符合学术写作规范，提升可读性。

**实施方法**：
1. 在 Abstract 开头定义 DAW、DSP、RAG
2. 在 Introduction 中定义 TRR、LLM
3. 全文统一使用 "Texture Resonance Retrieval (TRR)"、"Dual-Modal Retrieval"、"Vector-RAG"
4. 检查并修正不一致的术语使用

**示例**：

原文：
```latex
Despite the remarkable creative power of modern Digital Audio Workstations (DAWs), a persistent \textit{semantic gap} exists...
```

修改后：
```latex
Digital Audio Workstations (DAWs) provide unprecedented creative control in modern music production, yet a persistent \textit{semantic gap} exists between how musicians conceptually describe desired sounds and the technical parameters required to achieve them.
```

---

### 决策 3：减少被动语态使用

**决策**：将 Related Work 和 Method 章节的被动语态改为主动语态，适度使用主动语态。

**原因**：
- 被动语态过度使用会降低论文的可读性和生动性
- 主动语态更直接、更清晰
- 顶级会议的论文倾向于使用主动语态
- 适度使用主动语态可以增强论文的说服力

**考虑的替代方案**：
- **完全使用被动语态**：优点是显得客观；缺点是可读性差
- **完全使用主动语态**：优点是生动；缺点是可能显得主观

**选择理由**：适度使用主动语态，在保持客观性的同时提升可读性。

**实施方法**：
1. 识别全文中的被动语态（搜索 "was", "were", "is", "are" + 过去分词）
2. 判断是否需要改为主动语态
3. 将被动语态改为主动语态（使用 "We propose", "We demonstrate", "Our results show"）
4. 保持客观性，避免过度主观

**示例**：

原文：
```latex
The challenge of translating perceptual descriptions into technical parameters was formally characterized by \citet{stables2014semantic}.
```

修改后：
```latex
\citet{stables2014semantic} formally characterized the challenge of translating perceptual descriptions into technical parameters.
```

---

### 决策 4：完成系统架构图

**决策**：绘制清晰的系统架构图，展示 C++ DSP 客户端、Python 代理、桥接层三个组件及其交互。

**原因**：
- 红色占位符影响论文的完整性和专业性
- 系统架构图有助于读者理解系统设计
- 顶级会议的论文通常包含系统架构图
- 图表可以提升论文的可读性和说服力

**考虑的替代方案**：
- **移除图表引用**：优点是简单；缺点是失去重要信息
- **使用文本描述**：优点是无需绘图；缺点是不够直观

**选择理由**：绘制系统架构图，提升论文的完整性和可读性。

**实施方法**：
1. 使用绘图工具（如 draw.io、Inkscape、Lucidchart）创建架构图
2. 展示三个组件：C++ DSP 客户端、Python 代理、桥接层
3. 展示数据流向和通信机制
4. 保存为 PDF 或 PNG 格式（至少 300 DPI）
5. 移除红色占位符，引用图表

**图表设计要点**：
- 使用清晰的标签和箭头
- 使用一致的配色方案
- 确保文字可读（字体大小适中）
- 添加图表标题和说明

---

### 决策 5：添加统计信息到实验表格

**决策**：在所有实验结果表格中添加标准差或置信区间，为关键结果添加显著性检验标记。

**原因**：
- 缺少统计信息会影响实验结果的可信度
- 标准差或置信区间可以展示结果的稳定性
- 显著性检验可以证明改进的有效性
- 符合学术写作规范

**考虑的替代方案**：
- **不添加统计信息**：优点是简单；缺点是可信度低
- **只添加标准差**：优点是简单；缺点是信息不够全面

**选择理由**：添加标准差或置信区间，为关键结果添加显著性检验，提升实验结果的可信度。

**实施方法**：
1. 检查所有实验结果表格
2. 为每个数值添加标准差（使用 $\pm$ 符号）
3. 如果有多个样本，添加标准差
4. 如果是单次测量，说明局限性
5. 为关键结果添加显著性检验标记（*、**、***）
6. 在表格标题中说明标记含义

**示例**：

原文：
```latex
\begin{tabular}{lcccc}
\toprule
\textbf{Method} & \textbf{Param. Dist. (L2)} & \textbf{Acc@0.1} & \textbf{Cos} & \textbf{Active Recall} \\
\midrule
Zero-shot & 42.67 & 0.12 & 0.45 & 0.15 \\
Vector-RAG & 22.27 & 0.38 & 0.72 & 0.41 \\
\midrule
\textbf{Audio-Agent (Ours)} & \textbf{21.86} & \textbf{0.45} & \textbf{0.78} & \textbf{0.49} \\
\bottomrule
\end{tabular}
```

修改后：
```latex
\begin{tabular}{lcccc}
\toprule
\textbf{Method} & \textbf{Param. Dist. (L2)} & \textbf{Acc@0.1} & \textbf{Cos} & \textbf{Active Recall} \\
\midrule
Zero-shot & 42.67 $\pm$ 3.45 & 0.12 $\pm$ 0.03 & 0.45 $\pm$ 0.05 & 0.15 $\pm$ 0.04 \\
Vector-RAG & 22.27 $\pm$ 2.18 & 0.38 $\pm$ 0.06 & 0.72 $\pm$ 0.04 & 0.41 $\pm$ 0.05 \\
\midrule
\textbf{Audio-Agent (Ours)} & \textbf{21.86 $\pm$ 1.95*} & \textbf{0.45 $\pm$ 0.07*} & \textbf{0.78 $\pm$ 0.03**} & \textbf{0.49 $\pm$ 0.06*} \\
\bottomrule
\end{tabular}
```

**注意**：如果实验数据没有多次运行，无法计算标准差，应该在表格标题中说明这是单次运行的结果，并讨论其局限性。

---

### 决策 6：拆分过长句子

**决策**：将超过30词的句子拆分为多个短句，平均句子长度控制在15-20词。

**原因**：
- 过长的句子影响阅读流畅性
- 短句更容易理解和记忆
- 顶级会议的论文倾向于使用中等长度的句子
- 适度的句子长度变化可以提升阅读体验

**考虑的替代方案**：
- **保持长句**：优点是信息密度高；缺点是可读性差
- **使用过多的短句**：优点是简单；缺点是显得不连贯

**选择理由**：拆分过长句子，使用中等长度的句子，提升可读性。

**实施方法**：
1. 识别全文中超过30词的句子
2. 分析句子结构，找到合适的拆分点
3. 将长句拆分为2-3个短句
4. 使用连接词（and, but, however, therefore）保持逻辑流畅
5. 确保每个句子意思完整

**示例**：

原文：
```latex
We identify three root causes that make unconstrained, zero-shot parameter generation brittle in practice: (1) lack of grounding in concrete, previously validated presets; (2) sparse and biased training signals for niche sub-genres and production practices; and (3) non-linear parameter interactions that make local edits behave unintuitively.
```

修改后：
```latex
We identify three root causes that make unconstrained, zero-shot parameter generation brittle in practice. First, the lack of grounding in concrete, previously validated presets leads to unguided exploration of the parameter space. Second, sparse and biased training signals for niche sub-genres and production practices limit the model's ability to generalize to specialized use cases. Third, non-linear parameter interactions cause local edits to behave unintuitively, making it difficult to predict the effect of individual parameter adjustments.
```

---

### 决策 7：改进表格标题

**决策**：使所有表格标题更加简洁且信息丰富，添加必要的说明文字。

**原因**：
- 表格标题应该简洁明了，同时提供足够的信息
- 好的标题可以帮助读者快速理解表格内容
- 符合学术写作规范

**考虑的替代方案**：
- **保持原有标题**：优点是无需修改；缺点是不够清晰
- **使用冗长的标题**：优点是信息全面；缺点是过于冗长

**选择理由**：改进表格标题，使其简洁且信息丰富。

**实施方法**：
1. 检查所有表格标题
2. 评估标题的清晰度和信息量
3. 改进标题，使其更加简洁且信息丰富
4. 添加必要的说明文字

**示例**：

原文：
```latex
\caption{Hallucination in Zero-Shot LLM Parameter Generation (Range Violations)}
```

修改后：
```latex
\caption{Parameter range violations in zero-shot LLM generation. A violation occurs when a generated value falls outside the plugin-defined valid range.}
```

---

### 决策 8：添加公式解释

**决策**：在每个数学公式后添加对变量含义和公式物理意义的解释。

**原因**：
- 公式解释有助于读者理解公式的含义和作用
- 缺少解释会影响论文的可读性
- 符合学术写作规范

**考虑的替代方案**：
- **不添加解释**：优点是节省篇幅；缺点是影响可读性
- **在公式前添加解释**：优点是提前说明；缺点是可能打断阅读流畅性

**选择理由**：在公式后添加解释，帮助读者理解公式。

**实施方法**：
1. 识别所有数学公式
2. 为每个公式添加变量含义的解释
3. 说明公式的物理意义和作用
4. 确保解释简洁明了

**示例**：

原文：
```latex
\begin{equation}
\theta^* = \arg\min_{\theta \in \Theta} \mathcal{L}_{\text{semantic}}(f(\mathbf{x}, \theta), I) + \lambda \mathcal{L}_{\text{preference}}(\theta, \mathcal{H})
\end{equation}
```

修改后：
```latex
\begin{equation}
\theta^* = \arg\min_{\theta \in \Theta} \mathcal{L}_{\text{semantic}}(f(\mathbf{x}, \theta), I) + \lambda \mathcal{L}_{\text{preference}}(\theta, \mathcal{H})
\end{equation}
where $\mathcal{L}_{\text{semantic}}$ measures the perceptual alignment between the processed audio and the user's intent, and $\mathcal{L}_{\text{preference}}$ captures consistency with the user's historical preferences $\mathcal{H}$.
```

---

## 风险 / 权衡

| 风险 | 权衡 | 缓解措施 |
|------|------|----------|
| 工作量超预期 | 可能延期 | 按P0→P1优先级分阶段执行 |
| 与 paper-writing-enhancement 冲突 | 重复工作 | 两个变更互补，确保修改不重叠 |
| 篇幅增加过多 | 可能超限 | 保持简洁，避免冗余 |
| 风格改变影响审稿 | 未知 | 保持原有核心贡献，只改进表达方式 |
| 某个任务卡住 | 进度受阻 | 跳过，继续其他任务，记录问题 |

---

## 迁移计划

### 阶段 1：准备（0.5小时）
- 阅读 proposal.md，了解变更范围
- 阅读 tasks.md，了解任务清单
- 阅读 design.md，了解技术决策
- 备份原始论文文件

### 阶段 2：核心改进（10-12小时）
- 按顺序完成 P0 任务（Task 1-8）
- 每完成一个任务，更新 tasks.md 中的复选框
- 定期编译 LaTeX，确保无错误

### 阶段 3：次要改进（2-3小时）
- 完成 P1 任务（Task 9-12）
- 运行完整检查清单
- 最终验证

### 阶段 4：审查（0.5小时）
- 逐项检查验收标准
- 确认所有任务完成
- 准备提交

### 回滚计划
- 如果修改导致严重问题，可以从备份恢复
- 使用 Git 版本控制，可以随时回滚

---

## 待决问题

1. **统计信息来源**：实验数据是否有多次运行？如果没有，如何处理标准差？
   - 待确认：查看实验脚本和数据
   - 可能的解决方案：说明局限性，或补充实验

2. **架构图工具**：使用什么工具绘制系统架构图？
   - 待决定：draw.io、Inkscape、Lucidchart
   - 建议：使用 draw.io，免费且易用

3. **与 paper-writing-enhancement 的协调**：如何确保两个变更不冲突？
   - 待讨论：与 paper-writing-enhancement 的作者协调
   - 建议：定期同步进度，避免重复修改

4. **篇幅限制**：修改后是否会超过 ICLR 的篇幅限制？
   - 待检查：统计修改后的总页数
   - 可能的解决方案：使用 Appendix 存放补充材料

---

## 参考资料

- Scientific Writing 技能文档（`.iflow/skills/scientific-writing/`）
- ICLR 2025 会议投稿指南
- IEEE/ACM Transactions 写作规范
- 现有的写作审阅报告（本次审阅结果）
- 顶级期刊论文范文（ICLR、NeurIPS、TASLP）