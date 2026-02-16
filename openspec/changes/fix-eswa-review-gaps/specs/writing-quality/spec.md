# Spec: Writing Quality Improvement

## 概述
改进论文写作质量，修正表达模糊、逻辑不一致、图表缺失等问题。

---

## 修改需求

### 需求：修正Abstract中的35%描述

**优先级**: 必须
**风险**: 低
**依赖**: 无

#### 场景：Abstract中的百分比不明确

**Given**：Abstract说"improving style-consistent retrieval by 35%"

**When**：读者/审稿人问"35%是相对值还是绝对值？基准是什么？"

**Then**：
- 明确35%是relative improvement还是absolute improvement
- 提供基准值和计算过程
- 如果可能，使用更精确的数字

**Acceptance Criteria**:
- [ ] Abstract中的所有percentage有明确含义
- [ ] 如果是relative improvement，说明"(relative to baseline)"
- [ ] 提供计算公式或示例
- [ ] 重新验证所有percentage计算正确

**示例修改**:
- 原文："improving retrieval by 35%"
- 修改后："improving retrieval by 35% (from L2=0.1512 to 0.0980, relative to Text-RAG baseline)"

---

### 需求：分析FeatureNN-RAG性能差的原因

**优先级**: 必须
**风险**: 低
**依赖**: 无

#### 场景：审稿人想知道为何FeatureNN-RAG表现差

**Given**：Table 2显示FeatureNN-RAG的L2=0.3671，表现最差

**When**：阅读Section 4.3的Results Analysis

**Then**：
- 分析为何standard audio classification features不足
- 解释generic feature和texture-aware feature的区别
- 提供失败案例分析

**Acceptance Criteria**:
- [ ] Section 4.3有FeatureNN-RAG的失败分析
- [ ] 解释为何mean-pooling丢弃了texture信息
- [ ] 提供1-2个失败案例（e.g., modulation effects）

**示例文字**:
"FeatureNN-RAG performs poorly (L2=0.3671) because standard audio classification features use mean-pooling, which captures average spectral content but discards temporal co-activation patterns. For example, in modulation effects like tremolo or chorus, the rhythmic pulsing is encoded in second-order statistics that are lost in mean-pooled representations."

---

### 需求：定义active-parameter recall术语

**优先级**: 必须
**风险**: 低
**依赖**: 无

#### 场景：术语首次出现需要定义

**Given**："active-parameter recall"在Table 2首次出现

**When**：读者想知道这个指标的含义

**Then**：
- 在首次出现时提供定义
- 在全文保持术语一致
- 如果使用缩写，首次使用时展开

**Acceptance Criteria**:
- [ ] 首次出现时有定义："active-parameter recall = recall over non-zero parameters"
- [ ] 全文使用同一术语（不混用similar terms）
- [ ] 如果首次使用后缩写为"active recall"，需说明

**示例修改**:
- 首次出现："active-parameter recall (the recall rate for non-zero/active parameters)"
- 后续使用："active recall" or "active-parameter recall" (consistent)

---

### 需求：统一Abstract与Table 2的数据

**优先级**: 必须
**风险**: 低
**依赖**: 无

#### 场景：Abstract和Table 2的数据不一致

**Given**：Abstract说"parameter distance drops from 42.67 to 21.86"

**When**：查看Table 2，发现Audio-Agent的L2=0.0980

**Then**：
- 找出数据不一致的根源
- 确定正确的数据源
- 统一全文使用正确数据

**Acceptance Criteria**:
- [ ] Abstract和Table 2使用同一数据源
- [ ] 所有percentage计算正确且一致
- [ ] 创建results_summary.yaml作为single source of truth（推荐）

**可能的问题**:
- Abstract使用的是normalized L2，Table 2使用的是unnormalized L2
- Abstract使用的是different baseline
- Abstract的计算有错误

**解决方法**:
1. Audit所有results的data source
2. Create YAML file with all final numbers
3. Generate LaTeX tables and Abstract text from YAML

---

### 需求：扩展并独立Limitations章节

**优先级**: 强烈建议
**风险**: 低
**依赖**: 无

#### 场景：Limitations过于简略且位置不当

**Given**：当前Limitations仅3点，在Discussion 560-562行

**When**：审稿人指出"Every study has limitations, acknowledge honestly"

**Then**：
- 将Limitations独立为Section 6
- 扩展至至少5-6点
- 每个limitation包含impact和mitigation

**Acceptance Criteria**:
- [ ] Limitations是独立的Section 6
- [ ] 至少5个distinct limitations
- [ ] 每个limitation有2-3句话解释
- [ ] 每个limitation有future work或mitigation建议

**6个Limitations建议**:
1. **Dataset coverage**: 仅限guitar effects，泛化到其他乐器未知
2. **Parameter identifiability**: many-to-one mapping，parameter distance不是perfect proxy
3. **Computational cost**: TRR需要GPU，实时性受限
4. **Subjectivity of tone quality**: "good" sound depends on context，objective metrics不足
5. **Editability-synthesis trade-off**: 参数控制牺牲了波形level的灵活性
6. **Database dependence**: retrieval quality depends on preset database diversity

**章节结构**:
```latex
\section{Limitations}
\label{sec:limitations}

Our approach has several limitations that should be considered when interpreting the results.

\textbf{Dataset Coverage.} Our evaluation is limited to guitar effects...

\textbf{Parameter Identifiability.} The many-to-one nature of timbre...

[... other limitations ...]

\textbf{Database Dependence.} Retrieval quality depends on...
```

---

### 需求：补充Figure 2 - Experimental Setup Pipeline

**优先级**: 建议
**风险**: 中（设计高质量图表需要时间）
**依赖**: 无

#### 场景：当前Figure 2是placeholder

**Given**：Figure 2标注为`[Figure: Experimental Setup Pipeline]`

**When**：读者想了解实验设置

**Then**：
- 设计完整的实验设置流程图
- 包含4个子部分：数据集构建、特征提取、评估pipeline
- 使用color coding区分不同数据类型

**Acceptance Criteria**:
- [ ] Figure 2是完整的流程图（不是placeholder）
- [ ] 包含4个quadrants：Parameter DB, Audio DB, Dataset Construction, Eval Pipeline
- [ ] Color coding：Param=Blue, Audio=Orange, Process=Green, Eval=Red
- [ ] 箭头清晰显示data flow
- [ ] DPI ≥ 300 for publication

**Layout设计**:
```
┌─────────────────────┬─────────────────────┐
│  Parameter Database │  Audio Database      │
│  (CSV/JSON file)    │  (Vectors + TRR)     │
│  - Preset params    │  - Audio vectors     │
│  - Style tags       │  - Gram matrices     │
└──────────┬──────────┴──────────┬──────────┘
           │                     │
           └──────────┬──────────┘
                      ↓
           ┌─────────────────────┐
           │  Dataset Const.     │
           │  - Merge data       │
           │  - Train/Test split │
           └──────────┬──────────┘
                      ↓
           ┌─────────────────────┐
           │  Evaluation Pipeline│
           │  - RAG retrieval    │
           │  - Param generation │
           │  - Metrics compute  │
           └─────────────────────┘
```

---

### 需求：补充Figure 4 - Metric Computation Visualization

**优先级**: 建议
**风险**: 中（需要设计4个子图）
**依赖**: 无

#### 场景：当前Figure 4是placeholder

**Given**：Figure 4标注为`[Figure: Metric Computation]`

**When**：读者想了解每个metric如何计算

**Then**：
- 设计4个metric的计算可视化
- 每个子图显示公式和几何解释
- 使用color coding highlight正确/错误

**Acceptance Criteria**:
- [ ] Figure 4有4个子图（2x2 grid）
- [ ] 每个子图对应一个metric：Param Distance, Acc@0.1, Cosine, Active Recall
- [ ] 每个子图包含：公式、示例向量、计算结果
- [ ] Color coding：green=correct, red=incorrect
- [ ] DPI ≥ 300 for publication

**Sub-figure设计**:

1. **Parameter Distance** (top-left):
   - 两个向量θ_pred和θ_gt
   - 公式：L2 = ||θ_pred - θ_gt||_2
   - 几何解释：欧氏距离

2. **Acc@0.1** (top-right):
   - 逐元素绝对差值
   - 公式：|θ_pred[i] - θ_gt[i]| < 0.1
   - Highlight：green=within tolerance, red=outside

3. **Cosine Similarity** (bottom-left):
   - 两个向量的夹角
   - 公式：cos(θ) = (θ_pred·θ_gt) / (||θ_pred||·||θ_gt||)
   - 几何解释：角度越小越相似

4. **Active Recall** (bottom-right):
   - Confusion matrix (active vs inactive)
   - 公式：TP / (TP + FN)
   - Highlight：green=TP, red=FN

---

### 需求：确定Figure 5的内容并绘制

**优先级**: 可选（如果需要）
**风险**: 低
**依赖**: Phase 1和2的实验结果

#### 场景：当前Figure 5是placeholder

**Given**：Figure 5标注为`[Figure: ...]`

**When**：决定Figure 5应该展示什么

**Then**：
- 确定Figure 5的purpose
- 设计并绘制图表
- 确保图表支持论点

**Acceptance Criteria**:
- [ ] Figure 5的purpose明确
- [ ] 图表设计清晰、美观
- [ ] 图表支持论文的某个claim
- [ ] DPI ≥ 300 for publication

**Figure 5的可能内容**:
1. **Fusion weight分析**：显示不同query quality下的weight变化
2. **层选择消融实验**：显示不同Wav2Vec2层的性能
3. **TRR vs. Mean Pooling对比**：显示在texture-sensitive样本上的性能差异
4. **Cross-validation结果**：显示5-fold的性能分布
5. **Failure case分析**：显示某个interesting failure的细节

**推荐**：Fusion weight分析（如果完成）或层选择消融实验

---

### 需求：删除重复的Table 7

**优先级**: 低（quick fix）
**风险**: 无
**依赖**: 无

#### 场景：Table 3与Appendix Table 7重复

**Given**：Hyperparameters在主文和附录都有表格

**When**：审稿人指出"冗余内容"

**Then**：
- 保留主文中的版本（Table 3）
- 删除附录中的版本（Table 7）
- 确保无其他重复

**Acceptance Criteria**:
- [ ] Table 3保留在主文
- [ ] Appendix中的Table 7已删除
- [ ] 全文检查无其他重复表格

---

## 实施顺序

### Phase 1: 数据一致性修复（必须）
1. Abstract的35%描述 → 可立即修复
2. Abstract与Table 2数据统一 → 需要audit
3. 定义active-parameter recall → 可立即修复

### Phase 2: 内容扩展（强烈建议）
4. FeatureNN-RAG失败分析 → 可立即添加
5. Limitations章节扩展 → 可立即开始
6. 删除重复Table 7 → quick fix

### Phase 3: 图表补充（建议）
7. Figure 2 - Experimental Setup → 需要1-2天设计
8. Figure 4 - Metric Computation → 需要1-2天设计
9. Figure 5 - 待定内容 → 依赖Phase 1-2的实验

---

## 验证清单

### 数据一致性
- [ ] Abstract中的所有percentage有明确含义
- [ ] Abstract和所有Table使用同一数据源
- [ ] 所有术语在全文一致

### 内容完整性
- [ ] 所有placeholder text已替换为实际内容
- [ ] 所有missing figures已补充
- [ ] 所有重复内容已删除

### 表达清晰度
- [ ] 所有首次出现的术语有定义
- [ ] 所有failure cases有分析
- [ ] 所有limitations有impact和mitigation

### 图表质量
- [ ] 所有figures有清晰的caption
- [ ] 所有figures DPI ≥ 300
- [ ] 所有figures有color legend（如适用）
