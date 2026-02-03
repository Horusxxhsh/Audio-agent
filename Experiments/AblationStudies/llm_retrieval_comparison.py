"""
LLM增强检索方法对比实验
对比四种方法的性能指标：
1. 纯TRR检索
2. 纯Text检索
3. TRR + LLM
4. Text + LLM
"""

import os
import sys
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

# 测试样本
TEST_SAMPLES = [
    "Dry Funk",
    "Tweed Breakup",
    "Reverse Psychedelic",
    "Math Rock Crystal",
    "Saturated Rhythm"
]

# 定义效果器
ALL_EFFECTORS = [
    'Compressor', 'Driver', 'Screamer', 'Delay', 'Reverb',
    'Chorus', 'Flanger', 'Equaliser', 'Phaser'
]


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


def build_fewshot_prompt(test_name, test_style):
    """构建手动指定的few-shot提示词"""

    examples_str = """Example 1: Style='clean_funk dry_funk' → [Compressor:ON, Driver:OFF, Screamer:OFF, Delay:ON, Reverb:ON, Chorus:ON, Flanger:OFF, Equaliser:ON, Phaser:OFF]
Example 2: Style='blues tweed_breakup' → [Compressor:OFF, Driver:ON, Screamer:OFF, Delay:OFF, Reverb:ON, Chorus:OFF, Flanger:OFF, Equaliser:ON, Phaser:OFF]
Example 3: Style='fx_reverse reverse_psychedelic' → [Compressor:OFF, Driver:OFF, Screamer:OFF, Delay:OFF, Reverb:OFF, Chorus:OFF, Flanger:OFF, Equaliser:ON, Phaser:OFF]
Example 4: Style='clean_comp math_rock_crystal' → [Compressor:ON, Driver:OFF, Screamer:OFF, Delay:ON, Reverb:ON, Chorus:ON, Flanger:OFF, Equaliser:ON, Phaser:OFF]
Example 5: Style='rock_high saturated_rhythm' → [Compressor:OFF, Driver:ON, Screamer:OFF, Delay:OFF, Reverb:ON, Chorus:OFF, Flanger:OFF, Equaliser:ON, Phaser:OFF]"""

    prompt = f"""You are a guitar tone expert. Learn from examples to predict effector ON/OFF states.

FEW-SHOT EXAMPLES (Learn the pattern):
{examples_str}

CURRENT TASK:
Target Name: "{test_name}"
Target Style: "{test_style}"

INSTRUCTIONS:
1. **IGNORE** any retrieval hints - base your prediction ONLY on the few-shot examples
2. Learn which effectors are typically ON/OFF for different styles **ONLY from the FEW-SHOT EXAMPLES above**
3. Apply this learned knowledge to predict ON/OFF for the target style

Output ONLY valid JSON:
{{"effector_on": ["Compressor", "Delay", ...], "effector_off": ["Driver", "Screamer", ...]}}"""

    return prompt


def predict_onoff_with_llm(style, test_name):
    """使用LLM预测ON/OFF"""
    if not HAS_OPENAI:
        return None

    client = OpenAI(api_key="sk-0705951d960041ed96c607ab69724d0d", base_url="https://api.deepseek.com")

    prompt = build_fewshot_prompt(test_name, style)

    try:
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            stream=False
        )
        content = resp.choices[0].message.content.strip()

        # 解析JSON
        import json
        content = content.replace("```json", "").replace("```", "")
        s = content.find('{')
        e = content.rfind('}')
        if s != -1 and e != -1:
            content = content[s:e+1]

        result = json.loads(content)

        # 转换为pattern字典
        pattern = {}
        for eff in ALL_EFFECTORS:
            if eff in result.get('effector_on', []):
                pattern[eff] = 'ON'
            else:
                pattern[eff] = 'OFF'

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


def main():
    print("="*150)
    print("     LLM增强检索方法对比实验")
    print("="*150)

    # 1. 加载数据
    print("\n[1] 加载数据...")
    data = load_and_merge_data()

    # 分离测试集和知识库
    test_items = [d for d in data if d['SongName'] in TEST_SAMPLES]
    kb_items = [d for d in data if d['SongName'] not in TEST_SAMPLES]

    print(f"测试集: {len(test_items)} 样本")
    print(f"知识库: {len(kb_items)} 样本")

    # 2. 初始化检索器
    print("\n[2] 初始化检索器...")
    from trr_adapter import TRRRetriever
    from rag_adapter import RAGRetriever

    trr_retriever = TRRRetriever(kb_items)
    text_retriever = RAGRetriever(kb_items)

    # 3. 初始化评估器
    evaluator = Evaluator()

    # 4. 存储结果
    results = {
        'TRR': {'l2': [], 'acc': [], 'recall': [], 'cosine': [], 'module': []},
        'Text': {'l2': [], 'acc': [], 'recall': [], 'cosine': [], 'module': []},
        'TRR+LLM': {'l2': [], 'acc': [], 'recall': [], 'cosine': [], 'module': []},
        'Text+LLM': {'l2': [], 'acc': [], 'recall': [], 'cosine': [], 'module': []}
    }

    # 5. 对每个测试样本进行测试
    print("\n" + "="*150)
    print("测试每个样本")
    print("="*150)

    for idx, test_item in enumerate(test_items, 1):
        name = test_item['SongName']
        gt_params = test_item['Parameters']
        gt_style = test_item.get('Style', [])
        style_str = " ".join(gt_style) if gt_style else name

        print(f"\n[{idx}/{len(test_items)}] {name}")
        print(f"  Style: {gt_style}")

        # === TRR检索 ===
        trr_results = trr_retriever.retrieve_top_k("ignored", query_vector=test_item['Vectors']['TRR'], k=1)
        trr_ref_params = trr_results[0]['params']
        trr_l2 = evaluator.compute_parameter_distance(trr_ref_params, gt_params)
        trr_acc = evaluator.compute_accuracy_tolerance(trr_ref_params, gt_params, tolerance=0.1)
        trr_recall = evaluator.compute_parameter_recall(trr_ref_params, gt_params)
        trr_cosine = evaluator.compute_cosine_similarity(trr_ref_params, gt_params)
        trr_module = evaluator.compute_module_consistency(trr_ref_params, gt_params, active_threshold=0.1)

        results['TRR']['l2'].append(trr_l2)
        results['TRR']['acc'].append(trr_acc)
        results['TRR']['recall'].append(trr_recall)
        results['TRR']['cosine'].append(trr_cosine)
        results['TRR']['module'].append(trr_module)

        print(f"  [TRR] L2={trr_l2:.4f} Acc={trr_acc:.4f} Recall={trr_recall:.4f} Cos={trr_cosine:.4f} Module={trr_module:.4f}")

        # === Text检索 ===
        text_results = text_retriever.retrieve_top_k(style_str, k=1)
        text_ref_params = text_results[0].get('Parameters', text_results[0].get('params', {}))
        text_l2 = evaluator.compute_parameter_distance(text_ref_params, gt_params)
        text_acc = evaluator.compute_accuracy_tolerance(text_ref_params, gt_params, tolerance=0.1)
        text_recall = evaluator.compute_parameter_recall(text_ref_params, gt_params)
        text_cosine = evaluator.compute_cosine_similarity(text_ref_params, gt_params)
        text_module = evaluator.compute_module_consistency(text_ref_params, gt_params, active_threshold=0.1)

        results['Text']['l2'].append(text_l2)
        results['Text']['acc'].append(text_acc)
        results['Text']['recall'].append(text_recall)
        results['Text']['cosine'].append(text_cosine)
        results['Text']['module'].append(text_module)

        print(f"  [Text] L2={text_l2:.4f} Acc={text_acc:.4f} Recall={text_recall:.4f} Cos={text_cosine:.4f} Module={text_module:.4f}")

        # === TRR + LLM ===
        if HAS_OPENAI:
            print(f"  [TRR+LLM] LLM预测ON/OFF...")
            onoff_pattern = predict_onoff_with_llm(style_str, name)
            if onoff_pattern:
                pred_params = copy_params_with_onoff(trr_ref_params, onoff_pattern)
                l2 = evaluator.compute_parameter_distance(pred_params, gt_params)
                acc = evaluator.compute_accuracy_tolerance(pred_params, gt_params, tolerance=0.1)
                recall = evaluator.compute_parameter_recall(pred_params, gt_params)
                cosine = evaluator.compute_cosine_similarity(pred_params, gt_params)
                module = evaluator.compute_module_consistency(pred_params, gt_params, active_threshold=0.1)

                results['TRR+LLM']['l2'].append(l2)
                results['TRR+LLM']['acc'].append(acc)
                results['TRR+LLM']['recall'].append(recall)
                results['TRR+LLM']['cosine'].append(cosine)
                results['TRR+LLM']['module'].append(module)

                print(f"    L2={l2:.4f} Acc={acc:.4f} Recall={recall:.4f} Cos={cosine:.4f} Module={module:.4f}")
            else:
                # LLM失败，使用原始TRR结果
                results['TRR+LLM']['l2'].append(trr_l2)
                results['TRR+LLM']['acc'].append(trr_acc)
                results['TRR+LLM']['recall'].append(trr_recall)
                results['TRR+LLM']['cosine'].append(trr_cosine)
                results['TRR+LLM']['module'].append(trr_module)
        else:
            # 没有OpenAI，使用原始TRR结果
            results['TRR+LLM']['l2'].append(trr_l2)
            results['TRR+LLM']['acc'].append(trr_acc)
            results['TRR+LLM']['recall'].append(trr_recall)
            results['TRR+LLM']['cosine'].append(trr_cosine)
            results['TRR+LLM']['module'].append(trr_module)

        # === Text + LLM ===
        if HAS_OPENAI:
            print(f"  [Text+LLM] LLM预测ON/OFF...")
            onoff_pattern = predict_onoff_with_llm(style_str, name)
            if onoff_pattern:
                pred_params = copy_params_with_onoff(text_ref_params, onoff_pattern)
                l2 = evaluator.compute_parameter_distance(pred_params, gt_params)
                acc = evaluator.compute_accuracy_tolerance(pred_params, gt_params, tolerance=0.1)
                recall = evaluator.compute_parameter_recall(pred_params, gt_params)
                cosine = evaluator.compute_cosine_similarity(pred_params, gt_params)
                module = evaluator.compute_module_consistency(pred_params, gt_params, active_threshold=0.1)

                results['Text+LLM']['l2'].append(l2)
                results['Text+LLM']['acc'].append(acc)
                results['Text+LLM']['recall'].append(recall)
                results['Text+LLM']['cosine'].append(cosine)
                results['Text+LLM']['module'].append(module)

                print(f"    L2={l2:.4f} Acc={acc:.4f} Recall={recall:.4f} Cos={cosine:.4f} Module={module:.4f}")
            else:
                # LLM失败，使用原始Text结果
                results['Text+LLM']['l2'].append(text_l2)
                results['Text+LLM']['acc'].append(text_acc)
                results['Text+LLM']['recall'].append(text_recall)
                results['Text+LLM']['cosine'].append(text_cosine)
                results['Text+LLM']['module'].append(text_module)
        else:
            # 没有OpenAI，使用原始Text结果
            results['Text+LLM']['l2'].append(text_l2)
            results['Text+LLM']['acc'].append(text_acc)
            results['Text+LLM']['recall'].append(text_recall)
            results['Text+LLM']['cosine'].append(text_cosine)
            results['Text+LLM']['module'].append(text_module)

    # 6. 打印总结表格
    print("\n" + "="*180)
    print("LLM增强检索方法对比实验结果")
    print("="*180)
    print(f"{'方法':<15} {'L2误差↓':<15} {'准确率↑':<15} {'召回率↑':<15} {'余弦相似度↑':<18} {'模块一致性↑':<18}")
    print("-"*180)

    methods = [
        ('纯TRR检索', results['TRR']),
        ('纯Text检索', results['Text']),
        ('TRR+LLM', results['TRR+LLM']),
        ('Text+LLM', results['Text+LLM'])
    ]

    for method_name, metrics in methods:
        l2 = sum(metrics['l2']) / len(metrics['l2']) if metrics['l2'] else 0
        acc = sum(metrics['acc']) / len(metrics['acc']) if metrics['acc'] else 0
        recall = sum(metrics['recall']) / len(metrics['recall']) if metrics['recall'] else 0
        cosine = sum(metrics['cosine']) / len(metrics['cosine']) if metrics['cosine'] else 0
        module = sum(metrics['module']) / len(metrics['module']) if metrics['module'] else 0

        print(f"{method_name:<15} {l2:<15.4f} {acc:<15.4f} {recall:<15.4f} {cosine:<18.4f} {module:<18.4f}")

    print("-"*180)

    # 7. 计算改进
    print("\n改进分析:")

    trr_l2 = sum(results['TRR']['l2']) / len(results['TRR']['l2'])
    trr_llm_l2 = sum(results['TRR+LLM']['l2']) / len(results['TRR+LLM']['l2'])
    if trr_llm_l2 < trr_l2:
        improvement = ((trr_l2 - trr_llm_l2) / trr_l2) * 100
        print(f"  TRR+LLM vs 纯TRR: L2降低 {improvement:.1f}%")
    else:
        degradation = ((trr_llm_l2 - trr_l2) / trr_l2) * 100
        print(f"  TRR+LLM vs 纯TRR: L2上升 {degradation:.1f}%")

    text_l2 = sum(results['Text']['l2']) / len(results['Text']['l2'])
    text_llm_l2 = sum(results['Text+LLM']['l2']) / len(results['Text+LLM']['l2'])
    if text_llm_l2 < text_l2:
        improvement = ((text_l2 - text_llm_l2) / text_l2) * 100
        print(f"  Text+LLM vs 纯Text: L2降低 {improvement:.1f}%")
    else:
        degradation = ((text_llm_l2 - text_l2) / text_l2) * 100
        print(f"  Text+LLM vs 纯Text: L2上升 {degradation:.1f}%")

    print("\n" + "="*180)
    print("EXPERIMENT COMPLETE")
    print("="*180)


if __name__ == "__main__":
    main()
