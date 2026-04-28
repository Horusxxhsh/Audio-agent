## 为什么

IEEE TMM 审稿人核心关切 **C1: "贡献的新颖性不足"** —— "Gram 矩阵/二阶统计用于表征风格/纹理是经典套路...当前对比不足以证明这是该问题上的关键突破"。审稿人明确要求与更强的现代音频表征进行系统对比，包括 CLAP、PaSST、PANNs 等。本实验是回应 C1 的核心证据，直接决定论文能否证明 TRR 方法的价值。

## 变更内容

### 新增内容
- **CLAP Encoder**: 实现 LAION-CLAP 音频编码器 (Contrastive Language-Audio Pretraining)
- **PaSST Encoder**: 实现 PaSST 音频编码器 (Efficient Audio Spectrogram Transformer)
- **PANNs Encoder**: 实现 PANNs 音频编码器 (Pretrained Audio Neural Networks)
- **统一对比框架**: 实现公平对比协议，确保所有方法使用相同检索设置

### 实验设计
- 在相同吉他效果数据集上评估所有方法
- 使用相同评估指标：L2 误差、Acc@0.1、余弦相似度、Module 一致性
- 预计算所有基线的 embedding 避免重复推理
- 统计检验：性能差异的显著性分析

## 功能 (Capabilities)

### 新增功能
- `clap-encoder`: CLAP 音频特征提取器 (HuggingFace transformers)
- `passt-encoder`: PaSST 音频特征提取器 (专门化音频 Transformer)
- `panns-encoder`: PANNs 音频特征提取器 (AudioSet 预训练 CNN)
- `baseline-comparison-framework`: 统一基线对比框架，支持公平评估

### 修改功能
- 无现有功能修改（纯新增实验）

## 影响

### 代码影响
- **新增文件**: `Experiments/E2_SOTABaselines/clap_encoder.py` (~300 行)
- **新增文件**: `Experiments/E2_SOTABaselines/passt_encoder.py` (~250 行)
- **新增文件**: `Experiments/E2_SOTABaselines/panns_encoder.py` (~250 行)
- **新增文件**: `Experiments/E2_SOTABaselines/run_comparison.py` (~600 行)

### 计算资源
- **GPU**: RTX 3090 运行 8-12 小时（embedding 预计算）
- **存储**: ~20GB 用于缓存 embeddings
- **无 API 调用**（纯特征提取）

### 论文影响
- **Sec 4.2**: 新增 Table X - SOTA 基线对比表
- **Sec 3.2**: 补充 TRR 与 SOTA 方法的对比讨论
- **Response Letter**: 核心证据回应 C1 质疑
- **Impact**: 决定论文 claim 是否需要调整

### 关键风险
| 性能差距 | 应对策略 |
|----------|----------|
| TRR >= CLAP-10% | ✅ 继续原 claim: "TRR 优于或接近 SOTA" |
| CLAP-20% < TRR < CLAP-10% | ⚠️ 调整 claim: "专门化设计，轻量级优势" |
| TRR < CLAP-20% | 🚨 Plan B: 强调 "Agent 架构整合" 而非单一检索优势 |

## 预期结果

### 成功标准
- TRR 在吉他数据集上优于或接近 CLAP/PaSST/PANNs (差距 < 10%)
- 即使略逊，也能通过轻量级 (7MB vs 数百 MB) 和实时性进行辩护
- 提供详细的消融分析解释性能差异原因

### 依赖安装风险
- CLAP 依赖 notoriously tricky，准备 Docker 备选方案
- 如安装失败，使用 OpenL3 或 AST 作为替代基线
