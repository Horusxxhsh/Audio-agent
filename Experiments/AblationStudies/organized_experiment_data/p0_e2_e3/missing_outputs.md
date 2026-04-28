# P0 原始输出缺失清单

本清单记录 `p0_e2_e3/reports/P0_Experiments_Report.md` 中引用、但当前 Git 文件树中未提交的原始输出文件。本次归档只抽取 `origin/master` 上已经存在的报告、runbook 和脚本，不执行实验复现，也不生成替代数据。

## E2: SOTA Baseline Benchmark

报告引用路径：

- `Experiments/AblationStudies/outputs/p0_e2/e2_per_query.csv`
- `Experiments/AblationStudies/outputs/p0_e2/e2_summary.csv`
- `Experiments/AblationStudies/outputs/p0_e2/e2_stats.json`

当前状态：上述文件未出现在 `origin/master` 的 Git 文件树中，也未在当前工作区的 `Experiments/AblationStudies/outputs/` 目录下发现。

## E3: Real Degradation Robustness

报告引用路径：

- `Experiments/AblationStudies/outputs/p0_e3_shared_e2_test/e3_per_query.csv`
- `Experiments/AblationStudies/outputs/p0_e3_shared_e2_test/e3_summary.csv`
- `Experiments/AblationStudies/outputs/p0_e3_shared_e2_test/e3_overall_summary.csv`
- `Experiments/AblationStudies/outputs/p0_e3_shared_e2_test/e3_adaptive_vs_fixed.csv`
- `Experiments/AblationStudies/outputs/p0_e3_shared_e2_test/e3_meta.json`

当前状态：上述文件未出现在 `origin/master` 的 Git 文件树中，也未在当前工作区的 `Experiments/AblationStudies/outputs/` 目录下发现。

## 后续补证建议

若需要将 P0 结果作为正式论文证据，应优先补齐上述 CSV/JSON 原始输出，并重新生成 checksum 与 manifest。若无法找回原始输出，则应根据 `p0_e2_e3/reports/P0_RUNBOOK.md` 复现实验，并明确记录数据集快照、命令参数、运行日期和环境依赖。
