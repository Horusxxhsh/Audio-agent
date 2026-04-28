# `sota-retrieval-baselines` 规范

## ADDED Requirements

### 需求:Retrieval-only 评测必须纳入 CLAP/PaSST/PANNs 基线

论文 RQ1 / Table III（或等价主表）必须在统一的 Retrieval-only 协议下报告 CLAP、PaSST、PANNs 三类强基线的检索结果，并与 TRR/Wav2Vec/FeatureNN/Text-RAG 在同一 split 上进行可比对评测。

#### 场景:在 Protocol-A（held-out N=211）上输出逐 query 结果并可汇总复算

- **当** 作者运行 Retrieval-only 评测脚本（例如 `Experiments/AblationStudies/direct_retrieval_comparison.py`）并启用 CLAP/PaSST/PANNs 基线
- **那么** 脚本必须输出并保存逐 query 指标工件（CSV），每个 query 至少包含：
  - `L2`、`Acc@0.1`、`Recall`、`Cosine`、`ModuleConsistency`
  - `method` 字段包含 `CLAP`、`PaSST`、`PANNs` 三种方法名
  - `protocol` 字段明确标注为 `Protocol-A`

#### 场景:缺失可选依赖时仍可运行其余 baselines

- **当** 运行环境缺失 PaSST/PANNs 的可选依赖（例如 `torch/timm` 或对应模型包）
- **那么** 实验脚本必须：
  - 明确提示“该 baseline 被跳过的原因”
  - 继续完成 TRR/Wav2Vec/FeatureNN/Text-RAG/CLAP（如有缓存）等其余方法评测
  - 仍然生成可复算的逐 query CSV（不包含被跳过的方法列）

### 需求:CLAP/PaSST/PANNs 的对比必须与 TRR 共用同一 split 与指标口径

SOTA baseline 的对比必须与 TRR 使用相同的 held-out queries（N=211）与相同的参数空间指标实现（`Experiments/common/evaluate.py`），禁止在不同 split 或不同指标定义下直接写入同一主表。

#### 场景:同表可比性声明

- **当** 作者在论文中呈现包含 SOTA baseline 的检索对比表
- **那么** 表注必须声明：
  - 所有方法均在同一 Protocol-A（Retrieval-only）与同一 held-out pool 上评测
  - `L2` 等绝对数值仅在同协议内可比（禁止跨协议横向比较）

