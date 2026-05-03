# TMM 论文 Major Revision 实现计划

> **给执行者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐步实现此计划。步骤使用复选框（`- [ ]`）语法以便跟踪。

**目标：** 将 `Paper_submission` 从“系统型技术报告”收敛为证据边界清晰、协议可审计、主张不过界的 IEEE TMM major revision 稿件。

**架构：** 本计划先用自动化检查固定论文主张边界，再补齐最关键的 hard split 实验协议，随后重跑主检索表、补 uncached latency 边界，最后把结果以克制叙事整合进 LaTeX 并编译验证。方法层面不引入大规模 TRR++，避免在小数据集上新增过拟合风险；只把 hard split、normalized metrics、baseline fairness 和 claim consistency 做扎实。

**技术栈：** Python 3、`unittest`、现有 `Experiments/common/*` 评估模块、CSV/JSON 实验产物、IEEEtran LaTeX、`latexmk`。

**依赖关系图：**
```text
任务 1 ──→ 任务 2 ──→ 任务 3 ──→ 任务 5
                          │
任务 4 ───────────────────┘
```

---

## 文件结构

- `Experiments/common/claim_audit.py`：新增轻量论文文本审计工具，检查标题、摘要、Table I、正文是否仍含 overclaim 和 revision-memo 语气。
- `Experiments/common/tests/test_claim_audit.py`：新增 claim-audit 单元测试。
- `Experiments/common/hard_split.py`：新增 hard split 构造逻辑，按 normalized parameter fingerprint 聚类，防止同一近重复簇跨 query/KB。
- `Experiments/common/tests/test_hard_split.py`：新增 hard split 单元测试。
- `Experiments/E7_HardSplit/run_hard_split_retrieval.py`：新增 hard split 检索重跑入口，复用现有 evaluator 和 embedding retriever。
- `Experiments/E7_HardSplit/README.md`：新增实验说明，记录 split 定义、输入、输出和不可外推边界。
- `Experiments/E6_Latency/latency_profiler.py`：扩展现有 latency profiler，拆分 cached retrieval 与 uncached encoding 计时。
- `Paper_submission/content.tex`：修改摘要、贡献、Table I、Protocol-A、near-duplicate/hard split、latency、fusion、limitations。
- `Paper_submission/supplementary.tex`：同步补 hard split 细表、claim audit 说明、latency 细节。
- `Paper_submission/main.tex`：仅在编译依赖或标题需要时修改。

---

### 任务 1: 论文主张边界审计工具

**Harness（测试框架）:**

- **范围：** 新增一个文本审计工具，自动发现 `Paper_submission` 中不应作为主贡献出现的表述，包括 `Dual-Modal Retrieval`、`multimodal agent`、`real-time` 强 claim、`current codebase`、`server-side`、`journal readers`、`upon acceptance`。本任务只做检测工具，不改论文正文。
- **前置条件：** 当前工作区允许新增 `Experiments/common/claim_audit.py` 和测试文件；不要求论文已编译通过。
- **测试入口：** `python -m unittest Experiments.common.tests.test_claim_audit -v`
- **通过标准：** 4 个测试通过，0 失败；工具能返回违规项的文件、行号、pattern 和 reason。
- **失败恢复：** `git reset --hard HEAD~1`
- **依赖：** 无。

**文件:**

- 创建：`Experiments/common/claim_audit.py`
- 创建：`Experiments/common/tests/test_claim_audit.py`

- [ ] **步骤 1：编写失败的测试** (Red)

在 `Experiments/common/tests/test_claim_audit.py` 写入：

```python
import tempfile
import unittest
from pathlib import Path

from Experiments.common.claim_audit import audit_files


class ClaimAuditTests(unittest.TestCase):
    def test_flags_dual_modal_as_overclaim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            paper = Path(tmp_dir) / "content.tex"
            paper.write_text("Our system uses Dual-Modal Retrieval as the core contribution.\n", encoding="utf-8")

            findings = audit_files([paper])

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["line"], 1)
        self.assertEqual(findings[0]["pattern"], "Dual-Modal Retrieval")
        self.assertIn("multimodal claim", findings[0]["reason"])

    def test_flags_revision_memo_language(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            paper = Path(tmp_dir) / "supplementary.tex"
            paper.write_text("The current codebase uses a server-side artifact snapshot.\n", encoding="utf-8")

            findings = audit_files([paper])

        patterns = {finding["pattern"] for finding in findings}
        self.assertEqual(patterns, {"current codebase", "server-side"})

    def test_clean_narrow_claim_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            paper = Path(tmp_dir) / "content.tex"
            paper.write_text(
                "We study texture-aware retrieval for executable guitar-effect preset selection.\n",
                encoding="utf-8",
            )

            findings = audit_files([paper])

        self.assertEqual(findings, [])

    def test_reports_file_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            paper = Path(tmp_dir) / "content.tex"
            paper.write_text("This demonstrates real-time deployment.\n", encoding="utf-8")

            findings = audit_files([paper])

        self.assertEqual(findings[0]["file"], str(paper))
        self.assertEqual(findings[0]["pattern"], "real-time deployment")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **步骤 2：运行测试确认失败** (Red)

运行：`python -m unittest Experiments.common.tests.test_claim_audit -v`

预期：`ModuleNotFoundError: No module named 'Experiments.common.claim_audit'`

- [ ] **步骤 3：编写最小实现** (Green)

在 `Experiments/common/claim_audit.py` 写入：

```python
from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List


FORBIDDEN_PATTERNS = {
    "Dual-Modal Retrieval": "multimodal claim is not supported as a main contribution",
    "multimodal agent": "multimodal claim is not supported as a main contribution",
    "robust multimodal": "multimodal claim is not supported as a main contribution",
    "real-time deployment": "latency evidence is not sufficient for deployment-level real-time claims",
    "current codebase": "revision-memo language should not appear in the paper",
    "verified artifact set": "revision-memo language should not appear in the paper",
    "server-side": "internal execution provenance should be moved to lab notes",
    "journal readers often care": "meta-commentary should not appear in the paper",
    "upon acceptance": "release promises should not replace reproducibility details",
}


def audit_files(paths: Iterable[Path]) -> List[Dict[str, object]]:
    findings: List[Dict[str, object]] = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), start=1):
            for pattern, reason in FORBIDDEN_PATTERNS.items():
                if pattern in line:
                    findings.append(
                        {
                            "file": str(path),
                            "line": line_no,
                            "pattern": pattern,
                            "reason": reason,
                            "text": line.strip(),
                        }
                    )
    return findings
```

- [ ] **步骤 4：运行测试确认通过** (Green)

运行：`python -m unittest Experiments.common.tests.test_claim_audit -v`

预期：`Ran 4 tests` 且 `OK`

- [ ] **步骤 5：提交代码**

```bash
git add Experiments/common/claim_audit.py Experiments/common/tests/test_claim_audit.py
git commit -m "test: add paper claim audit harness"
```

- [ ] **步骤 6：请求代码审查** (必需)

使用 `superpowers:requesting-code-review` 技能：

```bash
BASE_SHA=$(git rev-parse HEAD~1)
HEAD_SHA=$(git rev-parse HEAD)
```

提供给子代理：
- **WHAT_WAS_IMPLEMENTED**: 新增论文主张边界审计工具和 4 个单元测试。
- **PLAN_OR_REQUIREMENTS**: `docs/superpowers/plans/2026-05-03-tmm-paper-major-revision.md` 任务 1。
- **BASE_SHA**: `$BASE_SHA`
- **HEAD_SHA**: `$HEAD_SHA`
- **DESCRIPTION**: Claim audit harness for TMM revision overclaim control.

**在审查反馈处理完毕之前，不要继续下一个任务。**

---

### 任务 2: Parameter-Cluster Hard Split 构造器

**Harness（测试框架）:**

- **范围：** 新增 hard split 构造器，按 normalized parameter RMSE 阈值把近重复样本连通成 cluster，并保证 query cluster 与 KB cluster 不交叉。本任务只生成 split 和 audit summary，不运行检索模型。
- **前置条件：** 任务 1 已提交；`Experiments/common/evaluate.py` 可导入；数据项包含 `Parameters` 和 `SongName`。
- **测试入口：** `python -m unittest Experiments.common.tests.test_hard_split -v`
- **通过标准：** 5 个测试通过，0 失败；同一 cluster 内样本不会被拆到 query/KB 两侧；输出包含 `test_indices`、`kb_indices`、`clusters`、`removed_query_count`。
- **失败恢复：** `git reset --hard HEAD~1`
- **依赖：** 任务 1。

**文件:**

- 创建：`Experiments/common/hard_split.py`
- 创建：`Experiments/common/tests/test_hard_split.py`

- [ ] **步骤 1：编写失败的测试** (Red)

在 `Experiments/common/tests/test_hard_split.py` 写入：

```python
import unittest

from Experiments.common.hard_split import build_parameter_cluster_split


def item(name: str, drive: float, mix: float) -> dict:
    return {
        "SongName": name,
        "Parameters": {
            "Drive": {"On": 1.0, "Amount": drive},
            "Delay": {"On": 1.0, "Mix": mix},
        },
    }


class HardSplitTests(unittest.TestCase):
    def test_keeps_near_duplicate_cluster_on_one_side(self) -> None:
        dataset = [
            item("query-a", 0.10, 0.20),
            item("near-a", 0.11, 0.20),
            item("kb-b", 0.80, 0.90),
        ]

        split = build_parameter_cluster_split(dataset, requested_query_indices=[0], threshold=0.02)

        self.assertEqual(split["test_indices"], [0])
        self.assertNotIn(1, split["kb_indices"])
        self.assertIn(2, split["kb_indices"])
        self.assertEqual(split["removed_query_count"], 0)

    def test_drops_requested_query_when_cluster_already_taken(self) -> None:
        dataset = [
            item("query-a", 0.10, 0.20),
            item("query-a-duplicate", 0.11, 0.20),
            item("kb-b", 0.80, 0.90),
        ]

        split = build_parameter_cluster_split(dataset, requested_query_indices=[0, 1], threshold=0.02)

        self.assertEqual(split["test_indices"], [0])
        self.assertEqual(split["removed_query_count"], 1)
        self.assertNotIn(1, split["kb_indices"])

    def test_threshold_zero_only_groups_exact_matches(self) -> None:
        dataset = [
            item("query-a", 0.10, 0.20),
            item("different", 0.11, 0.20),
            item("exact", 0.10, 0.20),
        ]

        split = build_parameter_cluster_split(dataset, requested_query_indices=[0], threshold=0.0)

        self.assertNotIn(2, split["kb_indices"])
        self.assertIn(1, split["kb_indices"])

    def test_cluster_summary_contains_members(self) -> None:
        dataset = [item("a", 0.10, 0.20), item("b", 0.10, 0.20)]

        split = build_parameter_cluster_split(dataset, requested_query_indices=[0], threshold=0.0)

        self.assertEqual(split["clusters"][0]["members"], [0, 1])
        self.assertEqual(split["clusters"][0]["names"], ["a", "b"])

    def test_rejects_empty_query_indices(self) -> None:
        with self.assertRaisesRegex(ValueError, "requested_query_indices must not be empty"):
            build_parameter_cluster_split([item("a", 0.1, 0.2)], requested_query_indices=[], threshold=0.02)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **步骤 2：运行测试确认失败** (Red)

运行：`python -m unittest Experiments.common.tests.test_hard_split -v`

预期：`ModuleNotFoundError: No module named 'Experiments.common.hard_split'`

- [ ] **步骤 3：编写最小实现** (Green)

在 `Experiments/common/hard_split.py` 写入：

```python
from __future__ import annotations

import math
from typing import Dict, List, Sequence

from Experiments.common.evaluate import Evaluator


def _distance(evaluator: Evaluator, left: Dict, right: Dict) -> float:
    return evaluator.compute_parameter_distance(left.get("Parameters", {}), right.get("Parameters", {}))


def _connected_components(dataset: Sequence[Dict], threshold: float) -> List[List[int]]:
    evaluator = Evaluator(normalize=True)
    n = len(dataset)
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra = find(a)
        rb = find(b)
        if ra != rb:
            parent[rb] = ra

    for i in range(n):
        for j in range(i + 1, n):
            dist = _distance(evaluator, dataset[i], dataset[j])
            if dist <= threshold or math.isclose(dist, threshold, abs_tol=1e-12):
                union(i, j)

    grouped: Dict[int, List[int]] = {}
    for idx in range(n):
        grouped.setdefault(find(idx), []).append(idx)
    return [members for _, members in sorted(grouped.items(), key=lambda pair: min(pair[1]))]


def build_parameter_cluster_split(
    dataset: Sequence[Dict],
    requested_query_indices: Sequence[int],
    threshold: float,
) -> Dict[str, object]:
    if not requested_query_indices:
        raise ValueError("requested_query_indices must not be empty")

    clusters = _connected_components(dataset, threshold)
    index_to_cluster = {
        member: cluster_id
        for cluster_id, members in enumerate(clusters)
        for member in members
    }

    selected_clusters = set()
    test_indices: List[int] = []
    removed_query_count = 0
    for idx in requested_query_indices:
        cluster_id = index_to_cluster[idx]
        if cluster_id in selected_clusters:
            removed_query_count += 1
            continue
        selected_clusters.add(cluster_id)
        test_indices.append(idx)

    kb_indices = [
        idx
        for idx in range(len(dataset))
        if index_to_cluster[idx] not in selected_clusters
    ]

    cluster_summary = [
        {
            "cluster_id": cluster_id,
            "members": members,
            "names": [str(dataset[idx].get("SongName", f"preset_{idx}")) for idx in members],
        }
        for cluster_id, members in enumerate(clusters)
    ]

    return {
        "threshold": threshold,
        "test_indices": test_indices,
        "kb_indices": kb_indices,
        "clusters": cluster_summary,
        "removed_query_count": removed_query_count,
        "cluster_count": len(clusters),
    }
```

- [ ] **步骤 4：运行测试确认通过** (Green)

运行：`python -m unittest Experiments.common.tests.test_hard_split -v`

预期：`Ran 5 tests` 且 `OK`

- [ ] **步骤 5：提交代码**

```bash
git add Experiments/common/hard_split.py Experiments/common/tests/test_hard_split.py
git commit -m "feat: add parameter cluster hard split"
```

- [ ] **步骤 6：请求代码审查** (必需)

使用 `superpowers:requesting-code-review` 技能：

```bash
BASE_SHA=$(git rev-parse HEAD~1)
HEAD_SHA=$(git rev-parse HEAD)
```

提供给子代理：
- **WHAT_WAS_IMPLEMENTED**: 新增 normalized parameter cluster hard split 构造器和测试。
- **PLAN_OR_REQUIREMENTS**: `docs/superpowers/plans/2026-05-03-tmm-paper-major-revision.md` 任务 2。
- **BASE_SHA**: `$BASE_SHA`
- **HEAD_SHA**: `$HEAD_SHA`
- **DESCRIPTION**: Parameter-cluster grouped split for leakage-audited retrieval evaluation.

**在审查反馈处理完毕之前，不要继续下一个任务。**

---

### 任务 3: Hard Split 检索重跑与结果产物

**Harness（测试框架）:**

- **范围：** 新增 `E7_HardSplit` 实验入口，基于任务 2 的 split 生成 TRR、Wav2Vec、FeatureNN、CLAP、PaSST、PANNs 的同子集结果表。若某个 embedding 缺失，脚本必须在 JSON 中显式记录 coverage，不得静默跳过。本任务不修改论文正文。
- **前置条件：** 任务 2 已提交；`Data/External_1267_211/dataset/dataset_full_vectors_1267.json` 存在；现有 baseline 向量可由 dataset 或现有脚本读取。
- **测试入口：** `python -m unittest Experiments.E7_HardSplit.test_run_hard_split_retrieval -v`
- **通过标准：** 3 个脚本级测试通过，0 失败；真实运行产出 `hard_split_results.json`、`hard_split_results.csv`、`hard_split_audit.json`。
- **失败恢复：** `git reset --hard HEAD~1`
- **依赖：** 任务 2。

**文件:**

- 创建：`Experiments/E7_HardSplit/run_hard_split_retrieval.py`
- 创建：`Experiments/E7_HardSplit/test_run_hard_split_retrieval.py`
- 创建：`Experiments/E7_HardSplit/README.md`
- 生成：`Experiments/E7_HardSplit/hard_split_results.json`
- 生成：`Experiments/E7_HardSplit/hard_split_results.csv`
- 生成：`Experiments/E7_HardSplit/hard_split_audit.json`

- [ ] **步骤 1：编写失败的测试** (Red)

在 `Experiments/E7_HardSplit/test_run_hard_split_retrieval.py` 写入：

```python
import tempfile
import unittest
from pathlib import Path

from Experiments.E7_HardSplit.run_hard_split_retrieval import write_outputs


class HardSplitRunnerTests(unittest.TestCase):
    def test_write_outputs_creates_json_csv_and_audit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)
            results = [
                {"method": "TRR", "n": 2, "norm_l2": 0.2, "acc_at_0_1": 0.6, "coverage": 1.0},
                {"method": "Wav2Vec", "n": 2, "norm_l2": 0.3, "acc_at_0_1": 0.5, "coverage": 1.0},
            ]
            audit = {"threshold": 0.02, "test_count": 2, "kb_count": 3}

            write_outputs(output_dir, results, audit)

            self.assertTrue((output_dir / "hard_split_results.json").exists())
            self.assertTrue((output_dir / "hard_split_results.csv").exists())
            self.assertTrue((output_dir / "hard_split_audit.json").exists())

    def test_csv_contains_method_header(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)
            write_outputs(output_dir, [{"method": "TRR", "n": 1, "norm_l2": 0.2}], {"threshold": 0.02})

            csv_text = (output_dir / "hard_split_results.csv").read_text(encoding="utf-8")

        self.assertTrue(csv_text.startswith("method,n,norm_l2"))

    def test_json_is_pretty_printed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)
            write_outputs(output_dir, [{"method": "TRR", "n": 1}], {"threshold": 0.02})

            json_text = (output_dir / "hard_split_results.json").read_text(encoding="utf-8")

        self.assertIn('\n  {', json_text)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **步骤 2：运行测试确认失败** (Red)

运行：`python -m unittest Experiments.E7_HardSplit.test_run_hard_split_retrieval -v`

预期：`ModuleNotFoundError: No module named 'Experiments.E7_HardSplit'`

- [ ] **步骤 3：编写最小实现** (Green)

在 `Experiments/E7_HardSplit/run_hard_split_retrieval.py` 写入最小可测输出层；真实检索逻辑在同文件后续函数中实现，但不得改变 `write_outputs` 接口：

```python
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, List


def write_outputs(output_dir: Path, results: List[Dict[str, object]], audit: Dict[str, object]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    result_keys = sorted({key for row in results for key in row.keys()})
    if "method" in result_keys:
        result_keys.remove("method")
        result_keys.insert(0, "method")

    (output_dir / "hard_split_results.json").write_text(
        json.dumps(results, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "hard_split_audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output_dir / "hard_split_results.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=result_keys)
        writer.writeheader()
        writer.writerows(results)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run parameter-cluster hard split retrieval evaluation.")
    parser.add_argument("--output-dir", default="Experiments/E7_HardSplit", help="Directory for JSON/CSV outputs.")
    args = parser.parse_args()
    raise SystemExit(
        "Retrieval execution is implemented after output contract tests pass; "
        "do not use this CLI before completing the Green phase extension."
    )


if __name__ == "__main__":
    main()
```

然后扩展同文件，实现真实逻辑：

```python
# 在 write_outputs 下方补充这些函数，并移除 main 中的临时 SystemExit。
# 复用 Experiments.common.hard_split.build_parameter_cluster_split。
# 复用 Experiments.common.evaluate.Evaluator(normalize=True) 计算 Norm.L2、Acc@0.1、Cosine。
# 对每个方法记录 coverage = usable_query_count / hard_split_query_count。
# 如果向量缺失，记录 missing_vector_count，不抛异常。
```

此处的最小实现原则是：先保证输出契约可测，再把现有 `Experiments/E2_SOTABaselines/run_comparison.py` 中的数据加载和 top-1 retrieval 逻辑搬入 `run_hard_split_retrieval.py`，不新增新的 baseline。

- [ ] **步骤 4：运行测试与真实实验** (Green)

运行单元测试：

```bash
python -m unittest Experiments.E7_HardSplit.test_run_hard_split_retrieval -v
```

预期：`Ran 3 tests` 且 `OK`

运行真实实验：

```bash
python Experiments/E7_HardSplit/run_hard_split_retrieval.py \
  --dataset Data/External_1267_211/dataset/dataset_full_vectors_1267.json \
  --threshold 0.02 \
  --output-dir Experiments/E7_HardSplit
```

预期：

```text
wrote Experiments/E7_HardSplit/hard_split_results.json
wrote Experiments/E7_HardSplit/hard_split_results.csv
wrote Experiments/E7_HardSplit/hard_split_audit.json
```

- [ ] **步骤 5：提交代码与结果**

```bash
git add Experiments/E7_HardSplit
git commit -m "test: add hard split retrieval evidence"
```

- [ ] **步骤 6：请求代码审查** (必需)

使用 `superpowers:requesting-code-review` 技能：

```bash
BASE_SHA=$(git rev-parse HEAD~1)
HEAD_SHA=$(git rev-parse HEAD)
```

提供给子代理：
- **WHAT_WAS_IMPLEMENTED**: 新增 hard split retrieval runner、测试和实验产物。
- **PLAN_OR_REQUIREMENTS**: `docs/superpowers/plans/2026-05-03-tmm-paper-major-revision.md` 任务 3。
- **BASE_SHA**: `$BASE_SHA`
- **HEAD_SHA**: `$HEAD_SHA`
- **DESCRIPTION**: Hard split retrieval evidence for TMM revision.

**在审查反馈处理完毕之前，不要继续下一个任务。**

---

### 任务 4: Uncached Latency 边界审计

**Harness（测试框架）:**

- **范围：** 扩展 latency profiler，分别报告 `audio_preprocess_ms`、`wav2vec_forward_ms`、`trr_encoding_ms`、`search_ms`、`validation_ms`、`total_uncached_ms`、`cached_search_ms`。本任务只补 latency 证据，不把它写入论文。
- **前置条件：** `Experiments/E6_Latency/latency_profiler.py` 存在；本地环境可运行现有 TRR encoding 依赖。若 Wav2Vec2 权重不可用，脚本必须输出 `status: unavailable` 和原因。
- **测试入口：** `python -m unittest Experiments.E6_Latency.test_latency_profiler -v`
- **通过标准：** 3 个测试通过，0 失败；真实运行产出 `Experiments/E6_Latency/uncached_latency_report.json` 和 `.md`。
- **失败恢复：** `git reset --hard HEAD~1`
- **依赖：** 可与任务 2 并行；任务 5 依赖本任务。

**文件:**

- 修改：`Experiments/E6_Latency/latency_profiler.py`
- 创建：`Experiments/E6_Latency/test_latency_profiler.py`
- 生成：`Experiments/E6_Latency/uncached_latency_report.json`
- 生成：`Experiments/E6_Latency/uncached_latency_report.md`

- [ ] **步骤 1：编写失败的测试** (Red)

在 `Experiments/E6_Latency/test_latency_profiler.py` 写入：

```python
import unittest

from Experiments.E6_Latency.latency_profiler import summarize_latency


class LatencyProfilerTests(unittest.TestCase):
    def test_summarize_latency_computes_total_uncached(self) -> None:
        rows = [
            {
                "audio_preprocess_ms": 1.0,
                "wav2vec_forward_ms": 10.0,
                "trr_encoding_ms": 2.0,
                "search_ms": 0.5,
                "validation_ms": 0.5,
            }
        ]

        summary = summarize_latency(rows)

        self.assertEqual(summary["median_total_uncached_ms"], 14.0)

    def test_summarize_latency_reports_p95(self) -> None:
        rows = [
            {"audio_preprocess_ms": 0.0, "wav2vec_forward_ms": float(i), "trr_encoding_ms": 0.0, "search_ms": 0.0, "validation_ms": 0.0}
            for i in range(1, 101)
        ]

        summary = summarize_latency(rows)

        self.assertEqual(summary["p95_total_uncached_ms"], 95.0)

    def test_summarize_latency_rejects_empty_rows(self) -> None:
        with self.assertRaisesRegex(ValueError, "latency rows must not be empty"):
            summarize_latency([])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **步骤 2：运行测试确认失败** (Red)

运行：`python -m unittest Experiments.E6_Latency.test_latency_profiler -v`

预期：`ImportError: cannot import name 'summarize_latency'`

- [ ] **步骤 3：编写最小实现** (Green)

在 `Experiments/E6_Latency/latency_profiler.py` 增加：

```python
from __future__ import annotations

import statistics
from typing import Dict, List


LATENCY_COMPONENTS = [
    "audio_preprocess_ms",
    "wav2vec_forward_ms",
    "trr_encoding_ms",
    "search_ms",
    "validation_ms",
]


def _percentile(values: List[float], pct: float) -> float:
    ordered = sorted(values)
    index = int(round((len(ordered) - 1) * pct))
    return ordered[index]


def summarize_latency(rows: List[Dict[str, float]]) -> Dict[str, float]:
    if not rows:
        raise ValueError("latency rows must not be empty")
    totals = [sum(float(row.get(component, 0.0)) for component in LATENCY_COMPONENTS) for row in rows]
    return {
        "median_total_uncached_ms": statistics.median(totals),
        "p95_total_uncached_ms": _percentile(totals, 0.95),
        "sample_count": float(len(rows)),
    }
```

保留现有 profiler 逻辑；若文件已有 imports，合并 imports，不重复定义 `from __future__`。

- [ ] **步骤 4：运行测试与真实 profiler** (Green)

运行测试：

```bash
python -m unittest Experiments.E6_Latency.test_latency_profiler -v
```

预期：`Ran 3 tests` 且 `OK`

运行真实 profiler：

```bash
python Experiments/E6_Latency/latency_profiler.py \
  --dataset Data/External_1267_211/dataset/dataset_full_vectors_1267.json \
  --sample-count 20 \
  --output-json Experiments/E6_Latency/uncached_latency_report.json \
  --output-md Experiments/E6_Latency/uncached_latency_report.md
```

预期：输出 JSON/Markdown；若模型权重不可用，JSON 必须包含 `"status": "unavailable"` 和 `"reason"`，论文中只能写“未完成 uncached latency 验证”。

- [ ] **步骤 5：提交代码与结果**

```bash
git add Experiments/E6_Latency/latency_profiler.py Experiments/E6_Latency/test_latency_profiler.py Experiments/E6_Latency/uncached_latency_report.json Experiments/E6_Latency/uncached_latency_report.md
git commit -m "test: add uncached latency audit"
```

- [ ] **步骤 6：请求代码审查** (必需)

使用 `superpowers:requesting-code-review` 技能：

```bash
BASE_SHA=$(git rev-parse HEAD~1)
HEAD_SHA=$(git rev-parse HEAD)
```

提供给子代理：
- **WHAT_WAS_IMPLEMENTED**: 扩展 latency profiler，区分 cached retrieval 与 uncached encoding latency。
- **PLAN_OR_REQUIREMENTS**: `docs/superpowers/plans/2026-05-03-tmm-paper-major-revision.md` 任务 4。
- **BASE_SHA**: `$BASE_SHA`
- **HEAD_SHA**: `$HEAD_SHA`
- **DESCRIPTION**: Uncached latency audit for deployment-claim boundary.

**在审查反馈处理完毕之前，不要继续下一个任务。**

---

### 任务 5: 投稿稿件整合与编译门禁

**Harness（测试框架）:**

- **范围：** 修改 `Paper_submission`，把主张收缩、hard split 结果、latency 边界、fusion 降级和 listening-study 限制整合进正文和 supplement；运行 claim audit 与 LaTeX 编译。本任务不新增实验算法。
- **前置条件：** 任务 1、任务 3、任务 4 已提交；hard split 和 latency 产物存在，或 latency 产物明确标记 unavailable。
- **测试入口：** `python - <<'PY'\nfrom pathlib import Path\nfrom Experiments.common.claim_audit import audit_files\nfindings = audit_files([Path('Paper_submission/content.tex'), Path('Paper_submission/supplementary.tex')])\nprint(findings)\nraise SystemExit(1 if findings else 0)\nPY`
- **通过标准：** claim audit 0 findings；`latexmk -pdf -interaction=nonstopmode main.tex` 在 `Paper_submission` 下成功；`Paper_submission/main.pdf` 更新时间晚于本任务开始时间。
- **失败恢复：** `git reset --hard HEAD~1`
- **依赖：** 任务 1、任务 3、任务 4。

**文件:**

- 修改：`Paper_submission/content.tex`
- 修改：`Paper_submission/supplementary.tex`
- 修改：`Paper_submission/main.tex`（仅当标题或编译依赖需要）
- 生成：`Paper_submission/main.pdf`

- [ ] **步骤 1：编写失败的文本门禁** (Red)

运行：

```bash
python - <<'PY'
from pathlib import Path
from Experiments.common.claim_audit import audit_files
findings = audit_files([Path("Paper_submission/content.tex"), Path("Paper_submission/supplementary.tex")])
for finding in findings:
    print(f'{finding["file"]}:{finding["line"]}: {finding["pattern"]}: {finding["reason"]}')
raise SystemExit(1 if findings else 0)
PY
```

预期：如果正文仍含 `Dual-Modal Retrieval`、`server-side`、`current codebase` 等，命令失败并打印具体行号；如果已经被前序人工修改清理，则记录 `0 findings`，继续步骤 3。

- [ ] **步骤 2：运行 LaTeX 编译确认当前基线** (Red)

运行：

```bash
cd Paper_submission
latexmk -pdf -interaction=nonstopmode main.tex
```

预期：若当前稿件可编译，记录成功基线；若失败，记录首个 LaTeX error，不在本步骤修复。

- [ ] **步骤 3：编写最小论文修改** (Green)

按以下替换原则修改 `Paper_submission/content.tex`：

```text
1. 标题/摘要/贡献：
   - 保留 “Texture Resonance Retrieval for Audited Guitar-Effect Preset Selection”。
   - 摘要只声称 guitar-effect preset retrieval，不声称 general music effect control。
   - contribution 改成两个主贡献：retrieval formulation；TRR under leakage-audited Protocol-A/hard split。

2. Table I：
   - 将 Ours 的 Input 从 “Text+Audio” 改为 “Audio reference; text used diagnostically”。
   - 将 Grounding 从 “Dual-Modal Retrieval” 改为 “Texture-aware preset retrieval”。

3. Protocol-A：
   - 主表保留 P0 shared 204-query table。
   - 新增一段 hard split：说明 parameter-cluster grouped split 的阈值、query 数、KB 数、coverage。
   - 若 hard split 下 TRR 仍领先，只写 “directionally consistent”；若不领先，写 “standard split advantage is density-sensitive”。

4. Protocol-C/Fusion：
   - 小节标题保留 Diagnostic。
   - 不把 adaptive fusion 写成核心贡献。

5. Latency：
   - cache-only 表述改为 cached retrieval-path latency。
   - 若 uncached report 可用，写分阶段 latency；若 unavailable，明确删除 practical real-time claim。

6. Limitations：
   - 明确 guitar-only、single chain topology、near-duplicate risk、metric-perception mismatch、regression boundary stronger on Norm.L2。
```

按以下原则修改 `Paper_submission/supplementary.tex`：

```text
1. 增加 hard split 细表，引用 `Experiments/E7_HardSplit/hard_split_results.csv` 的数值。
2. 增加 hard split audit summary，引用 `hard_split_audit.json`。
3. 增加 latency 细节，引用 `uncached_latency_report.json` 或说明 unavailable。
4. 删除 revision memo 语气：current local execution path、server-side snapshot、journal readers often care。
```

- [ ] **步骤 4：运行文本门禁和编译确认通过** (Green)

运行 claim audit：

```bash
python - <<'PY'
from pathlib import Path
from Experiments.common.claim_audit import audit_files
findings = audit_files([Path("Paper_submission/content.tex"), Path("Paper_submission/supplementary.tex")])
for finding in findings:
    print(f'{finding["file"]}:{finding["line"]}: {finding["pattern"]}: {finding["reason"]}')
raise SystemExit(1 if findings else 0)
PY
```

预期：无输出或仅输出空列表，退出码 0。

运行编译：

```bash
cd Paper_submission
latexmk -pdf -interaction=nonstopmode main.tex
```

预期：生成 `Paper_submission/main.pdf`，无 fatal error。若有 citation warning 但 PDF 成功生成，记录 warning 并检查 `main.bbl` 是否更新。

- [ ] **步骤 5：提交稿件修改**

```bash
git add Paper_submission/content.tex Paper_submission/supplementary.tex Paper_submission/main.tex Paper_submission/main.pdf
git commit -m "docs: revise TMM submission claims and hard split evidence"
```

- [ ] **步骤 6：请求代码审查** (必需)

使用 `superpowers:requesting-code-review` 技能：

```bash
BASE_SHA=$(git rev-parse HEAD~1)
HEAD_SHA=$(git rev-parse HEAD)
```

提供给子代理：
- **WHAT_WAS_IMPLEMENTED**: 整合 hard split、latency 边界和 claim 收缩，重新编译 `Paper_submission/main.pdf`。
- **PLAN_OR_REQUIREMENTS**: `docs/superpowers/plans/2026-05-03-tmm-paper-major-revision.md` 任务 5。
- **BASE_SHA**: `$BASE_SHA`
- **HEAD_SHA**: `$HEAD_SHA`
- **DESCRIPTION**: TMM major revision manuscript integration.

**在审查反馈处理完毕之前，不要宣布修订完成。**

---

## Quality Gate

每个任务进入下一任务前必须满足：

- [ ] 本任务测试全部通过。
- [ ] 未引入 lint/type/import 错误。
- [ ] 代码或论文修改已用描述性 commit 提交。
- [ ] 不存在未完成占位标记或占位注释。
- [ ] Harness Pass Criteria 已满足。
- [ ] 前序任务测试仍通过，无回归。
- [ ] 已通过 `requesting-code-review` 完成代码审查并处理反馈。

---

## 自审

**Spec coverage:**

- 审稿意见中的 overclaim 和 multimodal 叙事问题：任务 1、任务 5。
- Norm.L2 与 normalized metrics 主表问题：当前稿件已有基础，任务 5 负责保持主指标一致。
- Protocol/hard split/near-duplicate 问题：任务 2、任务 3、任务 5。
- baseline fairness：任务 3 在同一 hard split 子集上记录 coverage 和同子集结果。
- latency cache-only 问题：任务 4、任务 5。
- revision memo 语气问题：任务 1、任务 5。

**占位内容扫描:**

- 本计划不含未完成占位标记。
- 任务 3 中真实检索逻辑允许复用现有 runner，但接口、输出文件和测试契约已明确；执行者不得只提交测试层，必须完成真实实验运行产物。

**Type consistency:**

- `build_parameter_cluster_split()` 在任务 2 定义，任务 3 复用。
- `audit_files()` 在任务 1 定义，任务 5 复用。
- `summarize_latency()` 在任务 4 定义，测试与 profiler 复用同名函数。

**Harness completeness:**

- 5 个任务均包含范围、前置条件、测试入口、通过标准、失败恢复、依赖。

**Atomicity check:**

- 任务 1 只做文本审计工具。
- 任务 2 只做 hard split 构造。
- 任务 3 只做 hard split 实验产物。
- 任务 4 只做 latency 证据。
- 任务 5 只做稿件整合和编译。

**TDD compliance:**

- 每个任务均先写失败测试或失败门禁，再做最小实现，再验证通过。

**Code Review compliance:**

- 每个任务均包含 Step 6，并要求在审查反馈处理完之前不得进入下一任务。
