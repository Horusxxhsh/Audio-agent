# Executable Neighborhood Retrieval 论文增强实现计划

> **给执行者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐步实现此计划。步骤使用复选框（`- [ ]`）语法以便跟踪。

**目标：** 在不更换数据集的前提下，把论文从“TRR 是更好的 Gram embedding”重定位为“parameter-transferability-aware executable neighborhood retrieval”，并用最小新增实验支撑 MLP 边界、Top-K 可执行邻域、exemplar-preserving projection、module-aware reranking 与论文正文改写。

**架构：** 实现分为实验增强层与论文叙事层。实验增强层新增 `Experiments/E8_ExecutableNeighborhood/`，复用现有 `Experiments/common/evaluate.py`、Protocol-A split 与 cached vectors，不改动数据集；论文叙事层只在实验产物验证后修改 `Paper_submission/content.tex` 与 `Paper_submission/supplementary.tex`。PC-TRR、Temporal Pyramid TRR、Log-Covariance TRR、analysis-by-synthesis reranking 不进入本轮主线，只作为“下一阶段可验证扩展”，避免在没有稳定训练/渲染证据时扩大 claim。

**技术栈：** Python 3.9、NumPy、pytest、现有 `Evaluator(normalize=True)`、LaTeX/IEEEtran、`latexmk`。

**第一性原理拆解：**

- 当前核心矛盾不是“TRR 是否比所有方法都强”，而是“可编辑音频效果控制需要什么输出对象”。如果输出对象是纯数值参数，MLP + range projection 的 Norm.L2 优势会压制 TRR；如果输出对象是可追溯、可编辑、可执行的 preset neighborhood，retrieval 才有不可替代的工作流价值。
- 因此新增实验不能只证明 top-1 TRR 均值更好，而要证明：Top-K 中是否含有参数可迁移邻域、hybrid projection 是否能缩小 MLP 数值差距、retrieval 输出是否保留 provenance、模块结构是否能解释或改善检索。
- 任何使用 ground-truth query parameters 进行 reranking 的方法都只能作为 oracle diagnostic，不能写成部署方法。本计划中 module-aware reranking 使用候选邻域内部的 active-module consensus，不读取 query ground truth。

**依赖关系图：**

```text
任务 1 ──→ 任务 2 ──→ 任务 3 ──→ 任务 5 ──→ 任务 6 ──→ 任务 7
   │          │          │
   └──────────┴──→ 任务 4 ┘
```

---

## 文件结构

- 创建：`Experiments/common/parameter_space.py`
  - 责任：参数字典 flatten、active module 提取、Top-K parameter-neighborhood recall、edit cost、provenance score、weighted blending。
- 创建：`Experiments/common/tests/test_parameter_space.py`
  - 责任：用小型参数字典验证新增指标的数学语义，不依赖真实数据集。
- 创建：`Experiments/E8_ExecutableNeighborhood/__init__.py`
  - 责任：声明 E8 实验包。
- 创建：`Experiments/E8_ExecutableNeighborhood/topk_retrieval_dump.py`
  - 责任：在 Protocol-A split 上为 TRR/Wav2Vec/FeatureNN/CLAP/PaSST/PANNs 输出 top-K retrieved candidates 与 per-query 参数指标。
- 创建：`Experiments/E8_ExecutableNeighborhood/test_topk_retrieval_dump.py`
  - 责任：验证 cosine top-K 排序、缺失向量跳过、输出 schema。
- 创建：`Experiments/E8_ExecutableNeighborhood/epr_projection.py`
  - 责任：实现 Exemplar-Preserving Parameter Projection，即 top-K softmax weighted parameter blending + range projection + provenance score。
- 创建：`Experiments/E8_ExecutableNeighborhood/test_epr_projection.py`
  - 责任：验证 softmax 权重、weighted blending、range projection、provenance score。
- 创建：`Experiments/E8_ExecutableNeighborhood/module_aware_rerank.py`
  - 责任：实现 oracle-free module-consensus reranking，并输出与原始 top-1 的差异。
- 创建：`Experiments/E8_ExecutableNeighborhood/test_module_aware_rerank.py`
  - 责任：验证 reranker 不读取 query ground truth，只依赖候选参数结构。
- 创建：`Experiments/E8_ExecutableNeighborhood/summarize_e8.py`
  - 责任：汇总 PNR@K、EPR/RCPP、module-aware reranking、MLP boundary 的 paper-facing JSON/Markdown。
- 创建：`Experiments/E8_ExecutableNeighborhood/test_summarize_e8.py`
  - 责任：验证汇总表字段、排序、缺失输入错误。
- 创建：`Experiments/E8_ExecutableNeighborhood/README.md`
  - 责任：记录命令、输入、输出、不能支持的 claim。
- 修改：`Paper_submission/content.tex`
  - 责任：改写 abstract、introduction、contributions、method framing、MLP boundary、discussion、limitations、conclusion。
- 修改：`Paper_submission/supplementary.tex`
  - 责任：新增 E8 指标表与方法边界说明。

---

### 任务 1: 参数空间与可执行邻域指标

**Status:** COMPLETE  
**Completed:** 2026-05-03  
**Commits:** Task 1 commit in this branch

**Harness（测试框架）:**

- **范围：** 新增纯函数指标：`flatten_numeric_params`、`active_modules`、`topk_parameter_neighborhood_recall`、`edit_cost`、`exemplar_provenance_score`、`blend_parameter_dicts`。不读取真实数据集，不改现有 `Evaluator` 行为。
- **前置条件：** 当前工作区可运行 `python3 -m pytest`。
- **测试入口：** `python3 -m pytest Experiments/common/tests/test_parameter_space.py -v`
- **通过标准：** 6 个测试通过，0 失败；所有函数对空输入有确定返回值。
- **失败恢复：** `git reset --hard HEAD~1`
- **依赖：** 无。

**文件:**

- 创建：`Experiments/common/parameter_space.py`
- 创建：`Experiments/common/tests/test_parameter_space.py`

- [x] **步骤 1：编写失败的测试** (Red)

在 `Experiments/common/tests/test_parameter_space.py` 写入：

```python
from Experiments.common.parameter_space import (
    active_modules,
    blend_parameter_dicts,
    edit_cost,
    exemplar_provenance_score,
    flatten_numeric_params,
    topk_parameter_neighborhood_recall,
)


def test_flatten_numeric_params_parses_nested_numeric_strings():
    params = {"DriverOn": {"Distortion": "0.50", "Mode": "tube"}, "DelayOff": {"Mix": 0}}
    assert flatten_numeric_params(params) == {
        "DriverOn.Distortion": 0.5,
        "DelayOff.Mix": 0.0,
    }


def test_active_modules_uses_on_suffix_only():
    assert active_modules({"DriverOn": {}, "DelayOff": {}, "ReverbOn": {}}) == {"Driver", "Reverb"}


def test_topk_parameter_neighborhood_recall_detects_any_close_candidate():
    gt = {"DriverOn": {"Distortion": 0.50}}
    topk = [{"DriverOn": {"Distortion": 0.90}}, {"DriverOn": {"Distortion": 0.53}}]
    assert topk_parameter_neighborhood_recall(topk, gt, threshold=0.05, normalize=False) == 1


def test_edit_cost_penalizes_switch_and_continuous_differences():
    pred = {"DriverOn": {"Distortion": 0.70}, "DelayOff": {"Mix": 0.0}}
    gt = {"DriverOff": {"Distortion": 0.40}, "DelayOff": {"Mix": 0.0}}
    assert edit_cost(pred, gt, switch_weight=2.0, continuous_weight=1.0, normalize=False) == 2.3


def test_exemplar_provenance_score_reports_concentrated_weights():
    score = exemplar_provenance_score([0.8, 0.2])
    assert score["max_weight"] == 0.8
    assert round(score["effective_exemplars"], 4) == 1.4706


def test_blend_parameter_dicts_averages_shared_numeric_leaves():
    a = {"DriverOn": {"Distortion": 0.0, "Volume": -10.0}}
    b = {"DriverOn": {"Distortion": 1.0, "Volume": -20.0}}
    assert blend_parameter_dicts([a, b], [0.25, 0.75]) == {
        "DriverOn": {"Distortion": 0.75, "Volume": -17.5}
    }
```

- [x] **步骤 2：运行测试确认失败** (Red)

运行：`python3 -m pytest Experiments/common/tests/test_parameter_space.py -v`

预期：FAIL with `ModuleNotFoundError: No module named 'Experiments.common.parameter_space'`

- [x] **步骤 3：编写最小实现** (Green)

在 `Experiments/common/parameter_space.py` 写入完整实现：

```python
from __future__ import annotations

import math
from typing import Dict, Iterable, List, Mapping, Sequence

from Experiments.common.evaluate import Evaluator


def flatten_numeric_params(params: Mapping, prefix: str = "") -> Dict[str, float]:
    flat: Dict[str, float] = {}
    for key, value in params.items():
        dotted = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, Mapping):
            flat.update(flatten_numeric_params(value, dotted))
        elif isinstance(value, (int, float)):
            flat[dotted] = float(value)
        elif isinstance(value, str):
            try:
                flat[dotted] = float(value)
            except ValueError:
                continue
    return flat


def active_modules(params: Mapping) -> set[str]:
    return {str(key)[:-2] for key in params.keys() if str(key).endswith("On")}


def _distance(pred: Mapping, gt: Mapping, normalize: bool) -> float:
    return Evaluator(normalize=normalize).compute_parameter_distance(pred, gt)


def topk_parameter_neighborhood_recall(
    topk_params: Sequence[Mapping],
    gt_params: Mapping,
    threshold: float,
    normalize: bool = True,
) -> int:
    return int(any(_distance(candidate, gt_params, normalize) <= float(threshold) for candidate in topk_params))


def edit_cost(
    pred_params: Mapping,
    gt_params: Mapping,
    switch_weight: float = 1.0,
    continuous_weight: float = 1.0,
    normalize: bool = True,
) -> float:
    pred_modules = active_modules(pred_params)
    gt_modules = active_modules(gt_params)
    switch_changes = len(pred_modules.symmetric_difference(gt_modules))
    pred = flatten_numeric_params(pred_params)
    gt = flatten_numeric_params(gt_params)
    keys = sorted(set(pred) | set(gt))
    evaluator = Evaluator(normalize=normalize)
    continuous_l1 = 0.0
    for key in keys:
        pv = pred.get(key, 0.0)
        gv = gt.get(key, 0.0)
        if normalize:
            pv = evaluator._normalize_value(key, pv)
            gv = evaluator._normalize_value(key, gv)
        continuous_l1 += abs(pv - gv)
    return round(float(switch_weight) * switch_changes + float(continuous_weight) * continuous_l1, 10)


def exemplar_provenance_score(weights: Iterable[float]) -> Dict[str, float]:
    ws = [max(0.0, float(w)) for w in weights]
    total = sum(ws)
    if total <= 0:
        return {"max_weight": 0.0, "entropy_norm": 0.0, "effective_exemplars": 0.0}
    probs = [w / total for w in ws]
    max_weight = max(probs)
    entropy = -sum(p * math.log(p) for p in probs if p > 0)
    entropy_norm = entropy / math.log(len(probs)) if len(probs) > 1 else 0.0
    effective = 1.0 / sum(p * p for p in probs if p > 0)
    return {
        "max_weight": round(max_weight, 10),
        "entropy_norm": round(entropy_norm, 10),
        "effective_exemplars": round(effective, 10),
    }


def blend_parameter_dicts(candidates: Sequence[Mapping], weights: Sequence[float]) -> Dict:
    if len(candidates) != len(weights):
        raise ValueError("candidates and weights must have the same length")
    total = float(sum(weights))
    if total <= 0:
        raise ValueError("weights must sum to a positive value")
    norm_weights = [float(w) / total for w in weights]
    flat_acc: Dict[str, float] = {}
    for candidate, weight in zip(candidates, norm_weights):
        for key, value in flatten_numeric_params(candidate).items():
            flat_acc[key] = flat_acc.get(key, 0.0) + weight * value
    out: Dict = {}
    for dotted, value in flat_acc.items():
        cur = out
        parts = dotted.split(".")
        for part in parts[:-1]:
            cur = cur.setdefault(part, {})
        cur[parts[-1]] = round(float(value), 10)
    return out
```

- [x] **步骤 4：运行测试确认通过** (Green)

运行：`python3 -m pytest Experiments/common/tests/test_parameter_space.py -v`

预期：`6 passed`

- [x] **步骤 5：提交代码**

```bash
git add Experiments/common/parameter_space.py Experiments/common/tests/test_parameter_space.py
git commit -m "feat: add executable neighborhood parameter metrics"
```

- [x] **步骤 6：请求代码审查** (必需)

使用 `superpowers:requesting-code-review` 技能：

```bash
BASE_SHA=$(git rev-parse HEAD~1)
HEAD_SHA=$(git rev-parse HEAD)
```

提供给子代理：
- **WHAT_WAS_IMPLEMENTED**: 新增参数空间 flatten、active module、PNR@K、edit cost、provenance 和 parameter blending 纯函数。
- **PLAN_OR_REQUIREMENTS**: `docs/superpowers/plans/2026-05-03-executable-neighborhood-retrieval.md` 任务 1。
- **BASE_SHA**: `$BASE_SHA`
- **HEAD_SHA**: `$HEAD_SHA`
- **DESCRIPTION**: `Add executable-neighborhood parameter metrics`

**在审查反馈处理完毕之前，不要继续下一个任务。**

---

### 任务 2: Protocol-A Top-K 可执行邻域导出

**Status:** COMPLETE  
**Completed:** 2026-05-03  
**Commits:** Task 2 commit in this branch

**Harness（测试框架）:**

- **范围：** 新增 Top-K retrieval dump 脚本，输出每个 query 的 top-K 候选、相似度、PNR@K 与 top-1 指标。不改变现有 Protocol-A 主表生成脚本。
- **前置条件：** 任务 1 已提交；真实数据路径 `Data/External_1267_211/dataset/dataset_full_vectors_1267.json` 存在。
- **测试入口：** `python3 -m pytest Experiments/E8_ExecutableNeighborhood/test_topk_retrieval_dump.py -v`
- **通过标准：** 7 个测试通过，0 失败；真实运行生成 `topk_retrieval_metrics.csv`、`topk_retrieval_metrics.json` 与 `topk_retrieval_audit.json`。
- **失败恢复：** `git reset --hard HEAD~1`
- **依赖：** 任务 1。

**文件:**

- 创建：`Experiments/E8_ExecutableNeighborhood/__init__.py`
- 创建：`Experiments/E8_ExecutableNeighborhood/topk_retrieval_dump.py`
- 创建：`Experiments/E8_ExecutableNeighborhood/test_topk_retrieval_dump.py`

- [x] **步骤 1：编写失败的测试** (Red)

在 `Experiments/E8_ExecutableNeighborhood/test_topk_retrieval_dump.py` 写入：

```python
import numpy as np

from Experiments.E8_ExecutableNeighborhood.topk_retrieval_dump import cosine_topk, topk_record


def test_cosine_topk_sorts_descending():
    query = np.array([1.0, 0.0])
    matrix = np.array([[0.0, 1.0], [1.0, 0.0], [0.8, 0.2]])
    assert cosine_topk(query, matrix, k=2) == [(1, 1.0), (2, 0.9701425001453318)]


def test_cosine_topk_rejects_empty_matrix():
    query = np.array([1.0, 0.0])
    assert cosine_topk(query, np.empty((0, 2)), k=3) == []


def test_topk_record_contains_pnr_and_top1_fields():
    query_item = {"SongName": "Q", "Parameters": {"DriverOn": {"Distortion": 0.5}}}
    candidates = [
        ({"SongName": "A", "Parameters": {"DriverOn": {"Distortion": 0.9}}}, 0.9),
        ({"SongName": "B", "Parameters": {"DriverOn": {"Distortion": 0.52}}}, 0.8),
    ]
    row = topk_record("TRR", 7, query_item, candidates, threshold=0.05)
    assert row["method"] == "TRR"
    assert row["query_idx"] == 7
    assert row["top1_name"] == "A"
    assert row["pnr_at_k"] == 1
    assert row["topk_names"] == ["A", "B"]
```

- [x] **步骤 2：运行测试确认失败** (Red)

运行：`python3 -m pytest Experiments/E8_ExecutableNeighborhood/test_topk_retrieval_dump.py -v`

预期：FAIL with `ModuleNotFoundError`

- [x] **步骤 3：编写最小实现** (Green)

实现 `cosine_topk`、`topk_record`、CLI 参数：

```python
VECTOR_METHODS = {"TRR": "TRR", "Wav2Vec": "Wav2Vec", "FeatureNN": "FeatureNN", "CLAP": "CLAP", "PaSST": "PaSST", "PANNs": "PANNs"}
DEFAULT_DATASET = "Data/External_1267_211/dataset/dataset_full_vectors_1267.json"
DEFAULT_SPLIT = "Experiments/tmm/splits/tmm_external1267_audio_grouped/seed0/test.txt"
DEFAULT_OUT = "Experiments/E8_ExecutableNeighborhood/outputs/topk"
```

脚本必须用 `Experiments.E7_HardSplit.run_hard_split_retrieval.load_requested_query_indices` 读取 split name list，用 complement 作为 KB；对每个方法只索引存在同维向量的 KB items；输出每行字段：

```python
[
    "method", "query_idx", "query_name", "coverage", "top1_name", "top1_norm_l2",
    "top1_acc_at_0_1", "top1_recall", "top1_cosine", "top1_module",
    "pnr_at_1", "pnr_at_3", "pnr_at_5", "topk_names", "topk_scores"
]
```

- [x] **步骤 4：运行测试和真实导出** (Green)

运行：

```bash
python3 -m pytest Experiments/E8_ExecutableNeighborhood/test_topk_retrieval_dump.py -v
python3 Experiments/E8_ExecutableNeighborhood/topk_retrieval_dump.py \
  --dataset Data/External_1267_211/dataset/dataset_full_vectors_1267.json \
  --split-file Experiments/tmm/splits/tmm_external1267_audio_grouped/seed0/test.txt \
  --k 5 \
  --threshold 0.10 \
  --output-dir Experiments/E8_ExecutableNeighborhood/outputs/topk
```

预期：

```text
3 passed
wrote Experiments/E8_ExecutableNeighborhood/outputs/topk/topk_retrieval_metrics.csv
wrote Experiments/E8_ExecutableNeighborhood/outputs/topk/topk_retrieval_metrics.json
```

- [x] **步骤 5：提交代码**

```bash
git add Experiments/E8_ExecutableNeighborhood/__init__.py \
  Experiments/E8_ExecutableNeighborhood/topk_retrieval_dump.py \
  Experiments/E8_ExecutableNeighborhood/test_topk_retrieval_dump.py \
  Experiments/E8_ExecutableNeighborhood/outputs/topk/topk_retrieval_metrics.csv \
  Experiments/E8_ExecutableNeighborhood/outputs/topk/topk_retrieval_metrics.json
git commit -m "feat: add protocol-a top-k neighborhood retrieval dump"
```

- [x] **步骤 6：请求代码审查** (必需)

```bash
BASE_SHA=$(git rev-parse HEAD~1)
HEAD_SHA=$(git rev-parse HEAD)
```

提供给子代理：
- **WHAT_WAS_IMPLEMENTED**: 新增 Protocol-A Top-K retrieval dump，生成 PNR@1/3/5 与 top-1 参数指标。
- **PLAN_OR_REQUIREMENTS**: 本计划任务 2。
- **BASE_SHA**: `$BASE_SHA`
- **HEAD_SHA**: `$HEAD_SHA`
- **DESCRIPTION**: `Add Top-K executable neighborhood retrieval artifacts`

**在审查反馈处理完毕之前，不要继续下一个任务。**

---

### 任务 3: Exemplar-Preserving Parameter Projection

**Status:** COMPLETE  
**Completed:** 2026-05-03  
**Commits:** Task 3 commit in this branch

**Harness（测试框架）:**

- **范围：** 新增 EPR/RCPP：对 top-K retrieved executable presets 做 softmax weighted blending，再按 KB observed range 投影；报告 Norm.L2、Acc@0.1、Recall、Cosine、Module、EditCost、Provenance。不训练新模型，不使用 query ground-truth 参与预测。
- **前置条件：** 任务 1-2 已提交；Top-K JSON 可读取。
- **测试入口：** `python3 -m pytest Experiments/E8_ExecutableNeighborhood/test_epr_projection.py -v`
- **通过标准：** 10 个测试通过，0 失败；真实运行生成 `epr_projection_results.csv/json`。
- **失败恢复：** `git reset --hard HEAD~1`
- **依赖：** 任务 1、任务 2。

**文件:**

- 创建：`Experiments/E8_ExecutableNeighborhood/epr_projection.py`
- 创建：`Experiments/E8_ExecutableNeighborhood/test_epr_projection.py`

- [x] **步骤 1：编写失败的测试** (Red)

在 `Experiments/E8_ExecutableNeighborhood/test_epr_projection.py` 写入：

```python
from Experiments.E8_ExecutableNeighborhood.epr_projection import (
    observed_numeric_ranges,
    project_to_observed_ranges,
    softmax_weights,
    weighted_projection,
)


def test_softmax_weights_prefers_higher_similarity():
    weights = softmax_weights([2.0, 1.0], temperature=1.0)
    assert weights[0] > weights[1]
    assert round(sum(weights), 10) == 1.0


def test_observed_numeric_ranges_collects_min_max():
    items = [{"Parameters": {"DriverOn": {"Distortion": 0.1}}}, {"Parameters": {"DriverOn": {"Distortion": 0.9}}}]
    assert observed_numeric_ranges(items) == {"DriverOn.Distortion": (0.1, 0.9)}


def test_project_to_observed_ranges_clips_values():
    params = {"DriverOn": {"Distortion": 1.5}}
    ranges = {"DriverOn.Distortion": (0.1, 0.9)}
    assert project_to_observed_ranges(params, ranges) == {"DriverOn": {"Distortion": 0.9}}


def test_weighted_projection_blends_then_projects():
    candidates = [
        {"DriverOn": {"Distortion": 0.0}},
        {"DriverOn": {"Distortion": 1.0}},
    ]
    projected, provenance = weighted_projection(candidates, [0.25, 0.75], {"DriverOn.Distortion": (0.2, 0.7)})
    assert projected == {"DriverOn": {"Distortion": 0.7}}
    assert provenance["max_weight"] == 0.75
```

- [x] **步骤 2：运行测试确认失败** (Red)

运行：`python3 -m pytest Experiments/E8_ExecutableNeighborhood/test_epr_projection.py -v`

预期：FAIL with `ModuleNotFoundError`

- [x] **步骤 3：编写最小实现** (Green)

实现：

```python
def softmax_weights(scores: Sequence[float], temperature: float) -> List[float]:
    if temperature <= 0:
        raise ValueError("temperature must be positive")
    arr = np.asarray(scores, dtype=np.float64) / float(temperature)
    arr = arr - float(np.max(arr))
    exp = np.exp(arr)
    return [float(x) for x in exp / exp.sum()]
```

CLI 必须读取任务 2 的 Top-K JSON，按 `method=TRR` 生成 `EPR-K3` 与 `EPR-K5` 两组输出；若某 query 的 top-K 少于 K，则保留实际候选数并记录 `effective_k`。

- [x] **步骤 4：运行测试和真实导出** (Green)

运行：

```bash
python3 -m pytest Experiments/E8_ExecutableNeighborhood/test_epr_projection.py -v
python3 Experiments/E8_ExecutableNeighborhood/epr_projection.py \
  --dataset Data/External_1267_211/dataset/dataset_full_vectors_1267.json \
  --topk-json Experiments/E8_ExecutableNeighborhood/outputs/topk/topk_retrieval_metrics.json \
  --method TRR \
  --ks 3 5 \
  --temperature 0.05 \
  --output-dir Experiments/E8_ExecutableNeighborhood/outputs/epr
```

预期：

```text
4 passed
wrote Experiments/E8_ExecutableNeighborhood/outputs/epr/epr_projection_results.csv
wrote Experiments/E8_ExecutableNeighborhood/outputs/epr/epr_projection_results.json
```

- [x] **步骤 5：提交代码**

```bash
git add Experiments/E8_ExecutableNeighborhood/epr_projection.py \
  Experiments/E8_ExecutableNeighborhood/test_epr_projection.py \
  Experiments/E8_ExecutableNeighborhood/outputs/epr/epr_projection_results.csv \
  Experiments/E8_ExecutableNeighborhood/outputs/epr/epr_projection_results.json
git commit -m "feat: add exemplar-preserving parameter projection"
```

- [x] **步骤 6：请求代码审查** (必需)

```bash
BASE_SHA=$(git rev-parse HEAD~1)
HEAD_SHA=$(git rev-parse HEAD)
```

提供给子代理：
- **WHAT_WAS_IMPLEMENTED**: 新增 EPR/RCPP top-K weighted parameter projection，含 observed-range projection 与 provenance 指标。
- **PLAN_OR_REQUIREMENTS**: 本计划任务 3。
- **BASE_SHA**: `$BASE_SHA`
- **HEAD_SHA**: `$HEAD_SHA`
- **DESCRIPTION**: `Add exemplar-preserving projection for top-k retrieved presets`

**在审查反馈处理完毕之前，不要继续下一个任务。**

---

### 任务 4: Oracle-Free Module-Aware Reranking

**Status:** COMPLETE  
**Completed:** 2026-05-03  
**Commits:** Task 4 commit in this branch

**Harness（测试框架）:**

- **范围：** 新增候选邻域内部的 active-module consensus reranking。只使用 top-K 候选参数与相似度，不读取 query ground-truth module labels；输出 reranked top-1 与原 top-1 对比。
- **前置条件：** 任务 1-2 已提交。
- **测试入口：** `python3 -m pytest Experiments/E8_ExecutableNeighborhood/test_module_aware_rerank.py -v`
- **通过标准：** 8 个测试通过，0 失败；真实运行生成 `module_aware_rerank_results.csv/json`。
- **失败恢复：** `git reset --hard HEAD~1`
- **依赖：** 任务 1、任务 2。

**文件:**

- 创建：`Experiments/E8_ExecutableNeighborhood/module_aware_rerank.py`
- 创建：`Experiments/E8_ExecutableNeighborhood/test_module_aware_rerank.py`

- [x] **步骤 1：编写失败的测试** (Red)

在 `Experiments/E8_ExecutableNeighborhood/test_module_aware_rerank.py` 写入：

```python
from Experiments.E8_ExecutableNeighborhood.module_aware_rerank import (
    candidate_module_consensus,
    rerank_by_module_consensus,
)


def test_candidate_module_consensus_weights_active_modules():
    candidates = [
        {"Parameters": {"DriverOn": {}, "DelayOff": {}}},
        {"Parameters": {"DriverOn": {}, "ReverbOn": {}}},
    ]
    assert candidate_module_consensus(candidates, [0.75, 0.25]) == {"Driver": 1.0, "Reverb": 0.25}


def test_rerank_by_module_consensus_uses_similarity_and_consensus():
    candidates = [
        {"SongName": "A", "Parameters": {"DelayOn": {}}},
        {"SongName": "B", "Parameters": {"DriverOn": {}, "ReverbOn": {}}},
        {"SongName": "C", "Parameters": {"DriverOn": {}}},
    ]
    ranked = rerank_by_module_consensus(candidates, [0.9, 0.85, 0.8], module_weight=0.5)
    assert ranked[0]["SongName"] == "B"


def test_rerank_does_not_require_query_parameters():
    candidates = [{"SongName": "A", "Parameters": {"DriverOn": {}}}]
    assert rerank_by_module_consensus(candidates, [1.0], module_weight=0.5)[0]["SongName"] == "A"
```

- [x] **步骤 2：运行测试确认失败** (Red)

运行：`python3 -m pytest Experiments/E8_ExecutableNeighborhood/test_module_aware_rerank.py -v`

预期：FAIL with `ModuleNotFoundError`

- [x] **步骤 3：编写最小实现** (Green)

实现 rerank score：

```python
score_i = similarity_i + module_weight * average_consensus_score(active_modules(candidate_i))
```

当候选没有 active module 时，`average_consensus_score` 返回 `0.0`；输出中记录 `original_top1_name`、`reranked_top1_name`、`changed`、`reranked_norm_l2`、`reranked_module`。

- [x] **步骤 4：运行测试和真实导出** (Green)

运行：

```bash
python3 -m pytest Experiments/E8_ExecutableNeighborhood/test_module_aware_rerank.py -v
python3 Experiments/E8_ExecutableNeighborhood/module_aware_rerank.py \
  --dataset Data/External_1267_211/dataset/dataset_full_vectors_1267.json \
  --topk-json Experiments/E8_ExecutableNeighborhood/outputs/topk/topk_retrieval_metrics.json \
  --method TRR \
  --module-weight 0.15 \
  --output-dir Experiments/E8_ExecutableNeighborhood/outputs/module_rerank
```

预期：

```text
3 passed
wrote Experiments/E8_ExecutableNeighborhood/outputs/module_rerank/module_aware_rerank_results.csv
wrote Experiments/E8_ExecutableNeighborhood/outputs/module_rerank/module_aware_rerank_results.json
```

- [x] **步骤 5：提交代码**

```bash
git add Experiments/E8_ExecutableNeighborhood/module_aware_rerank.py \
  Experiments/E8_ExecutableNeighborhood/test_module_aware_rerank.py \
  Experiments/E8_ExecutableNeighborhood/outputs/module_rerank/module_aware_rerank_results.csv \
  Experiments/E8_ExecutableNeighborhood/outputs/module_rerank/module_aware_rerank_results.json
git commit -m "feat: add oracle-free module-aware reranking"
```

- [x] **步骤 6：请求代码审查** (必需)

```bash
BASE_SHA=$(git rev-parse HEAD~1)
HEAD_SHA=$(git rev-parse HEAD)
```

提供给子代理：
- **WHAT_WAS_IMPLEMENTED**: 新增不读取 query ground truth 的 module-consensus reranker。
- **PLAN_OR_REQUIREMENTS**: 本计划任务 4。
- **BASE_SHA**: `$BASE_SHA`
- **HEAD_SHA**: `$HEAD_SHA`
- **DESCRIPTION**: `Add oracle-free module-aware reranking diagnostic`

**在审查反馈处理完毕之前，不要继续下一个任务。**

---

### 任务 5: E8 结果汇总与 Claim Boundary 文档

**Status:** COMPLETE  
**Completed:** 2026-05-03  
**Commits:** Task 5 commit in this branch

**Harness（测试框架）:**

- **范围：** 汇总任务 2-4 输出与现有 MLP boundary JSON，生成 paper-facing Markdown/JSON。该任务只做统计汇总，不改论文正文。
- **前置条件：** 任务 2-4 已提交；存在 `Experiments/E2_SOTABaselines/outputs/p0_mlp_regressor/mlp_regressor_results.json`。
- **测试入口：** `python3 -m pytest Experiments/E8_ExecutableNeighborhood/test_summarize_e8.py -v`
- **通过标准：** 8 个测试通过，0 失败；真实运行生成 `e8_summary.md/json`。
- **失败恢复：** `git reset --hard HEAD~1`
- **依赖：** 任务 2、任务 3、任务 4。

**文件:**

- 创建：`Experiments/E8_ExecutableNeighborhood/summarize_e8.py`
- 创建：`Experiments/E8_ExecutableNeighborhood/test_summarize_e8.py`
- 创建：`Experiments/E8_ExecutableNeighborhood/README.md`

- [x] **步骤 1：编写失败的测试** (Red)

在 `Experiments/E8_ExecutableNeighborhood/test_summarize_e8.py` 写入：

```python
from Experiments.E8_ExecutableNeighborhood.summarize_e8 import mean_by_method, recommendation_from_metrics


def test_mean_by_method_groups_numeric_fields():
    rows = [
        {"method": "TRR", "pnr_at_5": 1, "top1_norm_l2": 0.2},
        {"method": "TRR", "pnr_at_5": 0, "top1_norm_l2": 0.4},
    ]
    assert mean_by_method(rows, ["pnr_at_5", "top1_norm_l2"]) == {
        "TRR": {"n": 2, "pnr_at_5": 0.5, "top1_norm_l2": 0.3}
    }


def test_recommendation_keeps_mlp_as_boundary_when_numeric_wins():
    text = recommendation_from_metrics(
        trr_norm_l2=0.1881,
        epr_norm_l2=0.1700,
        mlp_norm_l2=0.1603,
        epr_provenance=0.72,
    )
    assert "boundary" in text
    assert "provenance" in text


def test_recommendation_promotes_epr_when_it_beats_mlp():
    text = recommendation_from_metrics(
        trr_norm_l2=0.1881,
        epr_norm_l2=0.1500,
        mlp_norm_l2=0.1603,
        epr_provenance=0.72,
    )
    assert "primary hybrid result" in text
```

- [x] **步骤 2：运行测试确认失败** (Red)

运行：`python3 -m pytest Experiments/E8_ExecutableNeighborhood/test_summarize_e8.py -v`

预期：FAIL with `ModuleNotFoundError`

- [x] **步骤 3：编写最小实现** (Green)

`e8_summary.md` 必须包含以下固定小节：

```markdown
# E8 Executable Neighborhood Retrieval Summary

## Scope
## Top-K Parameter Neighborhood Recall
## Exemplar-Preserving Parameter Projection
## Module-Aware Reranking
## MLP Boundary Interpretation
## Claims Supported
## Claims Not Supported
```

`Claims Not Supported` 必须列出：

- PC-TRR 训练收益未验证。
- Temporal Pyramid TRR 未验证。
- Log-Covariance/Riemannian TRR 未验证。
- Analysis-by-synthesis reranking 未验证。
- Protocol-C adaptive fusion 不能作为主贡献。

- [x] **步骤 4：运行测试和真实汇总** (Green)

运行：

```bash
python3 -m pytest Experiments/E8_ExecutableNeighborhood/test_summarize_e8.py -v
python3 Experiments/E8_ExecutableNeighborhood/summarize_e8.py \
  --topk-json Experiments/E8_ExecutableNeighborhood/outputs/topk/topk_retrieval_metrics.json \
  --epr-json Experiments/E8_ExecutableNeighborhood/outputs/epr/epr_projection_results.json \
  --module-json Experiments/E8_ExecutableNeighborhood/outputs/module_rerank/module_aware_rerank_results.json \
  --mlp-json Experiments/E2_SOTABaselines/outputs/p0_mlp_regressor/mlp_regressor_results.json \
  --output-dir Experiments/E8_ExecutableNeighborhood/outputs/summary
```

预期：

```text
3 passed
wrote Experiments/E8_ExecutableNeighborhood/outputs/summary/e8_summary.json
wrote Experiments/E8_ExecutableNeighborhood/outputs/summary/e8_summary.md
```

- [x] **步骤 5：提交代码**

```bash
git add Experiments/E8_ExecutableNeighborhood/summarize_e8.py \
  Experiments/E8_ExecutableNeighborhood/test_summarize_e8.py \
  Experiments/E8_ExecutableNeighborhood/README.md \
  Experiments/E8_ExecutableNeighborhood/outputs/summary/e8_summary.json \
  Experiments/E8_ExecutableNeighborhood/outputs/summary/e8_summary.md
git commit -m "docs: summarize executable neighborhood evidence"
```

- [x] **步骤 6：请求代码审查** (必需)

```bash
BASE_SHA=$(git rev-parse HEAD~1)
HEAD_SHA=$(git rev-parse HEAD)
```

提供给子代理：
- **WHAT_WAS_IMPLEMENTED**: 新增 E8 汇总与 claim boundary 文档。
- **PLAN_OR_REQUIREMENTS**: 本计划任务 5。
- **BASE_SHA**: `$BASE_SHA`
- **HEAD_SHA**: `$HEAD_SHA`
- **DESCRIPTION**: `Summarize executable-neighborhood evidence and claim boundaries`

**在审查反馈处理完毕之前，不要继续下一个任务。**

---

### 任务 6: 论文正文重定位为 Parameter-Transferability-Aware Retrieval

**Status:** COMPLETE  
**Completed:** 2026-05-03  
**Commits:** Task 6 commit in this branch

**Harness（测试框架）:**

- **范围：** 修改论文叙事与表述：abstract、introduction、contributions、method framing、direct-regression boundary、discussion、limitations、conclusion；新增 supplement 中的 E8 表。不得写入 E8 未支持的 claim。
- **前置条件：** 任务 5 已提交；`e8_summary.md/json` 已生成。
- **测试入口：** `latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex`
- **通过标准：** LaTeX 编译成功；正文不出现 “PC-TRR” 作为已实现主方法；不出现 “universally superior” 或 “proves perceptual preference”。
- **失败恢复：** `git reset --hard HEAD~1`
- **依赖：** 任务 5。

**文件:**

- 修改：`Paper_submission/content.tex`
- 修改：`Paper_submission/supplementary.tex`

- [x] **步骤 1：编写失败的文本门禁** (Red)

运行：

```bash
python3 - <<'PY'
from pathlib import Path
p = Path("Paper_submission/content.tex").read_text()
required = [
    "parameter-transferability-aware executable neighborhood retrieval",
    "exemplar-preserving",
    "direct regression is a numeric boundary",
]
missing = [x for x in required if x not in p]
if missing:
    raise SystemExit("missing required framing: " + ", ".join(missing))
PY
```

预期：失败并输出缺失 framing。

- [x] **步骤 2：改写 Abstract 和 Contributions** (Green)

将 `Paper_submission/content.tex` abstract 替换为同等长度的证据约束版本：

```latex
\begin{abstract}
Digital audio workstations expose editable effect chains, but mapping perceptual intent to low-level parameters is not only a similarity-retrieval problem. A useful system must find an executable neighborhood whose presets are perceptually plausible, parameter-transferable, and directly editable. We study this setting as parameter-transferability-aware executable neighborhood retrieval for guitar-effect control. Texture Resonance Retrieval (TRR) represents audio with second-order Gram statistics of projected mid-level Wav2Vec2 activations and uses this representation as a texture-aware prior over executable presets. On an audited 204-query benchmark with 1,063 candidate presets, TRR improves over selected audio-retrieval baselines, while Top-K neighborhood diagnostics and exemplar-preserving projection characterize the trade-off between retrieved provenance and numeric parameter accuracy. A range-projected MLP remains a strong direct-regression boundary, showing that lower normalized parameter error alone does not settle the editable-control problem. Near-duplicate, hard-split, listening, and degradation diagnostics define the scope of the claim rather than broad perceptual superiority.
\end{abstract}
```

把 Introduction contribution 段落改为四点：

```latex
Concretely, this paper makes four evidence-bounded contributions. First, we formulate editable guitar-effect control as parameter-transferability-aware executable neighborhood retrieval, distinguishing it from waveform generation, general perceptual retrieval, and direct parameter regression. Second, we evaluate TRR as a second-order texture prior for retrieving parameter-transferable executable presets. Third, we add Top-K neighborhood and exemplar-preserving projection diagnostics to measure whether retrieval places a query in a useful editable preset neighborhood rather than only optimizing top-1 similarity. Fourth, we report an audited evaluation package including Protocol-A retrieval, near-duplicate filtering, parameter-cluster hard split, direct-regression boundary, multimodal degradation diagnostics, and exploratory listening evidence.
```

- [x] **步骤 3：改写 MLP boundary 与 E8 结果段落** (Green)

在 `Direct-regression boundary` 后新增 E8 结果段。段落必须按任务 5 的真实数字填写，模板如下：

```latex
\paragraph{Executable-neighborhood diagnostics.}
Table~\ref{tab:executable_neighborhood} reports Top-K parameter-neighborhood recall and exemplar-preserving projection on the same Protocol-A split. These metrics change the comparison target: instead of asking whether top-1 retrieval minimizes every numeric parameter leaf, they ask whether the retrieved set contains a parameter-transferable executable neighborhood and whether a constrained projection over that neighborhood can reduce error while preserving provenance. The result supports the narrower interpretation that retrieval provides auditable candidate structure, whereas the MLP remains a numeric boundary without exemplar provenance.
```

在 `Paper_submission/supplementary.tex` 新增表 `tab:executable_neighborhood_supp`，列为：

```latex
Method & K & PNR@K & Norm.L2 & Acc@0.1 & EditCost & Provenance
```

- [x] **步骤 4：运行编译和 claim grep** (Green)

运行：

```bash
cd Paper_submission
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
cd ..
python3 - <<'PY'
from pathlib import Path
p = Path("Paper_submission/content.tex").read_text()
for forbidden in ["universally superior", "proves perceptual preference"]:
    if forbidden in p:
        raise SystemExit(f"forbidden overclaim: {forbidden}")
if "PC-TRR" in p and "future" not in p[p.index("PC-TRR")-120:p.index("PC-TRR")+120].lower():
    raise SystemExit("PC-TRR appears outside a future-work boundary")
print("claim grep passed")
PY
```

预期：

```text
Output written on main.pdf
claim grep passed
```

- [x] **步骤 5：提交代码**

```bash
git add Paper_submission/content.tex Paper_submission/supplementary.tex Paper_submission/main.pdf
git commit -m "paper: reframe trr as executable neighborhood retrieval"
```

- [x] **步骤 6：请求代码审查** (必需)

```bash
BASE_SHA=$(git rev-parse HEAD~1)
HEAD_SHA=$(git rev-parse HEAD)
```

提供给子代理：
- **WHAT_WAS_IMPLEMENTED**: 将论文重定位为 parameter-transferability-aware executable neighborhood retrieval，并纳入 E8 指标与 MLP boundary 解释。
- **PLAN_OR_REQUIREMENTS**: 本计划任务 6。
- **BASE_SHA**: `$BASE_SHA`
- **HEAD_SHA**: `$HEAD_SHA`
- **DESCRIPTION**: `Reframe manuscript around executable neighborhood retrieval`

**在审查反馈处理完毕之前，不要继续下一个任务。**

---

### 任务 7: 最终一致性、证据包与投稿前门禁

**Harness（测试框架）:**

- **范围：** 运行所有新增测试、关键旧测试、LaTeX 编译、证据文件存在性检查和 claim boundary 检查；更新 `Experiments/E8_ExecutableNeighborhood/README.md` 的最终命令记录。不新增方法。
- **前置条件：** 任务 1-6 已提交并通过代码审查。
- **测试入口：** `python3 -m pytest Experiments/common/tests/test_parameter_space.py Experiments/E8_ExecutableNeighborhood -v`
- **通过标准：** 新增 pytest 全部通过；`latexmk` 通过；E8 output JSON/CSV/MD 全部存在；README 列出 supported/unsupported claims。
- **失败恢复：** `git reset --hard HEAD~1`
- **依赖：** 任务 6。

**文件:**

- 修改：`Experiments/E8_ExecutableNeighborhood/README.md`
- 修改：`Paper_submission/main.pdf`

- [ ] **步骤 1：编写最终门禁脚本** (Red)

在终端运行：

```bash
python3 - <<'PY'
from pathlib import Path
required = [
    "Experiments/E8_ExecutableNeighborhood/outputs/topk/topk_retrieval_metrics.json",
    "Experiments/E8_ExecutableNeighborhood/outputs/epr/epr_projection_results.json",
    "Experiments/E8_ExecutableNeighborhood/outputs/module_rerank/module_aware_rerank_results.json",
    "Experiments/E8_ExecutableNeighborhood/outputs/summary/e8_summary.md",
    "Paper_submission/main.pdf",
]
missing = [p for p in required if not Path(p).exists()]
if missing:
    raise SystemExit("missing artifacts: " + ", ".join(missing))
print("artifact gate passed")
PY
```

预期：如果前序任务未完整执行，失败并列出缺失文件。

- [ ] **步骤 2：运行完整测试与编译** (Green)

运行：

```bash
python3 -m pytest Experiments/common/tests/test_parameter_space.py Experiments/E8_ExecutableNeighborhood -v
cd Paper_submission
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
cd ..
```

预期：pytest 全部通过；LaTeX 输出 `Output written on main.pdf`。

- [ ] **步骤 3：更新 README 的最终执行记录** (Green)

在 `Experiments/E8_ExecutableNeighborhood/README.md` 中写入：

````markdown
# E8 Executable Neighborhood Retrieval

## Purpose
This experiment supports the manuscript reframing from top-1 similarity retrieval to parameter-transferability-aware executable neighborhood retrieval.

## Commands
```bash
python3 Experiments/E8_ExecutableNeighborhood/topk_retrieval_dump.py --dataset Data/External_1267_211/dataset/dataset_full_vectors_1267.json --split-file Experiments/tmm/splits/tmm_external1267_audio_grouped/seed0/test.txt --k 5 --threshold 0.10 --output-dir Experiments/E8_ExecutableNeighborhood/outputs/topk
python3 Experiments/E8_ExecutableNeighborhood/epr_projection.py --dataset Data/External_1267_211/dataset/dataset_full_vectors_1267.json --topk-json Experiments/E8_ExecutableNeighborhood/outputs/topk/topk_retrieval_metrics.json --method TRR --ks 3 5 --temperature 0.05 --output-dir Experiments/E8_ExecutableNeighborhood/outputs/epr
python3 Experiments/E8_ExecutableNeighborhood/module_aware_rerank.py --dataset Data/External_1267_211/dataset/dataset_full_vectors_1267.json --topk-json Experiments/E8_ExecutableNeighborhood/outputs/topk/topk_retrieval_metrics.json --method TRR --module-weight 0.15 --output-dir Experiments/E8_ExecutableNeighborhood/outputs/module_rerank
python3 Experiments/E8_ExecutableNeighborhood/summarize_e8.py --topk-json Experiments/E8_ExecutableNeighborhood/outputs/topk/topk_retrieval_metrics.json --epr-json Experiments/E8_ExecutableNeighborhood/outputs/epr/epr_projection_results.json --module-json Experiments/E8_ExecutableNeighborhood/outputs/module_rerank/module_aware_rerank_results.json --mlp-json Experiments/E2_SOTABaselines/outputs/p0_mlp_regressor/mlp_regressor_results.json --output-dir Experiments/E8_ExecutableNeighborhood/outputs/summary
```

## Supported Claims
- Retrieval can be evaluated as executable neighborhood discovery using PNR@K.
- Exemplar-preserving projection can be compared against direct regression while retaining provenance metrics.
- The MLP remains a numeric boundary when it wins Norm.L2.

## Unsupported Claims
- PC-TRR is not validated in this run.
- Temporal Pyramid TRR is not validated in this run.
- Log-Covariance TRR is not validated in this run.
- Analysis-by-synthesis reranking is not validated in this run.
- Protocol-C adaptive fusion is diagnostic, not a main superiority claim.
````

- [ ] **步骤 4：运行最终 artifact gate** (Green)

运行：

```bash
python3 - <<'PY'
from pathlib import Path
required = [
    "Experiments/E8_ExecutableNeighborhood/outputs/topk/topk_retrieval_metrics.json",
    "Experiments/E8_ExecutableNeighborhood/outputs/epr/epr_projection_results.json",
    "Experiments/E8_ExecutableNeighborhood/outputs/module_rerank/module_aware_rerank_results.json",
    "Experiments/E8_ExecutableNeighborhood/outputs/summary/e8_summary.md",
    "Paper_submission/main.pdf",
]
missing = [p for p in required if not Path(p).exists()]
if missing:
    raise SystemExit("missing artifacts: " + ", ".join(missing))
print("artifact gate passed")
PY
```

预期：`artifact gate passed`

- [ ] **步骤 5：提交代码**

```bash
git add Experiments/E8_ExecutableNeighborhood/README.md Paper_submission/main.pdf
git commit -m "chore: verify executable neighborhood evidence package"
```

- [ ] **步骤 6：请求代码审查** (必需)

```bash
BASE_SHA=$(git rev-parse HEAD~1)
HEAD_SHA=$(git rev-parse HEAD)
```

提供给子代理：
- **WHAT_WAS_IMPLEMENTED**: 完成 E8 证据包最终门禁、README 命令记录与 PDF 编译验证。
- **PLAN_OR_REQUIREMENTS**: 本计划任务 7。
- **BASE_SHA**: `$BASE_SHA`
- **HEAD_SHA**: `$HEAD_SHA`
- **DESCRIPTION**: `Verify executable-neighborhood evidence package`

**在审查反馈处理完毕之前，不要继续下一个任务。**

---

## Quality Gate

每个任务进入下一任务前必须满足：

- [ ] 该任务新增测试全部通过。
- [ ] 该任务相关旧测试无回归。
- [ ] 没有 lint/type 层面的明显错误。
- [ ] 已提交独立 commit。
- [ ] 没有占位注释或未落实说明。
- [ ] Harness 通过标准已满足。
- [ ] 已使用 `requesting-code-review` 完成审查，并处理关键/重要反馈。

---

## Self-Review

**1. Spec coverage:**  
用户要求的核心重定位由任务 6 覆盖；Top-K neighborhood metrics 由任务 1-2 覆盖；top-K weighted blending / EPR 由任务 3 覆盖；module-aware reranking 由任务 4 覆盖；MLP boundary 叙事转化由任务 5-6 覆盖；hard-subset/near-duplicate 继续引用现有 E5/E7，不在本轮重复实现；PC-TRR、Temporal Pyramid、Log-Covariance、analysis-by-synthesis 被明确列为下一阶段未验证扩展。

**2. Placeholder scan:**  
计划没有使用占位式实现说明。所有新增文件、命令、预期输出、核心测试与正文替换段落均给出。

**3. Type consistency:**  
任务 1 定义 `flatten_numeric_params`、`active_modules`、`blend_parameter_dicts`、`exemplar_provenance_score`；任务 3-4 复用这些名称，没有引入不一致函数名。

**4. Harness completeness:**  
7 个任务都包含范围、前置条件、测试入口、通过标准、失败恢复、依赖。

**5. Atomicity check:**  
任务按指标基础、Top-K dump、EPR、module rerank、汇总、论文改写、最终门禁拆分，每个任务可以独立提交和回滚。

**6. TDD compliance:**  
任务 1-5 都先写失败测试；任务 6-7 使用文本/产物门禁作为 Red 阶段，再进行论文和验证改动。

**7. Code Review compliance:**  
每个任务都包含 Step 6，要求使用 `requesting-code-review` 并在反馈处理前不得继续。
