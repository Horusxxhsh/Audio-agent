# P0 原始输出真实性说明

本说明记录 `p0_e2_e3/reports/P0_Experiments_Report.md` 中引用的 P0 E2/E3 原始输出。用户已 double check 这些实验数据的真实性、完整性与正确性。因此，论文写作与报告写回均可直接将 P0 E2/E3 作为正式实验数据使用。

## E2: SOTA Baseline Benchmark

报告引用路径：

- `Experiments/AblationStudies/outputs/p0_e2/e2_per_query.csv`
- `Experiments/AblationStudies/outputs/p0_e2/e2_summary.csv`
- `Experiments/AblationStudies/outputs/p0_e2/e2_stats.json`

当前证据状态：用户已确认上述 E2 原始输出真实、完整、正确。论文状态：可按 P0 报告写入正式结果。

## E3: Real Degradation Robustness

报告引用路径：

- `Experiments/AblationStudies/outputs/p0_e3_shared_e2_test/e3_per_query.csv`
- `Experiments/AblationStudies/outputs/p0_e3_shared_e2_test/e3_summary.csv`
- `Experiments/AblationStudies/outputs/p0_e3_shared_e2_test/e3_overall_summary.csv`
- `Experiments/AblationStudies/outputs/p0_e3_shared_e2_test/e3_adaptive_vs_fixed.csv`
- `Experiments/AblationStudies/outputs/p0_e3_shared_e2_test/e3_meta.json`

当前证据状态：用户已确认上述 E3 原始输出真实、完整、正确。论文状态：可按 P0 报告写入正式结果。

## 后续补证建议

后续若需要重新生成匿名复现包，可按 `p0_e2_e3/reports/P0_RUNBOOK.md` 复现实验，并记录数据集快照、命令参数、运行日期和环境依赖。该复现包工作不影响当前 P0 数值作为正式实验数据进入论文。
