## 为什么

当前 TMM 稿件存在“结论数字与仓库可复现实验工件不一致”的风险：部分表格与摘要数字依赖缺失的历史全向量数据链，同时存在同名指标（L2）跨章节混用不同尺度、数据规模描述冲突（31/51 与当前可加载 50 条记录）以及 supplementary 与主文层选择结果不一致等问题。这会直接影响可复现性、可信度与审稿通过率。

现在需要一个以“可追溯证据优先”为原则的收敛变更：在不新增实验、不伪造数据的前提下，让论文中所有保留的定量结论都能从当前仓库文件直接定位、复算与解释。

## 变更内容

- 建立论文量化结论的“Claim -> Evidence”可追溯规则：每个关键数字必须有仓库内来源文件与一致的指标定义。
- 统一实验规模与口径：修正 `Paper/content.tex` 中与当前数据资产不一致的样本数/知识库规模描述，并明确子集评估范围。
- 清理不可复现数字：对依赖缺失工件的数据表与文字结论执行“删除、降级为定性、或标注 future work”的规范化处理策略。
- 修复跨文档冲突：统一主文与 supplementary 的 layer sweep 叙述、样本数与最优层表述；统一 fusion 与 TRR 章节的指标尺度命名。
- 保留并强调可复现证据链：TRR vs MFCC/ModSpec、Fusion beta/ablation、MUSHRA（清洗后 26 被试/910 评分）等可由仓库现有 CSV/报告支持的结果。

## 功能 (Capabilities)

### 新增功能
- `paper-evidence-traceability`: 约束论文中的关键量化结论必须可在仓库内追溯到具体工件（CSV/MD/脚本输出），并要求指标定义与尺度在全文一致。

### 修改功能
- `trr-analysis-section`: 修正样本规模口径与 layer sweep 结果一致性要求，禁止主文与补充材料出现相互冲突的层选择结论。
- `fusion-analysis-section`: 仅允许引用当前可复现 fusion 工件中的统计与消融结果；不可复现的极端鲁棒性数字需降级处理。
- `mushra-subsection`: 明确统计口径基于清洗后的原始评分数据（去除误入表头行），确保“26/910”等核心数字可复算。

## 影响

- 论文文档：`Paper/content.tex`, `Paper/supplementary.tex`。
- 实验证据引用：`Experiments/Fusion/fusion_beta_sensitivity.csv`, `Experiments/TextureResonance/texture_representation_comparison.csv`, `Experiments/TextureResonance/layer_selection_results.csv`, `Experiments/mushura/mushra.csv`, `Experiments/mushura/results_report.md`。
- OpenSpec 规范增量：新增 `paper-evidence-traceability`，并更新 `trr-analysis-section`、`fusion-analysis-section`、`mushra-subsection`。
- 风险与兼容性：属于论文证据口径与陈述一致性修复，不涉及运行时代码或 API 破坏性变更。
