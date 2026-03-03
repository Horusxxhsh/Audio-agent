## 上下文

本变更面向 IEEE TMM Major Revision 的“实验补强”诉求：在不引入新数据样本、不修改既有实验原始数据与结论方向的前提下，补齐强检索基线（CLAP/PaSST/PANNs）、扩大 Protocol‑B/C 的样本量到 N=211、补充客观/主观统计检验、增加模态冲突与 latency 证据，并将所有新增结果落到可复算的逐 query 工件（CSV/JSON/MD）。

当前仓库已具备可本地复跑的完整数据资产（KB=1267，held‑out=211），且 `Experiments/common/dataset_loader.py` 已支持从外部 JSON 加载并将 Windows `AudioPath` 映射到本地 `Data/Audio_Synthetic/*.wav`。与此同时，现状仍存在：

- SOTA baseline 缺失（CLAP/PaSST/PANNs）导致对比不完整；
- Protocol‑B/C 脚本仍以 N=5 为默认子集，难以支撑统计功效；
- 主观实验当前为 “MUSHRA-style”，缺少标准 anchor，因此需要术语收敛与重复测量统计；
- 依赖与缓存策略不统一：新增模型引入后，必须保证“可选依赖 + 缓存优先 + 可离线复跑”。

## 目标 / 非目标

**目标：**

1. **SOTA baseline 可复现落地**：在 Retrieval‑only 协议中新增 CLAP/PaSST/PANNs 基线，支持与 TRR/Wav2Vec/FeatureNN/Text‑RAG 在同一 held‑out pool 上对比，并生成逐 query CSV 与统计报告（CI/p/校正）。
2. **Protocol‑B/C 扩展到 N=211**：LLM+Projection 与 stress tests 默认在 N=211 上运行；历史 N=5/N=30 仅作为诊断可选项，不再作为主结论依据。
3. **统计严谨性补齐**：客观指标与主观评分均提供重复测量/配对统计检验、置信区间与多重比较校正；所有数字可由仓库内工件复算。
4. **边界与部署证据补齐**：新增 modality conflict stress 与 latency 基准表，明确系统适用边界与工程可行性。
5. **不破坏现有可跑路径**：不安装新依赖时，既有实验（TRR/Wav2Vec/FeatureNN/Text）仍可运行；新增 baselines 以“可选依赖/可选缓存”方式接入。

**非目标：**

- 不扩充/重采集数据集样本；不引入新的音频数据源。
- 不修改任何既有结果表格的原始数值来源；若新增 baseline 结果与原叙述冲突，只允许通过“边界/措辞/协议”修订收敛结论，而不是重写历史结果。
- 不在本变更内重新设计主方法（TRR/Fusion/Projection/Agent 架构保持不变）。

## 决策

### 决策 1：以“Retriever Adapter + 逐 query 工件”作为统一对比接口

**选择：**为每个 baseline（CLAP/PaSST/PANNs）实现与现有 TRR/RAG 一致的检索适配器接口（`retrieve_top_k(...)`），并在核心评测脚本中统一输出逐 query CSV。

**原因：**
- 避免每个 baseline 各写一套评测逻辑，降低口径漂移风险；
- 逐 query 工件是统计检验与审计的最小充分证据；
- 可与现有 `objective_stats.py` 复用（或扩展）形成一致的统计产物。

**替代方案：**
- 仅在论文表格中手工补 baseline 数字（拒绝：不可审计、易引入口径不一致）。

### 决策 2：缓存优先（sidecar .npy），模型依赖可选

**选择：**
- CLAP：优先复用 `Data/Audio_Synthetic/*.wav.clap.npy`，不强制重新提取；
- PaSST/PANNs：新增预计算脚本生成 `*.wav.passt.npy` / `*.wav.panns.npy`（或可配置 cache dir），检索阶段只加载缓存；
- 代码层面：缺失 `torch/timm/scipy` 等依赖时给出明确提示并跳过对应 baseline，而不是让整个实验崩溃。

**原因：**
- 保障本地复跑速度与稳定性；
- 避免将大体量 embedding 工件提交到 Git；
- 允许审稿期间在不同机器上快速复现（只需下载权重并跑预计算）。

**替代方案：**
- 运行时即时提取 embedding（拒绝：速度慢、失败点多、不可控）。

### 决策 3：Protocol‑B/C 的默认测试集与 Protocol‑A 对齐为 N=211

**选择：**将 Protocol‑B（LLM+Projection）与 Protocol‑C（stress tests）默认测试集统一为 held‑out pool（N=211），并强制在表注/正文声明“L2 仅同协议内可比”。

**原因：**
- 直接回应审稿人对统计功效与可比性的质疑；
- 同一 held‑out pool 可减少 split 引入的混杂因素；
- 统一后可做 paired 检验与 effect size 报告。

**替代方案：**
- 继续以 N=5/N=30 作为主要证据（拒绝：TMM 级别不可接受）。

### 决策 4：主观评分采用重复测量的非参数统计（路线 A）

**选择：**将表述改为 “Multiple‑Stimulus Listening Test with Hidden Reference（no explicit anchor）”，并对被试内数据做 Friedman 总检验 + post‑hoc Wilcoxon（Holm 校正），同时报告效应量与 CI。

**原因：**
- 设计不满足 ITU‑R BS.1534 的 anchor 要求，不能继续称为标准 MUSHRA；
- 重复测量结构（同被试听多个系统）适合非参数检验；
- 以最小改动满足“统计严谨性 + 术语准确性”。

**替代方案：**
- 重新做完整 MUSHRA（本变更非目标）。

### 决策 5：模态冲突 stress 以“自动生成矛盾文本”构造可规模化评测

**选择：**在不新增音频样本的前提下，为每个 query 自动生成与其目标语义相反的文本描述，构成低熵冲突条件；报告融合权重 α 分布与性能退化。

**原因：**
- 可扩展到 N=211，避免小样本手工挑选偏差；
- 精确对应审稿人提出的“低熵且冲突”边界风险。

## 风险 / 权衡

- **[依赖复杂度上升]** 引入 torch/timm/scipy/模型包 → **缓解：**可选依赖；提供 `requirements_experiments_sota.txt` 与缺失依赖的降级提示；核心实验仍可无 torch 运行。
- **[预训练权重来源/版本不一致]** 不同实现可能导致 embedding 不可比 → **缓解：**在代码与补充材料中锁定 checkpoint 名称/版本号与提取口径（采样率、mono、分段与 pooling）。
- **[运行时间较长]** PaSST/PANNs 预计算可能耗时 → **缓解：**支持断点续跑与“仅 KB/仅 test/仅缺失项”模式；缓存命中时评测快速。
- **[结果可能与原叙述冲突]** 新 SOTA baseline 可能更强 → **缓解：**提前在写作上收敛为“在当前协议/参数空间对齐任务上的相对优势/边界”，避免绝对 SOTA 论断。
- **[LLM 调用不可复现]** API 波动/费用 → **缓解：**LLM 输出按 query 缓存；论文与补充材料引用缓存工件；默认不触发网络调用。

## Migration Plan

1. 新增 SOTA baseline 预计算脚本与缓存命名约定（默认写入 `Data/Audio_Synthetic/` sidecar 或独立 cache dir）。
2. 在核心评测脚本中增加 baseline 选项与逐 query 输出；将 Protocol‑B/C 默认 test 对齐到 N=211。
3. 扩展统计脚本支持新增方法列，并生成可直接纳入 Supplementary 的表格片段。
4. 更新论文：表格新增 baseline 行、补齐 CI/p/校正说明；主观实验术语收敛与统计补齐；新增 conflict/latency 表。

## Open Questions

- PaSST 与 PANNs 的具体实现来源与 checkpoint 选择（HEAR21/官方实现/第三方包）以“稳定可复现”为优先。
- Embedding 提取口径：是否统一为固定时长分段（例如 10s）或整段 mean pooling；需要在速度与公平性之间取舍。
- 主观实验效应量报告形式：是否统一为 Cliff’s delta / r / Cohen’s d（非参数更适合 delta/r）。

