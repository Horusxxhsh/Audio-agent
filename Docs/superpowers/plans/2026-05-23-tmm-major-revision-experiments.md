# TMM 大修补充实验实现计划

> **给执行者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐步实现此计划。步骤使用复选框（`- [ ]`）语法以便跟踪。

**目标：** 完成审稿意见中 8 项关键修订（CRITICAL items）+ 7 项主要修订（MAJOR items），使论文达到可重新提交状态

**架构：** 以现有实验框架（E5_Ablations, E9_TMMMajorRevision, E2_SOTABaselines, E7_HardSplit）为基础，增量补充缺失实验；所有结果通过统一导出器汇总后更新正文（`Paper/content.tex`）和补充材料（`Paper/supplementary.tex`）

**技术栈：** Python, numpy, scipy, Wav2Vec2 (huggingface), PANNs, PaSST, CLAP, FAISS, 统计检验 (scipy.stats)

**Report 对齐：**
- **对应章节：** 编辑决定包 Part 2（Revision Roadmap）CR-1~CR-8 和 MA-1~MA-12
- **证据层：** `repo-observed fact`（新实验结果）、`design intent`（修订策略）
- **状态追踪：** 完成后更新 `Docs/superpowers/plans/2026-05-23-tmm-paper-major-revision.md` 状态

**依赖关系图：**
```
任务 1 (Layer-5 混淆) ──→ 任务 5 (声明重述) ──→ 任务 8 (正文更新)
任务 2 (PANNs)         ──→ 任务 5 ──→ 任务 8
任务 3 (近重复)        ──→ 任务 5 ──→ 任务 8
任务 4 (EPR敏感性)    ──→ 任务 5 ──→ 任务 8
任务 6 (容差敏感性)   ──→ 任务 5 ──→ 任务 8
任务 7 (统计校正)     ──→ 任务 5 ──→ 任务 8
```

---

## 修订路线图执行优先级

| 优先级 | 编号 | 项目 | 依赖 | 难度 |
|--------|------|------|------|------|
| P0 | CR-1 | Gram vs Layer-5 混淆 | 无 | 低 |
| P0 | CR-4 | PANNs 基线补充 | 无 | 中 |
| P1 | CR-5 | 近重复正式过滤 | 无 | 中 |
| P1 | CR-3 | Holm-Bonferroni 校正 | 无 | 低 |
| P1 | CR-7 | MLP 边界声明重述 | 无 | 低 |
| P2 | CR-2 | 摘要-表格数据一致性 | CR-1~CR-4 结果 | 低 |
| P2 | MA-1 | EPR 超参敏感性 | CR-1 结果 | 低 |
| P2 | MA-2 | 容差敏感性 | 无 | 低 |
| P2 | MA-12 | 延迟基准测试 | 无 | 低 |

---

### 任务 1: Gram vs Layer-5 混淆对照（CR-1）

**Harness（测试框架）:**

- **范围：** 设计对照实验分离 Gram 统计效应与 Layer-5 选择效应。明确回答"TRR 优势来自 Gram 还是 Layer-5"
- **前置条件：** 任务 0（无，此任务独立）
- **测试入口：** `pytest tests/test_layer5_confound.py -v`
- **通过标准：** 6 个测试通过，产生完整消融表格（含 Gram vs mean-pool 逐层对比）
- **失败恢复：** `git reset --hard HEAD~1`
- **依赖：** 无（独立任务）
- **证据层：** `repo-observed fact`

**文件:**

- 创建：`Experiments/E5_Ablations/layer5_confound_ablation.py`
- 创建：`Experiments/E5_Ablations/outputs/layer5_confound/layer5_confound_results.csv`
- 修改：`Paper/content.tex`（机制解释段落、讨论部分）
- 测试：`Experiments/E5_Ablations/tests/test_layer5_confound.py`

**行为清单（Behavior List）:**

- [ ] 行为 1: 对每个层 (4, 5, 6) 分别计算 mean-pool 和 Gram 检索结果，逐层对比
- [ ] 行为 2: 计算每个配置的提升量：ΔGram = mean_pool_L2 - gram_L2；报告绝对提升和相对提升
- [ ] 行为 3: 对每层做 Wilcoxon 配对符号检验（Gram vs mean-pool at same layer），报告 p 值
- [ ] 行为 4: 输出结构化 CSV：层、方法、Norm.L2 均值、95% CI、提升量、p 值
- [ ] 行为 5: 验证数据一致性：所有配置使用相同的 204 查询和 1063 KB

**接口合同（Interface Contract）:**

```python
@dataclass
class LayerAblationResult:
    layer: List[int]          # e.g., [5], [4,5,6]
    method: str               # "mean_pool" | "gram"
    project_dim: int         # 0 for mean_pool, 64 for Gram
    norm_l2_mean: float
    norm_l2_ci_lower: float  # bootstrap 95% CI
    norm_l2_ci_upper: float
    improvement_vs_mean: float  # positive = Gram better
    wilcoxon_p: float       # Gram vs mean-pool at same layer
    n_queries: int          # must be 204
```

- [ ] **步骤 1：编写失败的测试** (Red)

```python
# tests/test_layer5_confound.py
def test_layer5_confound_produces_results():
    """验证层-5 混淆实验生成完整结果表格"""
    # Test that the ablation script produces expected output structure
    ...

def test_all_configs_have_204_queries():
    """验证所有配置在相同查询集上评估"""
    ...

def test_gram_beats_mean_at_layer5_significant():
    """验证 Gram 在 Layer-5 上显著优于 mean-pool"""
    ...

def test_multilayer_gram_not_better_than_multilayer_mean():
    """验证多层 Gram 不显著优于多层 mean-pool"""
    ...

def test_output_csv_structure():
    """验证输出 CSV 包含所有必需列"""
    ...

def test_improvement_values_consistent():
    """验证提升量计算正确：improvement = mean_L2 - gram_L2"""
    ...
```

运行：`pytest Experiments/E5_Ablations/tests/test_layer5_confound.py -v`
预期：FAIL（模块不存在或函数未定义）

- [ ] **步骤 2：运行测试确认失败** (Red)

**必须确认：**
- 测试确实失败
- 失败原因是因为功能缺失，不是因为 typo
- 测试名清楚地描述了一个行为
- 测试用了真实代码（不是 mock）

- [ ] **步骤 3：编写最小实现** (Green)

> **原则：Plan 不提供实现代码。** 执行者根据"接口合同"和"行为清单"，从零写最小实现。
>
> 铁律：
> - 不写超出当前测试所需的功能
> - 不改其他代码
> - 不重构

运行：`pytest Experiments/E5_Ablations/tests/test_layer5_confound.py -v`
预期：PASS

- [ ] **步骤 4：运行测试确认通过** (Green)

**必须确认：**
- 当前 task 的测试通过
- 之前所有 task 的测试仍然通过（运行 `pytest tests/`）
- 输出无错误、无警告

- [ ] **步骤 5：提交代码**

```bash
git add Experiments/E5_Ablations/layer5_confound_ablation.py \
        Experiments/E5_Ablations/outputs/layer5_confound/ \
        Experiments/E5_Ablations/tests/test_layer5_confound.py
git commit -m "exp(E5): add layer-5 confound ablation with Gram vs mean-pool per-layer comparison"
```

- [ ] **步骤 6：验证 spec 合规（自检）**

对照本 task 的"行为清单"和"接口合同"，逐项验证：

- [ ] 每个行为清单项都有对应的测试覆盖
- [ ] 接口签名与合同完全一致（类型、参数名、返回值）
- [ ] 没有多实现 spec 未要求的功能（YAGNI）
- [ ] 没有遗漏 spec 要求的任何行为

---

### 任务 2: PANNs 基线补充（CR-4）

**Harness（测试框架）:**

- **范围：** 修复 PANNs 编码器的依赖问题，运行完整 Protocol-A 评估。如果无法修复，则产出正式声明文档
- **前置条件：** 无
- **测试入口：** `pytest tests/test_panns_baseline.py -v`
- **通过标准：** PANNs 基线成功运行，产出 Norm.L2 结果；或产出正式缺失声明
- **失败恢复：** `git reset --hard HEAD~1`
- **依赖：** 无
- **证据层：** `repo-observed fact`

**文件:**

- 修改：`Experiments/E2_SOTABaselines/panns_encoder.py`（修复依赖/环境问题）
- 修改：`Experiments/E2_SOTABaselines/panns_baseline.py`（确保完整 Protocol-A 评估）
- 创建：`Experiments/E9_TMMMajorRevision/outputs/panns_baseline/panns_results.json`
- 修改：`Experiments/E9_TMMMajorRevision/unified_protocol_export.py`（加入 PANNs 到统一表）
- 测试：`Experiments/E2_SOTABaselines/tests/test_panns_baseline.py`

**行为清单（Behavior List）:**

- [ ] 行为 1: 诊断 PANNs 编码器在当前 Python 3.12 环境中的具体问题（依赖链、版本不匹配、导入错误）
- [ ] 行为 2: 修复依赖问题或创建隔离环境（conda/mamba）使得 PANNs CNN14 能正常运行
- [ ] 行为 3: 对 204 个查询和 1063 个 KB 条目提取 PANNs 嵌入向量
- [ ] 行为 4: 运行 Protocol-A 检索评估，计算 Norm.L2、Acc@0.1、Recall、Cosine、SwitchF1
- [ ] 行为 5: 将 PANNs 结果纳入统一结果表（`unified_topk_rows.csv`）
- [ ] 行为 6: 如果 PANNs 无法运行，产出正式声明文档（记录环境、问题、尝试修复步骤）

**接口合同（Interface Contract）:**

```python
@dataclass
class PANNsBaselineResult:
    method: str              # "PANNs"
    protocol: str            # "Protocol-A"
    n_queries: int          # must be 204
    coverage: float         # fraction of evaluable queries
    norm_l2: float
    acc_at_0_1: float
    recall: float
    cosine: float
    switch_f1: float
    status: str             # "success" | "skipped" | "partial"
    skip_reason: str        # if status != "success"
```

- [ ] **步骤 1：编写失败的测试** (Red)

```python
# tests/test_panns_baseline.py
def test_panns_encoder_imports():
    """验证 PANNs 编码器可导入"""
    ...

def test_panns_vector_extraction():
    """验证 PANNs 向量提取产出正确维度"""
    ...

def test_panns_protocol_a_results():
    """验证 PANNs Protocol-A 结果包含所有必需指标"""
    ...

def test_panns_added_to_unified_table():
    """验证 PANNs 已加入统一结果表"""
    ...
```

运行：`pytest Experiments/E2_SOTABaselines/tests/test_panns_baseline.py -v`
预期：FAIL（模块不存在或函数未定义）

- [ ] **步骤 2：运行测试确认失败** (Red)

**必须确认：**
- 测试确实失败
- 失败原因是功能缺失，不是因为 typo
- 如果 PANNs 确实无法修复，测试记录正式的失败原因

- [ ] **步骤 3：编写最小实现** (Green)

> 尝试修复 PANNs 依赖。如果 30 分钟内无法修复，产出正式声明文档并跳过此基线。
>
> 铁律：
> - 不写超出当前测试所需的功能
> - 不改其他代码
> - 不重构

运行：`pytest Experiments/E2_SOTABaselines/tests/test_panns_baseline.py -v`
预期：PASS（或正式跳过记录）

- [ ] **步骤 4：运行测试确认通过** (Green)

**必须确认：**
- 当前 task 的测试通过
- PANNs 结果已纳入统一表
- 如果跳过，有正式声明

- [ ] **步骤 5：提交代码**

```bash
git add Experiments/E2_SOTABaselines/panns_*.py \
        Experiments/E2_SOTABaselines/outputs/panns_results.json \
        Experiments/E9_TMMMajorRevision/unified_protocol_export.py
git commit -m "exp(E2): add PANNs baseline or formal skip documentation"
```

- [ ] **步骤 6：验证 spec 合规（自检）**

- [ ] 每个行为清单项都有对应的测试或正式跳过记录
- [ ] 接口签名与合同完全一致
- [ ] 没有多实现 spec 未要求的功能
- [ ] 没有遗漏 spec 要求的任何行为

---

### 任务 3: 近重复正式过滤（CR-5）

**Harness（测试框架）:**

- **范围：** 实现基于参数空间的近重复检测算法，生成正式过滤后的基准，并在过滤后基准上重新评估所有方法
- **前置条件：** 无
- **测试入口：** `pytest tests/test_near_dup_filter.py -v`
- **通过标准：** 近重复过滤脚本运行成功，产出过滤后基准（含查询/KB 数量变化统计），所有方法在过滤后基准上重新评估
- **失败恢复：** `git reset --hard HEAD~1`
- **依赖：** 无
- **证据层：** `repo-observed fact`

**文件:**

- 创建：`Experiments/E5_Ablations/formal_near_dup_filter.py`
- 创建：`Experiments/E5_Ablations/outputs/formal_near_dup/filter_stats.json`
- 创建：`Experiments/E5_Ablations/outputs/formal_near_dup/filtered_results.csv`
- 测试：`Experiments/E5_Ablations/tests/test_formal_near_dup_filter.py`

**行为清单（Behavior List）:**

- [ ] 行为 1: 实现基于参数空间距离的 near-duplicate 检测：对每对 (query, KB_item) 计算参数空间归一化 L2 距离，若距离 < 阈值则标记为 near-duplicate
- [ ] 行为 2: 在三个阈值 (0.02, 0.05, 0.10) 下运行过滤，报告每个阈值下的查询数、KB 数、过滤对数
- [ ] 行为 3: 在过滤后的 KB 上重新评估所有方法（Wav2Vec, FeatureNN, CLAP, PaSST, TRR），报告 Norm.L2
- [ ] 行为 4: 输出过滤统计 JSON：阈值、原始查询数、保留查询数、原始 KB 数、保留 KB 数、过滤对数
- [ ] 行为 5: 输出过滤后结果 CSV：方法、阈值、Norm.L2、覆盖度

**接口合同（Interface Contract）:**

```python
@dataclass
class NearDupFilterStats:
    threshold: float        # distance threshold for near-dup
    original_queries: int   # 204
    retained_queries: int
    original_kb: int       # 1063
    retained_kb: int
    filtered_pairs: int    # number of near-dup pairs removed
    filter_rate: float     # filtered_pairs / (queries * kb)

@dataclass
class FilteredResult:
    method: str
    threshold: float
    norm_l2: float
    coverage: float
    n_queries: int
```

- [ ] **步骤 1：编写失败的测试** (Red)

```python
def test_near_dup_filter_reduces_kb():
    """验证近重复过滤减少了 KB 大小"""
    ...

def test_all_methods_evaluated_on_filtered():
    """验证所有方法在过滤后基准上重新评估"""
    ...

def test_filter_stats_complete():
    """验证过滤统计包含所有必需字段"""
    ...

def test_trr_still_leads_at_threshold_0_02():
    """验证 TRR 在 0.02 阈值下仍然领先"""
    ...
```

运行：`pytest Experiments/E5_Ablations/tests/test_formal_near_dup_filter.py -v`
预期：FAIL

- [ ] **步骤 2：运行测试确认失败** (Red)

**必须确认：** 测试失败，原因是功能缺失

- [ ] **步骤 3：编写最小实现** (Green)

运行：`pytest Experiments/E5_Ablations/tests/test_formal_near_dup_filter.py -v`
预期：PASS

- [ ] **步骤 4：运行测试确认通过** (Green)

- [ ] **步骤 5：提交代码**

```bash
git add Experiments/E5_Ablations/formal_near_dup_filter.py \
        Experiments/E5_Ablations/outputs/formal_near_dup/
git commit -m "exp(E5): formal near-duplicate filter with multi-threshold evaluation"
```

- [ ] **步骤 6：验证 spec 合规（自检）**

---

### 任务 4: EPR 超参敏感性分析（MA-1）

**Harness（测试框架）:**

- **范围：** 对 EPR-K5 进行超参数敏感性分析，覆盖 K ∈ {3, 5, 10, 20} 和温度 τ ∈ {0.01, 0.05, 0.10, 0.20, 0.50}
- **前置条件：** 任务 1（Layer-5 混淆结果已出）
- **测试入口：** `pytest tests/test_epr_sensitivity.py -v`
- **通过标准：** 5×4=20 个配置全部运行完成，产出敏感性热力图数据
- **失败恢复：** `git reset --hard HEAD~1`
- **依赖：** 任务 1
- **证据层：** `repo-observed fact`

**文件:**

- 修改：`Experiments/E9_TMMMajorRevision/epr_sensitivity.py`（扩展超参范围）
- 创建：`Experiments/E9_TMMMajorRevision/outputs/epr_sensitivity_full/epr_sensitivity_grid.csv`
- 创建：`Experiments/E9_TMMMajorRevision/outputs/epr_sensitivity_full/epr_sensitivity_heatmap.pdf`
- 测试：`Experiments/E9_TMMMajorRevision/tests/test_epr_sensitivity.py`

**行为清单（Behavior List）:**

- [ ] 行为 1: 在 K ∈ {3, 5, 10, 20} × τ ∈ {0.01, 0.05, 0.10, 0.20, 0.50} 网格上运行 EPR 投影
- [ ] 行为 2: 对每个配置报告 Norm.L2、Acc@0.1、Recall、Cosine、SwitchF1、N_eff、max_wi
- [ ] 行为 3: 输出网格 CSV 和敏感性热力图（K 为 x 轴，τ 为 y 轴，颜色为 Norm.L2）
- [ ] 行为 4: 标识最优配置及其置信区间
- [ ] 行为 5: 验证 K=5, τ=0.05 在合理范围内（不是全局最优或最差）

**接口合同（Interface Contract）:**

```python
@dataclass
class EPRGridResult:
    k: int                  # neighborhood size
    temperature: float
    norm_l2: float
    acc_at_0_1: float
    recall: float
    cosine: float
    switch_f1: float
    n_eff: float           # effective exemplar count
    max_wi: float          # max exemplar weight
    n_queries: int          # must be 204
```

- [ ] **步骤 1：编写失败的测试** (Red)

```python
def test_epr_grid_complete():
    """验证 EPR 敏感性网格覆盖所有 20 个配置"""
    ...

def test_epr_results_have_all_metrics():
    """验证每个配置产出 7 个指标"""
    ...

def test_k5_t005_in_reasonable_range():
    """验证 K=5, τ=0.05 不是最差点"""
    ...
```

运行：`pytest Experiments/E9_TMMMajorRevision/tests/test_epr_sensitivity.py -v`
预期：FAIL

- [ ] **步骤 2：运行测试确认失败** (Red)

- [ ] **步骤 3：编写最小实现** (Green)

运行：`pytest Experiments/E9_TMMMajorRevision/tests/test_epr_sensitivity.py -v`
预期：PASS

- [ ] **步骤 4：运行测试确认通过** (Green)

- [ ] **步骤 5：提交代码**

```bash
git add Experiments/E9_TMMMajorRevision/epr_sensitivity.py \
        Experiments/E9_TMMMajorRevision/outputs/epr_sensitivity_full/
git commit -m "exp(E9): full EPR hyperparameter sensitivity grid (K×τ)"
```

- [ ] **步骤 6：验证 spec 合规（自检）**

---

### 任务 5: 容差敏感性分析（MA-2）

**Harness（测试框架）:**

- **范围：** 在多个容差值（0.05, 0.10, 0.15, 0.20）下评估 Acc@τ 和 Recall@τ，验证 TRR 的相对优势在不同容差下是否稳定
- **前置条件：** 无
- **测试入口：** `pytest tests/test_tolerance_sensitivity.py -v`
- **通过标准：** 4 个容差值 × 5 个方法全部完成，产出敏感性曲线
- **失败恢复：** `git reset --hard HEAD~1`
- **依赖：** 无
- **证据层：** `repo-observed fact`

**文件:**

- 创建：`Experiments/E9_TMMMajorRevision/tolerance_sensitivity.py`
- 创建：`Experiments/E9_TMMMajorRevision/outputs/tolerance_sensitivity/tolerance_sensitivity.csv`
- 创建：`Experiments/E9_TMMMajorRevision/outputs/tolerance_sensitivity/tolerance_curves.pdf`
- 测试：`Experiments/E9_TMMMajorRevision/tests/test_tolerance_sensitivity.py`

**行为清单（Behavior List）:**

- [ ] 行为 1: 对每个方法在 τ ∈ {0.05, 0.10, 0.15, 0.20} 下计算 Acc@τ
- [ ] 行为 2: 对每个方法在 τ ∈ {0.05, 0.10, 0.15, 0.20} 下计算 Recall@τ
- [ ] 行为 3: 输出敏感性曲线：x=τ, y=Acc/Recall, 每条线一个方法
- [ ] 行为 4: 验证 TRR 在哪些容差区间领先，在哪些容差区间被其他方法追上

**接口合同（Interface Contract）:**

```python
@dataclass
class ToleranceSensitivityResult:
    method: str
    tolerance: float
    acc_at_tau: float
    recall_at_tau: float
    n_queries: int
```

- [ ] **步骤 1：编写失败的测试** (Red)
- [ ] **步骤 2：运行测试确认失败** (Red)
- [ ] **步骤 3：编写最小实现** (Green)
- [ ] **步骤 4：运行测试确认通过** (Green)
- [ ] **步骤 5：提交代码**
- [ ] **步骤 6：验证 spec 合规（自检）**

---

### 任务 6: Holm-Bonferroni 多重比较校正（CR-3）

**Harness（测试框架）:**

- **范围：** 对所有配对 Wilcoxon 检验应用 Holm-Bonferroni 校正，报告校正后 p 值
- **前置条件：** 无
- **测试入口：** `pytest tests/test_holm_bonferroni.py -v`
- **通过标准：** 校正后所有 p 值仍显著；如果校正后不显著，需要在正文中重新表述
- **失败恢复：** `git reset --hard HEAD~1`
- **依赖：** 无
- **证据层：** `repo-observed fact`

**文件:**

- 修改：`Experiments/E9_TMMMajorRevision/outputs/unified_protocol/significance_test.py`
- 创建：`Experiments/E9_TMMMajorRevision/outputs/unified_protocol/holm_corrected_results.json`
- 测试：`Experiments/E9_TMMMajorRevision/tests/test_holm_bonferroni.py`

**行为清单（Behavior List）:**

- [ ] 行为 1: 收集所有原始 Wilcoxon p 值（按指标分组：Norm.L2、Acc@0.1、Recall、Cosine、SwitchF1）
- [ ] 行为 2: 对每个指标组内的 p 值应用 Holm-Bonferroni 校正
- [ ] 行为 3: 报告校正前/后 p 值对比表
- [ ] 行为 4: 如果校正后仍有显著差异，更新正文统计声明；如果校正后不显著，标记为"方向性结果"

**接口合同（Interface Contract）:**

```python
@dataclass
class HolmCorrectedResult:
    metric: str
    baseline: str
    raw_p: float
    holm_corrected_p: float
    n_comparisons: int
    significant_raw: bool
    significant_corrected: bool
    alpha: float  # 0.05
```

- [ ] **步骤 1：编写失败的测试** (Red)
- [ ] **步骤 2：运行测试确认失败** (Red)
- [ ] **步骤 3：编写最小实现** (Green)
- [ ] **步骤 4：运行测试确认通过** (Green)
- [ ] **步骤 5：提交代码**
- [ ] **步骤 6：验证 spec 合规（自检）**

---

### 任务 7: MLP 边界声明重述（CR-7）

**Harness（测试框架）:**

- **范围：** 重述 TRR vs MLP 的比较结论，强调"可编辑溯源性"作为 TRR 的核心优势而非数值精度
- **前置条件：** 无
- **测试入口：** 无需代码测试（纯文本修订）
- **通过标准：** 正文中 MLP 边界段落已更新，声明 TRR 与 MLP 在不同指标上的权衡关系
- **失败恢复：** `git reset --hard HEAD~1`
- **依赖：** 任务 1（Layer-5 混淆结果）
- **证据层：** `design intent`

**文件:**

- 修改：`Paper/content.tex`（Section I 贡献声明、Section V 结果讨论、Section VII 局限性）
- 修改：`Paper/abstract.tex`（如需）

**行为清单（Behavior List）:**

- [ ] 行为 1: 在摘要中重述 TRR vs MLP 对比：MLP 在 Acc@0.1 上接近 TRR EPR-K5，但 TRR 提供可编辑溯源性
- [ ] 行为 2: 在主结果表中重述 MLP 行标题：明确标注为"直接回归边界（无溯源性）"
- [ ] 行为 3: 在讨论部分增加段落：解释检索 vs 回归的权衡（数值精度 vs 溯源性+可编辑性）
- [ ] 行为 4: 在局限性中明确：MLP 边界说明 TRR 的 Acc@0.1 优势较小；核心优势在 Recall、Cosine 和溯源性

**接口合同：** 不适用（纯文本修订任务）

- [ ] **步骤 1-2：** 修订 `content.tex` 中相关段落
- [ ] **步骤 3：** 验证 LaTeX 编译通过
- [ ] **步骤 4：提交代码**

```bash
git add Paper/content.tex Paper/abstract.tex
git commit -m "writeup: reframe MLP boundary as provenance vs accuracy trade-off"
```

- [ ] **步骤 5：验证 spec 合规（自检）**

---

### 任务 8: 正文全面更新（CR-2, CR-6）

**Harness（测试框架）:**

- **范围：** 根据所有新实验结果更新正文和补充材料。修正摘要-表格数据一致性、更新机制解释、加入新诊断结果
- **前置条件：** 任务 1~7 全部完成
- **测试入口：** `cd Paper && pdflatex main.tex && pdflatex main.tex`（验证编译通过）
- **通过标准：** LaTeX 编译无错误，所有数字与实验结果一致
- **失败恢复：** `git reset --hard HEAD~1`
- **依赖：** 任务 1~7
- **证据层：** `repo-observed fact`（实验数据）、`design intent`（声明策略）

**文件:**

- 修改：`Paper/content.tex`（全面更新）
- 修改：`Paper/supplementary.tex`（加入新消融表、敏感性分析、延迟数据）
- 创建：`Paper/figures/layer5_confound.pdf`（Layer-5 混淆对照图）
- 创建：`Paper/figures/epr_sensitivity_heatmap.pdf`（EPR 敏感性热力图）
- 创建：`Paper/figures/tolerance_sensitivity_curves.pdf`（容差敏感性曲线）

**行为清单（Behavior List）:**

- [ ] 行为 1: 修正摘要中所有数字与主表一致（Norm.L2 0.1454、Acc@0.1 0.7863 等）
- [ ] 行为 2: 更新机制解释段落：加入 Layer-5 混淆讨论，区分 Gram 效应与 Layer-5 效应
- [ ] 行为 3: 更新主结果表：加入 PANNs 行（如有）、Holm-Bonferroni 校正 p 值
- [ ] 行为 4: 更新近重复过滤段落：加入正式过滤结果
- [ ] 行为 5: 更新 EPR 段落：加入敏感性分析结果，说明 K=5, τ=0.05 的合理性
- [ ] 行为 6: 更新讨论部分：加入跨域迁移讨论、延迟估计、GRACE 声明
- [ ] 行为 7: 更新局限性部分：加入 GRACE 检查、PANNs 缺失声明
- [ ] 行为 8: 验证 LaTeX 编译通过，所有交叉引用正确

**接口合同：** 不适用（LaTeX 修订任务）

- [ ] **步骤 1：** 根据任务 1~7 的结果，逐项更新 `content.tex`
- [ ] **步骤 2：** 更新 `supplementary.tex`
- [ ] **步骤 3：** 加入新图表（layer5_confound.pdf, epr_heatmap.pdf, tolerance_curves.pdf）
- [ ] **步骤 4：编译验证**

```bash
cd Paper && pdflatex main.tex && pdflatex main.tex
# 验证编译无错误、无缺失引用
```

- [ ] **步骤 5：提交代码**

```bash
git add Paper/content.tex Paper/supplementary.tex Paper/figures/
git commit -m "writeup: comprehensive paper update with all revision experiments"
```

- [ ] **步骤 6：验证 spec 合规（自检）**

---

## 质量门（Quality Gate）

每个任务完成后，必须通过以下检查：

- [ ] 所有测试通过
- [ ] 无 lint/type 错误
- [ ] 代码已提交，有描述性提交信息
- [ ] 无 TODO、TBD 或占位符
- [ ] Harness 通过标准已满足
- [ ] 之前所有任务的测试仍然通过（无回归）
- [ ] Spec 合规自检通过

---

## Report 进度更新

### 1. 更新进度章节
- [ ] 在 `Docs/superpowers/plans/2026-05-23-tmm-paper-major-revision.md` 中标记已完成项
- [ ] 引用实现 commits（每个任务的 commit SHA）
- [ ] 如有偏离原始 spec 的地方，在"风险与边界"中注明

### 2. 更新风险/下一步章节
- [ ] **风险矩阵**：补充或更新风险项
- [ ] **后续动作清单**：更新动作状态

### 3. 证据层标记
- [ ] 本计划产生的代码/测试 → `repo-observed fact`
- [ ] 本计划中的设计决策 → `design intent`（仅在 spec 中）
- [ ] 引用外部文献 → `source claim`

### 4. 交叉检查
- [ ] 进度章节未把未实现的 roadmap 写成已实现事实
- [ ] 风险章节未遗漏 report 中已知的、本计划未解决的风险
- [ ] 证据层未混淆 `design intent` 和 `repo-observed fact`

---

## 计划完成检查清单

- [ ] 所有 8 个任务按计划完成
- [ ] 所有测试通过，无回归
- [ ] 论文编译通过，所有数字一致
- [ ] 编辑决定包中所有 CRITICAL 项已处理
- [ ] 所有 MAJOR 项（MA-1, MA-2, MA-12）已处理
- [ ] 提交完整的 Response to Reviewers 文档
- [ ] 代码已推送到远程仓库

---

## 执行方式选择

Plan 已保存至 `docs/superpowers/plans/2026-05-23-tmm-major-revision-experiments.md`。

**两种执行方式：**

**1. 子代理驱动（推荐）** — 每个任务派遣一个新鲜子代理，每个任务有 spec review，计划结束时统一质量 review

**2. 内联执行** — 在本会话中使用 executing-plans 批量执行，带检查点 review

**选择哪种方式？**
