# Self Check

- 报告工作区: `/home/xyh/code/Audio-agent/docs/report/audio-agent-experiment-evidence-archive`
- error: 0
- warn: 15
- info: 0

## 编译审查摘要

- compile review 未发现 warning。

## 金字塔结构报告

| 检查项 | 命中数 | 状态 |
| --- | ---: | --- |
| 结构 / 项目进度 | 0 | 通过 |
| 模板占位 | 0 | 通过 |

## 图解覆盖率报告

| 检查项 | 命中数 | 状态 |
| --- | ---: | --- |
| 图表 / TikZ / PGFPlots | 0 | 通过 |
| 图表引用 | 0 | 通过 |

## 信息密度报告

| 检查项 | 命中数 | 状态 |
| --- | ---: | --- |
| 低密度句式 / 伪列表 | 0 | 通过 |
| 术语漂移 | 4 | 需统一 |

## 模块级细节与证据报告

| 检查项 | 命中数 | 状态 |
| --- | ---: | --- |
| 科研证据链 | 0 | 通过或不适用 |
| 工程运行就绪 | 3 | 需补运行矩阵 |
| 模块级设计 | 0 | 通过或不适用 |
| Repo 事实外溢 | 8 | 需收回项目进度 |

## 编译审查问题

- 无。

## 结构问题

- 无。

## 模板占位提醒

- 无。

## 低信息密度句式命中

- 无。

## 仓库现状渗透提醒

- [WARN] 00-executive-summary.tex:3 非 `项目进度` 章节出现仓库现状表述：本报告将 Audio-Agent 当前代码库中的实验材料整理为一份学术论文式证据报告。报告的核心问题是：在可编辑音频效果参数控制任务中，基于二阶纹理统计的 Texture Resonance Retrieval（TRR）是否比当前已评估的文本检索与音频嵌入检索基线更能找到参数空间上接近目标的可执行预设。本文结论限定于当前 guitar-effects 检索基准、当前数据切分和当前仓库产物下的检索式参数对齐证据；通用音频理解模型优越性和完整自动化音频系统端到端效果均不在本报告的证据范围内。
- [WARN] 01-project-overview.tex:34 非 `项目进度` 章节出现仓库现状表述：本文的贡献边界包括三个层面。本文将当前代码库中的主实验收敛到一个可审计证据链，其中 P0 E2 是主要客观检索证据，P0 E3 是真实退化下的 fusion robustness 证据。本文还根据代码实现解释 TRR、文本检索、音频嵌入检索、质量感知融合和评价指标之间的关系。本文进一步明确标注尚不能支撑论文主张的材料，包括 deprecated Protocol-B、direct regression、learned reranker 和跨域鲁棒性结果。该边界使得报告主张更强但仍可复核。
- [WARN] 01-project-overview.tex:36 非 `项目进度` 章节出现仓库现状表述：因此，本文不把 Audio-Agent 描述成已经完成验证的全栈音频智能体。更准确的定位是：Audio-Agent 当前代码库为 retrieval-grounded editable audio effect control 提供了一个实验性证据面，其中 TRR 是最有统计支持的核心检索表示，融合和端到端插件链路仍处于补充、诊断或探索阶段。
- [WARN] 02-background-and-context.tex:7 非 `项目进度` 章节出现仓库现状表述：在当前代码库中，实验证据与产品链路应当分开理解。产品链路包含 DeepSeek 风格解析、MusicGen 音频生成、JUCE 插件参数导入与离线渲染；实验链路则主要围绕外部 1267 条 benchmark 数据、缓存向量和参数 JSON 展开。本文的主结论来自实验链路，尚未覆盖完整插件输出音频质量。这个区分很重要，因为参数空间评价能够支持 retrieval prior 的有效性，却不能自动证明端到端听感最优。
- [WARN] 02-background-and-context.tex:9 非 `项目进度` 章节出现仓库现状表述：现有论文材料已经对主张进行了收敛。提交面文稿将主贡献限定为 retrieval-grounded editable preset control，并在本轮根据用户已 double check 的 P0 E3 结果，把 real-audio degradation robustness 从“待补实验”升级为“当前退化集合下的 fusion 证据”。本报告仍将证据层分为 source claim、repo-observed fact、已确认正式实验数据、design intent 和 report synthesis。凡是只存在于计划或脚本中的内容，仍不能被写成已经验证的事实；P0 E2/E3 则按已确认真实、完整、正确的正式实验数据处理。
- [WARN] 06-algorithm-and-workflow.tex:66 非 `项目进度` 章节出现仓库现状表述：代码库中存在产品链路与实验链路两套路径。产品链路从用户文本和可选音频出发，通过 DeepSeek 解析风格与参数，经 \texttt{import\_params.json} 传入 JUCE 插件，再由插件加载参数和音频并离线渲染。该链路说明 Audio-Agent 具备可执行插件控制的工程背景，但本文不把它作为主实验结果来源，因为主实验没有评价完整插件输出音频质量。
- [WARN] 06-algorithm-and-workflow.tex:68 非 `项目进度` 章节出现仓库现状表述：实验链路更适合作为论文证据。数据加载由 common dataset loader 负责，优先读取外部 1267 条数据集 JSON，再回退到 repo 内 JSON 或 SQLite 合并。TRR 检索由 common TRR adapter 实现，优先使用缓存向量。直接检索比较与 Protocol-C 分别由 AblationStudies 下的 comparison 与 robustness 脚本驱动，评价指标由公共 evaluator 计算。
- [WARN] 07-system-and-resource-design.tex:32 非 `项目进度` 章节出现仓库现状表述：第三层是历史与待补目录，包含 Protocol-B、legacy retrieval report、direct regression 和 future reranker。这个结构有助于在写作中持续区分已确认正式实验数据、repo-observed fact 与 design intent。

## 图文并茂与 TikZ 检查

- 无。

## 科研证据链检查

- 无。

## 工程运行就绪检查

- [WARN] 工程型报告缺少 owner / 责任归属：请标明关键组件的维护责任。
- [WARN] 工程型报告缺少 interface boundary：请说明 API、模块和数据契约的边界。
- [WARN] 工程型报告缺少 compatibility bridge 退役条件：请说明兼容层退出标准。

## 模块级设计检查

- 无。

## 术语首次定义检查

- 无。

## 图表引用检查

- 无。

## 术语与概念一致性提醒

- [WARN] 检测到可能的术语或标识写法漂移：`Protocol-A`×10, `protocolA`×2
- [WARN] 检测到可能的术语或标识写法漂移：`Protocol-B`×9, `protocolB`×1
- [WARN] 检测到可能的术语或标识写法漂移：`Protocol-C`×12, `protocolC`×1
- [WARN] 检测到可能的术语或标识写法漂移：`theta`×14, `theta_`×2

## 建议动作

- 先修复 error；编译审查里的 warning 也按 error 处理，不能作为可发布状态。
- 若命中了低信息密度句式，优先改成直接陈述信息的写法。
- 若一段中已经出现多个小点，优先改成“总括句 + itemize / enumerate + \item”或分段小点，而不是继续堆叠 `第一，第二，第三`。
- 若命中了伪列表，直接改成 LaTeX 列表环境，不要在 `.tex` 正文里保留 `- `、`* `、`1. ` 这类写法。
- 若 repo 现状扩散到非 `项目进度` 章节，优先把状态事实收回 `项目进度`。
- 若关键章节尚未配图，优先补 TikZ / PGFPlots 图，而不是把结构信息继续压回长段落。
- 若科研证据链缺口存在，先补 claim/evidence/source/limitation/confidence 台账，再补 baseline、ablation、reproducibility 与 failure-case 表。
- 若工程运行就绪缺口存在，先补 source-of-truth、owner、runbook/rollback、接口边界与 compatibility bridge 退役条件。
- 若术语存在多种写法，统一摘要、标题、图注、表头和正文中的版本。
