# 规范: 数据一致性修复

本文档定义修复论文中数据一致性问题所需的规范。

## 修改需求

### 需求:Noisy Audio 场景数值统一
论文必须在所有位置对 Noisy Audio 场景使用统一的 L2 数值 `1.4964`。

#### 场景:修复 content.tex robustness_noise 表格
- **当** 读者查看 `content.tex` 第 568 行的 robustness_noise 表格
- **那么** Noisy Audio 行的 L2 值必须显示为 `1.4964`

#### 场景:修复 content.tex robustness_summary 表格
- **当** 读者查看 `content.tex` 第 583 行的 robustness_summary 表格
- **那么** Noisy Audio 场景的 L2 值必须显示为 `1.4964`

#### 场景:修复 content.tex dynamic_weight_strategy 表格
- **当** 读者查看 `content.tex` 第 601 行的 dynamic_weight_strategy 表格
- **那么** Noisy Audio 场景的 L2 值必须显示为 `1.4964`

#### 场景:保持 supplementary.tex 一致性
- **当** 读者查看 `supplementary.tex` Table S9
- **那么** Noisy Audio 场景的 L2 值应当为 `1.4964`（当前已正确）

### 需求:β 敏感性分析叙述更新
论文必须更新 β 敏感性分析的叙述，解释为什么表格显示所有 β 值产生相同结果。

#### 场景:更新 content.tex 第 516 行叙述
- **当** 读者阅读 `content.tex` 第 516 行关于 β 敏感性的描述
- **那么** 叙述必须解释：当 `quality_weight=1.0` 时，质量一致性主导权重分配，导致不同 β 值产生相同的融合结果

#### 场景:解释 β 效果被掩盖的原因
- **当** 读者质疑为何所有 β 值产生相同结果 (0.3056)
- **那么** 论文应当说明这是质量主导机制的预期行为，而非实验错误

### 需求:指标数量修正
论文必须正确陈述评估指标的数量为 4 个，而非 5 个。

#### 场景:修正 content.tex 第 366 行
- **当** 读者阅读 `content.tex` 第 366 行
- **那么** 文本必须陈述 "four operational metrics" 而非 "five metrics"

#### 场景:保持指标定义一致性
- **当** 读者查看指标定义章节
- **那么** 必须恰好找到 4 个指标的定义：L2、Acc@0.1、Recall、Cosine

### 需求:动态权重表验证
论文中的动态权重数值必须与实际计算结果一致。

#### 场景:验证权重数值
- **当** 检查 dynamic_weight_strategy 表格中的权重值
- **那么** 权重值应在同一数量级（约 0.4716），且与 Fusion 实验结果一致

## ADDED Requirements

### 需求:单一真相来源原则
论文中所有数值必须可追溯到唯一的源数据文件。

#### 场景:数值可追溯性
- **当** 审稿人验证论文中的任何数值
- **那么** 必须能够在对应的 JSON/CSV 数据文件中找到相同的数值

#### 场景:跨文件一致性检查
- **当** 同一实验场景在多个位置出现
- **那么** 所有位置必须使用完全相同的数值

## 移除需求

**Reason**: 无（本变更仅修改现有内容，不移除功能）
