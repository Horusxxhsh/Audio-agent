# 资料来源

本报告以当前仓库、论文目录和归档目录中的内部证据为主，同时把 IEEE Transactions on Multimedia（TMM）与 IEEE Signal Processing Society 的作者要求作为监督约束。外部资料在本文中只用于确定 TMM scope、supplement/page hygiene、baseline 补齐方向和 claim 边界；主结果仍必须回到本地 CSV、JSON、Markdown 统计产物与可复核运行日志。

## 主证据

- `Experiments/AblationStudies/organized_experiment_data/protocol_results/protocolA_audio_grouped/protocolA_audio_grouped_objective_stats.md`
- `Experiments/AblationStudies/organized_experiment_data/protocol_results/protocolA_audio_grouped/protocolA_audio_grouped_objective_stats.json`
- `Experiments/AblationStudies/organized_experiment_data/protocol_results/protocolA_audio_grouped/protocolA_audio_grouped_per_query_metrics.csv`
- `Experiments/tmm/protocolA_split_audit.md`

## 辅助诊断

- `Experiments/AblationStudies/organized_experiment_data/protocol_results/protocolC/protocolC_objective_stats.md`
- `Experiments/AblationStudies/organized_experiment_data/protocol_results/protocolC/protocolC_objective_stats.json`
- `Experiments/AblationStudies/organized_experiment_data/protocol_results/protocolC/protocolC_per_query_metrics.csv`
- `Experiments/mushura/results_report.md`

## 代码实现证据

- `Paper/main.tex`
- `Paper/content.tex`
- `Paper/supplementary.tex`
- `Paper/TMM_Response_to_Reviewers.md`
- `Paper/TMM_Revision_Checklist.md`
- `Experiments/tmm/protocolA_split_audit.md`
- `Experiments/tmm/protocolA_audio_grouped_leakage_report.json`
- `Experiments/common/trr_adapter.py`
- `Experiments/common/evaluate.py`
- `Experiments/common/dataset_loader.py`
- `Experiments/AblationStudies/direct_retrieval_comparison.py`
- `Experiments/AblationStudies/robustness_test.py`
- `Experiments/common/rag_adapter.py`
- `Source/rag_system.py`

## TMM 与相关工作约束

- IEEE Transactions on Multimedia scope and reproducible research: `https://signalprocessingsociety.org/publications-resources/ieee-transactions-multimedia`
- IEEE Signal Processing Society Information for Authors: `https://signalprocessingsociety.org/publications-resources/information-authors`
- Text2FX: Harnessing CLAP Embeddings for Text-Guided Audio Effects, arXiv:2409.18847
- Guitar Effects Recognition and Parameter Estimation with Convolutional Neural Networks, arXiv:2012.03216
- Differentiable Signal Processing With Black-Box Audio Effects, arXiv:2105.04752

## 待补或历史材料

- `Experiments/AblationStudies/organized_experiment_data/p0_e2_e3/reports/P0_Experiments_Report.md`
- `Experiments/AblationStudies/organized_experiment_data/p0_e2_e3/missing_outputs.md`（P0 原始输出真实性说明；用户已 double check 数据真实、完整、正确）
- `Experiments/AblationStudies/organized_experiment_data/p0_e2_e3/missing_outputs.md`
- `Experiments/AblationStudies/organized_experiment_data/protocol_results/protocolB/protocolB_objective_stats.md`
- `Experiments/AblationStudies/organized_experiment_data/protocol_results/retrieval_legacy_report/retrieval_comparison_report.md`
