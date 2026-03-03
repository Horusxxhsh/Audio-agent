# `trr-analysis-section` 规范（增量）

## MODIFIED Requirements

### 需求：Sec 4.2 必须包含 TRR 与基线方法的定量对比

论文 Sec 4.2 必须包含 TRR 与其他音频纹理表示方法的定量对比（至少包含 MFCC Temporal 与 Modulation Spectrogram），并在统一的 held-out pool（N=211）与参数空间指标口径下报告结果；禁止继续使用 N=5/N=30 子集作为主结论证据。

#### 场景：基线对比表格口径统一且可复算

- **当** 读者阅读 Sec 4.2 的纹理表示对比表格
- **那么** 必须看到：
  - 方法行至少包含：`TRR (Gram Matrix)`、`MFCC Temporal`、`Modulation Spectrogram`
  - 指标列至少包含：`L2 Error`、`Acc@0.1`、`Cosine`
  - 样本量声明：`N=211`（held-out queries），并明确候选集来自同一知识库 split
  - 数据来源脚本：`Experiments/TextureResonance/compare_texture_representations.py`
  - 结果工件路径：`Experiments/TextureResonance/texture_representation_comparison.csv`（或等价、可追溯的 CSV）

#### 场景：计算可行性（缓存或预计算）

- **当** 作者在 N=211 的设置下运行该对比实验
- **那么** 实现必须通过缓存/预计算避免对同一音频重复提取 embedding（禁止 O(N_query × N_kb) 次重复 STFT 计算导致不可运行）
- **并且** 脚本输出必须记录：
  - 候选集大小与测试集大小
  - 各方法 embedding 的维度与缓存命中率（如适用）

### 需求：必须包含 Wav2Vec2 层选择分析结果

论文 Sec 4.2 必须解释 Wav2Vec2 中间层选择的依据，并提供层 sweep 的定量结果；层 sweep 的评测口径必须与主实验一致（同一 held-out pool，参数空间指标一致），并保证主文与补充材料结论一致。

#### 场景：层 sweep 结果与最终选层一致性披露

- **当** 读者阅读 Sec 4.2 的层选择分析
- **那么** 必须看到：
  - 层 sweep 的对比结果（至少包含最优层与最终选用层）
  - 若最终选层不等于最优层，必须给出工程/稳定性理由
  - 数据来源脚本：`Experiments/TextureResonance/layer_selection_analysis.py`
  - 工件输出：`Experiments/TextureResonance/layer_selection_results.csv`（或等价可追溯文件）

### 需求：必须更新测试样本数量描述

论文 Sec 4.1 的实验设置必须准确描述当前实验规模与 split：知识库规模为 1267 条记录，所有核心客观评测默认在 held-out queries N=211 上进行；禁止在主文中继续使用或混用 “N=5/N=30/31/51” 等历史口径。

#### 场景：实验设置口径一致

- **当** 读者阅读 Sec 4.1 Experimental Setup
- **那么** 必须看到：
  - `Knowledge base size = 1267`
  - `Held-out queries = 211`
  - 并声明该口径适用于 Protocol-A/B/C（除非某表显式标注为诊断子集）

### 需求：必须添加 TRR 计算复杂度分析

论文必须包含 TRR 的计算与检索复杂度说明，并给出与一阶 embedding 基线（例如 CLAP/PaSST/PANNs）的对比性解释（不要求同一复杂度公式，但必须解释主要瓶颈与可缓存策略）。

#### 场景：复杂度与缓存策略说明

- **当** 读者阅读 Sec 4.2 的复杂度分析
- **那么** 必须看到：
  - TRR 的主要计算开销来源（特征提取、Gram 计算、投影维度）
  - 检索阶段的复杂度（随 KB 大小增长的趋势）
  - 缓存/预计算如何降低在线推理开销（与 latency 表保持一致）

