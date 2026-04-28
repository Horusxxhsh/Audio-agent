# Audio-Agent 实验数据归档说明

本目录是对当前工作区可见实验材料的低侵入归档快照。归档采用复制方式生成，不移动、不删除、不覆盖原始实验文件；因此这里应被视为证据包与复核入口，而不是新的实验运行目录。

## 目录结构

- `p0_e2_e3/reports/`：从 `origin/master` 抽取的 P0 实验报告与 runbook。
- `p0_e2_e3/scripts/`：从 `origin/master` 抽取的 P0 运行脚本与依赖快照。
- `p0_e2_e3/missing_outputs.md`：P0 报告引用但当前 Git 文件树中缺失的原始输出清单。
- `protocol_results/protocolA/`：当前工作区中的 Protocol-A 基础结果。
- `protocol_results/protocolA_strong_baselines/`：当前工作区中的 Protocol-A 强基线与派生分析结果。
- `protocol_results/protocolA_audio_grouped/`：当前工作区中的 Protocol-A audio-grouped 版本结果。
- `protocol_results/protocolB/`：当前工作区中的 Protocol-B 结果。
- `protocol_results/protocolC/`：当前工作区中的 Protocol-C 结果。
- `protocol_results/fusion_beta/`：已提交的 fusion beta sweep 小型结果表。
- `protocol_results/retrieval_legacy_report/`：已提交的 legacy retrieval comparison 报告快照。

## 证据边界

P0 报告说明了 `E2: SOTA Baseline Benchmark` 与 `E3: Real Degradation Robustness` 的实验设计和汇总结果，但报告引用的 `outputs/p0_e2` 与 `outputs/p0_e3_shared_e2_test` 原始 CSV/JSON 当前不在 Git 文件树中。本归档不伪造、不重算这些结果，只保留报告、runbook、脚本和缺失清单。

Protocol A/B/C 结果来自当前本地工作区，其中部分文件被 `.gitignore` 忽略，部分文件尚未跟踪。它们可以用于内部复核和结果对照；若要作为论文或答辩证据，应先确认数据生成命令、数据集版本和统计口径。

`retrieval_comparison_report.md` 明确标注为 legacy working note，不应作为 TMM revision 的 canonical 证据。它仅用于追踪早期 retrieval 对比叙述与数值来源。

## 索引与校验

- `MANIFEST.csv` 记录每个归档文件的来源路径、Git 状态、来源提交或工作区状态，以及用途说明。
- `checksums.sha256` 记录归档文件校验和，可用以下命令复核：

```bash
cd /Users/xyh/Code/Audio-agent/Experiments/AblationStudies/organized_experiment_data
shasum -a 256 -c checksums.sha256
```
