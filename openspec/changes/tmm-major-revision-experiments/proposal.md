## 为什么

当前 TMM 复审的主要风险集中在“实验说服力与可审计性”：缺少 CLAP/PaSST/PANNs 等强检索基线、Protocol-B/Protocol-C 的样本量过小、客观与主观结果缺少配对统计检验与置信区间、LLM 推理过程与 few-shot 隔离缺乏可复核披露。现在仓库已具备完整数据资产（KB=1267、held-out queries=211）并可在本地稳定复跑，因此需要一次面向 TMM 审稿标准的实验补强变更，把证据链从“可读”提升到“可审计”。

本变更不引入新的数据集样本，不修改任何既有实验原始数据与结论走向；仅在现有数据上补齐基线、统计、协议披露与复现工件。

## 变更内容

- **补齐强检索基线（Retrieval-only）**：在统一的 Protocol-A 下新增 CLAP / PaSST / PANNs 三类 SOTA 表征的 KNN 检索基线，并与 TRR/Wav2Vec/FeatureNN/Text-RAG 在同一 split 上对比。
- **新增 embedding 预计算与缓存流水线**：对现有音频资产（`Data/Audio_Synthetic/*.wav`）离线计算 PaSST/PANNs embedding（CLAP 优先复用已有 `*.wav.clap.npy`），输出可复用的 `*.npy` sidecar 缓存与索引文件，避免重复计算；缓存默认不进入 Git。
- **扩大 Protocol-B/Protocol-C 到 N=211**：将 “LLM+Projection” 与 stress-test（文本退化/音频退化/单模态）统一扩展到 held-out pool（N=211），并以逐 query 输出对齐统计口径；历史 N=5/N=30 设置降级为诊断/附录或移除。
- **统计显著性与不确定性报告**：对核心客观指标（主指标 L2，其余为次指标）提供 95% CI（bootstrap）与 paired 显著性检验（置换/Wilcoxon），并对多重比较进行 Holm 校正；所有新增表格提供可复算的逐 query CSV。
- **LLM 透明化与关键消融**：补齐 prompt 模板、输出 schema、token 长度分布与缓存；新增 “Top-K mean/weighted mean + projection” vs “LLM rewrite + projection” 消融；增加 few-shot 去重/隔离审计与 “w/o few-shot” 对照，以回答“推理有效性/泄漏风险”的质疑。
- **主观实验术语与统计补强（路线 A）**：将 “MUSHRA-style” 严格改名为 “Multiple-Stimulus Listening Test with Hidden Reference（no explicit low-quality anchor）”；补齐随机化/参与者/时长/界面截图；在现有 `mushra.csv` 上增加重复测量统计（Friedman + post-hoc Wilcoxon，Holm 校正）与效应量/CI 报告。
- **新增模态冲突边界测试**：构造低熵但文本/音频语义冲突的 stress 条件，报告融合权重分布（α）与性能退化，给出典型失败案例与讨论边界。
- **补齐 latency 评估**：输出端到端与分模块耗时（median/p95），明确硬件与计时口径，形成可直接入论文的延迟表格。

## 功能 (Capabilities)

### 新增功能

- `sota-retrieval-baselines`: 在 Protocol-A 下新增 CLAP/PaSST/PANNs 的检索基线，并与 TRR/Wav2Vec/FeatureNN/Text-RAG 在同一 held-out pool 上进行逐 query 评估与统计检验。
- `embedding-precompute-cache`: 为 PaSST/PANNs 提供可复现的 embedding 预计算/缓存/索引工具链（面向 KB 与 held-out queries），并统一缓存命名、采样率与分段策略。
- `protocol-bc-expanded-evaluation`: 将 Protocol-B（Retrieval+LLM+Projection）与 Protocol-C（stress tests）扩展到 N=211，并统一输出逐 query CSV 与统计报告（CI/p/多重比较校正）。
- `llm-ablations-and-leakage-audit`: 提供 prompt/输出 schema 披露、LLM 输出缓存、Top-K mean 对照、few-shot 去重审计与无 few-shot 对照实验。
- `latency-profiling`: 端到端与分模块 latency 基准测试脚本与表格产出规范（含 median/p95 与硬件说明）。
- `modality-conflict-stress-test`: 构造并评估跨模态冲突 stress 条件，报告 α 分布、性能退化与失败案例。

### 修改功能

- `trr-analysis-section`: 更新 Sec 4.2 的实验口径与表格，使其与当前 KB=1267、held-out=211 的统一协议一致，并补齐与 CLAP/PaSST/PANNs 的可比对基线说明与统计报告要求。
- `fusion-analysis-section`: 增加“跨模态冲突”边界与 stress 结果披露要求，并修正“动态融合”在常规设置下近似静态的表述边界。
- `mushra-subsection`: 将术语收敛为“Multiple-Stimulus + Hidden Reference（no anchor）”，并把重复测量统计检验与界面/随机化披露写入 requirements。

## 影响

- 实验代码：`Experiments/AblationStudies/`、`Experiments/common/`（新增/改造 retriever、逐 query dump、统计报告、LLM 缓存与泄漏审计、stress/冲突测试、latency 脚本）。
- 数据资产：复用现有 `Data/Audio_Synthetic/` 与 `Data/External_1267_211/`；新增的 embedding 缓存（PaSST/PANNs）作为本地工件，不纳入 Git。
- 论文与补充材料：`Paper/content.tex`、`Paper/supplementary.tex`（新增基线行、统计显著性与 CI 披露、听音实验术语与统计、modality conflict 与 latency 表）。
- 依赖：新增可选 Python 依赖（如 torch/timm 及相应模型包）；须保持“无这些依赖也可运行既有非 SOTA baseline 实验”的降级路径。

