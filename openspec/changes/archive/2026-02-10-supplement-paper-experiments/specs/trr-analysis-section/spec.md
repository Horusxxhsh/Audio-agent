# TRR 方法分析扩展规范

## 修改需求

### 需求：Sec 4.2 必须包含 TRR 与基线方法的定量对比

论文 Sec 4.2 必须添加 TRR 与其他音频纹理表示方法的定量对比，包括 MFCC 和 Modulation Spectrogram。

#### 场景：基线对比表格

- **当** 读者阅读 Sec 4.2 方法对比部分
- **那么** 必须看到对比表格：
  | 方法 | L2 Error | Acc@0.1 | Cosine |
  |------|----------|---------|--------|
  | TRR (Ours) | 13.57 | 0.734 | 0.973 |
  | MFCC Temporal | 24.95 | 0.632 | 0.999 |
  | Modulation Spectrogram | 32.02 | 0.651 | 0.998 |
  - 数据来源：`Experiments/TextureResonance/compare_texture_representations.py`（输出：`Experiments/TextureResonance/texture_representation_comparison.csv`）
  - 说明：该表使用论文中同一套 held-out subset（$N=5$）与参数空间指标。

### 需求：必须包含 Wav2Vec2 层选择分析结果

论文 Sec 4.2 必须解释为何选择某一 Wav2Vec2 中间层进行特征提取，并提供不同层的性能对比数据；论文必须明确指出层 sweep 中的最优层，并说明最终选用层与最优层是否一致（如不一致，需要给出工程/稳定性理由）。

#### 场景：层选择分析展示

- **当** 读者阅读 Sec 4.2 层选择分析部分
- **那么** 必须看到以下内容：
  - 层选择折线图：X 轴为层数 (1-12)，Y 轴为 L2 Error
  - 最优层的说明（文本中明确指出最优层；图中可高亮/标注）
  - 数据来源：`Experiments/TextureResonance/layer_selection_analysis.py`

### 需求：必须更新测试样本数量描述

论文 Sec 4.1 必须准确描述实验使用的测试样本数量。

#### 场景：样本数量修正

- **当** 读者阅读 Sec 4.1 实验设置
- **那么** 必须看到：
  - 原描述："5 held-out queries"
  - 新描述："31 test samples including both human-recorded and MusicGen-generated guitar effects"

## 新增需求

### 需求：必须添加 TRR 计算复杂度分析

论文应包含 TRR 方法的计算复杂度分析，与基线方法进行对比。

#### 场景：复杂度分析展示

- **当** 读者阅读 Sec 4.2 复杂度分析部分
- **那么** 必须看到：
  - TRR 时间复杂度：O(N × d × log d) 其中 N 为样本数，d 为特征维度
  - 与基线方法的复杂度对比表

## 移除需求

（无移除需求）
