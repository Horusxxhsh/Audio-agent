# Spec: Theoretical Foundation Enhancement

## 概述
增强论文的理论论证，解决TRR理论依据不足、Dual-Modal Fusion机制不清晰、Constraint Repair实现过于简略等问题。

---

## 新增需求

### 需求：THEO-001 TRR理论论证增强
系统必须在Methodology章节提供TRR（Texture Resonance Retrieval）的理论论证，包括信号处理、神经科学和实证三个角度的支持。

**优先级**: 必须
**风险**: 低
**依赖**: 无

#### 场景：审稿人质疑TRR的理论依据

**Given**：审稿人指出"论文将图像领域的Gram矩阵直接迁移到音频域，但缺乏理论论证"

**When**：阅读Methodology章节的TRR部分

**Then**：
- 提供多角度的理论论证（信号处理、神经科学、实证）
- 引用至少2篇支持性文献
- 解释为何音频纹理可以用二阶统计特征表征

**Acceptance Criteria**:
- [ ] 理论论证部分有清晰的sub-section
- [ ] 至少引用2篇相关文献（McDermott et al. 2013等）
- [ ] 与传统方法（modulation spectrogram）进行比较

---

### 需求：Gram矩阵与其他纹理表示方法的比较

**优先级**: 必须
**风险**: 中（实验结果可能不如预期）
**依赖**: TRR理论论证

#### 场景：证明TRR优于简单mean pooling

**Given**：审稿人质疑"为何不用更简单的mean pooling"

**When**：评估TRR的检索性能

**Then**：
- 实现至少2个baseline方法（MFCC temporal patterns, modulation spectrogram）
- 在相同数据集上比较各方法的检索性能
- 用消融实验表格展示结果

**Acceptance Criteria**:
- [ ] 实现2个baseline方法
- [ ] 消融实验表格显示TRR相对baseline的L2 distance改进>10%
- [ ] 分析TRR在哪些类型的样本上表现更好

---

### 需求：Wav2Vec2层选择分析

**优先级**: 强烈建议
**风险**: 低
**依赖**: 无

#### 场景：解释为何选择第9层

**Given**：审稿人可能质疑"为何选择第9层而非其他层"

**When**：阅读Methodology的feature extraction部分

**Then**：
- 提供层选择的消融实验
- 解释浅层/中层/深层的特点
- 给出第9层是最优选择的理论解释

**Acceptance Criteria**:
- [ ] 测试至少5个层（6, 7, 8, 9, 10）
- [ ] 消融实验表格显示各层的检索性能
- [ ] 文字解释为何第9层在semantic和texture之间达到最佳平衡

---

### 需求：Dual-Modal Fusion的完整数学公式

**优先级**: 必须
**风险**: 低
**依赖**: 无

#### 场景：读者无法复现fusion算法

**Given**：当前论文说"uncertainty-aware adaptive fusion"但未给出公式

**When**：读者尝试实现fusion算法

**Then**：
- 提供uncertainty估计的完整公式（entropy计算）
- 提供weight计算的完整公式（exponential decay）
- 添加algorithm pseudocode

**Acceptance Criteria**:
- [ ] Entropy公式：$u = -\sum_{i=1}^K p_i \log p_i$
- [ ] Weight公式：$w = \exp(-\beta \cdot u) / Z$
- [ ] Algorithm 2: Dual-Modal Fusion with Uncertainty

---

### 需求：Fusion失败案例分析

**优先级**: 强烈建议
**风险**: 低
**依赖**: Dual-Modal Fusion的完整数学公式

#### 场景：解释为何fusion在某些情况下损害性能

**Given**：Table 2显示Module Consistency下降了1.8%

**When**：审稿人询问"为何fusion反而降低了性能"

**Then**：
- 分析失败案例的特点
- 提供可视化（weight distribution对比）
- 给出理论解释（模态矛盾、uncertainty传播）

**Acceptance Criteria**:
- [ ] 识别并分析至少5个失败案例
- [ ] 可视化显示成功vs失败的weight分布
- [ ] 文字解释失败原因

---

### 需求：Constraint Repair的完整算法描述

**优先级**: 必须
**风险**: 低
**依赖**: 无

#### 场景：读者无法理解constraint repair如何工作

**Given**：当前论文仅说"clamping + interpolation"

**When**：读者尝试实现constraint repair

**Then**：
- 提供完整的algorithm pseudocode
- 详细描述interpolation策略
- 分析算法的计算复杂度和收敛性

**Acceptance Criteria**:
- [ ] Algorithm 3: Constraint Repair with详细步骤
- [ ] Interpolation公式：$\theta_{new} = (1-\alpha)\theta_{invalid} + \alpha\theta_{neighbor}$
- [ ] 复杂度分析：O(N*D) where N是max iterations, D是database size

---

### 需求：Constraint Repair的正确性证明

**优先级**: 强烈建议
**风险**: 低
**依赖**: Constraint Repair的完整算法描述

#### 场景：证明算法保证输出valid parameters

**Given**：论文声称"所有生成的presets都immediately usable"

**When**：审稿人质疑"如何保证算法一定收敛到valid space"

**Then**：
- 提供Property 1的formal statement
- 提供正确性证明
- 解释为何算法在有限步内收敛

**Acceptance Criteria**:
- [ ] Property 1: "Constraint repair algorithm ensures $\theta^* \in \Theta$"
- [ ] 证明：每次迭代都向valid space靠近，且database有限
- [ ] 收敛性分析：worst-case iterations = database size

---

### 需求：Hallucination的操作化定义

**优先级**: 必须
**风险**: 低
**依赖**: Constraint Repair的完整算法描述

#### 场景：明确"hallucination by 78%"的含义

**Given**：论文声称"减少hallucination by 78%"但未定义hallucination

**When**：审稿人询问"hallucination是如何度量的"

**Then**：
- 定义hallucination = 超出有效范围的参数比例
- 建立Table 1的violation rate与78% reduction的数学联系
- 提供计算示例

**Acceptance Criteria**:
- [ ] 定义：$\text{hallucination rate} = \frac{|\{\theta_i \notin \Theta_i\}|}{d}$
- [ ] 计算：$\text{reduction} = \frac{0.187 - 0.041}{0.187} = 78\%$（示例）
- [ ] Table 1与reduction percentage之间的明确联系

---

## 实施顺序

1. TRR理论论证 → 无依赖，可立即开始
2. Gram矩阵比较 → 依赖TRR理论论证
3. 层选择分析 → 可并行进行
4. Dual-Modal Fusion公式 → 无依赖，可并行进行
5. Fusion失败案例分析 → 依赖Dual-Modal Fusion公式
6. Constraint Repair算法 → 无依赖，可并行进行
7. Constraint Repair证明 → 依赖Constraint Repair算法
8. Hallucination定义 → 依赖Constraint Repair算法

---

## 验证清单

### 文档完整性
- [ ] Methodology章节有TRR理论论证sub-section
- [ ] 有Gram矩阵比较的消融实验表格
- [ ] 有层选择的消融实验表格
- [ ] 有Algorithm 2 (Dual-Modal Fusion)
- [ ] 有Algorithm 3 (Constraint Repair)
- [ ] 有Property 1及其证明

### 逻辑一致性
- [ ] 理论论证与实验结果一致
- [ ] 数学公式符号定义清晰
- [ ] 算法描述与implementation一致

### 可复现性
- [ ] 所有算法有pseudocode
- [ ] 所有公式有变量定义
- [ ] 所有实验有参数设置
