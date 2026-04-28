## ADDED Requirements

### 需求:必须新增 PANNs 音频检索基线

系统必须使用预训练 PANNs (CNN14) 模型提取数据集中所有音频的 embedding，并在 Protocol-A split 上执行 cosine top-1 检索评估。

#### 场景:PANNs 基线评估
- **当** 运行 PANNs 基线评估脚本
- **那么** 脚本必须：(1) 使用 `torchlibrosa` 或 HuggingFace 加载预训练 CNN14；(2) 提取 2048-dim embedding；(3) 对 204 queries 执行 cosine 检索；(4) 报告 L2, Acc@0.1, Recall, Cosine, Module 五项指标

### 需求:必须新增 PaSST 音频检索基线

系统必须使用预训练 PaSST 模型提取音频 embedding，并在 Protocol-A split 上执行 cosine top-1 检索评估。

#### 场景:PaSST 基线评估
- **当** 运行 PaSST 基线评估脚本
- **那么** 脚本必须：(1) 使用 HuggingFace `hear21passt` 加载预训练 PaSST；(2) 提取 embedding；(3) 对 204 queries 执行 cosine 检索；(4) 报告五项指标

### 需求:必须新增 MLP 直接参数回归基线

系统必须实现一个 MLP 回归基线，输入为 Wav2Vec2 mean-pooled embedding，输出为 flattened parameter vector，并在 Protocol-A split 上评估。

#### 场景:MLP 回归基线评估
- **当** 运行 MLP 回归基线脚本
- **那么** 脚本必须：(1) 使用 KB 数据训练 MLP（输入 768-dim → 隐层 → 输出 d-dim params）；(2) 使用 5-fold CV 或 KB-only 训练避免泄露；(3) 在 204 test queries 上预测参数并报告五项指标

### 需求:Protocol-A 主表必须包含所有新基线

论文 Table 3（Protocol-A 主表）必须更新，在现有五行（TRR, Wav2Vec-RAG, Text-RAG, FeatureNN-RAG, CLAP）基础上新增 PANNs, PaSST, MLP-Regressor 三行。

#### 场景:主表更新
- **当** 读者阅读 Table 3
- **那么** 必须看到 8 行方法对比（含 TRR 和 7 个基线），每行包含 n, L2↓, Acc@0.1↑, Recall↑, Cos↑, Module↑
