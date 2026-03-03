## 1. Baseline 依赖与运行入口

- [x] 1.1 新增可选依赖清单（例如 `Experiments/requirements_sota.txt`），覆盖 PaSST/PANNs 所需的 `torch/timm` 与统计所需依赖（如 `scipy`），并在 README/脚本帮助中说明安装方式
- [x] 1.2 清理并禁止硬编码 LLM API key：将 `Experiments/AblationStudies/llm_retrieval_comparison.py` 与 `Experiments/AblationStudies/robustness_test.py` 的 key/base_url 改为环境变量读取，并提供缺失变量时的安全失败提示

## 2. Embedding 预计算与缓存（PaSST / PANNs）

- [x] 2.1 新增 `Experiments/common/audio_io.py`（或等价模块）：统一 wav 读取、mono/stereo 处理、采样率转换与分段策略，确保 PaSST/PANNs 使用一致口径
- [x] 2.2 实现预计算脚本：`Experiments/baselines/precompute_embeddings.py`（或等价路径），支持 `--model passt|panns`、`--audio_dir`、`--resume`、`--overwrite`、`--report_out`
- [x] 2.3 生成覆盖率报告：在 N≈1056 的 KB 音频上运行预计算脚本，产出缓存命中/缺失统计与缺失列表文件（本地工件，默认 gitignored）

## 3. SOTA Retriever 适配器（CLAP / PaSST / PANNs）

- [x] 3.1 新增 `Experiments/common/embedding_knn_retriever.py`：抽象“embedding + cosine KNN”检索器（索引、查询、Top‑K 输出统一 schema）
- [x] 3.2 实现 `CLAPRetriever`：从 `*.wav.clap.npy` 读取 embedding（512‑d），并作为 Retrieval-only baseline 接入
- [x] 3.3 实现 `PaSSTRetriever` 与 `PANNsRetriever`：优先读取 `*.wav.passt.npy` / `*.wav.panns.npy`，缺失时给出明确提示并可选择跳过

## 4. Protocol-A：Table III 增强（逐 query + 统计）

- [x] 4.1 扩展 `Experiments/AblationStudies/direct_retrieval_comparison.py`：加入 CLAP/PaSST/PANNs 三条 baseline，确保默认 test=211、kb=1267-211，并写入 per-query CSV
- [x] 4.2 扩展 `Experiments/AblationStudies/objective_stats.py`：兼容新增方法列，输出 Table III 对应的 CI/p/Holm 校正汇总（Markdown + JSON）

## 5. Protocol-B：LLM 透明化与消融（N=211）

- [x] 5.1 改造 `Experiments/AblationStudies/llm_retrieval_comparison.py`：支持 `--test_list`/默认 N=211；新增 `top-k mean/weighted mean + projection` 对照；逐 query 输出 + 统计报告
- [x] 5.2 新增 LLM 输出缓存目录与命名规范（按 query + prompt hash），并在脚本中实现“缓存优先，显式开关才调用网络”
- [x] 5.3 新增 “w/o few-shot” 对照运行模式，并输出与默认设置的 paired 统计差异

## 6. 泄漏审计（few-shot / held-out）

- [x] 6.1 新增审计脚本 `Experiments/tmm/leakage_audit_llm.py`（或等价路径）：检查 few-shot 与 held-out（N=211）在 `SongName/AudioPath/text` 层面的 overlap
- [x] 6.2 让 CI/报告生成在 overlap≠0 时失败（阻断强结论），并输出可归档的 JSON/MD 报告（本地工件，默认 gitignored 或放入 Supplementary 生成目录）

## 7. Protocol-C：Stress Tests + Modality Conflict（N=211）

- [x] 7.1 改造 `Experiments/AblationStudies/robustness_test.py`：默认 N=211；逐 query 输出；统计报告；并在表注/输出中强制标注 `Protocol-C`
- [x] 7.2 新增冲突 stress：实现“自动生成矛盾文本”的构造逻辑与评测输出（α 分布 + ΔL2 等），并生成可写入补充材料的图表/表格数据

## 8. Latency Profiling

- [x] 8.1 新增 `Experiments/latency/profile_latency.py`：端到端与分模块计时（median/p95），记录硬件/环境与重复次数，输出 JSON/Markdown 表
- [x] 8.2 在无 LLM 网络调用条件下提供可复现的 latency 基线（缓存模式），并可选输出“真实 API 调用”耗时（显式开关）

## 9. 主观实验（路线 A）：改名 + 重复测量统计

- [x] 9.1 更新 `Experiments/mushura/mushra_analysis.py`：输出命名收敛为 “Multiple‑Stimulus Listening Test with Hidden Reference”；补齐 Friedman + post‑hoc Wilcoxon(Holm)；在 `results_report.md` 中写入 p-value 与效应量
- [x] 9.2 在 `Paper/content.tex` 与 `Paper/supplementary.tex` 更新术语、方法细节（随机化/界面说明/无 anchor 声明）并引用统计结果位置

## 10. 论文表格与文字更新（TMM 复审提交）

- [x] 10.1 更新 Table III：加入 CLAP/PaSST/PANNs 行，并在补充材料中加入 CI/p/Holm 校正表
- [x] 10.2 更新 Protocol-B/Protocol-C 对应表：统一 N=211；加入 LLM 消融与 modality conflict；补充统计检验与结论边界措辞
- [x] 10.3 新增 latency 表并在实验设置/系统章节中声明计时口径与硬件
