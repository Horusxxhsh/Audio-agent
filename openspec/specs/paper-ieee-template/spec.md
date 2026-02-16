# `paper-ieee-template` 规范

## Purpose

（待定：描述该 capability 的目的与范围。）

## Requirements

### 需求：论文必须使用官方 IEEE Transactions LaTeX 模板并锁定版本
论文 LaTeX 工程必须使用用户提供的模板包 `Paper/IEEE-Transactions-LaTeX2e-templates-and-instructions.zip` 中的 `IEEEtran.cls`，并将其复制到 `Paper/IEEEtran.cls` 以锁定模板版本，避免不同 TeX 环境导致的版式差异。

#### 场景：模板版本固定
- **当** 用户在任意机器上编译论文
- **那么** `Paper/main.tex` 必须优先使用仓库内的 `Paper/IEEEtran.cls`（而非系统内置版本），且编译结果应在版式上保持一致

### 需求：`Paper/main.tex` 必须是唯一的 IEEE 编译入口
仓库必须将 `Paper/main.tex` 作为唯一编译入口文件，并采用 `\\documentclass[journal,10pt]{IEEEtran}`（或等价 IEEE Transactions journal 配置）。不得再保留会造成歧义的第二入口（例如 `main_ieee.tex`）作为默认入口。

#### 场景：单入口编译
- **当** 用户运行 `latexmk -pdf Paper/main.tex`
- **那么** 论文必须成功编译，且生成 IEEE 双栏 PDF（满足初稿 ≤13 页要求的前提下）

### 需求：必须清理不再使用的 ICLR 模板材料
论文目录中不再使用的 ICLR 模板材料必须从 `Paper/` 中移除，以避免误用与歧义，包括：
- `Paper/Template_for_ICLR_2025_Conference_Submission/`
- `Paper/iclr2025_conference.sty`
- `Paper/iclr2025_conference.bst`
- 任何只为 ICLR wrapper 服务的入口内容

#### 场景：目录中不存在 ICLR 模板依赖
- **当** 用户在 `Paper/` 中搜索 ICLR 模板引用
- **那么** 不应存在对 `iclr2025_conference` 的 `\\usepackage{...}` 或文件依赖

### 需求：必须定义构建产物与备份文件的处理策略
论文目录必须明确并一致地处理 LaTeX 构建产物（如 `*.aux/*.log/*.fls/*.fdb_latexmk/*.out/*.bbl/*.blg`）与历史备份文件（如 `main.bak*`），以降低仓库噪音并提升复现体验。该策略必须在任务清单中体现，并在执行后可验证。

#### 场景：产物策略可验证
- **当** 变更完成后检查 `Paper/` 目录
- **那么** 应满足约定的“保留/删除”策略，并且不会影响 `Paper/main.tex` 的正常编译
