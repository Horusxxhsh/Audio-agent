## 1. 模板落地（IEEEtran）

- [x] 1.1 从 `Paper/IEEE-Transactions-LaTeX2e-templates-and-instructions.zip` 解出 `IEEEtran.cls` 到 `Paper/IEEEtran.cls`
- [x] 1.2 确认 `Paper/main.tex` 使用 `\\documentclass[journal,10pt]{IEEEtran}` 并以 `Paper/IEEEtran.cls` 为优先模板来源
- [x] 1.3 校验参考文献风格仍符合 IEEE 数字引用（保持 `natbib` + `IEEEtranN` 或按需要调整）

## 2. 入口统一与清理

- [x] 2.1 将 `Paper/main.tex` 从 ICLR wrapper 迁移为 IEEE 单入口（继续 `\\input{content.tex}`）
- [x] 2.2 移除冗余入口文件 `Paper/main_ieee.tex`（必要时改名为备份而非保留为入口）
- [x] 2.3 移除 ICLR 模板材料：`Paper/Template_for_ICLR_2025_Conference_Submission/`、`Paper/iclr2025_conference.sty`、`Paper/iclr2025_conference.bst`
- [x] 2.4 全库搜索并消除对 `iclr2025_conference` 的引用（确保不会隐式依赖 ICLR 模板）

## 3. 构建产物与仓库卫生

- [x] 3.1 明确并执行 LaTeX 构建产物处理策略（删除产物并/或完善 `.gitignore` 覆盖 `Paper/*.aux/*.log/*.fls/*.fdb_latexmk/*.out/*.bbl/*.blg/*.pdf`）
- [x] 3.2 处理历史备份文件策略（`Paper/main.bak*`、`Paper/main.tex.bak` 等：保留、迁移到归档目录或删除）
- [x] 3.3 更新 `Paper/tmm_submission_checklist.md` 或新增说明，明确唯一入口与编译命令（`latexmk -pdf Paper/main.tex`）

## 4. 验证（必须可复现）

- [x] 4.1 运行 `latexmk -pdf Paper/main.tex`，确保编译成功且为 IEEE 双栏输出
- [x] 4.2 检查 IEEE PDF 页数满足初稿 ≤13 页要求（记录页数到 checklist）
- [x] 4.3 重新编译 `Paper/supplementary.tex`（若保留），确认不受入口迁移影响
