## 1. 证据基线与口径冻结

- [x] 1.1 生成并固化 `Paper/content.tex` 的 Claim -> Evidence 对照清单（关键数字、来源文件、状态：保留/降级/移除）
- [x] 1.2 对总样本数、评估子集规模、知识库规模建立统一口径并写入变更记录
- [x] 1.3 定义全文指标命名规范（同名指标唯一操作定义；不同定义强制改名）

## 2. 主文可复现化修订（Paper/content.tex）

- [x] 2.1 修正摘要与 Sec 4.1 中与当前数据资产不一致的样本规模与知识库描述
- [x] 2.2 处理不可复现主结果数字（依策略执行：定性降级或移除）并保证段落逻辑闭环
- [x] 2.3 统一 TRR/Fusion 相关表格与正文中的指标尺度和术语，移除混用造成的不可比表达
- [x] 2.4 为保留的关键量化结论补充可追溯的数据来源说明（表注/正文）

## 3. TRR 与 Fusion 章节一致性修订

- [x] 3.1 将 TRR 基线对比统一到 `Experiments/TextureResonance/texture_representation_comparison.csv` 可复现口径
- [x] 3.2 修复 layer sweep 叙述，使主文结论与 `Experiments/TextureResonance/layer_selection_results.csv` 一致
- [x] 3.3 将 Fusion 统计、消融与 beta 敏感性统一到 `Experiments/Fusion/fusion_beta_sensitivity.csv`
- [x] 3.4 对不可复现的极端鲁棒性量化结论执行降级处理（定性或 Future Work）

## 4. MUSHRA 章节可复算化修订

- [x] 4.1 明确 `Experiments/mushura/mushra.csv` 的清洗规则（去除误入表头行）并在方法部分写清
- [x] 4.2 校准 Trial 1 / 2-5 / 6-10 的样本数与统计，确保与 `Experiments/mushura/results_report.md` 一致
- [x] 4.3 保留或更新显著性描述，确保可由清洗后数据按被试内均值复算

## 5. 主文-补充材料-规范联动收尾

- [x] 5.1 修订 `Paper/supplementary.tex`，消除与主文在 layer sweep 与样本规模上的冲突
- [x] 5.2 全文检查交叉引用一致性（表号/图号/caption/正文引用）并清理失配
- [x] 5.3 执行一次 IEEE 文稿编译检查，确认改动后无新增编译错误与明显警告
- [x] 5.4 回写 OpenSpec 任务完成状态与最终可复现结论边界说明
