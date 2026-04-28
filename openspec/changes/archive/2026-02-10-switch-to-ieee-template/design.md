## 上下文

论文目录 `Paper/` 当前同时保留 ICLR 模板入口（`Paper/main.tex` + `iclr2025_conference.*` + `Template_for_ICLR_2025_Conference_Submission/`）与 IEEE 构建入口（`Paper/main_ieee.tex`）。这造成：
- “默认入口”与投稿目标（IEEE Transactions / TMM）不一致；
- 模板、构建产物、历史备份混杂，打包与复现成本上升；
- IEEE 合规检查（页数、摘要、PDF eXpress）需要一个稳定、单一的入口与模板版本。

本变更将以用户提供的官方模板包 `Paper/IEEE-Transactions-LaTeX2e-templates-and-instructions.zip` 为源，统一为单入口 IEEEtran 构建，并明确清理策略。

## 目标 / 非目标

**目标：**
- 将 `Paper/main.tex` 变为 IEEEtran journal 模板的唯一入口（与投稿目标一致）。
- 固定使用 zip 内的 `IEEEtran.cls`（拷贝到 `Paper/IEEEtran.cls`，确保环境一致）。
- 保持 `Paper/content.tex`（正文）与 `Paper/figures/`（图表）复用，尽量减少正文迁移成本。
- 明确清理范围：移除 ICLR 模板目录/文件、移除冗余入口 `main_ieee.tex`，并按约定处理构建产物。
- 用 `latexmk` 验证：`Paper/main.tex` 可编译，页数仍满足 IEEE ≤13（初稿）要求。

**非目标：**
- 不重写论文内容、实验结果或图表（只做模板/工程结构迁移）。
- 不在本变更中解决所有排版警告（如 overfull hbox），除非影响投稿/编译。
- 不引入新的引用管理体系（继续沿用现有 `reference.bib` 与当前 bib 样式策略）。

## 决策

1) **单入口文件命名**
- 决策：仅保留 `Paper/main.tex` 作为唯一入口。
- 备选：保留 `Paper/main_ieee.tex` 并删除 `main.tex`。
- 理由：投稿与打包通常期望默认 `main.tex`；减少“入口选择错误”的风险。

2) **IEEE 模板来源与版本锁定**
- 决策：从 zip 解出 `IEEEtran.cls` 到 `Paper/IEEEtran.cls` 并优先使用本地版本。
- 备选：依赖 TeX Live 自带 `IEEEtran.cls`。
- 理由：锁定版本，避免不同环境造成版式差异或编译行为不一致。

3) **正文与入口分离**
- 决策：保持 `Paper/content.tex` 为正文主体，入口只负责模板、包、宏、作者信息、bibliography style。
- 备选：将正文重新合并回单文件。
- 理由：最小迁移；与现有工作流兼容；便于继续迭代内容。

4) **清理策略分层**
- 决策：强制清理 ICLR 模板（目录与 `iclr2025_conference.*`）与冗余入口（`main_ieee.tex`）；构建产物/历史备份作为“可选清理”，由 tasks 明确是否移除并确保 `.gitignore` 覆盖。
- 备选：全部保留，仅不再使用。
- 理由：ICLR 模板与目标投稿不一致，保留会造成混淆；构建产物删除需尊重仓库习惯，因此显式列为可选并在任务中验证。

5) **参考文献与引用包**
- 决策：沿用当前 IEEE 入口中的 `natbib` + `IEEEtranN` 风格（以现有可编译配置为基线）。
- 备选：切换到 `IEEEtran` 推荐的 `\bibliographystyle{IEEEtran}`（非 natbib）。
- 理由：当前已经可编译且满足 IEEE 数字引用风格；减少迁移风险。

## 风险 / 权衡

- **IEEEtran 与现有宏/包冲突** → 缓解：迁移时先最小化包列表；以 `main_ieee.tex` 的已工作配置为基线迁移到 `main.tex`。
- **本地 `IEEEtran.cls` 覆盖系统版本导致团队差异** → 缓解：明确将 `Paper/IEEEtran.cls` 纳入版本控制，并在文档中说明。
- **清理构建产物可能影响他人习惯/调试** → 缓解：将“产物删除”作为可选任务；优先通过 `.gitignore` 规范化。
- **单入口切换导致脚本/CI 失效** → 缓解：在任务中搜索并更新任何引用 `main_ieee.tex` 的脚本/文档。

