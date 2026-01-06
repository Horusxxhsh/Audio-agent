# 图表绘制清单

## 说明

本文档列出了论文中所有需要绘制的图表，包括已有的占位符和新添加的图表。每个图表都提供了详细的内容说明，指导图表绘制工作。

## 已有占位符图表（14 个）

### Figure 1: System Architecture
- **位置**: Section 5.1
- **标签**: `figures/system_architecture.pdf`
- **内容**: 展示 C++ DSP 客户端、Python RAG 代理和双向通信流的完整系统架构
- **说明**:
  - 顶部：用户界面（DAW/插件界面）
  - 中部：Python 代理（左侧：文本检索，右侧：音频检索，中央：融合模块）
  - 底部：C++ 客户端（DSP 引擎、音频 I/O）
  - 使用箭头表示数据流和通信方向
  - 标注关键组件：WebSocket 连接、知识库、推理模块

### Figure 2: C++ Client Detailed Architecture
- **位置**: Section 5.1
- **标签**: `figures/cpp_client_architecture.pdf`
- **内容**: 展示基于 JUCE 的 C++ 客户端的内部架构
- **说明**:
  - 顶部：音频 I/O 层（输入/输出缓冲区）
  - 中部左侧：实时 DSP 处理线程（效果链：EQ → 压缩器 → 失真 → 混响）
  - 中部右侧：后台参数更新线程（无锁队列、参数插值）
  - 底部：WebSocket 服务器（端口 8765，JSON 消息解析器和验证器）
  - 用虚线表示线程边界
  - 包含缓冲区大小（如 512 个样本）、线程优先级（REALTIME_PRIORITY）和通信机制的注释

### Figure 3: Python Agent Detailed Architecture
- **位置**: Section 5.1
- **标签**: `figures/python_agent_architecture.pdf`
- **内容**: 展示 Python RAG 代理的内部架构
- **说明**:
  - 顶部：接受文本描述和音频引用的查询接口
  - 左分支：文本知识库 $\mathcal{K}_{\text{text}}$（SBERT 嵌入、语义图）
  - 右分支：音频知识库 $\mathcal{K}_{\text{audio}}$（Wav2Vec2 特征、TRR Gram 矩阵）
  - 中央：双模态检索引擎（不确定性估计、融合）
  - 左下：LLM 推理模块（提示格式化、结构化输出解析）
  - 右下：约束验证器和修复模块
  - 输出：通过 WebSocket 发送到 C++ 客户端的有效参数向量
  - 使用颜色编码：蓝色（文本路径）、橙色（音频路径）、绿色（LLM 推理）、红色（约束验证）

### Figure 4: Data Flow and Control Flow
- **位置**: Section 5.1
- **标签**: `figures/data_control_flow.pdf`
- **内容**: 展示完整的端到端数据流和控制流
- **说明**:
  - 顶部：用户提供文本描述（"warm vintage breakup"）和可选的音频引用
  - 流分为两个并行路径：
    - 文本编码（SBERT）→ 从 $\mathcal{K}_{\text{text}}$ 的文本检索
    - 音频编码（Wav2Vec2 + TRR）→ 从 $\mathcal{K}_{\text{audio}}$ 的音频检索
  - 路径在融合模块汇合（不确定性权重）
  - 检索的上下文 + 查询 → LLM 提示格式化
  - LLM 生成原始参数
  - 约束验证检查范围和依赖约束
  - 如果存在违规，修复模块修复它们
  - 有效参数通过 WebSocket 发送到 C++ 客户端
  - C++ 客户端插值参数并应用到 DSP 链
  - 处理后的音频输出
  - 使用实线箭头表示数据流，虚线箭头表示控制流
  - 包含时序注释（哪些步骤是同步的 vs. 异步的）

### Figure 7: TRR Feature Extraction Pipeline
- **位置**: Section 5.4.2
- **标签**: `figures/trr_feature_extraction.pdf`
- **内容**: 展示从音频输入到 TRR 特征的完整流程
- **说明**:
  - (1) 16kHz 采样率的输入音频波形
  - (2) 从 Wav2Vec2 第 9 层提取特征，产生 $\mathbf{H} \in \mathbb{R}^{768 \times T}$
  - (3) Gram 矩阵计算 $\mathbf{G} = \frac{1}{T}\mathbf{H}\mathbf{H}^\top$
  - (4) 谱归一化以产生 $\mathbf{G}_{\text{norm}}$
  - 在每个阶段显示数据维度
  - 使用箭头指示流程
  - 包含示例 Gram 矩阵的热图可视化以说明二阶结构

### Figure 8: Gram Matrix Computation
- **位置**: Section 5.4.2
- **标签**: `figures/gram_matrix_computation.pdf`
- **内容**: 展示 Gram 矩阵计算的可视化
- **说明**:
  - (1) 将特征矩阵 $\mathbf{H}$ 显示为 2D 热图（$C \times T$）
  - (2) 矩阵乘法 $\mathbf{H}\mathbf{H}^\top$，带有显示操作的箭头
  - (3) 结果 Gram 矩阵 $\mathbf{G}$ 显示为对称的 $C \times C$ 热图
  - 使用颜色编码显示不同特征通道之间的关联是如何被捕获的
  - 包含注释说明对角线元素捕获通道方差，而非对角线元素捕获共激活模式

### Figure 10: TRR vs. Mean Pooling
- **位置**: Section 5.4.3
- **标签**: `figures/trr_vs_mean_pooling.pdf`
- **内容**: 对比平均池化和纹理共振检索
- **说明**:
  - 为两个音频样本展示并排对比：
    - (1) 持续失真音色
    - (2) 调制合唱音色
  - 对每个样本，显示：
    - (a) 波形
    - (b) 平均池化嵌入作为显示平均通道激活的柱状图
    - (c) TRR Gram 矩阵作为热图
  - 高亮显示两个样本有相似的平均池化嵌入（相似的柱状高度）但明显不同的 Gram 矩阵（不同的相关模式）
  - 使用注释指出共激活结构中的关键差异

### Figure 11: Dual-Modal Retrieval Flow
- **位置**: Section 5.5.2
- **标签**: `figures/dual_modal_retrieval.pdf`
- **内容**: 展示完整的双模态检索流程
- **说明**:
  - (1) 左分支：文本描述 → SBERT 编码 → 从 $\mathcal{K}_{\text{text}}$ 的文本检索 → 带不确定性 $u_{\text{text}}$ 的前 K 个文本结果
  - (2) 右分支：音频引用 → Wav2Vec2 + TRR 编码 → 从 $\mathcal{K}_{\text{audio}}$ 的音频检索 → 带不确定性 $u_{\text{audio}}$ 的前 K 个音频结果
  - (3) 中央：不确定性感知权重计算（$w_{\text{text}}, w_{\text{audio}}$）
  - (4) 底部：通过加权分数组合融合模块，产生最终前 K 个结果
  - 为文本（蓝色）和音频（橙色）路径使用颜色编码
  - 使用箭头显示数据流

### Figure 12: Modality Fusion Mechanism
- **位置**: Section 5.5.2
- **标签**: `figures/modality_fusion.pdf`
- **内容**: 展示模态融合机制
- **说明**:
  - (1) 顶部：文本和音频检索结果的相似度分布，可视化为直方图或柱状图
  - (2) 中部：不确定性计算，显示如何从相似度分布计算熵，并注释显示高不确定性（平坦分布）vs. 低不确定性（尖峰分布）
  - (3) 底部：使用指数衰减 $w = \exp(-\beta \cdot u)$ 的权重计算，带有显示不确定性如何映射到权重的曲线
  - 包含具体示例，显示模糊文本（高 $u_{\text{text}}$，低 $w_{\text{text}}$）被降权，而自信音频（低 $u_{\text{audio}}$，高 $w_{\text{audio}}$）主导融合

### Figure 13: Constraint Satisfaction
- **位置**: Section 5.6.3
- **标签**: `figures/constraint_satisfaction.pdf`
- **内容**: 展示约束检查和修复过程
- **说明**:
  - (1) 顶部：LLM 生成原始参数，显示为参数向量，其中一些值以红色高亮显示（违规）
  - (2) 中部：约束验证，显示范围检查（最小/最大边界）和依赖检查（如 attack < release），带有指向违规的箭头
  - (3) 底部：修复过程，显示通过剪裁修复范围违规，以及通过与检索引用插值修复依赖违规
  - 使用颜色编码：绿色表示有效参数，红色表示违规，黄色表示修复参数
  - 包含显示决策逻辑的流程图：如果违规存在 → 修复 → 重新验证 → 如需要则回退

### Figure 14: Parameter Space Mapping
- **位置**: Section 5.6.3
- **标签**: `figures/parameter_space_mapping.pdf`
- **内容**: 可视化从检素结果到参数空间的映射
- **说明**:
  - (1) 左侧：检索预设显示为参数空间的 2D 投影中的点（使用 t-SNE 或 PCA），按风格/流派着色
  - (2) 中央：查询点（文本 + 音频）显示为星形，带有指向前 K 个检索邻居的箭头
  - (3) 右侧：生成的参数显示为一个新点，带有指示有效参数空间 $\Theta$ 的凸包或阴影区域
  - 用虚线显示约束边界
  - 包含注释说明检索如何将生成分限定到可行的邻域，以及约束修复如何将无效输出投影回 $\Theta$

## 新增图表（1 个）

### Figure: Experimental Setup Pipeline
- **位置**: Section 6.1
- **标签**: `figures/experimental_setup.pdf`
- **内容**: 展示完整的实验设置流程
- **说明**:
  - (1) 左上：原始参数数据库，显示吉他预设参数（增益、EQ、压缩等）
  - (2) 右上：音频数据库，显示相应的音频向量和 TRR Gram 矩阵
  - (3) 左下：数据集构建，显示合并过程和训练/测试集划分
  - (4) 右下：评估流程，显示查询处理、检索、参数生成和指标计算
  - 使用箭头显示数据流
  - 为不同数据类型使用颜色编码

### Figure: Metric Computation
- **位置**: Section 6.3
- **标签**: `figures/metric_computation.pdf`
- **内容**: 展示每个指标的计算过程
- **说明**:
  - (1) 左上：参数距离 - 显示两个参数向量 $\theta_{\text{pred}}$ 和 $\theta_{\text{gt}}$，带有 L2 距离公式和几何解释
  - (2) 右上：Acc@0.1 - 显示逐个参数的绝对差值，高亮显示容差内（< 0.1）vs. 容差外的参数
  - (3) 左下：余弦相似度 - 显示高维空间中的参数向量，带有角度计算公式
  - (4) 右下：活动召回率 - 显示预测参数与地面真值之间活动（非零）参数的混淆矩阵，并带有召回率计算
  - 使用颜色编码：绿色表示正确，红色表示不正确

## 待整合图表（在 case_studies_addition.tex 中）

### Figure: Feature Visualization for Stadium Rock Case Study
- **位置**: Section 6.2.2 (待整合)
- **标签**: `figures/stadium_rock_features.pdf`
- **内容**: 展示 Stadium Rock 案例研究的特征可视化
- **说明**:
  - (1) 左上：特征嵌入的 t-SNE 可视化，高亮显示地面真值和检索的预设
  - (2) 右上：地面真值、Vector-RAG 最佳和 TRR 最佳检索预设的 TRR Gram 矩阵热图，显示共激活模式
  - (3) 底部：参数雷达图，在关键参数上对比地面真值 vs. Vector-RAG 最佳 vs. TRR 最佳
  - 包含图例和轴标签
  - 使用不同颜色区分不同方法的结果

## 绘制建议

### 工具推荐
- **推荐工具**: draw.io, Inkscape, Python (matplotlib), MATLAB
- **输出格式**: PDF 或 SVG（高分辨率，适合论文排版）
- **样式指南**:
  - 使用一致的配色方案（建议使用色盲友好的调色板）
  - 保持字体大小可读性（标题：12-14pt，标签：10-12pt）
  - 使用清晰的图例和轴标签
  - 避免过多的文本，依赖视觉传达

### 优先级
1. **高优先级**: Figure 1-14（论文核心流程的占位符）
2. **中优先级**: Figure: Experimental Setup, Metric Computation（实验设置）
3. **低优先级**: Figure: Stadium Rock Features（案例研究可视化）

### 总计
- **总图表数**: 16 个
- **已占位符**: 15 个
- **待整合**: 1 个

## 检查清单
- [ ] 所有图表都有详细的内容说明
- [ ] 所有图表都有清晰的标签和说明
- [ ] 图表风格一致
- [ ] 图表分辨率足够（建议至少 300 DPI）
- [ ] 图表文件名正确（与 LaTeX 引用匹配）
