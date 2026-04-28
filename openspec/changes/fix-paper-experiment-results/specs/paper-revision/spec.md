# 论文修订规范

本规范定义论文 `Paper/main.tex` 和 `Paper/content.tex` 需要进行的修订内容。

## 新增需求

### 需求: 移除无法验证的 CLAP 基线
论文 Table I (main_results) 必须移除 CLAP (KNN) 基线行，因为其数据无法在正式实验报告中验证。

#### 场景: CLAP 基线移除
- **当** 读者查看 Table I
- **那么** 表格中不包含 CLAP (KNN) 行
- **并且** "Improvement over Text-RAG" 的数值相应更新

### 需求: 加强 LLM 修正局限性的量化讨论
论文 Section 4.2 必须添加 LLM 修正效果的量化数据，说明其在大多数情况下的有害性。

#### 场景: LLM 修正量化数据
- **当** 读者阅读 Section 4.2 的 LLM 修正讨论
- **那么** 必须看到以下数据：
  - 36.6% 的查询 L2 误差增加
  - 3.3% 的查询 L2 误差降低
  - Module Consistency 在 126/211 个查询中下降
- **并且** 必须引用极端失败案例 (Infinite Sustain: L2 0.81 → 65.68)

### 需求: 说明 Fusion 在标准场景下的表现
论文 Section 4.3 必须说明 Fusion 在 Standard 场景下从未优于 TRR-only。

#### 场景: Fusion 标准场景表现说明
- **当** 读者阅读 Section 4.3 的 Fusion 讨论
- **那么** 必须看到说明：
  - Standard 场景下 0 个查询表现更好
  - Standard 场景下 18 个查询表现更差
  - Fusion 的优势主要体现在降质场景 (Vague Text, Noisy Audio)

### 需求: 在 Limitations 中添加 LLM 修正的系统性问题
论文 Section 6 (Limitations) 必须添加关于 LLM 修正不稳定的讨论。

#### 场景: Limitations 中的 LLM 修正问题
- **当** 读者阅读 Section 6
- **那么** 必须看到关于 LLM 修正以下问题的说明：
  - 对 Few-shot 示例选择敏感
  - Module Consistency 大幅下降
  - 需要重新设计提示策略

## 修改需求

无系统功能修改需求。本变更仅涉及论文内容的修订。

## 移除需求

### 需求: CLAP 基线引用
**Reason**: 数据无法在正式实验报告中验证
**Migration**: 使用现有的 4 个基线（Text-RAG、Wav2Vec-RAG、FeatureNN-RAG、TRR）
