## MODIFIED Requirements

### 需求：Sec 4.2 必须包含 TRR 与基线方法的定量对比

论文 Protocol-A 主表必须更新为包含 PANNs、PaSST、MLP-Regressor 在内的八行对比。原有的纹理表示对比（MFCC、Modulation Spectrogram）可保留但应移至消融子节或补充材料。

#### 场景：扩展后的主表对比

- **当** 读者阅读 Protocol-A 主结果
- **那么** 必须看到 8 行对比表格，包含 TRR、Wav2Vec-RAG、Text-RAG、FeatureNN-RAG、CLAP、PANNs、PaSST、MLP-Regressor

### 需求：必须包含 Wav2Vec2 层选择分析结果

（保持原始需求不变——已有层选择折线图的规范。本次修改增加将该分析纳入消融子节的要求。）

#### 场景：层选择分析纳入消融子节

- **当** 读者阅读消融实验子节
- **那么** 必须看到层选择分析的全表结果（包含 L2, Acc@0.1, Cosine 三项指标，覆盖 6 种层组合）

### 需求：必须明确投影矩阵来源并给出消融

论文 Sec 3.2（Methodology → TRR）必须在 Algorithm 1 的文字描述中明确投影矩阵 P 为 PCA 拟合，并在消融子节展示 PCA vs random projection 的对比结果。

#### 场景：投影矩阵说明

- **当** 读者阅读 TRR 方法描述
- **那么** 必须看到明确说明 P 是 PCA 投影（从 KB 音频的 Wav2Vec2 激活上拟合），且消融表中包含 PCA vs random 的行

## ADDED Requirements

### 需求：必须添加消融实验子节

论文 Sec 4 必须新增一个消融子节（如 Sec 4.X Ablation Studies），包含投影维度消融、层选择消融和投影类型消融的结果。

#### 场景：消融子节结构

- **当** 读者阅读 Sec 4 的消融子节
- **那么** 必须看到三组消融结果（维度 / 层 / 投影类型），每组以表格形式呈现
