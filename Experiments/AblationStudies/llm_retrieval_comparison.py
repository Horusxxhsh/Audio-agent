"""
LLM增强检索方法对比实验
对比四种方法的性能指标：
1. 纯TRR检索
2. 纯Text检索
3. TRR + LLM
4. Text + LLM
"""

import argparse
import copy
import csv
import hashlib
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

# Add paths
current_dir = os.path.dirname(os.path.abspath(__file__))
common_dir = os.path.join(current_dir, '..', 'common')
sys.path.append(common_dir)

from dataset_loader import load_and_merge_data
from evaluate import Evaluator

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    print("Warning: openai not found. Cannot run LLM experiments.")

# Default held-out query pool (Protocol-B): same as Protocol-A (N=211 records; 210 unique SongName).
# NOTE: we import the split definition from direct_retrieval_comparison.py to avoid divergence.
FALLBACK_TEST_SAMPLES = [
    "Dry Funk",
    "Tweed Breakup",
    "Reverse Psychedelic",
    "Math Rock Crystal",
    "Saturated Rhythm",
]
try:
    from direct_retrieval_comparison import TEST_SAMPLE_SET as DEFAULT_TEST_NAME_SET
except Exception:
    DEFAULT_TEST_NAME_SET = set(FALLBACK_TEST_SAMPLES)

# 定义效果器
ALL_EFFECTORS = [
    'Compressor', 'Driver', 'Screamer', 'Delay', 'Reverb',
    'Chorus', 'Flanger', 'Equaliser', 'Phaser'
]


@dataclass(frozen=True)
class ParamRange:
    min_v: float
    max_v: float


def _split_module_key(module_key: str) -> Tuple[str, str]:
    if module_key.endswith("On"):
        return module_key[:-2], "On"
    if module_key.endswith("Off"):
        return module_key[:-3], "Off"
    return module_key, ""


def _to_float(x: Any) -> Optional[float]:
    if isinstance(x, (int, float)):
        return float(x)
    return None


def compute_param_ranges(dataset: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str, str], ParamRange]:
    """
    Build per-parameter value ranges from the KB (used as a deterministic projection).
    Keyed by (module_root, state, sub_key).
    """
    values: Dict[Tuple[str, str, str], List[float]] = {}
    for item in dataset:
        params = item.get("Parameters") or {}
        if not isinstance(params, dict):
            continue
        for module_key, module_value in params.items():
            if not isinstance(module_value, dict):
                continue
            root, state = _split_module_key(str(module_key))
            for sub_key, sub_value in module_value.items():
                fv = _to_float(sub_value)
                if fv is None:
                    continue
                key = (str(root), str(state), str(sub_key))
                values.setdefault(key, []).append(float(fv))

    ranges: Dict[Tuple[str, str, str], ParamRange] = {}
    for k, vs in values.items():
        if not vs:
            continue
        ranges[k] = ParamRange(min_v=float(min(vs)), max_v=float(max(vs)))
    return ranges


def project_params(params: Dict[str, Any], ranges: Dict[Tuple[str, str, str], ParamRange]) -> Dict[str, Any]:
    """
    Deterministic parameter projection:
    - Ensures each effector has either an On or Off key (defaults to Off if missing)
    - Clamps numeric values to the observed KB ranges (module_root/state/sub_key)
    """
    out: Dict[str, Any] = {}
    for eff in ALL_EFFECTORS:
        on_key = f"{eff}On"
        off_key = f"{eff}Off"

        # Choose a single state per effector.
        if on_key in params and off_key in params:
            chosen_key = on_key
            chosen_state = "On"
        elif on_key in params:
            chosen_key = on_key
            chosen_state = "On"
        elif off_key in params:
            chosen_key = off_key
            chosen_state = "Off"
        else:
            chosen_key = off_key
            chosen_state = "Off"

        module_val = params.get(chosen_key)
        if isinstance(module_val, dict):
            projected: Dict[str, Any] = {}
            for sub_key, sub_val in module_val.items():
                fv = _to_float(sub_val)
                if fv is None:
                    projected[str(sub_key)] = copy.deepcopy(sub_val)
                    continue
                pr = ranges.get((eff, chosen_state, str(sub_key)))
                if pr:
                    fv = max(pr.min_v, min(pr.max_v, fv))
                projected[str(sub_key)] = float(fv)
            out[chosen_key] = projected
        else:
            # Fill with defaults for schema completeness.
            if chosen_state == "On":
                out[chosen_key] = copy.deepcopy(get_default_on_params(eff))
            else:
                out[chosen_key] = copy.deepcopy(get_default_off_params(eff))

    return out


def _softmax_weights(scores: Sequence[float]) -> List[float]:
    s = np.asarray(list(scores), dtype=np.float64)
    if s.size == 0:
        return []
    s = s - float(np.max(s))
    w = np.exp(s)
    z = float(np.sum(w))
    if z <= 0:
        return [1.0 / float(s.size)] * int(s.size)
    w = w / z
    return [float(x) for x in w.tolist()]


def aggregate_topk_params(
    topk_params: Sequence[Dict[str, Any]], *, weights: Optional[Sequence[float]] = None
) -> Dict[str, Any]:
    """
    Aggregate Top-K retrieved parameters via (weighted) mean, using the schema of rank-1 item.
    - numeric leaves: mean / weighted mean across items where the leaf exists and is numeric
    - non-numeric leaves: kept from rank-1
    """
    if not topk_params:
        return {}
    base = copy.deepcopy(topk_params[0])
    if not isinstance(base, dict):
        return {}
    if weights is None:
        weights = [1.0] * int(len(topk_params))
    weights = list(weights)
    if len(weights) != len(topk_params):
        raise ValueError("weights must have same length as topk_params")

    for module_key, module_val in list(base.items()):
        if not isinstance(module_val, dict):
            continue
        for sub_key, sub_val in list(module_val.items()):
            if _to_float(sub_val) is None:
                continue
            acc_v = 0.0
            acc_w = 0.0
            for p, w in zip(topk_params, weights):
                mv = p.get(module_key)
                if not isinstance(mv, dict):
                    continue
                fv = _to_float(mv.get(sub_key))
                if fv is None:
                    continue
                acc_v += float(fv) * float(w)
                acc_w += float(w)
            if acc_w > 0:
                module_val[sub_key] = float(acc_v / acc_w)
    return base


def _bootstrap_ci_mean(x: np.ndarray, *, n_boot: int, seed: int, alpha: float = 0.05) -> Tuple[float, float]:
    rng = np.random.default_rng(int(seed))
    n = int(x.shape[0])
    if n <= 0:
        return float("nan"), float("nan")
    idx = rng.integers(0, n, size=(int(n_boot), n))
    samples = x[idx].mean(axis=1)
    lo = float(np.quantile(samples, alpha / 2.0))
    hi = float(np.quantile(samples, 1.0 - alpha / 2.0))
    return lo, hi


def _paired_permutation_pvalue(d: np.ndarray, *, n_perm: int, seed: int) -> float:
    rng = np.random.default_rng(int(seed))
    n = int(d.shape[0])
    if n <= 0:
        return float("nan")
    obs = float(d.mean())
    signs = rng.choice(np.array([-1.0, 1.0], dtype=float), size=(int(n_perm), n), replace=True)
    perm_means = (signs * d).mean(axis=1)
    p = (float(np.sum(np.abs(perm_means) >= abs(obs))) + 1.0) / (float(n_perm) + 1.0)
    return float(p)


def get_onoff_pattern(params):
    """从参数中提取ON/OFF模式"""
    pattern = {}
    for key in params.keys():
        for eff in ALL_EFFECTORS:
            if f'{eff}On' in key:
                pattern[eff] = 'ON'
                break
            elif f'{eff}Off' in key:
                pattern[eff] = 'OFF'
                break
    return pattern


def build_fewshot_prompt(test_name: str, test_style: str, *, with_fewshot: bool) -> str:
    """
    Build a prompt that predicts effector ON/OFF states.

    IMPORTANT: few-shot examples are handcrafted and should not be copied from held-out queries.
    We keep the style strings *not exactly equal* to any held-out query style string to avoid
    trivial prompt leakage at the text level.
    """

    if with_fewshot:
        examples_str = """Example 1: Style='clean_funk dry_funk groove' → [Compressor:ON, Driver:OFF, Screamer:OFF, Delay:ON, Reverb:ON, Chorus:ON, Flanger:OFF, Equaliser:ON, Phaser:OFF]
Example 2: Style='blues tweed_breakup vintage_drive' → [Compressor:OFF, Driver:ON, Screamer:OFF, Delay:OFF, Reverb:ON, Chorus:OFF, Flanger:OFF, Equaliser:ON, Phaser:OFF]
Example 3: Style='fx_reverse reverse_psychedelic tape_echo' → [Compressor:OFF, Driver:OFF, Screamer:OFF, Delay:OFF, Reverb:OFF, Chorus:OFF, Flanger:OFF, Equaliser:ON, Phaser:OFF]
Example 4: Style='clean_comp math_rock_crystal shimmer' → [Compressor:ON, Driver:OFF, Screamer:OFF, Delay:ON, Reverb:ON, Chorus:ON, Flanger:OFF, Equaliser:ON, Phaser:OFF]
Example 5: Style='rock_high saturated_rhythm heavy' → [Compressor:OFF, Driver:ON, Screamer:OFF, Delay:OFF, Reverb:ON, Chorus:OFF, Flanger:OFF, Equaliser:ON, Phaser:OFF]"""
        fewshot_block = f"FEW-SHOT EXAMPLES (learn the pattern):\n{examples_str}\n"
    else:
        fewshot_block = "FEW-SHOT EXAMPLES: (none)\n"

    prompt = f"""PROMPT_VERSION: onoff_v2

You are a guitar tone expert. Predict effector ON/OFF states from the target style.

{fewshot_block}
CURRENT TASK:
Target Name: "{test_name}"
Target Style: "{test_style}"

INSTRUCTIONS:
1. Output only valid JSON.
2. Only choose effectors from this fixed set:
   {ALL_EFFECTORS}

Output JSON schema:
{{"effector_on": ["Compressor", "Delay", ...], "effector_off": ["Driver", "Screamer", ...]}}"""

    return prompt


def _sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _slugify(text: str) -> str:
    keep = []
    for c in text:
        if c.isalnum() or c in ("-", "_"):
            keep.append(c)
        elif c.isspace():
            keep.append("_")
    s = "".join(keep).strip("_")
    return s[:80] if len(s) > 80 else s


def _extract_json_block(content: str) -> str:
    s = content.find("{")
    e = content.rfind("}")
    if s != -1 and e != -1 and e > s:
        return content[s : e + 1]
    return content


def _parse_onoff_json(content: str) -> Optional[Dict[str, str]]:
    content = content.replace("```json", "").replace("```", "").strip()
    content = _extract_json_block(content)
    try:
        result = json.loads(content)
    except Exception:
        return None

    on = set(result.get("effector_on", []) or [])
    pattern: Dict[str, str] = {}
    for eff in ALL_EFFECTORS:
        pattern[eff] = "ON" if eff in on else "OFF"
    return pattern


def predict_onoff_with_llm_cached(
    style: str,
    test_name: str,
    *,
    cache_dir: Path,
    allow_network: bool,
    with_fewshot: bool,
    model: str = "deepseek-chat",
) -> Optional[Dict[str, str]]:
    """
    Cache-first LLM prediction. Default behavior is offline (no network).
    Cache key: (query SongName, prompt hash).
    """
    prompt = build_fewshot_prompt(test_name, style, with_fewshot=bool(with_fewshot))
    prompt_hash = _sha256_hex(f"{model}\n{prompt}")

    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{_slugify(test_name)}__{prompt_hash[:12]}.json"

    if cache_path.exists():
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            pattern = cached.get("parsed", {}).get("pattern")
            if isinstance(pattern, dict) and pattern:
                return {str(k): str(v) for k, v in pattern.items()}
        except Exception:
            pass

    if not allow_network:
        return None

    if not HAS_OPENAI:
        return None

    api_key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("DEEPSEEK_BASE_URL") or os.environ.get("OPENAI_BASE_URL") or "https://api.deepseek.com"
    if not api_key:
        print("  LLM未配置：请设置环境变量 DEEPSEEK_API_KEY（或 OPENAI_API_KEY）。")
        return None

    # Conservative defaults: deterministic decoding + finite timeout to avoid hanging runs.
    client = OpenAI(api_key=api_key, base_url=base_url, timeout=60, max_retries=0)

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            top_p=1,
            max_tokens=128,
            stream=False,
        )
        content = resp.choices[0].message.content.strip()
        pattern = _parse_onoff_json(content)
        usage = getattr(resp, "usage", None)
        usage_obj = None
        if usage is not None:
            if hasattr(usage, "model_dump"):
                usage_obj = usage.model_dump()
            elif hasattr(usage, "dict"):
                usage_obj = usage.dict()
            else:
                usage_obj = {
                    "prompt_tokens": getattr(usage, "prompt_tokens", None),
                    "completion_tokens": getattr(usage, "completion_tokens", None),
                    "total_tokens": getattr(usage, "total_tokens", None),
                }
        cache_obj = {
            "query": {"song_name": test_name, "style": style},
            "model": model,
            "base_url": base_url,
            "prompt_hash": prompt_hash,
            "prompt_text": prompt,
            "raw_output": content,
            "parsed": {"pattern": pattern},
            "usage": usage_obj,
        }
        cache_path.write_text(json.dumps(cache_obj, indent=2, ensure_ascii=False), encoding="utf-8")
        return pattern
    except Exception as e:
        print(f"  LLM预测失败: {e}")
        return None


def get_default_on_params(effector):
    """获取默认ON参数"""
    defaults = {
        'Compressor': {'Threshold': 0.2, 'Ratio': 2.0, 'Attack': 0.01, 'Release': 0.1, 'Makeup': 1.0, 'Mix': 0.6},
        'Driver': {'Distortion': 0.5, 'Volume': 0.0},
        'Screamer': {'Drive': 0.5, 'Tone': 0.5, 'Level': 0.0},
        'Delay': {'Feedback': 0.4, 'Delay': 0.3, 'Mix': 0.3},
        'Reverb': {'Size': 0.5, 'Damping': 0.5, 'Width': 0.5, 'Mix': 0.3},
        'Chorus': {'Delay': 0.2, 'Depth': 0.2, 'Frequency': 0.5, 'Width': 0.5},
        'Flanger': {'Delay': 0.0, 'Depth': 0.0, 'Feedback': 0.1, 'Frequency': 0.2, 'Width': 0.0},
        'Equaliser': {'100hz': 0.0, '200hz': 0.0, '400hz': 0.2, '800hz': 0.0, '1600hz': 0.8, '3200hz': 0.8, '6400hz': 0.0, 'Level': 0.1},
        'Phaser': {'Depth': 0.1, 'Feedback': 0.0, 'Frequency': 0.1, 'Width': 50}
    }
    return defaults.get(effector, {})


def get_default_off_params(effector):
    """获取默认OFF参数"""
    defaults = {
        'Compressor': {'Threshold': 1.0, 'Ratio': 1.0, 'Attack': 0.0, 'Release': 0.0, 'Makeup': 0.0, 'Mix': 0.0},
        'Driver': {'Distortion': '0.00', 'Volume': '-64.0'},
        'Screamer': {'Drive': '0.00', 'Tone': '0.00', 'Level': '-64.0'},
        'Delay': {'Feedback': 0.0, 'Delay': 0.0, 'Mix': 0.0},
        'Reverb': {'Size': 0.0, 'Damping': 0.0, 'Width': 0.0, 'Mix': 0.0},
        'Chorus': {'Delay': '0.00', 'Depth': '0.00', 'Frequency': '0.00', 'Width': '0.00'},
        'Flanger': {'Delay': '0.00', 'Depth': '0.00', 'Feedback': '0.00', 'Frequency': '0.00', 'Width': '0.00'},
        'Equaliser': {'100hz': 0.0, '200hz': 0.0, '400hz': 0.0, '800hz': 0.0, '1600hz': 0.0, '3200hz': 0.0, '6400hz': 0.0, 'Level': 0.0},
        'Phaser': {'Depth': '0.00', 'Feedback': '0.00', 'Frequency': '0.00', 'Width': '50'}
    }
    return defaults.get(effector, {})


def copy_params_with_onoff(reference_params, onoff_pattern):
    """根据ON/OFF模式复制参数"""
    new_params = {}

    for eff, state in onoff_pattern.items():
        on_key = f'{eff}On'
        off_key = f'{eff}Off'

        if state == 'ON':
            if on_key in reference_params:
                new_params[on_key] = reference_params[on_key]
            else:
                new_params[on_key] = get_default_on_params(eff)
        else:
            if off_key in reference_params:
                new_params[off_key] = reference_params[off_key]
            else:
                new_params[off_key] = get_default_off_params(eff)

    return new_params


def main() -> None:
    ap = argparse.ArgumentParser(description="Protocol-B: Retrieval + LLM ablations (cache-first, no network by default).")
    ap.add_argument("--dump_csv", type=str, default="", help="Optional path to write per-query metrics CSV.")
    ap.add_argument("--test_list", type=str, default="", help="Optional newline-separated SongName list for held-out queries.")
    ap.add_argument("--k", type=int, default=5, help="Top-K for TRR aggregation baselines (default: 5).")
    ap.add_argument(
        "--llm_cache_dir",
        type=str,
        default=str(Path("Experiments") / "llm_cache" / "protocolB_onoff"),
        help="LLM cache directory (JSON files, gitignored).",
    )
    ap.add_argument("--allow_network_llm", action="store_true", help="Allow live LLM calls on cache miss (disabled by default).")
    ap.add_argument("--with_no_fewshot", action="store_true", help="Also run w/o few-shot LLM variants (extra cache key).")
    ap.add_argument("--stats_out_json", type=str, default="", help="Optional stats JSON (calls objective_stats.py on dump_csv).")
    ap.add_argument("--stats_out_md", type=str, default="", help="Optional stats Markdown (calls objective_stats.py on dump_csv).")
    ap.add_argument("--stats_n_boot", type=int, default=10000, help="Bootstrap resamples for stats report.")
    ap.add_argument("--stats_n_perm", type=int, default=20000, help="Permutation samples for stats report.")
    ap.add_argument("--seed", type=int, default=42, help="RNG seed for stats report.")
    args = ap.parse_args()

    print("=" * 150)
    print("     Protocol-B: LLM-Enhanced Retrieval Ablations (N=211 by default)")
    print("=" * 150)

    # 1) Load data
    print("\n[1] 加载数据...")
    data = load_and_merge_data()

    # 2) Split held-out vs KB
    test_name_set = DEFAULT_TEST_NAME_SET
    if args.test_list:
        test_list_path = Path(args.test_list)
        if not test_list_path.exists():
            raise FileNotFoundError(f"--test_list not found: {test_list_path}")
        names = []
        for line in test_list_path.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            names.append(s)
        test_name_set = set(names)
        print(f"[Split] Loaded held-out query list from {test_list_path} (n={len(test_name_set)})")

    test_items = [d for d in data if d.get("SongName") in test_name_set]
    kb_items = [d for d in data if d.get("SongName") not in test_name_set]

    print(f"总数据: {len(data)} 样本")
    print(f"测试集: {len(test_items)} 样本")
    print(f"知识库: {len(kb_items)} 样本")

    # 3) Init retrievers + projection ranges
    print("\n[2] 初始化检索器...")
    from trr_adapter import TRRRetriever
    from rag_adapter import RAGRetriever

    trr_retriever = TRRRetriever(kb_items)
    text_retriever = RAGRetriever(kb_items)

    ranges = compute_param_ranges(kb_items)
    print(f"[Projection] Built param ranges: {len(ranges)} numeric leaves")

    evaluator = Evaluator()
    llm_cache_dir = Path(args.llm_cache_dir)

    methods = [
        "TRR",
        "TRR-TopKMean",
        "TRR-TopKWeightedMean",
        "Text-RAG",
        "TRR+LLM",
        "Text+LLM",
    ]
    if args.with_no_fewshot:
        methods += ["TRR+LLM(noFS)", "Text+LLM(noFS)"]

    results = {m: {"l2": [], "acc": [], "recall": [], "cosine": [], "module": []} for m in methods}
    per_query_rows: List[Dict[str, Any]] = []

    def record_row(
        query_idx: int,
        query_name: str,
        method: str,
        retrieved_name: str,
        l2,
        acc,
        recall,
        cosine,
        module,
        missing: int,
    ) -> None:
        per_query_rows.append(
            {
                "query_idx": int(query_idx),
                "query_name": str(query_name),
                "method": str(method),
                "retrieved_name": str(retrieved_name),
                "l2": l2,
                "acc@0.1": acc,
                "recall": recall,
                "cosine": cosine,
                "module": module,
                "missing": int(missing),
            }
        )

    def eval_and_record(method: str, pred_params: Dict[str, Any], *, retrieved_name: str, qidx: int, qname: str, gt: Dict[str, Any]) -> None:
        l2 = evaluator.compute_parameter_distance(pred_params, gt)
        acc = evaluator.compute_accuracy_tolerance(pred_params, gt, tolerance=0.1)
        rec = evaluator.compute_parameter_recall(pred_params, gt)
        cos = evaluator.compute_cosine_similarity(pred_params, gt)
        mod = evaluator.compute_module_consistency(pred_params, gt, active_threshold=0.1)

        results[method]["l2"].append(l2)
        results[method]["acc"].append(acc)
        results[method]["recall"].append(rec)
        results[method]["cosine"].append(cos)
        results[method]["module"].append(mod)
        record_row(qidx, qname, method, retrieved_name, l2, acc, rec, cos, mod, 0)

    # 4) Run queries
    print("\n" + "=" * 150)
    print("逐 query 评估 (per-query evaluation)")
    print("=" * 150)

    for idx, test_item in enumerate(test_items, 1):
        name = str(test_item.get("SongName", ""))
        gt_params = test_item.get("Parameters") or {}
        gt_style = test_item.get("Style", []) or []
        style_str = " ".join(gt_style) if gt_style else name

        print(f"\n[{idx}/{len(test_items)}] {name}")

        vectors = test_item.get("Vectors") or {}
        trr_vec = vectors.get("TRR")
        if not trr_vec:
            # No TRR vector => TRR-based methods missing for this query.
            for m in ["TRR", "TRR-TopKMean", "TRR-TopKWeightedMean", "TRR+LLM", "TRR+LLM(noFS)"]:
                if m in results:
                    record_row(idx, name, m, "", "", "", "", "", 1)
            continue

        trr_topk = trr_retriever.retrieve_top_k("ignored", query_vector=trr_vec, k=int(args.k))
        trr_topk_params: List[Dict[str, Any]] = []
        trr_topk_scores: List[float] = []
        trr_top1_name = ""
        for r in trr_topk:
            p = r.get("params")
            if isinstance(p, dict):
                trr_topk_params.append(p)
                trr_topk_scores.append(float(r.get("score", 0.0)))
                if not trr_top1_name:
                    trr_top1_name = str(r.get("song_name", ""))

        if not trr_topk_params:
            for m in ["TRR", "TRR-TopKMean", "TRR-TopKWeightedMean", "TRR+LLM", "TRR+LLM(noFS)"]:
                if m in results:
                    record_row(idx, name, m, "", "", "", "", "", 1)
        else:
            trr_ref = project_params(trr_topk_params[0], ranges)
            eval_and_record("TRR", trr_ref, retrieved_name=trr_top1_name, qidx=idx, qname=name, gt=gt_params)

            mean_params = aggregate_topk_params(trr_topk_params, weights=[1.0] * len(trr_topk_params))
            mean_params = project_params(mean_params, ranges)
            eval_and_record(
                "TRR-TopKMean",
                mean_params,
                retrieved_name=f"mean@{len(trr_topk_params)} ({trr_top1_name})",
                qidx=idx,
                qname=name,
                gt=gt_params,
            )

            w = _softmax_weights(trr_topk_scores)
            wmean_params = aggregate_topk_params(trr_topk_params, weights=w)
            wmean_params = project_params(wmean_params, ranges)
            eval_and_record(
                "TRR-TopKWeightedMean",
                wmean_params,
                retrieved_name=f"wmean@{len(trr_topk_params)} ({trr_top1_name})",
                qidx=idx,
                qname=name,
                gt=gt_params,
            )

            # LLM variants (cache-first)
            pattern = predict_onoff_with_llm_cached(
                style_str,
                name,
                cache_dir=llm_cache_dir,
                allow_network=bool(args.allow_network_llm),
                with_fewshot=True,
            )
            if pattern:
                pred = copy_params_with_onoff(trr_topk_params[0], pattern)
                pred = project_params(pred, ranges)
                eval_and_record("TRR+LLM", pred, retrieved_name=trr_top1_name, qidx=idx, qname=name, gt=gt_params)
            else:
                record_row(idx, name, "TRR+LLM", trr_top1_name, "", "", "", "", "", 1)

            if args.with_no_fewshot:
                pattern_nf = predict_onoff_with_llm_cached(
                    style_str,
                    name,
                    cache_dir=llm_cache_dir,
                    allow_network=bool(args.allow_network_llm),
                    with_fewshot=False,
                )
                if pattern_nf:
                    pred = copy_params_with_onoff(trr_topk_params[0], pattern_nf)
                    pred = project_params(pred, ranges)
                    eval_and_record("TRR+LLM(noFS)", pred, retrieved_name=trr_top1_name, qidx=idx, qname=name, gt=gt_params)
                else:
                    record_row(idx, name, "TRR+LLM(noFS)", trr_top1_name, "", "", "", "", "", 1)

        # Text retrieval (top-1) + projection
        text_results = text_retriever.retrieve_top_k(style_str, k=1)
        if text_results:
            text_item = text_results[0]
            text_ref_params = text_item.get("Parameters", text_item.get("params", {})) or {}
            text_ref = project_params(text_ref_params, ranges)
            text_top1_name = str(text_item.get("SongName", text_item.get("song_name", "")))
            eval_and_record("Text-RAG", text_ref, retrieved_name=text_top1_name, qidx=idx, qname=name, gt=gt_params)

            pattern = predict_onoff_with_llm_cached(
                style_str,
                name,
                cache_dir=llm_cache_dir,
                allow_network=bool(args.allow_network_llm),
                with_fewshot=True,
            )
            if pattern:
                pred = copy_params_with_onoff(text_ref_params, pattern)
                pred = project_params(pred, ranges)
                eval_and_record("Text+LLM", pred, retrieved_name=text_top1_name, qidx=idx, qname=name, gt=gt_params)
            else:
                record_row(idx, name, "Text+LLM", text_top1_name, "", "", "", "", "", 1)

            if args.with_no_fewshot:
                pattern_nf = predict_onoff_with_llm_cached(
                    style_str,
                    name,
                    cache_dir=llm_cache_dir,
                    allow_network=bool(args.allow_network_llm),
                    with_fewshot=False,
                )
                if pattern_nf:
                    pred = copy_params_with_onoff(text_ref_params, pattern_nf)
                    pred = project_params(pred, ranges)
                    eval_and_record("Text+LLM(noFS)", pred, retrieved_name=text_top1_name, qidx=idx, qname=name, gt=gt_params)
                else:
                    record_row(idx, name, "Text+LLM(noFS)", text_top1_name, "", "", "", "", "", 1)
        else:
            record_row(idx, name, "Text-RAG", "", "", "", "", "", 1)
            record_row(idx, name, "Text+LLM", "", "", "", "", "", 1)
            if args.with_no_fewshot:
                record_row(idx, name, "Text+LLM(noFS)", "", "", "", "", "", 1)

    # 5) Summary
    print("\n" + "=" * 180)
    print("Protocol-B Results Summary")
    print("=" * 180)
    print(f"{'Method':<22} {'L2↓':<12} {'Acc@0.1↑':<12} {'Recall↑':<12} {'Cos↑':<12} {'Module↑':<12}")
    print("-" * 180)
    for m in methods:
        ms = results[m]
        l2 = sum(ms["l2"]) / len(ms["l2"]) if ms["l2"] else float("nan")
        acc = sum(ms["acc"]) / len(ms["acc"]) if ms["acc"] else float("nan")
        rec = sum(ms["recall"]) / len(ms["recall"]) if ms["recall"] else float("nan")
        cos = sum(ms["cosine"]) / len(ms["cosine"]) if ms["cosine"] else float("nan")
        mod = sum(ms["module"]) / len(ms["module"]) if ms["module"] else float("nan")
        print(f"{m:<22} {l2:<12.4f} {acc:<12.4f} {rec:<12.4f} {cos:<12.4f} {mod:<12.4f}")
    print("-" * 180)

    # Optional: paired diff few-shot vs no-fewshot (L2 only)
    if args.with_no_fewshot and results.get("TRR+LLM") and results.get("TRR+LLM(noFS)"):
        # Build qidx -> l2 maps from CSV rows
        def l2_map(method: str) -> Dict[int, float]:
            out = {}
            for r in per_query_rows:
                if r["method"] != method:
                    continue
                if int(r.get("missing", 0) or 0):
                    continue
                out[int(r["query_idx"])] = float(r["l2"])
            return out

        a = l2_map("TRR+LLM")
        b = l2_map("TRR+LLM(noFS)")
        shared = sorted(set(a.keys()).intersection(set(b.keys())))
        if shared:
            d = np.asarray([b[q] - a[q] for q in shared], dtype=float)  # positive means noFS worse (higher L2)
            lo, hi = _bootstrap_ci_mean(d, n_boot=int(args.stats_n_boot), seed=int(args.seed), alpha=0.05)
            p = _paired_permutation_pvalue(d, n_perm=int(args.stats_n_perm), seed=int(args.seed))
            print(
                f"\n[NoFS] TRR+LLM(noFS) - TRR+LLM (L2): mean={float(d.mean()):.4f} "
                f"95% CI=[{lo:.4f}, {hi:.4f}] p={p:.3g} (n={len(shared)})"
            )

    # 6) Write per-query CSV
    if args.dump_csv:
        out_path = Path(args.dump_csv)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = [
            "query_idx",
            "query_name",
            "method",
            "retrieved_name",
            "l2",
            "acc@0.1",
            "recall",
            "cosine",
            "module",
            "missing",
        ]
        with out_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for row in per_query_rows:
                w.writerow(row)
        print(f"\n[Dump] Wrote per-query metrics to: {out_path}")

    # 7) Optional stats report (re-use objective_stats.py)
    if args.dump_csv and args.stats_out_json and args.stats_out_md:
        objective_stats_py = Path(__file__).with_name("objective_stats.py")
        cmd = [
            sys.executable,
            str(objective_stats_py),
            "--csv",
            str(Path(args.dump_csv)),
            "--out_json",
            str(Path(args.stats_out_json)),
            "--out_md",
            str(Path(args.stats_out_md)),
            "--n_boot",
            str(int(args.stats_n_boot)),
            "--n_perm",
            str(int(args.stats_n_perm)),
            "--seed",
            str(int(args.seed)),
        ]
        print(f"\n[Stats] Running: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)

    print("\n" + "=" * 180)
    print("EXPERIMENT COMPLETE")
    print("=" * 180)


if __name__ == "__main__":
    main()
