## ADDED Requirements

### 需求:近重复敏感性分析实验必须在 Protocol-A 上执行

系统必须在现有 Protocol-A split（204 queries, 1063 KB items）基础上，识别并移除所有近重复对（当前审计报告 200 对），然后重新计算所有检索基线在去重后 split 上的五项指标（L2, Acc@0.1, Recall, Cosine, Module）。

#### 场景:执行去重后评估
- **当** 运行近重复敏感性分析脚本
- **那么** 脚本必须：(1) 加载 Protocol-A split；(2) 使用 cheap fingerprint 方法识别 near-dup 对；(3) 从 KB 中移除 near-dup 项得到 cleaned KB；(4) 对 TRR、Wav2Vec-RAG、Text-RAG、FeatureNN-RAG、CLAP 五种方法重新进行 top-1 检索和指标计算

### 需求:必须报告去重前后指标变化对比表

论文 Sec 4.1 或 Sec 4.2 必须包含一个对比表，展示去重前后各方法在 Protocol-A 上的指标变化。

#### 场景:去重敏感性表格呈现
- **当** 读者阅读近重复敏感性分析结果
- **那么** 必须看到包含以下列的表格：Method | L2 (原始) | L2 (去重后) | Δ L2 | Acc@0.1 (原始) | Acc@0.1 (去重后) | Δ Acc@0.1

### 需求:必须报告 TRR 在去重后仍优于基线的统计显著性

去重后的对比必须包含 bootstrap 95% CI 或 paired permutation test，以证明 TRR 的优势在去重后仍然统计显著（或诚实报告不再显著）。

#### 场景:去重后统计检验
- **当** 去重后 TRR 与某基线的差异被报告
- **那么** 必须附带 95% CI 和 Holm-corrected p-value
