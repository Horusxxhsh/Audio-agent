# TMM 现有数据优先实验包

## 0. 目标

在 **不新增数据采集**、尽量少改论文主叙事的前提下，利用当前仓库中已有的 benchmark、听测和渲染资产，补出一组对 IEEE TMM 审稿意见最有杀伤力的实验。

核心策略不是“多做实验”，而是用最少的新工作换取最大的 **可信度增益**：

1. 先证明 benchmark 不是因为 leakage / easy split 才好看。
2. 再证明 TRR 的收益确实来自 texture-aware second-order statistics。
3. 最后补参数指标与可听结果之间的桥。

## 1. 边界条件

### 1.1 本轮允许做的事

- 使用现有 `Experiments/dataset_full_vectors.json` 与 `Data/External_1267_211/` 中已存在的数据资产
- 重切 split、重跑 retrieval、补统计、补听测分析
- 在 renderer 支持的子集上补 re-rendered audio evaluation
- 在已有 raw listening ratings 上补更严谨的相关性与 failure analysis

### 1.2 本轮不作为主路径的事

- 新采集非吉他域数据
- 把 AEM / personalization 拉回主文
- 把 synthetic Protocol-C 继续扩成主证据
- 在没有完整缓存和 coverage 之前，把 CLAP / PaSST / PANNs 强行写成“已完成”

## 2. 优先级总览

| 优先级 | 实验 | 主要回应 reviewer concern | 新数据需求 | 预期收益 | 风险 |
|---|---|---|---|---|---|
| P0 | 分组切分 + leakage 审计 | 数据泄漏、外部有效性、benchmark 难度 | 无 | 极高 | 结果可能显著下降 |
| P0 | 同源变体 hard subset | “系统只是在认 source/riff” | 无 | 极高 | 需要定义 base/source group |
| P0 | TRR 机制消融（固定容量） | 新颖性偏薄、二阶统计是否必要 | 无 | 极高 | 需要小心控制表示维度/预算 |
| P1 | top-k / selective retrieval 分析 | “只是 top-1 preset retrieval” | 无 | 高 | 叙事要克制 |
| P1 | renderer-compatible audio evaluation | 参数指标与感知质量脱节 | 无 | 高 | renderer 覆盖有限 |
| P1 | listener-aligned metric analysis | 参数指标是否真和听感对齐 | 无 | 中高 | 听测协议信息仍有限 |
| P2 | 强 baseline rescue（CLAP 优先） | baseline 不够强 | 无新数据，但需新缓存/依赖 | 高 | 计算与环境不稳 |

## 3. 必做实验

### E0A: 分组切分 + leakage 审计

**目标**

把当前随机 `SongName` 切分，升级为以 `base source / source group / preset family` 为单位的 group-aware split，并给出 exact duplicate + near duplicate 审计。

**为什么必须做**

这是当前最硬的 reviewer risk。现有 [make_splits.py](/Users/xyh/Code/Audio-agent/Experiments/tmm/make_splits.py) 是随机切分，而 [dataset_loader.py](/Users/xyh/Code/Audio-agent/Experiments/common/dataset_loader.py) 已经说明大量 `"<Base> - <Suffix>"` 会回落到同一底层音频。这个问题不解决，后面所有 improvement 都容易被怀疑。

**建议实现**

- 定义 `base_name = SongName.split(" - ", 1)[0].strip()`
- 用 `base_name` 作为最小 group 单位做 train/val/test split
- 对 `Style` / `Feature` 做家族标签统计，输出 split coverage 表
- 对每个 split 运行 exact duplicate + near duplicate scan
- near duplicate 不只报全库，还要报 **跨 split pair**

**优先触达文件**

- 修改: [make_splits.py](/Users/xyh/Code/Audio-agent/Experiments/tmm/make_splits.py)
- 修改: [leakage_scan.py](/Users/xyh/Code/Audio-agent/Experiments/tmm/leakage_scan.py)
- 复用: [dataset_loader.py](/Users/xyh/Code/Audio-agent/Experiments/common/dataset_loader.py)
- 复用: [dataset_audit.py](/Users/xyh/Code/Audio-agent/Experiments/tmm/dataset_audit.py)

**交付物**

- `Experiments/tmm/splits/<name>/seed*/{train,val,test}.txt`
- `Experiments/tmm/leakage_report_<name>.json`
- `tables/dataset_split_stats.csv`

**执行提示**

- 主实验脚本已经可以直接消费生成好的 `test.txt`
- 示例:
  `python3 Experiments/AblationStudies/direct_retrieval_comparison.py --query_split file:Experiments/tmm/splits/<name>/seed0/test.txt`
  `python3 Experiments/AblationStudies/llm_retrieval_comparison.py --query_split file:Experiments/tmm/splits/<name>/seed0/test.txt`
  `python3 Experiments/AblationStudies/robustness_test.py --query_split file:Experiments/tmm/splits/<name>/seed0/test.txt`

**成功标准**

- 无 exact duplicate 跨 split
- near duplicate 有完整报告
- 论文正文能明确写出 split principle，而不是模糊说 held-out

**风险**

- 结果可能比当前下降很多

**如果结果下降怎么办**

- 这不是坏事。它能把论文从“可能泄漏”变成“严格协议下仍然有效/或只在某些子集有效”

### E0B: 同源变体 hard subset

**目标**

从现有 `"<Base> - <Suffix>"` 变体中构造一个 hard subset，专门测试“同一 source 下，不同 effect variant 的可分性”。

**为什么值得做**

这个实验几乎是 reviewer concern 的镜像检验。若 TRR 仍能在同源变体中优于 mean pooling，说明它捕获的是 effect texture，而不是 source identity。

**建议实现**

- 以 `base_name` 分组
- 只保留 group size >= 3 或 >= 4 的 source family
- 对每个 query，检索候选限定在“不同 variant but same base family”或“排除完全同名项，只保留相邻难例”
- 报单独的 hard-subset 表

**优先触达文件**

- 修改: [direct_retrieval_comparison.py](/Users/xyh/Code/Audio-agent/Experiments/AblationStudies/direct_retrieval_comparison.py)
- 新增: `Experiments/tmm/build_hard_subset.py`

**交付物**

- `tables/hard_subset_main.csv`
- `tables/hard_subset_per_query.csv`

**执行提示**

- 当前最小落地路径是直接复用 [direct_retrieval_comparison.py](/Users/xyh/Code/Audio-agent/Experiments/AblationStudies/direct_retrieval_comparison.py)
- 示例:
  `python3 Experiments/AblationStudies/direct_retrieval_comparison.py --hard_subset_mode same_base_exclude_self --hard_subset_min_family_size 3 --dump_csv Experiments/AblationStudies/hard_subset_per_query_metrics.csv`

**当前数据审计结论**

- 基于 `Experiments/dataset_full_vectors.json` 的快速审计显示:
  - `min_family_size >= 3` 时共有 `30` 个 family、`211` 个 eligible query
  - 但其中 `29/30` 个 family 内只有 `1` 组唯一参数配置
  - 只有 `Hard Rock Crunch` family 出现了 `2` 组唯一参数配置
- 这意味着当前数据上的 `same_base_exclude_self` 更像“同 preset 的音频变体检索”，不适合作为主文里的参数判别性证据

**成功标准**

- TRR 相比 mean pooling / text baseline 仍有稳定优势

**风险**

- 样本量变小，统计显著性可能减弱

### E0C: TRR 机制消融（固定容量、固定预算）

**目标**

证明提升来自 second-order texture statistics，而不是表示更大、归一化偶然、或实现细节。

**建议最小消融集**

- mean pooled Wav2Vec2
- Gram
- covariance
- Gram diagonal only
- frame-shuffled Gram
- Frobenius norm on/off
- cosine vs L2 similarity

**关键设计原则**

- 尽量固定下游检索流程
- 尽量控制表示维度或比较预算
- 明确把它写成 “necessity ablation”，不是“实现选型笔记”

**优先触达文件**

- 修改: [direct_retrieval_comparison.py](/Users/xyh/Code/Audio-agent/Experiments/AblationStudies/direct_retrieval_comparison.py)
- 参考: [texture_encoder.py](/Users/xyh/Code/Audio-agent/Experiments/TextureResonance/texture_encoder.py)
- 参考: [compare_texture_representations.py](/Users/xyh/Code/Audio-agent/Experiments/TextureResonance/compare_texture_representations.py)

**交付物**

- `tables/trr_necessity_ablation.csv`
- `figures/trr_ablation_barplot.pdf`

**成功标准**

- 至少回答 2 个问题:
  - 二阶统计是否比一阶统计更好
  - 归一化/相似度是否关键

**风险**

- 如果 Gram 优势只在部分子集存在，就要改写 claim 为“texture-sensitive subset 上更有效”

## 4. 推荐实验

### E1A: Top-k editable retrieval 分析

**目标**

把论文从 “top-1 preset retrieval” 往 “editable candidate generation” 推一步。

**建议分析**

- top-1
- oracle@k
- mean@k
- weighted mean@k
- top-1 margin / entropy 与错误率的关系

**为什么有用**

如果 oracle@k 很高但 top-1 不稳定，你的系统更像一个 “good candidate proposer”，这仍然符合 DAW 编辑工作流。

**优先触达文件**

- 修改: [direct_retrieval_comparison.py](/Users/xyh/Code/Audio-agent/Experiments/AblationStudies/direct_retrieval_comparison.py)
- 利用现有 `TopKMean` / `TopKWeightedMean` 逻辑

**交付物**

- `tables/topk_editable_control.csv`
- `figures/risk_coverage_curve.pdf`

### E1B: renderer-compatible re-rendered audio evaluation

**目标**

在 renderer 支持的参数子集上，把预测参数重新渲染为音频，再算音频空间指标。

**为什么有用**

它不能完全解决 identifiability，但能显著削弱 reviewer 对“你只看参数空间”的攻击。

**建议范围**

- 不追求覆盖全模块
- 诚实限定为 renderer-compatible subset
- 在这个子集上比较 TRR / Wav2Vec / Text-RAG

**优先触达文件**

- 参考: [README.md](/Users/xyh/Code/Audio-agent/Experiments/tmm/README.md)
- 参考: [synth_dataset.py](/Users/xyh/Code/Audio-agent/Experiments/tmm/synth_dataset.py)

**交付物**

- `tables/audio_space_eval_subset.csv`
- `tables/renderer_subset_manifest.csv`

### E1C: listener-aligned metric analysis

**目标**

直接问：哪些 objective metrics 真能解释已有 listening scores，哪些不能。

**为什么有用**

这会把 reviewer 对 metric 合理性的批评，转化为你的主动讨论，而不是被动挨打。

**建议实现**

- 清洗听测数据
- 用 `email` 作为 participant id，而不是 `session_test_id`
- 分 trial group 计算 metric-rating correlation
- 输出 holding cases 和 failure cases

**优先触达文件**

- 修改: [correlation_analysis.py](/Users/xyh/Code/Audio-agent/Experiments/E4_MetricCorrelation/correlation_analysis.py)
- 复用: [mushra_analysis.py](/Users/xyh/Code/Audio-agent/Experiments/mushura/mushra_analysis.py)
- 复用: [results_report.md](/Users/xyh/Code/Audio-agent/Experiments/mushura/results_report.md)

**交付物**

- `tables/metric_perception_correlation.csv`
- `tables/perception_independent_cases.csv`

## 5. 条件性实验

### E2A: 强 baseline rescue

**目标**

在不换数据的前提下补至少一个真正强的 retrieval baseline。

**推荐顺序**

1. 先 CLAP
2. 再看 PaSST
3. 最后才是 PANNs

**原因**

- reviewer 需要的是“不是只和弱 baseline 比”
- 你不一定要三者全齐，先补一个 strong external baseline 就能明显改善说服力

**现实限制**

当前 coverage 工件显示 PaSST / PANNs 还没真正跑通，不能把这条当短平快任务。

**优先触达文件**

- [run_comparison.py](/Users/xyh/Code/Audio-agent/Experiments/E2_SOTABaselines/run_comparison.py)
- [precompute_embeddings.py](/Users/xyh/Code/Audio-agent/Experiments/baselines/precompute_embeddings.py)

**建议止损点**

- 如果 1 天内连 CLAP cache 都稳定不下来，就停止，不要拖累 P0 实验

## 6. 明确不建议现在做的事

- 再补 synthetic Protocol-C 主表
- 再补 cache-only latency 表
- 把 personalization / AEM 拉回主文
- 做“更大系统”叙事包装
- 在 response letter 里提前承诺尚未跑通的强 baseline

## 7. 推荐执行顺序（3-5 天版本）

### Day 1

- 做 E0A 的 group-aware split 与 leakage audit
- 同时导出 split coverage 表

### Day 2

- 做 E0B 的同源 hard subset
- 重跑 TRR / Wav2Vec / Text-RAG / FeatureNN

### Day 3

- 做 E0C 的机制消融
- 形成一张 “why Gram helps” 的 necessity ablation 表

### Day 4

- 做 E1A 的 top-k / selective retrieval 分析
- 若渲染链稳定，开始 E1B 的 renderer-compatible subset

### Day 5

- 做 E1C 的 metric-perception correlation
- 汇总哪些 objective metrics 可保留在主文，哪些应降级为 proxy

## 8. Go / No-Go 规则

### 可以直接支撑 rebuttal / major revision 的最小组合

- E0A 已完成
- E0B 或 E0C 至少完成一个
- E1A 或 E1C 至少完成一个

### 可以显著增强接收概率的组合

- E0A + E0B + E0C
- 再加 E1B 或 E2A 任意一个

### 如果时间只够做一件事

- 只做 E0A

理由：没有严谨 split 和 leakage 审计，其他所有 improvement 都容易被 reviewer 继续质疑。

## 9. 对论文叙事的直接影响

如果以上实验补出来，主文建议收束为：

- **主证据**: group-aware benchmark 下，TRR 在 texture-sensitive retrieval 上优于 first-order baselines
- **机制证据**: Gram-style second-order statistics 的增益在 fixed-capacity ablation 中可复现
- **工作流证据**: top-k editable retrieval 与 listening-linked analysis 表明系统价值不只等于 top-1 exact preset hit

不要把新实验包装成“系统全能”，而是把它们作为 **证据结构加固**。
