## 为什么

当前论文目录同时保留 ICLR 模板与 IEEE 构建入口（`Paper/main.tex` vs `Paper/main_ieee.tex`），导致：
- 投稿目标（IEEE Transactions/TMM）与默认入口不一致，容易误用模板；
- 冗余模板与构建产物混杂，增加打包与复现成本；
- IEEE 投稿合规检查（页数、摘要、PDF eXpress）需要一个稳定、单一的 LaTeX 入口与锁定的模板版本。

因此需要将论文统一迁移到官方 IEEE Transactions LaTeX 模板（来自 `Paper/IEEE-Transactions-LaTeX2e-templates-and-instructions.zip`），并清理无关模板/入口，确保后续修改与编译链路稳定可复现。

## 变更内容

- 将 `Paper/main.tex` 迁移为 IEEEtran journal 模板的**唯一入口**（取代 ICLR wrapper 与 `main_ieee.tex` 入口分裂）。
- 从 zip 解出并在 `Paper/` 中固定使用 `IEEEtran.cls`（锁定模板版本，避免环境差异）。
- 统一引用与编译方式（`latexmk -pdf Paper/main.tex`）。
- 清理 `Paper/` 内不再使用的 ICLR 模板与冗余入口文件；按约定处理构建产物与历史备份文件（保留/移除策略在设计中定义）。

## 功能 (Capabilities)

### 新增功能
- `paper-ieee-template`: 将论文 LaTeX 工程统一为 IEEE Transactions 模板，提供单一入口与可复现的构建方式，并定义清理/打包规则。

### 修改功能

（无）

## 影响

- 受影响目录：`Paper/`（入口文件、cls/sty/bst、模板与构建产物清理）
- 受影响构建命令：LaTeX 编译入口从 `Paper/main_ieee.tex`/`Paper/main.tex` 分裂变为仅 `Paper/main.tex`
- 受影响投稿流程：IEEE 页数/摘要合规检查与最终打包结构

