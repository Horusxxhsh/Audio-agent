## 1. 证据对齐与差异审计

- [x] 1.1 对照 `Paper/content.tex` 主实验表与 `Experiments/AblationStudies/retrieval_comparison_report.md`，逐项核验方法名、指标名与数值
- [x] 1.2 产出一致性审计记录（包含“一致项/差异项/处理状态”）并附文件定位
- [x] 1.3 若发现与 canonical Protocol-A 工件冲突，记录冲突点并确定单一来源口径

## 2. 主文与补充材料修订

- [x] 2.1 在 `Paper/content.tex` 中收敛主实验叙事为 TRR 主证据链，移除 fusion 作为主结论证据
- [x] 2.2 恢复与主线一致的历史有效图表（TRR 层选择、听测图）并补齐对应描述
- [x] 2.3 校正 `Paper/content.tex` 中 setup 描述，移除脚本文件名/临时实现名
- [x] 2.4 在 `Paper/supplementary.tex` 中同步主文口径，避免跨文档冲突

## 3. 审稿回应包维护

- [x] 3.1 在编写回应文稿前完成证据来源核对（结论-数字-文件三元映射）
- [x] 3.2 显式调用 `scientific-writing` skill 生成 `Paper/TMM_Response_to_Reviewers.md` 段落文本
- [x] 3.3 使用 `scientific-writing` 风格更新 `Paper/TMM_Revision_Checklist.md` 的说明段并保持可执行结构
- [x] 3.4 确认回应文档中的“已完成/待完成”状态与论文实际改动一致

## 4. 质量门禁与可提交性检查

- [x] 4.1 运行 LaTeX 编译检查 `Paper/main.tex` 与 `Paper/supplementary.tex`，确认无新增致命错误
- [x] 4.2 检查图表引用、表格编号、术语边界（TRR vs HCAP）一致性
- [x] 4.3 完成最终变更摘要，标注重投前仍需补做的实验项（如跨域泛化与强基线）
