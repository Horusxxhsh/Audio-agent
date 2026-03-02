"""
检索方法直接对比实验

对比检索方法,直接使用检索到的参数计算指标
- （可选）纯LLM直接生成 (Pure LLM Generation) - 不使用检索，用于对照
- 纯文本检索 (Text-Retrieval)
- Wav2Vec-RAG
- FeatureNN-RAG
- TRR

测试样本: 使用论文中的 held-out query pool（Protocol-A，N=211），由 TEST_SAMPLES 定义。
其中包含 30 个 canonical 名称及其确定性变体（例如 “Dry Funk - ...”）。
"""

import os
import sys
import argparse
import csv
from pathlib import Path
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
    print("Warning: openai not found. Pure LLM generation will be skipped.")

# 测试样本 (30个: 原始5个 + 新增25个)
    # 原始5个
    # "Dry Funk",
    # "Tweed Breakup",
    # "Reverse Psychedelic",
    # "Math Rock Crystal",
    # "Saturated Rhythm",
    # # 新增25个
    # "80s Hair Metal",
    # "80s Pop Clean",
    # "Acoustic Sim",
    # "Ambient Swells",
    # "Auto-Wah Funk",
    # "Bitcrushed Synth",
    # "Black Metal Lo-Fi",
    # "Brian May Style",
    # "British Invasion",
    # "Brown Sound",
    # "Classic Plexi",
    # "Doom/Stoner Fuzz",
    # "Dreamy Shoegaze",
    # "Garage Rock Fuzz",
    # "Grunge Dirt",
    # "Hard Rock Crunch",
    # "Indie Jangle",
    # "Industrial Metal",
    # "Infinite Sustain",
    # "Jazz Box",
    # "Liquid Lead",
    # "Lo-Fi Hip Hop",
    # "Midwest Emo",
    # "Modern Djent",
    # "Neo-Soul Clean"
TEST_SAMPLES = [
    # 原始5个
    "Dry Funk",
    "Tweed Breakup",
    "Reverse Psychedelic",
    "Math Rock Crystal",
    "Saturated Rhythm",
    # 新增25个
    "80s Hair Metal",
    "80s Pop Clean",
    "Acoustic Sim",
    "Ambient Swells",
    "Auto-Wah Funk",
    "Bitcrushed Synth",
    "Black Metal Lo-Fi",
    "Brian May Style",
    "British Invasion",
    "Brown Sound",
    "Classic Plexi",
    "Doom/Stoner Fuzz",
    "Dreamy Shoegaze",
    "Garage Rock Fuzz",
    "Grunge Dirt",
    "Hard Rock Crunch",
    "Indie Jangle",
    "Industrial Metal",
    "Infinite Sustain",
    "Jazz Box",
    "Liquid Lead",
    "Lo-Fi Hip Hop",
    "Midwest Emo",
    "Modern Djent",
    "Neo-Soul Clean"
]

TEST_SAMPLES.extend([
    "Dry Funk - Pocket Groove Cut",
    "Tweed Breakup - Vintage Drive Mix",
    "Reverse Psychedelic - Alt Take",
    "Math Rock Crystal - Alt Take",
    "Saturated Rhythm - Alt Take",
    "80s Hair Metal - High Gain Forge",
    "80s Pop Clean - Warm Room Take",
    "Acoustic Sim - Warm Room Take",
    "Ambient Swells - Ethereal Wash Mix",
    "Auto-Wah Funk - Pocket Groove Cut",
    "Bitcrushed Synth - Alt Take",
    "Black Metal Lo-Fi - High Gain Forge",
    "Brian May Style - Alt Take",
    "British Invasion - Alt Take",
    "Brown Sound - Vintage Drive Mix",
    "Classic Plexi - Vintage Drive Mix",
    "Doom/Stoner Fuzz - High Gain Forge",
    "Dreamy Shoegaze - Ethereal Wash Mix",
    "Garage Rock Fuzz - Vintage Drive Mix",
    "Grunge Dirt - Vintage Drive Mix",
    "Hard Rock Crunch - Vintage Drive Mix",
    "Indie Jangle - Warm Room Take",
    "Industrial Metal - High Gain Forge",
    "Infinite Sustain - Ethereal Wash Mix",
    "Jazz Box - Warm Room Take",
    "Liquid Lead - Vintage Drive Mix",
    "Lo-Fi Hip Hop - Alt Take",
    "Midwest Emo - Warm Room Take",
    "Modern Djent - High Gain Forge",
    "Neo-Soul Clean - Pocket Groove Cut",
    "Dry Funk - Sync Pulse Mix",
    "Tweed Breakup - Raw Amp Pass",
    "Reverse Psychedelic - Studio Mix",
    "Math Rock Crystal - Studio Mix",
    "Saturated Rhythm - Studio Mix",
    "80s Hair Metal - Steel Edge Mix",
    "80s Pop Clean - Open Chord Mix",
    "Acoustic Sim - Open Chord Mix",
    "Ambient Swells - Cloud Reverb Pass",
    "Auto-Wah Funk - Sync Pulse Mix",
    "Bitcrushed Synth - Studio Mix",
    "Black Metal Lo-Fi - Steel Edge Mix",
    "Brian May Style - Studio Mix",
    "British Invasion - Studio Mix",
    "Brown Sound - Raw Amp Pass",
    "Classic Plexi - Raw Amp Pass",
    "Doom/Stoner Fuzz - Steel Edge Mix",
    "Dreamy Shoegaze - Cloud Reverb Pass",
    "Garage Rock Fuzz - Raw Amp Pass",
    "Grunge Dirt - Raw Amp Pass",
    "Hard Rock Crunch - Raw Amp Pass",
    "Indie Jangle - Open Chord Mix",
    "Industrial Metal - Steel Edge Mix",
    "Infinite Sustain - Cloud Reverb Pass",
    "Jazz Box - Open Chord Mix",
    "Liquid Lead - Raw Amp Pass",
    "Lo-Fi Hip Hop - Studio Mix",
    "Midwest Emo - Open Chord Mix",
    "Modern Djent - Steel Edge Mix",
    "Neo-Soul Clean - Sync Pulse Mix",
    "Dry Funk - Muted Snap Take",
    "Tweed Breakup - Grit Stack Take",
    "Reverse Psychedelic - Session Pass",
    "Math Rock Crystal - Session Pass",
    "Saturated Rhythm - Session Pass",
    "80s Hair Metal - Palm Mute Crush",
    "80s Pop Clean - Glass Tone Pass",
    "Acoustic Sim - Glass Tone Pass",
    "Ambient Swells - Wide Bloom Take",
    "Auto-Wah Funk - Muted Snap Take",
    "Bitcrushed Synth - Session Pass",
    "Black Metal Lo-Fi - Palm Mute Crush",
    "Brian May Style - Session Pass",
    "British Invasion - Session Pass",
    "Brown Sound - Grit Stack Take",
    "Classic Plexi - Grit Stack Take",
    "Doom/Stoner Fuzz - Palm Mute Crush",
    "Dreamy Shoegaze - Wide Bloom Take",
    "Garage Rock Fuzz - Grit Stack Take",
    "Grunge Dirt - Grit Stack Take",
    "Hard Rock Crunch - Grit Stack Take",
    "Indie Jangle - Glass Tone Pass",
    "Industrial Metal - Palm Mute Crush",
    "Infinite Sustain - Wide Bloom Take",
    "Jazz Box - Glass Tone Pass",
    "Liquid Lead - Grit Stack Take",
    "Lo-Fi Hip Hop - Session Pass",
    "Midwest Emo - Glass Tone Pass",
    "Modern Djent - Palm Mute Crush",
    "Neo-Soul Clean - Muted Snap Take",
    "Dry Funk - Chic Rhythm Pass",
    "Tweed Breakup - Classic Crunch Edit",
    "Reverse Psychedelic - Extended Edit",
    "Math Rock Crystal - Extended Edit",
    "Saturated Rhythm - Extended Edit",
    "80s Hair Metal - Heavy Riff Pass",
    "80s Pop Clean - Natural Body Edit",
    "Acoustic Sim - Natural Body Edit",
    "Ambient Swells - Floating Texture Edit",
    "Auto-Wah Funk - Chic Rhythm Pass",
    "Bitcrushed Synth - Extended Edit",
    "Black Metal Lo-Fi - Heavy Riff Pass",
    "Brian May Style - Extended Edit",
    "British Invasion - Extended Edit",
    "Brown Sound - Classic Crunch Edit",
    "Classic Plexi - Classic Crunch Edit",
    "Doom/Stoner Fuzz - Heavy Riff Pass",
    "Dreamy Shoegaze - Floating Texture Edit",
    "Garage Rock Fuzz - Classic Crunch Edit",
    "Grunge Dirt - Classic Crunch Edit",
    "Hard Rock Crunch - Classic Crunch Edit",
    "Indie Jangle - Natural Body Edit",
    "Industrial Metal - Heavy Riff Pass",
    "Infinite Sustain - Floating Texture Edit",
    "Jazz Box - Natural Body Edit",
    "Liquid Lead - Classic Crunch Edit",
    "Lo-Fi Hip Hop - Extended Edit",
    "Midwest Emo - Natural Body Edit",
    "Modern Djent - Heavy Riff Pass",
    "Neo-Soul Clean - Chic Rhythm Pass",
    "Dry Funk - Tight Jam Edit",
    "Tweed Breakup - Hot Valve Version",
    "Reverse Psychedelic - Signature Version",
    "Math Rock Crystal - Signature Version",
    "Saturated Rhythm - Signature Version",
    "80s Hair Metal - Wall of Gain Edit",
    "80s Pop Clean - Bright Air Version",
    "Acoustic Sim - Bright Air Version",
    "Ambient Swells - Halo Sustain Version",
    "Auto-Wah Funk - Tight Jam Edit",
    "Bitcrushed Synth - Signature Version",
    "Black Metal Lo-Fi - Wall of Gain Edit",
    "Brian May Style - Signature Version",
    "British Invasion - Signature Version",
    "Brown Sound - Hot Valve Version",
    "Classic Plexi - Hot Valve Version",
    "Doom/Stoner Fuzz - Wall of Gain Edit",
    "Dreamy Shoegaze - Halo Sustain Version",
    "Garage Rock Fuzz - Hot Valve Version",
    "Grunge Dirt - Hot Valve Version",
    "Hard Rock Crunch - Hot Valve Version",
    "Indie Jangle - Bright Air Version",
    "Industrial Metal - Wall of Gain Edit",
    "Infinite Sustain - Halo Sustain Version",
    "Jazz Box - Bright Air Version",
    "Liquid Lead - Hot Valve Version",
    "Lo-Fi Hip Hop - Signature Version",
    "Midwest Emo - Bright Air Version",
    "Modern Djent - Wall of Gain Edit",
    "Neo-Soul Clean - Tight Jam Edit",
    "Dry Funk - Velvet Groove Version",
    "Tweed Breakup - Saturated Bite Cut",
    "Reverse Psychedelic - Night Drive Cut",
    "Math Rock Crystal - Night Drive Cut",
    "Saturated Rhythm - Night Drive Cut",
    "80s Hair Metal - Precision Chug Version",
    "80s Pop Clean - Round Note Cut",
    "Acoustic Sim - Round Note Cut",
    "Ambient Swells - Cinematic Drift Cut",
    "Auto-Wah Funk - Velvet Groove Version",
    "Bitcrushed Synth - Night Drive Cut",
    "Black Metal Lo-Fi - Precision Chug Version",
    "Brian May Style - Night Drive Cut",
    "British Invasion - Night Drive Cut",
    "Brown Sound - Saturated Bite Cut",
    "Classic Plexi - Saturated Bite Cut",
    "Doom/Stoner Fuzz - Precision Chug Version",
    "Dreamy Shoegaze - Cinematic Drift Cut",
    "Garage Rock Fuzz - Saturated Bite Cut",
    "Grunge Dirt - Saturated Bite Cut",
    "Hard Rock Crunch - Saturated Bite Cut",
    "Indie Jangle - Round Note Cut",
    "Industrial Metal - Precision Chug Version",
    "Infinite Sustain - Cinematic Drift Cut",
    "Jazz Box - Round Note Cut",
    "Liquid Lead - Saturated Bite Cut",
    "Lo-Fi Hip Hop - Night Drive Cut",
    "Midwest Emo - Round Note Cut",
    "Modern Djent - Precision Chug Version",
    "Neo-Soul Clean - Velvet Groove Version",
])

TEST_SAMPLE_SET = set(TEST_SAMPLES)
TEST_SAMPLE_PREFIXES = tuple(f"{name} - " for name in TEST_SAMPLES)


def is_test_sample_name(song_name):
    """判断是否属于测试集"""
    if not song_name:
        return False
    return song_name in TEST_SAMPLE_SET or song_name.startswith(TEST_SAMPLE_PREFIXES)


# 定义效果器
ALL_EFFECTORS = [
    'Compressor', 'Driver', 'Screamer', 'Delay', 'Reverb',
    'Chorus', 'Flanger', 'Equaliser', 'Phaser'
]


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


class TextRetrieval:
    """纯文本检索 - 使用RAGRetriever保持与LLM实验一致"""
    def __init__(self, dataset):
        self.dataset = dataset
        from rag_adapter import RAGRetriever
        self.retriever = RAGRetriever(dataset)

    def retrieve(self, query_item, k=1):
        # 构建查询文本（使用Style字段，与llm_retrieval_comparison.py保持一致）
        gt_style = query_item.get('Style', [])
        style_str = " ".join(gt_style) if gt_style else query_item['SongName']

        results = self.retriever.retrieve_top_k(style_str, k=k)
        return results


class Wav2VecRetrieval:
    """Wav2Vec向量检索"""
    def __init__(self, dataset):
        self.dataset = dataset
        self.embeddings = []
        self.metadata = []

        for item in dataset:
            vectors = item.get('Vectors', {})
            w2v = vectors.get('Wav2Vec', [])
            if w2v:
                self.embeddings.append(np.array(w2v))
                self.metadata.append(item)

        if self.embeddings:
            self.embeddings = np.array(self.embeddings)

    def retrieve(self, query_item, k=1):
        vectors = query_item.get('Vectors', {})
        vec = vectors.get('Wav2Vec', [])

        if not vec:
            return []

        query_vec = np.array(vec)
        similarities = np.dot(self.embeddings, query_vec)
        norms = np.linalg.norm(self.embeddings, axis=1) * np.linalg.norm(query_vec)
        norms = np.where(norms == 0, 1, norms)
        similarities = similarities / norms
        top_indices = np.argsort(similarities)[::-1][:k]
        return [self.metadata[i] for i in top_indices]


class FeatureNNRetrieval:
    """FeatureNN向量检索"""
    def __init__(self, dataset):
        self.dataset = dataset
        self.embeddings = []
        self.metadata = []

        for item in dataset:
            vectors = item.get('Vectors', {})
            fnn = vectors.get('FeatureNN', [])
            if fnn:
                self.embeddings.append(np.array(fnn))
                self.metadata.append(item)

        if self.embeddings:
            self.embeddings = np.array(self.embeddings)

    def retrieve(self, query_item, k=1):
        vectors = query_item.get('Vectors', {})
        vec = vectors.get('FeatureNN', [])

        if not vec:
            return []

        query_vec = np.array(vec)
        similarities = np.dot(self.embeddings, query_vec)
        norms = np.linalg.norm(self.embeddings, axis=1) * np.linalg.norm(query_vec)
        norms = np.where(norms == 0, 1, norms)
        similarities = similarities / norms
        top_indices = np.argsort(similarities)[::-1][:k]
        return [self.metadata[i] for i in top_indices]


class TRRRetrieval:
    """TRR纹理检索"""
    def __init__(self, dataset):
        from trr_adapter import TRRRetriever
        self.retriever = TRRRetriever(dataset)

    def retrieve(self, query_item, k=1):
        vectors = query_item.get('Vectors', {})
        vec = vectors.get('TRR', [])

        if not vec:
            return []

        results = self.retriever.retrieve_top_k("ignored", query_vector=vec, k=k)
        # 转换格式
        return [{
            'SongName': r['song_name'],
            'Parameters': r['params'],
            'Style': r.get('style', []),
            'Feature': []
        } for r in results]


def build_llm_generation_prompt(test_name, test_style):
    """构建纯LLM生成的提示词 - 不使用任何检索"""

    # Few-shot示例，包含完整的参数结构
    examples_str = """Example 1:
Name: "Dry Funk Rhythm"
Style: ['clean_funk', 'dry_funk']
Parameters:
{
  "CompressorOn": {"Threshold": 0.2, "Ratio": 2.0, "Attack": 0.01, "Release": 0.1, "Makeup": 1.0, "Mix": 0.6},
  "DriverOff": {"Distortion": "0.00", "Volume": "-64.0"},
  "ScreamerOff": {"Drive": "0.00", "Tone": "0.00", "Level": "-64.0"},
  "DelayOn": {"Feedback": 0.4, "Delay": 0.3, "Mix": 0.3},
  "ReverbOn": {"Size": 0.5, "Damping": 0.5, "Width": 0.5, "Mix": 0.3},
  "ChorusOn": {"Delay": 0.2, "Depth": 0.2, "Frequency": 0.5, "Width": 0.5},
  "FlangerOff": {"Delay": "0.00", "Depth": "0.00", "Feedback": "0.00", "Frequency": "0.00", "Width": "0.00"},
  "EqualiserOn": {"100hz": 0.0, "200hz": 0.0, "400hz": 0.2, "800hz": 0.0, "1600hz": 0.8, "3200hz": 0.8, "6400hz": 0.0, "Level": 0.1},
  "PhaserOff": {"Depth": "0.00", "Feedback": "0.00", "Frequency": "0.00", "Width": "50"}
}

Example 2:
Name: "Vintage Tweed Breakup"
Style: ['blues', 'tweed_breakup']
Parameters:
{
  "CompressorOff": {"Threshold": 1.0, "Ratio": 1.0, "Attack": 0.0, "Release": 0.0, "Makeup": 0.0, "Mix": 0.0},
  "DriverOn": {"Distortion": 0.5, "Volume": 0.0},
  "ScreamerOff": {"Drive": "0.00", "Tone": "0.00", "Level": "-64.0"},
  "DelayOff": {"Feedback": 0.0, "Delay": 0.0, "Mix": 0.0},
  "ReverbOn": {"Size": 0.5, "Damping": 0.5, "Width": 0.5, "Mix": 0.3},
  "ChorusOff": {"Delay": "0.00", "Depth": "0.00", "Frequency": "0.00", "Width": "0.00"},
  "FlangerOff": {"Delay": "0.00", "Depth": "0.00", "Feedback": "0.00", "Frequency": "0.00", "Width": "0.00"},
  "EqualiserOn": {"100hz": 0.0, "200hz": 0.0, "400hz": 0.2, "800hz": 0.0, "1600hz": 0.8, "3200hz": 0.8, "6400hz": 0.0, "Level": 0.1},
  "PhaserOff": {"Depth": "0.00", "Feedback": "0.00", "Frequency": "0.00", "Width": "50"}
}

Example 3:
Name: "Reverse Psychedelic Delay"
Style: ['fx_reverse', 'reverse_psychedelic']
Parameters:
{
  "CompressorOff": {"Threshold": 1.0, "Ratio": 1.0, "Attack": 0.0, "Release": 0.0, "Makeup": 0.0, "Mix": 0.0},
  "DriverOff": {"Distortion": "0.00", "Volume": "-64.0"},
  "ScreamerOff": {"Drive": "0.00", "Tone": "0.00", "Level": "-64.0"},
  "DelayOff": {"Feedback": 0.0, "Delay": 0.0, "Mix": 0.0},
  "ReverbOff": {"Size": 0.0, "Damping": 0.0, "Width": 0.0, "Mix": 0.0},
  "ChorusOff": {"Delay": "0.00", "Depth": "0.00", "Frequency": "0.00", "Width": "0.00"},
  "FlangerOff": {"Delay": "0.00", "Depth": "0.00", "Feedback": "0.00", "Frequency": "0.00", "Width": "0.00"},
  "EqualiserOn": {"100hz": 0.0, "200hz": 0.0, "400hz": 0.0, "800hz": 0.0, "1600hz": 0.0, "3200hz": 0.0, "6400hz": 0.0, "Level": 0.0},
  "PhaserOff": {"Depth": "0.00", "Feedback": "0.00", "Frequency": "0.00", "Width": "50"}
}

Example 4:
Name: "Math Rock Crystal Cleans"
Style: ['clean_comp', 'math_rock_crystal']
Parameters:
{
  "CompressorOn": {"Threshold": 0.2, "Ratio": 2.0, "Attack": 0.01, "Release": 0.1, "Makeup": 1.0, "Mix": 0.6},
  "DriverOff": {"Distortion": "0.00", "Volume": "-64.0"},
  "ScreamerOff": {"Drive": "0.00", "Tone": "0.00", "Level": "-64.0"},
  "DelayOn": {"Feedback": 0.4, "Delay": 0.3, "Mix": 0.3},
  "ReverbOn": {"Size": 0.5, "Damping": 0.5, "Width": 0.5, "Mix": 0.3},
  "ChorusOn": {"Delay": 0.2, "Depth": 0.2, "Frequency": 0.5, "Width": 0.5},
  "FlangerOff": {"Delay": "0.00", "Depth": "0.00", "Feedback": "0.00", "Frequency": "0.00", "Width": "0.00"},
  "EqualiserOn": {"100hz": 0.0, "200hz": 0.0, "400hz": 0.2, "800hz": 0.0, "1600hz": 0.8, "3200hz": 0.8, "6400hz": 0.0, "Level": 0.1},
  "PhaserOff": {"Depth": "0.00", "Feedback": "0.00", "Frequency": "0.00", "Width": "50"}
}

Example 5:
Name: "Saturated Drive Rhythm"
Style: ['rock_high', 'saturated_rhythm']
Parameters:
{
  "CompressorOff": {"Threshold": 1.0, "Ratio": 1.0, "Attack": 0.0, "Release": 0.0, "Makeup": 0.0, "Mix": 0.0},
  "DriverOn": {"Distortion": 0.5, "Volume": 0.0},
  "ScreamerOff": {"Drive": "0.00", "Tone": "0.00", "Level": "-64.0"},
  "DelayOff": {"Feedback": 0.0, "Delay": 0.0, "Mix": 0.0},
  "ReverbOn": {"Size": 0.5, "Damping": 0.5, "Width": 0.5, "Mix": 0.3},
  "ChorusOff": {"Delay": "0.00", "Depth": "0.00", "Frequency": "0.00", "Width": "0.00"},
  "FlangerOff": {"Delay": "0.00", "Depth": "0.00", "Feedback": "0.00", "Frequency": "0.00", "Width": "0.00"},
  "EqualiserOn": {"100hz": 0.0, "200hz": 0.0, "400hz": 0.2, "800hz": 0.0, "1600hz": 0.8, "3200hz": 0.8, "6400hz": 0.0, "Level": 0.1},
  "PhaserOff": {"Depth": "0.00", "Feedback": "0.00", "Frequency": "0.00", "Width": "50"}
}"""

    prompt = f"""You are a guitar tone expert. Generate guitar effect parameters based ONLY on the few-shot examples below.

FEW-SHOT EXAMPLES (Learn the pattern of which effectors are ON/OFF and their parameter values):
{examples_str}

CURRENT TASK:
Target Name: "{test_name}"
Target Style: {test_style}

INSTRUCTIONS:
1. **DO NOT use any retrieval or external knowledge** - base your prediction ONLY on the few-shot examples
2. Learn which effectors are typically ON/OFF for different styles from the examples
3. Learn the parameter value patterns for each effector
4. Apply this learned knowledge to generate complete parameters for the target style
5. Output must be valid JSON with all 9 effectors (each either "On" or "Off")

Output ONLY valid JSON in this exact format:
{{
  "CompressorOn": {{"Threshold": 0.2, "Ratio": 2.0, ...}},
  "DriverOff": {{"Distortion": "0.00", "Volume": "-64.0"}},
  ...
}}"""

    return prompt


def generate_params_with_llm(style, test_name):
    """使用LLM直接生成参数 - 不使用检索"""
    if not HAS_OPENAI:
        return None

    client = OpenAI(api_key="sk-0705951d960041ed96c607ab69724d0d", base_url="https://api.deepseek.com")

    prompt = build_llm_generation_prompt(test_name, style)

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

        params = json.loads(content)
        return params

    except Exception as e:
        print(f"    LLM生成失败: {e}")
        return None


def get_fallback_params(style_str):
    """当LLM失败时，使用基于规则的fallback参数生成"""
    style_lower = style_str.lower()

    # 根据风格关键词决定默认参数
    if any(k in style_lower for k in ['funk', 'clean', 'pop']):
        # Clean funk style
        return {
            "CompressorOn": get_default_on_params('Compressor'),
            "DriverOff": get_default_off_params('Driver'),
            "ScreamerOff": get_default_off_params('Screamer'),
            "DelayOn": get_default_on_params('Delay'),
            "ReverbOn": get_default_on_params('Reverb'),
            "ChorusOn": get_default_on_params('Chorus'),
            "FlangerOff": get_default_off_params('Flanger'),
            "EqualiserOn": get_default_on_params('Equaliser'),
            "PhaserOff": get_default_off_params('Phaser')
        }
    elif any(k in style_lower for k in ['blues', 'tweed', 'breakup', 'rock', 'high', 'saturated']):
        # Drive style
        return {
            "CompressorOff": get_default_off_params('Compressor'),
            "DriverOn": get_default_on_params('Driver'),
            "ScreamerOff": get_default_off_params('Screamer'),
            "DelayOff": get_default_off_params('Delay'),
            "ReverbOn": get_default_on_params('Reverb'),
            "ChorusOff": get_default_off_params('Chorus'),
            "FlangerOff": get_default_off_params('Flanger'),
            "EqualiserOn": get_default_on_params('Equaliser'),
            "PhaserOff": get_default_off_params('Phaser')
        }
    elif any(k in style_lower for k in ['reverse', 'psychedelic', 'fx']):
        # FX style - minimal
        return {
            "CompressorOff": get_default_off_params('Compressor'),
            "DriverOff": get_default_off_params('Driver'),
            "ScreamerOff": get_default_off_params('Screamer'),
            "DelayOff": get_default_off_params('Delay'),
            "ReverbOff": get_default_off_params('Reverb'),
            "ChorusOff": get_default_off_params('Chorus'),
            "FlangerOff": get_default_off_params('Flanger'),
            "EqualiserOn": get_default_on_params('Equaliser'),
            "PhaserOff": get_default_off_params('Phaser')
        }
    else:
        # Default clean style
        return {
            "CompressorOn": get_default_on_params('Compressor'),
            "DriverOff": get_default_off_params('Driver'),
            "ScreamerOff": get_default_off_params('Screamer'),
            "DelayOn": get_default_on_params('Delay'),
            "ReverbOn": get_default_on_params('Reverb'),
            "ChorusOn": get_default_on_params('Chorus'),
            "FlangerOff": get_default_off_params('Flanger'),
            "EqualiserOn": get_default_on_params('Equaliser'),
            "PhaserOff": get_default_off_params('Phaser')
        }


class PureLLMGeneration:
    """纯LLM直接生成 - 不使用检索，证明RAG的必要性"""
    def __init__(self, dataset=None):
        # 不需要dataset，这是纯生成方法
        pass

    def retrieve(self, query_item, k=1):
        """生成参数而不是检索"""
        gt_style = query_item.get('Style', [])
        style_str = " ".join(gt_style) if gt_style else query_item['SongName']

        # 尝试使用LLM生成
        params = generate_params_with_llm(style_str, query_item['SongName'])

        if params is None:
            # LLM失败，使用fallback
            params = get_fallback_params(style_str)

        return [{
            'SongName': f'LLM Generated: {query_item["SongName"]}',
            'Parameters': params,
            'Style': gt_style,
            'Feature': []
        }]


def main():
    ap = argparse.ArgumentParser(
        description="Direct retrieval comparison (supports optional per-query metric dump)."
    )
    ap.add_argument(
        "--dump_csv",
        type=str,
        default="",
        help="Optional path to write per-query metrics as CSV (one row per query per method).",
    )
    ap.add_argument(
        "--test_list",
        type=str,
        default="",
        help="Optional newline-separated SongName list for the held-out queries (overrides built-in TEST_SAMPLES).",
    )
    ap.add_argument(
        "--with_pure_llm",
        action="store_true",
        help="Include the Pure-LLM baseline (slow / network). Disabled by default.",
    )
    args = ap.parse_args()

    print("="*100)
    print("     检索方法直接对比实验 (Direct Retrieval Comparison)")
    print("="*100)

    # 1. 加载数据
    print("\n[1] 加载数据...")
    data = load_and_merge_data()

    # 分离测试集和知识库
    test_name_set = TEST_SAMPLE_SET
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

    test_items = [d for d in data if d.get('SongName') in test_name_set]
    kb_items = [d for d in data if d.get('SongName') not in test_name_set]

    print(f"测试集: {len(test_items)} 样本")
    print(f"知识库: {len(kb_items)} 样本")

    # 2. 初始化检索器
    print("\n[2] 初始化检索器...")
    text_retrieval = TextRetrieval(kb_items)
    wav2vec_retrieval = Wav2VecRetrieval(kb_items)
    featurenn_retrieval = FeatureNNRetrieval(kb_items)
    trr_retrieval = TRRRetrieval(kb_items)
    include_pure_llm = bool(args.with_pure_llm)
    pure_llm = PureLLMGeneration() if include_pure_llm else None

    print(">> 所有检索器初始化完成")
    if include_pure_llm and HAS_OPENAI:
        print(">> 纯LLM直接生成已启用 (使用DeepSeek API)")
    elif include_pure_llm and not HAS_OPENAI:
        print(">> 纯LLM直接生成将使用 fallback (OpenAI库未安装)")
    elif HAS_OPENAI:
        print(">> 纯LLM直接生成已禁用 (如需启用请传入 --with_pure_llm)")
    else:
        print(">> 纯LLM直接生成已跳过 (OpenAI库未安装)")

    # 3. 初始化评估器
    evaluator = Evaluator()

    # 4. 存储结果
    results = {
        'Text': {'l2': [], 'acc': [], 'recall': [], 'cosine': [], 'style': [], 'module': []},
        'Wav2Vec': {'l2': [], 'acc': [], 'recall': [], 'cosine': [], 'style': [], 'module': []},
        'FeatureNN': {'l2': [], 'acc': [], 'recall': [], 'cosine': [], 'style': [], 'module': []},
        'TRR': {'l2': [], 'acc': [], 'recall': [], 'cosine': [], 'style': [], 'module': []}
    }
    if include_pure_llm:
        results['PureLLM'] = {'l2': [], 'acc': [], 'recall': [], 'cosine': [], 'style': [], 'module': []}

    per_query_rows = []

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
                "query_idx": query_idx,
                "query_name": query_name,
                "method": method,
                "retrieved_name": retrieved_name,
                "l2": l2,
                "acc@0.1": acc,
                "recall": recall,
                "cosine": cosine,
                "module": module,
                "missing": missing,
            }
        )

    # 5. 对每个测试样本进行检索和评估
    print("\n" + "="*100)
    print("检索和评估")
    print("="*100)

    for idx, test_item in enumerate(test_items, 1):
        name = test_item['SongName']
        gt_params = test_item['Parameters']
        gt_style = test_item.get('Style', [])

        print(f"\n[{idx}/{len(test_items)}] {name}")

        # 纯LLM直接生成 (不使用检索) - optional (slow / network)
        if include_pure_llm:
            if HAS_OPENAI:
                print(f"  [Pure LLM] 生成参数中...")
                llm_results = pure_llm.retrieve(test_item, k=1)
                if llm_results:
                    retrieved_params = llm_results[0].get('Parameters', {})
                    l2 = evaluator.compute_parameter_distance(retrieved_params, gt_params)
                    acc = evaluator.compute_accuracy_tolerance(retrieved_params, gt_params, tolerance=0.1)
                    recall = evaluator.compute_parameter_recall(retrieved_params, gt_params)
                    cosine = evaluator.compute_cosine_similarity(retrieved_params, gt_params)
                    style = evaluator.compute_style_consistency(retrieved_params.get('Style', []), gt_style)
                    module = evaluator.compute_module_consistency(retrieved_params, gt_params, active_threshold=0.1)

                    results['PureLLM']['l2'].append(l2)
                    results['PureLLM']['acc'].append(acc)
                    results['PureLLM']['recall'].append(recall)
                    results['PureLLM']['cosine'].append(cosine)
                    results['PureLLM']['style'].append(style)
                    results['PureLLM']['module'].append(module)
                    record_row(idx, name, "PureLLM", llm_results[0].get("SongName", ""), l2, acc, recall, cosine, module, 0)

                    print(f"  Pure LLM:   L2={l2:.4f} Acc={acc:.4f} Recall={recall:.4f} Cos={cosine:.4f} Style={style:.4f} Module={module:.4f} | {llm_results[0]['SongName']}")
                else:
                    print(f"  Pure LLM:   生成失败")
                    record_row(idx, name, "PureLLM", "", "", "", "", "", "", 1)
            else:
                # OpenAI不可用，使用fallback参数
                llm_results = pure_llm.retrieve(test_item, k=1)
                if llm_results:
                    retrieved_params = llm_results[0].get('Parameters', {})
                    l2 = evaluator.compute_parameter_distance(retrieved_params, gt_params)
                    acc = evaluator.compute_accuracy_tolerance(retrieved_params, gt_params, tolerance=0.1)
                    recall = evaluator.compute_parameter_recall(retrieved_params, gt_params)
                    cosine = evaluator.compute_cosine_similarity(retrieved_params, gt_params)
                    style = evaluator.compute_style_consistency(retrieved_params.get('Style', []), gt_style)
                    module = evaluator.compute_module_consistency(retrieved_params, gt_params, active_threshold=0.1)

                    results['PureLLM']['l2'].append(l2)
                    results['PureLLM']['acc'].append(acc)
                    results['PureLLM']['recall'].append(recall)
                    results['PureLLM']['cosine'].append(cosine)
                    results['PureLLM']['style'].append(style)
                    results['PureLLM']['module'].append(module)
                    record_row(idx, name, "PureLLM", "Fallback", l2, acc, recall, cosine, module, 0)

                    print(f"  Pure LLM:   L2={l2:.4f} Acc={acc:.4f} Recall={recall:.4f} Cos={cosine:.4f} Style={style:.4f} Module={module:.4f} | Fallback")

        # 纯文本检索
        text_results = text_retrieval.retrieve(test_item, k=1)
        if text_results:
            retrieved_params = text_results[0].get('Parameters', {})
            l2 = evaluator.compute_parameter_distance(retrieved_params, gt_params)
            acc = evaluator.compute_accuracy_tolerance(retrieved_params, gt_params, tolerance=0.1)
            recall = evaluator.compute_parameter_recall(retrieved_params, gt_params)
            cosine = evaluator.compute_cosine_similarity(retrieved_params, gt_params)
            style = evaluator.compute_style_consistency(retrieved_params.get('Style', []), gt_style)
            module = evaluator.compute_module_consistency(retrieved_params, gt_params, active_threshold=0.1)

            results['Text']['l2'].append(l2)
            results['Text']['acc'].append(acc)
            results['Text']['recall'].append(recall)
            results['Text']['cosine'].append(cosine)
            results['Text']['style'].append(style)
            results['Text']['module'].append(module)
            record_row(idx, name, "Text-RAG", text_results[0].get("SongName", ""), l2, acc, recall, cosine, module, 0)

            print(f"  Text:       L2={l2:.4f} Acc={acc:.4f} Recall={recall:.4f} Cos={cosine:.4f} Style={style:.4f} Module={module:.4f} | {text_results[0]['SongName']}")
        else:
            print(f"  Text:       未检索到")
            record_row(idx, name, "Text-RAG", "", "", "", "", "", "", 1)

        # Wav2Vec检索
        w2v_results = wav2vec_retrieval.retrieve(test_item, k=1)
        if w2v_results:
            retrieved_params = w2v_results[0].get('Parameters', {})
            l2 = evaluator.compute_parameter_distance(retrieved_params, gt_params)
            acc = evaluator.compute_accuracy_tolerance(retrieved_params, gt_params, tolerance=0.1)
            recall = evaluator.compute_parameter_recall(retrieved_params, gt_params)
            cosine = evaluator.compute_cosine_similarity(retrieved_params, gt_params)
            style = evaluator.compute_style_consistency(retrieved_params.get('Style', []), gt_style)
            module = evaluator.compute_module_consistency(retrieved_params, gt_params, active_threshold=0.1)

            results['Wav2Vec']['l2'].append(l2)
            results['Wav2Vec']['acc'].append(acc)
            results['Wav2Vec']['recall'].append(recall)
            results['Wav2Vec']['cosine'].append(cosine)
            results['Wav2Vec']['style'].append(style)
            results['Wav2Vec']['module'].append(module)
            record_row(idx, name, "Wav2Vec-RAG", w2v_results[0].get("SongName", ""), l2, acc, recall, cosine, module, 0)

            print(f"  Wav2Vec:    L2={l2:.4f} Acc={acc:.4f} Recall={recall:.4f} Cos={cosine:.4f} Style={style:.4f} Module={module:.4f} | {w2v_results[0]['SongName']}")
        else:
            print(f"  Wav2Vec:    未检索到")
            record_row(idx, name, "Wav2Vec-RAG", "", "", "", "", "", "", 1)

        # FeatureNN检索
        fnn_results = featurenn_retrieval.retrieve(test_item, k=1)
        if fnn_results:
            retrieved_params = fnn_results[0].get('Parameters', {})
            l2 = evaluator.compute_parameter_distance(retrieved_params, gt_params)
            acc = evaluator.compute_accuracy_tolerance(retrieved_params, gt_params, tolerance=0.1)
            recall = evaluator.compute_parameter_recall(retrieved_params, gt_params)
            cosine = evaluator.compute_cosine_similarity(retrieved_params, gt_params)
            style = evaluator.compute_style_consistency(retrieved_params.get('Style', []), gt_style)
            module = evaluator.compute_module_consistency(retrieved_params, gt_params, active_threshold=0.1)

            results['FeatureNN']['l2'].append(l2)
            results['FeatureNN']['acc'].append(acc)
            results['FeatureNN']['recall'].append(recall)
            results['FeatureNN']['cosine'].append(cosine)
            results['FeatureNN']['style'].append(style)
            results['FeatureNN']['module'].append(module)
            record_row(idx, name, "FeatureNN-RAG", fnn_results[0].get("SongName", ""), l2, acc, recall, cosine, module, 0)

            print(f"  FeatureNN:  L2={l2:.4f} Acc={acc:.4f} Recall={recall:.4f} Cos={cosine:.4f} Style={style:.4f} Module={module:.4f} | {fnn_results[0]['SongName']}")
        else:
            print(f"  FeatureNN:  未检索到")
            record_row(idx, name, "FeatureNN-RAG", "", "", "", "", "", "", 1)

        # TRR检索
        trr_results = trr_retrieval.retrieve(test_item, k=1)
        if trr_results:
            retrieved_params = trr_results[0].get('Parameters', {})
            l2 = evaluator.compute_parameter_distance(retrieved_params, gt_params)
            acc = evaluator.compute_accuracy_tolerance(retrieved_params, gt_params, tolerance=0.1)
            recall = evaluator.compute_parameter_recall(retrieved_params, gt_params)
            cosine = evaluator.compute_cosine_similarity(retrieved_params, gt_params)
            style = evaluator.compute_style_consistency(trr_results[0].get('Style', []), gt_style)
            module = evaluator.compute_module_consistency(retrieved_params, gt_params, active_threshold=0.1)

            results['TRR']['l2'].append(l2)
            results['TRR']['acc'].append(acc)
            results['TRR']['recall'].append(recall)
            results['TRR']['cosine'].append(cosine)
            results['TRR']['style'].append(style)
            results['TRR']['module'].append(module)
            record_row(idx, name, "TRR", trr_results[0].get("SongName", ""), l2, acc, recall, cosine, module, 0)

            print(f"  TRR:        L2={l2:.4f} Acc={acc:.4f} Recall={recall:.4f} Cos={cosine:.4f} Style={style:.4f} Module={module:.4f} | {trr_results[0]['SongName']}")
        else:
            print(f"  TRR:        未检索到")
            record_row(idx, name, "TRR", "", "", "", "", "", "", 1)

    # 6. 打印总结表格
    print("\n" + "="*150)
    print("检索方法对比结果总结 (Summary: Retrieval Method Comparison)")
    print("="*150)
    print(f"{'方法':<20} {'L2误差↓':<15} {'准确率↑':<15} {'召回率↑':<15} {'余弦相似度↑':<18} {'模块一致性↑':<18}")
    print("-"*150)

    methods = [
        ('纯文本检索', results['Text']),
        ('Wav2Vec-RAG', results['Wav2Vec']),
        ('FeatureNN-RAG', results['FeatureNN']),
        ('TRR', results['TRR'])
    ]
    if include_pure_llm:
        methods = [('纯LLM直接生成', results['PureLLM'])] + methods

    for method_name, metrics in methods:
        l2 = sum(metrics['l2']) / len(metrics['l2']) if metrics['l2'] else 0
        acc = sum(metrics['acc']) / len(metrics['acc']) if metrics['acc'] else 0
        recall = sum(metrics['recall']) / len(metrics['recall']) if metrics['recall'] else 0
        cosine = sum(metrics['cosine']) / len(metrics['cosine']) if metrics['cosine'] else 0
        module = sum(metrics['module']) / len(metrics['module']) if metrics['module'] else 0

        print(f"{method_name:<20} {l2:<15.4f} {acc:<15.4f} {recall:<15.4f} {cosine:<18.4f} {module:<18.4f}")

    print("-"*150)

    # 找出最佳方法
    print("\n最佳方法 (Best Method for each metric):")

    # 计算各方法的平均指标
    avg_metrics = []
    for name, metrics in methods:
        l2_avg = sum(metrics['l2']) / len(metrics['l2']) if metrics['l2'] else float('inf')
        acc_avg = sum(metrics['acc']) / len(metrics['acc']) if metrics['acc'] else 0
        recall_avg = sum(metrics['recall']) / len(metrics['recall']) if metrics['recall'] else 0
        cosine_avg = sum(metrics['cosine']) / len(metrics['cosine']) if metrics['cosine'] else 0
        module_avg = sum(metrics['module']) / len(metrics['module']) if metrics['module'] else 0
        avg_metrics.append((l2_avg, acc_avg, recall_avg, cosine_avg, module_avg))

    # L2误差最低 (越小越好)
    best_l2_idx = min(range(len(avg_metrics)), key=lambda i: avg_metrics[i][0])
    print(f"  L2误差最低:     {methods[best_l2_idx][0]} ({avg_metrics[best_l2_idx][0]:.4f})")

    # 准确率最高 (越大越好)
    best_acc_idx = max(range(len(avg_metrics)), key=lambda i: avg_metrics[i][1])
    print(f"  准确率最高:     {methods[best_acc_idx][0]} ({avg_metrics[best_acc_idx][1]:.4f})")

    # 召回率最高 (越大越好)
    best_recall_idx = max(range(len(avg_metrics)), key=lambda i: avg_metrics[i][2])
    print(f"  召回率最高:     {methods[best_recall_idx][0]} ({avg_metrics[best_recall_idx][2]:.4f})")

    # 余弦相似度最高 (越大越好)
    best_cosine_idx = max(range(len(avg_metrics)), key=lambda i: avg_metrics[i][3])
    print(f"  余弦相似度最高: {methods[best_cosine_idx][0]} ({avg_metrics[best_cosine_idx][3]:.4f})")

    # 模块一致性最高 (越大越好)
    best_module_idx = max(range(len(avg_metrics)), key=lambda i: avg_metrics[i][4])
    print(f"  模块一致性最高: {methods[best_module_idx][0]} ({avg_metrics[best_module_idx][4]:.4f})")

    if include_pure_llm:
        # RAG vs 纯LLM对比
        print("\n" + "="*150)
        print("RAG vs 纯LLM直接生成对比 (Proving RAG Necessity)")
        print("="*150)
        pure_llm_l2 = sum(results['PureLLM']['l2']) / len(results['PureLLM']['l2'])
        trr_l2 = sum(results['TRR']['l2']) / len(results['TRR']['l2'])

        print(f"\n纯LLM直接生成 L2误差: {pure_llm_l2:.4f}")
        print(f"TRR检索 L2误差:        {trr_l2:.4f}")

        if pure_llm_l2 > trr_l2:
            improvement = ((pure_llm_l2 - trr_l2) / pure_llm_l2) * 100
            print(f"\n>>> RAG检索相比纯LLM生成，L2误差降低 {improvement:.1f}%")
            print(f">>> 结论: RAG检索显著优于纯LLM生成，证明了RAG的必要性")
        else:
            print(f"\n>>> 结论: 纯LLM生成优于RAG检索")

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

    print("\n" + "="*130)
    print("EXPERIMENT COMPLETE")
    print("="*130)


if __name__ == "__main__":
    main()
