# Audio-agent 项目整理基线清单

**采集日期：** 2026-07-30  
**分支：** `tmm-major-revision-hard-split`  
**状态：** 只读盘点；本文件未移动、删除、恢复、暂存或提交任何既有资产。

## 1. 安全边界

- 工作区已有 115 个未暂存删除（11,337 行），仅涉及 `Docs/superpowers/` 和 `openspec/`；它们是受保护的既有用户改动，不属于本次整理目标。
- `.env` 和 `.env.local-backup-before-pull-20260503193810` 被 Git 跟踪。盘点未读取其内容；后续只可通过无回显的密钥迁移流程处理。
- 本清单按“逻辑资产”而非逐文件列举；机器可读的动作列表见同目录的 `2026-07-30-project-organization-manifest.csv`。

## 2. 已确认的权威关系

| 范围 | 已验证事实 | 整理结论 |
| --- | --- | --- |
| 插件运行入口 | `Audio-agent.jucer` 与 C++ 调用均指向 `Source/llm.py`、`Source/sql.py` | `Source/` 保持当前运行权威；不得提前删除或改名。 |
| Python 重构 | `Source_new/` 有模块化实现和测试，但尚未被插件入口引用 | 标记为 `MIGRATE_AFTER_SMOKE`，先做集成 smoke test，再决定接入或归档。 |
| 当前论文源 | `Paper/README.md` 指定 `Paper/` 为当前工作区；`Paper/content.tex` 的 SHA-256 为 `93121640…b77a39` | 推荐把 `Paper/` 设为唯一可编辑论文源。 |
| 上传包副本 | `Paper/submission/source/content.tex` 及两个 `TMM_source_package.zip` 内的 `content.tex` 都是 `93121640…b77a39` | `Paper/submission/` 是与当前工作源匹配的上传包。 |
| 历史论文快照 | 原 `Paper_submission/source/content.tex` 为 `7f341120…ecf6d6`，与 zip 内源码不同 | 已完整迁入 `archive/Paper_submission_snapshot_20260730/`，保留其独立身份。 |

## 3. 数据与实验资产

| 资产 | 规模与状态 | 分类 | 后续动作 |
| --- | --- | --- | --- |
| `Data/Audio_Synthetic/` | 351 MB，5,277 文件；98 tracked、5,179 ignored | `KEEP_GENERATED_DATA` | 保留音频与缓存；生成新的覆盖率/参数 manifest。 |
| `Data/External_1267_211/` | 203 MB，1 个 ignored 原始 JSON | `KEEP_EXTERNAL_RAW` | 保持不可变；记录来源、许可证和 SHA-256。 |
| `Data/TMM_Synth_preflight/`、`Data/TMM_Synth_v1/` | 各 12 KB，tracked | `KEEP_PROTOCOL_FIXTURE` | 保留为小型协议/测试夹具。 |
| `Experiments/` | 286 MB，627 文件；314 tracked、314 ignored | `KEEP_EVIDENCE_SURFACE` | 不按大小清理；后续将输出规范为 `outputs/<run_id>/`。 |
| `Experiments/E9_TMMMajorRevision/` | 77 MB；72 tracked、13 ignored | `KEEP_EVIDENCE_SURFACE` | 各 seed 结果哈希不同，必须作为独立运行保留。 |
| `Experiments/dataset_full_vectors.backup_20260228_144845.json` | 184 MB，ignored | `MIGRATE_AFTER_SEMANTIC_AUDIT` | 不与外部 JSON 合并；先比较记录数、schema、数据版本与生成命令。 |
| `Experiments/common/dataset_full_vectors.json` | 8.6 MB，ignored | `MIGRATE_AFTER_SEMANTIC_AUDIT` | 与原始 JSON 哈希不同，不能按重复文件处理。 |
| `musiccaps_guitar_solo/` | 188 MB，149 ignored WAV | `KEEP_EXTERNAL_EVAL_DATA` | 作为本机评测数据登记来源与许可，不入普通 Git。 |

### 数据完整性观察

- `Data/Audio_Synthetic/` 有 1,057 个 WAV；Wav2Vec2 和 MFCC 均完整覆盖，TRR 与 CLAP 各缺 5 个特征文件。
- 缺失项均为：`Base_TRR_Advantage_for_{Dry_Funk,Math_Rock_Crystal,Reverse_Psychedelic,Saturated_Rhythm,Tweed_Breakup}`。
- 这些项目应在后续 manifest 中明确标为 `missing_feature`、`not_applicable` 或补算结果；不能因缺缓存而删除原始音频。
- `Data/dataset_metadata.json` 的 `file_count: 1319` 与当前目录规模需要进行语义核对后再更新，不能直接把该字段当作可删除依据。

### 不可去重的关键 JSON

| 文件 | SHA-256 |
| --- | --- |
| `Data/External_1267_211/dataset/dataset_full_vectors_1267.json` | `077577c654e360fa7cce4328c6e2c263773ac14d8c8331e5ccebe29e54129c28` |
| `Experiments/dataset_full_vectors.backup_20260228_144845.json` | `1bace867fcba6c36613d1e0d96f3126ab49c628e936ae5a347d01a40cce05ecb` |
| `Experiments/common/dataset_full_vectors.json` | `c8e7ca54a6a8e9373b44e929730f7064bc24a50a75542b06bb883d910c81244c` |

`Experiments/dataset_full_vectors.json` 是到外部 JSON 的软链接，保留该链接即可，不创建新的全量副本。

## 4. 运行状态、缓存与可回收候选

| 资产 | 现状 | 分类 | 清理前置条件 |
| --- | --- | --- | --- |
| `audio_info.db`、`music_info.db` | tracked SQLite 数据库 | `RUNTIME_STATE_DECISION` | 先决定其是否为可公开的 seed 数据；真实运行状态应迁入 ignored 位置。 |
| `vector_db/` | tracked Chroma 向量库 | `RUNTIME_STATE_DECISION` | 用配置统一其位置后，验证检索读写。 |
| `C:\Users\Public\Documents\Supertonal DSP/vector_db/` | 1.1 MB ignored 本机向量库 | `MIGRATE_AFTER_RUNTIME_SMOKE` | 不能与 `vector_db/` 盲目合并；先确认 collection 与数据来源。 |
| `test_rag_db/` | 168 KB ignored | `TEST_FIXTURE_OR_LOCAL_STATE` | 由测试引用关系决定保留位置。 |
| `.venv/` | 285 MB ignored Linux 环境 | `KEEP_LOCAL_ENV` | 保留当前可用环境。 |
| `.venv.macos-broken-20260727/` | 1.3 GB ignored，含 macOS 二进制 | `RECLAIM_CANDIDATE` | 在当前 `.venv` 重建/测试通过后，获明确删除授权再清理。 |
| `.opencode/node_modules/` | 约 58 MB 可再生本机依赖 | `RECLAIM_CANDIDATE` | 确认对应工具可由 lockfile 重装后再清理。 |
| `__pycache__/`、`.pytest_cache/`、`*.log` | 本机缓存/日志 | `RECLAIM_CANDIDATE` | 仅清理本次产生或明确确认的缓存，不触碰证据日志。 |

## 5. 归档与去重候选

- `Paper_submission/TMM_source_package.zip` 与 `Paper/submission/TMM_source_package.zip` 哈希相同：`8f8467cde626…cd5ff2f12`。
- 三份 supplementary PDF（`Paper_submission/`、`Paper/submission/`、`Paper/`）哈希相同：`6c4cda315065…f5c81b`。
- 这类重复的空间收益有限，但会产生提交版本漂移风险。下一阶段应仅保留一份上传工件，并在其旁保留 `SHA256SUMS` 和来源说明；其余副本先归档，不直接删除。
- `archive/` 已是有时间戳的历史层，应保留；不得把当前可编辑论文或有效实验输出混入其中。

## 6. 后续最小迁移顺序（Phase 3+）

1. 新增数据与运行产物的 manifest 模板，并将每个实验输出绑定到数据哈希、配置、seed 和代码版本。
2. 统一 Python/C++ 配置中的数据库、向量库和数据根路径；通过单个检索 smoke test 验证后再移动本机状态。
3. 审核 `Research/` 与 `docs/` 的交叉引用后，再决定是否合并文档根；当前不做目录重命名。
4. 单独审计根目录 `debug_rag_init.py` 的调用关系后，再确定其是否迁入 `Source/` 或测试工具目录。
5. 最后才处理获授权的可再生缓存与失效环境。

## 7. 后续动作的验收门槛

- 每次移动前后：`git status --short` 只出现预期路径变化，当前 115 个删除保持原样。
- 数据移动前后：关键 JSON 的 SHA-256、文件计数与软链接目标不变。
- 运行状态迁移后：SQLite 完整性检查和一次 RAG/retrieval smoke test 通过。
- 论文整理后：工作源、上传 zip 内源码和 PDF 的哈希/编译关系一致。
- 缓存删除前：确认其可从锁文件、依赖声明或生成脚本恢复。

## 8. Phase 2 已执行的可恢复迁移

| 原路径 | 新路径 | 验证 |
| --- | --- | --- |
| `Paper_submission/` | `archive/Paper_submission_snapshot_20260730/Paper_submission/` | 保留完整目录与源文件差异。 |
| `Paper_submission.zip` | `archive/Paper_submission_snapshot_20260730/Paper_submission_snapshot_20260730.zip` | zip 内保留原始 `Paper_submission/` 顶层结构。 |
| `retrieval_comparison_report.md` | `archive/legacy_reports/2025-01-09_retrieval_comparison_report.md` | 原文件明确标注为 N=5 legacy 报告；研究计划已更新引用。 |
| 两份纹理比较 CSV | `Experiments/TextureResonance/outputs/` 下按日期和样本量命名 | 分别保留 N=5 与 N=30 结果，不覆盖。 |
| `guitar_solo_evaluation_metadata.csv` | `Data/metadata/guitar_solo_evaluation_metadata.csv` | `Source/compute_fad.py` 默认路径已同步。 |

本阶段没有删除任何资产，也没有暂存或提交变更。
