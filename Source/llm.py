from asyncio.windows_events import NULL
from email.mime import audio
from pickle import FLOAT
import sys
import json
import sqlite3
import math
from networkx import preferential_attachment
from openai import OpenAI
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import torch
import librosa
from transformers import Wav2Vec2Processor, Wav2Vec2Model
import numpy as np
import tempfile


# 定义一个函数来安全地写入文件
def safe_write_file(filename, content):
    try:
        # 首先尝试在当前目录写入
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
            print(f"文件已保存到当前目录: {os.path.abspath(filename)}")
    except (IOError, PermissionError):
        try:
            # 如果失败，尝试在环境变量指定的文档目录写入
            docs_dir = os.environ.get('DOCUMENTS_DIR')  # 获取环境变量

            if docs_dir:
                full_path = os.path.join(docs_dir, filename)
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"文件已保存到文档目录: {full_path}")
            else:
                # 如果环境变量不存在，抛出异常以进入下一个尝试
                raise FileNotFoundError("环境变量 DOCUMENTS_DIR 未设置")

        except (IOError, PermissionError, FileNotFoundError):
            # 如果仍然失败，尝试在系统临时目录写入
            temp_dir = tempfile.gettempdir()
            full_path = os.path.join(temp_dir, filename)
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"文件已保存到临时目录: {full_path}")

# 定义Jaccard相似度函数
def jaccard_similarity(set1, set2):
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    return intersection / union if union != 0 else 0


# 定义文本相似度函数
def text_similarity(text1, text2):
    if not text1 or not text2:
        return 0.0
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform([text1, text2])
    return cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]

def audio_to_vector(file_path):
    # 加载预训练的处理器和模型
    processor = Wav2Vec2Processor.from_pretrained("facebook/wav2vec2-base-960h")
    model = Wav2Vec2Model.from_pretrained("facebook/wav2vec2-base-960h")

    # 加载音频文件（librosa默认采样率为22050Hz，wav2vec2通常期望16000Hz）
    audio, sample_rate = librosa.load(file_path, sr=16000)

    # 预处理音频：转换为输入特征
    inputs = processor(audio, sampling_rate=16000, return_tensors="pt")

    # 获取模型输出（不计算梯度以提高效率）
    with torch.no_grad():
        outputs = model(**inputs)

    # outputs.last_hidden_state是序列级特征，形状为 [1, seq_len, hidden_size]
    # 可以通过平均等方式得到整个音频的向量表示
    audio_vector = outputs.last_hidden_state.mean(dim=1).squeeze()

    return audio_vector.numpy()  # 转换为numpy数组返回


# 使用C盘固定路径连接到数据库
db_dir = "C:\\MusicData"
if not os.path.exists(db_dir):
    os.makedirs(db_dir)  # 创建目录（如果不存在）
db_path = os.path.join(db_dir, "music_info.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 连接到外部音频信息数据库
audio_db_dir = os.environ.get('SUPERTONAL_DIR')
audio_db_path = os.path.join(audio_db_dir, "audio_info.db")
audio_conn = sqlite3.connect(audio_db_path)
audio_cursor = audio_conn.cursor()
"""
# 删除表
try:
    cursor.execute("DROP TABLE IF EXISTS music_responses")
    conn.commit()
    print("Table 'music_responses' has been dropped successfully.")
except sqlite3.Error as e:
    print(f"An error occurred while dropping the table: {e}")
"""
# 修改表结构，仅保留需要的列
cursor.execute('''
CREATE TABLE IF NOT EXISTS music_responses (
    SongName TEXT PRIMARY KEY,
    Parameters TEXT,
    Preferences TEXT,
    Style TEXT,
    Feature TEXT 
)
''')
conn.commit()

# 检查audio_vector表是否存在，若不存在则创建
audio_cursor.execute('''
CREATE TABLE IF NOT EXISTS audio_vector (
    Parameters TEXT PRIMARY KEY,
    Vector TEXT
)
''')
audio_conn.commit()

client = OpenAI(api_key="sk-1b73586fde854a329ec187dc371f53ef", base_url="https://api.deepseek.com")

import platform

if len(sys.argv) > 1:
    if platform.system() == "Windows":
        print(f"sys.argv: {len(sys.argv)}")
        # Windows命令行通常使用GBK编码
        chat_message = sys.argv[1].encode('cp936').decode('utf-8', errors='replace')
        memoryEnabled = sys.argv[2]
        file_path = ""
        text_Weight = ""
        preference_Weight = ""
        audio_Weight = ""
        if len(sys.argv) == 4:
            file_path = sys.argv[3].encode('cp936').decode('utf-8', errors='replace')
            text_Weight = ""
            preference_Weight = ""
            audio_Weight = ""
        if 4 < len(sys.argv) < 7:
            file_path = ""
            text_Weight = sys.argv[3]
            preference_Weight = sys.argv[4]
            audio_Weight = ""
        if len(sys.argv) > 6:
            file_path = sys.argv[3].encode('cp936').decode('utf-8', errors='replace')
            text_Weight = sys.argv[4]
            preference_Weight = sys.argv[5]
            audio_Weight = sys.argv[6]
    else:
        # Linux/macOS通常使用UTF-8
        chat_message = sys.argv[1]
        memoryEnabled = sys.argv[2]
        file_path = ""
        text_Weight = ""
        preference_Weight = ""
        audio_Weight = ""
        if len(sys.argv) == 4:
            file_path = sys.argv[3]
            text_Weight = ""
            preference_Weight = ""
            audio_Weight = ""
        if 4 < len(sys.argv) < 7:
            file_path = ""
            text_Weight = sys.argv[3]
            preference_Weight = sys.argv[4]
            audio_Weight = ""
        if len(sys.argv) > 6:
            file_path = sys.argv[3]
            text_Weight = sys.argv[4]
            preference_Weight = sys.argv[5]
            audio_Weight = sys.argv[6]
else:
    chat_message = sys.argv[1].encode('cp936').decode('utf-8', errors='replace')
    memoryEnabled = sys.argv[2]
    file_path = ""
    text_Weight = ""
    preference_Weight = ""
    audio_Weight = ""
    if len(sys.argv) == 4:
        file_path = sys.argv[3].encode('cp936').decode('utf-8', errors='replace')
        text_Weight = ""
        preference_Weight = ""
        audio_Weight = ""
    if 4 < len(sys.argv) < 7:
        file_path = ""
        text_Weight = sys.argv[3]
        preference_Weight = sys.argv[4]
        audio_Weight = ""
    if len(sys.argv) > 6:
        file_path = sys.argv[3].encode('cp936').decode('utf-8', errors='replace')
        text_Weight = sys.argv[4]
        preference_Weight = sys.argv[5]
        audio_Weight = sys.argv[6]
print(f"Chat message: {chat_message}")
print(f"memoryEnabled: {memoryEnabled}")
print(f"text_Weight: {text_Weight}")
print(f"preference_Weight: {preference_Weight}")
print(f"audio_Weight: {audio_Weight}")
print(f"File path: {file_path}")
if file_path and file_path.strip():
    vector = audio_to_vector(file_path)
    print("音频向量形状：", vector)
else:
    vector = None  # 或空列表[]，根据后续使用场景确定
    print("未提供有效的文件路径，音频向量为空")

# 创建对话历史列表
conversation_history = []
# 第二个系统提示(风格和特征提示词)
system_prompt2 = f"""
你是资深音乐分析师与风格相似度检索描述顾问。基于用户输入 (变量: {chat_message}) 生成：
  1) 精炼、结构化的风格与技巧标签 (tags)
  2) 多条结合用户偏好的有助于检索“相似风格歌曲”的英文扩展描述 (description)


（多语言增强版：支持中文、英文、日文、韩文、西/葡/法/德/俄等歌曲名或情绪描述）

==============================
总体目标
- tags：主风格 + 子风格/质感 + 技巧 / 结构特征；≤6；面向检索
- description：2~6 条英语句子；不同维度；可含 1 条 token bundle；高信息密度、无冗余

==============================
阶段0 输入初判
  - 分类：明确音乐 / 可能音乐相关（情绪或可映射风格） / 非音乐
  - 若明显非音乐 → 输出 {{ "tags": [], "description": [] }}
  - 若仅给出疑似歌曲名（任一语种）→ 尝试歌曲名识别与风格推断

==============================
阶段1 信息抽取 (Extraction)
  A. 通用抽取：
    - 歌曲 / 艺人（仅内部参考，不直接输出名称）
    - 风格 / 子风格（post-rock, math_rock, jazz_fusion, shoegaze, dream_pop, city_pop, britpop, synthwave, vaporwave, gothic_metal, symphonic_metal, melodic_death_metal, bossa_nova_fusion, tango_nuevo, latin_rock, reggaeton, k_indie, j_rock, visual_keI(若有强烈视觉系暗示则可转化为 japanese_alternative_rock + theatrical_aesthetic)，k_pop_ballad 等）
    - 情绪/氛围：melancholic / uplifting / introspective / ethereal / brooding / nostalgic / cinematic / aggressive / dreamy 等
    - 时代信号：80s/90s/2000s/modern（仅在文本或风格显著暗示，如 city_pop → 80s inspired；synthwave → 80s retro；britpop → 90s；vaporwave → retro_digital）
    - 技巧词：tapping, sweep, legato, hybrid_picking, polyrhythm, syncopated, palm_mute, ambient_swells, fuzz, clean_arpeggios, layered_delays, reverse_reverb, sidechain_pulse, gated_reverb
    - 音色词：clean, glassy, chimey, mid-gain, saturated, high-gain, fuzzy, reverb-drenched, modulated, tape_warmth, compressed, lo_fi, analog, shimmering
    - 节奏/速度：slow, mid-tempo 100-110 bpm, fast, driving 120+, syncopated groove, straight 16ths, swung, polyrhythmic, halftime, reggaeton_dembow
    - 和声/调式：modal, aeolian melancholy, dorian tint, lydian lift, extended jazz chords, chromatic tension-release, droning pedal, pentatonic lyrical, harmonic_minor_color
    - 纹理 / 编配：layered guitars, sparse minimal space, dense wall-of-sound, shimmering delay pads, pulsating synth bass, atmospheric pads, rhythmic stabs, cinematic swells
  B. 多参考冲突处理：取主频率 + 用户明确强调；不强行融合对立风格除非文本暗示 hybrid
  C. 纯情绪输入映射（跨语言）： 
     - “孤独/宇宙/空/冷/寂静” → cinematic_ambient / atmospheric_post_rock / spacey_dream_pop
     - “厚重/压抑/泥泞” → doom / sludge / dark_post_metal
     - “律动/舞动/节奏感” → funk_rock / disco_funk / groove_metal / nu_disco
     - “迷幻/恍惚” → psychedelic_rock / space_rock / shoegaze / dream_pop
     - “复杂/错综/变拍/多层” → math_rock / progressive_metal / polyrhythmic_fusion
     - “温柔/治愈/疗愈/抚慰” → dreamy_ambient / clean_post_rock / soft_dream_pop / lofi_chill
     - “怀旧/复古” → retro_synthwave / city_pop_influence / vintage_analog_texture / nostalgic_90s_alt
  D. 多语言情绪词（内部映射，示例）：
     - 日文：切ない=melancholic, 懐かしい=nostalgic, 激しい=aggressive
     - 韩文：우울한=melancholic, 몽환적인=dreamy, 강렬한=intense
     - 西语：melancólico=melancholic, atmosférico=atmospheric, bailable=danceable
     - 葡语：sonhador=dreamy, pesado=heavy, suave=soft
     - 法语：rêveur=dreamy, nostalgique=nostalgic
     - 德语：melancholisch=melancholic, treibend=driving
     - 俄语：мрачный=dark, атмосферный=atmospheric

==============================
多语言歌曲名识别与风格推断 (关键增强)
  1. 识别：若输入主要由（中文 / 假名 / 韩文 / 拉丁字母 + 少量标点/空格）构成且长度 2~40，无明确普通句式 → 优先视作“歌曲 / 标题片段”
  2. 规范化：
     - 去除引号、全角空格、尾部语气词，大小写统一
     - 去除常见前后缀（如 "歌曲", "歌", "lyrics", "lyric", "翻唱"）
     - 日文假名：片假名→平假名归一；可内部用于模糊匹配
     - 去除重音与变音 (áàäâ→a, ñ→n, ü→u)
  3. 模糊匹配策略（内部）：
     - Levenshtein 距离 ≤ max(1, 标题长度*0.15) 视作可疑命中
     - 去停用符号后 trigram Jaccard ≥0.72 视作可疑命中
     - 中日韩：按字符 bigram；拉丁语系：按不含空格的子串与 n-gram
  4. 可使用外部可注入词典（变量：{{multilingual_song_dict}} 若存在）：
     - 结构建议:
       {{
         "zh": {{"灰色轨迹": {{"artist":"Beyond","style_hints":["cantonese_rock","melodic_emotional_rock"]}}}},
         "ja": {{"残酷な天使のテーゼ": {{"style_hints":["anime_theme","90s_j_rock","anthemic"]}}}},
         "ko": {{"너의 의미": {{"style_hints":["k_pop_ballad","soft_acoustic"]}}}},
         "es": {{"despacito": {{"style_hints":["latin_pop","reggaeton","tropical_influence"]}}}}
       }}
     - 若未注入则使用内部常识高频列表（不外显）
  5. 高置信度命中时：
     - 利用 style_hints 抽象出检索标签（不输出艺人名）
     - 若 style_hints 中含地域/时代/结构特征，可择最具区分度 1~2 个作为 tags 前部
  6. 低置信度或冲突：
     - 不臆造具体歌曲；改用情绪 + 质感泛化
  7. 永不在输出 description 中直接写真实艺人名（保持可泛化检索）

==============================
跨语言风格归纳补充（仅在文本或映射暗示时使用）：
  - city_pop：smooth_groove, soft_fusion_chords, retro_80s_gloss
  - j_rock / japanese_alternative_rock：melodic hooks + emotive anthemic lift
  - shoegaze：washed_fuzzy_layers, reverb_drenched_wall, hazy_vocals
  - dream_pop：lush_airy_textures, soft_etherial_pads
  - k_indie：intimate_clean_tones, mellow_midtempo
  - latin_rock / latin_pop：rhythmic_percussion_layers, syncopated_groove, bright_melodic
  - reggaeton：dembow_pattern, syncopated_percussion, tropical_atmosphere
  - bossa_nova_fusion：soft syncopated jazz-influenced chords, gentle swing
  - nordic_melodeath：melodic_harmonic_minor_riffs + driving double_kick（仅在明确极端金属信号时）
  - synthwave：retro_analog_synths, steady_four_on_floor, neon_atmosphere
  - vaporwave：lo_fi_sampled_loops, detuned_retro, slowed_reverbed_aesthetic

==============================
阶段2 风格推断 (Genre Inference)
  - 基于抽取 & 多语言推断：给出 1~3 个具体方向（优先具体细分而非 broad）
  - 允许地域/时代与质感组合：e.g. cantonese_melodic_rock, 90s_britpop_atmospheric, retro_synthwave, latin_pop_reggaeton, japanese_dream_pop
  - 无足够信号：可用 broad+质感（ambient_dreamy, dark_atmospheric, melodic_clean）

==============================
阶段3 标签构建 (Tags)
  规则：
    1. 数量 ≤6
    2. 小写英文字母/数字/下划线/短横线
    3. 排序：主/核心风格 → 次风格/地域/时代 → 质感/技巧 (ambient_swells, layered_textures, polyrhythmic_pulse, melodic_emotion, fuzzy_wall, clean_arpeggios, syncopated_groove)
    4. 不重复；不产生未被暗示的极窄标签
    5. 高置信度歌曲匹配：包含最具区分度地域或风格标签（≤2）；避免仅 "rock"
    6. 信息不足：tags=[]

==============================
阶段4 英文扩展检索描述 (Descriptions for Similarity Retrieval)
  - 2~6 条；每条 14~30 英文单词（信息极少可 ≥10）
  - 各条侧重点不同，可组合维度：
     * Style / Subgenre Layering
     * Mood & Emotional Color
     * Tempo & Rhythmic Feel
     * Harmonic / Modal Traits
     * Texture & Arrangement
     * Instrument Roles
     * Tone & Production
     * Dynamic / Structural Arc
     * Abstract Influence Qualifiers
     * Token Bundle (1 条可用逗号分隔密集 tokens)
  - 不出现中文 / 不写真实艺人名
  - 不重复语序模板
  - 若仍缺少信息：至少 1 条含 "general stylistic inference"
  - Token bundle 示例格式：
     "melodic cantonese rock, emotional mid-gain guitars, clean-crunch layering, moderate tempo, lyrical phrasing, gradual lift"

==============================
阶段5 质量与合规校验
  - 去重句子
  - 无中文、无未闭合引号、无艺人名
  - 若无法确定音乐特征 → 输出 {{ "tags": [], "description": [] }}

==============================
防幻觉与约束
  - 不凭单一情绪词直接推断高度具体亚流派
  - 没有节奏/多节奏暗示不写 polyrhythmic_pulse
  - 没有重型失真不写 death_metal / djent 等
  - 多语言标题若不在映射 / 字典且无上下文，不创造虚构风格
  - 不把常见单词误判为曲名（如 "love", "rain" 单独出现 → 视作情绪/主题，除非格式强烈指向标题）

==============================
外部可注入资源（可选）
  - {{multilingual_song_dict}} 若存在：
    * 优先使用其 style_hints 补强标签
    * 未匹配则按常规推断
  - 允许未来扩展 {{style_alias_map}} 将用户俗称映射到规范标签（内部：{{"shoegazing":"shoegaze","mathrock":"math_rock"}}）

==============================
输出格式（唯一合法）
{{
  "tags": ["tag1","tag2"],
  "description": ["sentence 1","sentence 2"]
}}

==============================
执行
  - 基于 {chat_message} 完成分析，仅输出最终 JSON

"""

user_prompt2 = f"""
请根据：{chat_message}，
1. 分析其具体音乐风格（尽量细致）。
2. 生成 tags（英文、小写、具体）。
3. 用英文描述吉他 solo 的可能演奏特点（数组形式，2~6 条）。

仅输出 JSON（含 keys: tags, description），不要其它文本。
"""

# 保存系统消息
system_message = {"role": "system", "content": system_prompt2}
conversation_history.append(system_message)
# 保存用户消息
user_message = {"role": "user", "content": user_prompt2}
conversation_history.append(user_message)
# 发送请求
response2 = client.chat.completions.create(
    model="deepseek-chat",
    messages=[system_message, user_message],
    stream=False
)
# 保存助手回复
assistant_message = {
    "role": "assistant",
    "content": response2.choices[0].message.content
}
conversation_history.append(assistant_message)

# 获取 response2 响应数据并转换为 JSON
response_content2 = response2.choices[0].message.content
# 去除前后的代码块标记和换行
cleaned_content2 = response_content2.replace("```json", "").replace("```", "").strip()
try:
    result2 = json.loads(cleaned_content2)
    result2_str = json.dumps(result2, ensure_ascii=False)
    # 获取歌曲的风格
    song_style = result2.get("tags", [])
    # 获取吉他演奏的特点
    guitar_features = result2.get("description", [])
    # 打印信息
    print(f"风格: {song_style}")
    print(f"吉他演奏的特点: {guitar_features}")
except json.JSONDecodeError:
    print(f"Error: 无效的JSON响应: {cleaned_content2}")
    sys.exit(1)

effectors = [
    {
        "name": "compression",
        "example_with": '{"CompressorOn":{"Threshold":-24.0,"Ratio":4.0,"Attack":0.012,"Release":0.180,"Makeup":6.0,"Mix":0.85}}',
        "prompt_with": (
            f"基于风格标签(若已生成): {song_style} 与原始描述: {chat_message} 。"
            "任务: 为吉他或总线路(根据语义自行判断)生成压缩器设置 JSON。"
            "\n参数要求："
            "\n1) Threshold (-128.00~0.00 dB, 越激进=值越低；清透保动态=偏高 -20~-10；强烈挤压= -40~-25 或更低)。"
            "\n2) Ratio (1~100, 轻柔:1.5~3；常规控制:3~6；高度控制/现代金属:6~12；限制器式挤压:>12)。"
            "\n3) Attack (0.00~1.00 ms, 数值越小越快。保留瞬态=略放大 ~0.10~0.30；金属高致密=极快 <0.05；若为营造呼吸感可适度放慢 >0.30)。"
            "\n4) Release (0.00~1.00 ms，模拟这里是“秒的小数”概念，需相对 Attack 更长；平滑自然=0.10~0.30；泵感=0.05~0.12；持续铺垫氛围可更长 0.30~0.60)。"
            "\n5) Makeup (-128.00~64.00 dB，补偿压缩导致的增益降低。轻压缩 2~6 dB；强压缩 8~14；若阈值极低再适度提升)。"
            "\n6) Mix (0.00~1.00 并行压缩混合，保动态=0.5~0.8；激进致密=0.9~1.0；透明保原味=0.3~0.5)。"
            "\n逻辑映射指南："
            "\n- ‘ambient, atmospheric, post-rock, cinematic’：较温和阈值(>-30)，较低 Ratio(2~4)，中等较慢 Attack 以保瞬态，较长 Release，Mix 偏高并行保原声。"
            "\n- ‘progressive_metal, djent, modern metal’：低阈值(-45~-30)，高 Ratio(6~10+)，极快 Attack，较快 Release 防止拖尾，较高 Makeup。"
            "\n- ‘blues, vintage, expressive’：阈值中等(-28~-20)，Ratio 2~4，Attack 适中(0.10~0.25)，Release 中等自然，Makeup 适度，Mix 0.6~0.8。"
            "\n- 若标签指向“dynamic, touch, expressive”为主，避免过度压缩。"
            "\n- 若无法确定风格，使用 neutral 设定：Threshold -24, Ratio 3, Attack 0.08, Release 0.18, Makeup 4, Mix 0.7。"
            "\n输出：只返回 JSON："
            '\n{"CompressorOn":{"Threshold":<float>,"Ratio":<float>,"Attack":<float>,"Release":<float>,"Makeup":<float>,"Mix":<float>}}'
            "\n确保数值在范围内，保留 2~3 位小数，无额外文本。"
        )
    },
    {
        "name": "distortion",
        "example_with": '{"DriverOn":{"Distortion":0.70,"Volume":-18.4}}',
        "prompt_with": (
            f"基于风格标签 {song_style} 与原始描述 {chat_message} ，生成失真器参数。"
            "\n参数：Distortion 0.00~1.00 (驱动强度)，Volume -64.0~0.0 dB (输出补偿)。"
            "\n风格映射："
            "\n- ‘high gain metal / djent / modern shred’：Distortion 0.75~0.95；Volume 视链路适度负补偿(-24~-12)。"
            "\n- ‘classic rock / blues rock’：Distortion 0.40~0.65；Volume -18~-6。"
            "\n- ‘fusion / expressive mid-gain’：Distortion 0.45~0.60；Volume -12~-4。"
            "\n- ‘ambient / clean emphasis’：Distortion 0.05~0.25；Volume -6~-2。"
            "\n- 若后接过载器(出现 screamer / overdrive / boost 语义)则此处 Distortion 略收敛。"
            "\n若信息不足使用中性：Distortion 0.55, Volume -12。"
            '\n输出 JSON: {"DriverOn":{"Distortion":<float>,"Volume":<float>}}'
            "\n只输出 JSON，数值合法，2~3 位小数。"
        )
    },
    {
        "name": "overload",
        "example_with": '{"ScreamerOn":{"Drive":0.82,"Tone":0.55,"Level":-18.3}}',
        "prompt_with": (
            f"基于 {song_style} 与 {chat_message} 生成过载(Screamer类)参数。"
            "\n参数范围：Drive 0.00~1.00；Tone 0.00~1.00（重点调中高频咬合度）；Level -64.00~0.00 dB。"
            "\n风格映射："
            "\n- 用作前级 tighten（金属、djent）：Drive 0.25~0.45，Tone 0.55~0.70，Level -18~-8。"
            "\n- 主音中增亮 sustain（fusion / prog lead）：Drive 0.50~0.70，Tone 0.50~0.62，Level -14~-6。"
            "\n- 复古/布鲁斯：Drive 0.55~0.80，Tone 0.40~0.55，Level -10~-4。"
            "\n- 只需轻微 edge：Drive 0.20~0.35，Tone 0.45~0.55，Level -12~-6。"
            "\n中性回退：Drive 0.60, Tone 0.52, Level -12。"
            '\n输出 JSON: {"ScreamerOn":{"Drive":<float>,"Tone":<float>,"Level":<float>}}'
            "\n仅 JSON，无解释。"
        )
    },
    {
        "name": "delay",
        "example_with": '{"DelayOn":{"Feedback":0.32,"Delay":380.0,"Mix":0.42}}',
        "prompt_with": (
            f"基于 {song_style} 与 {chat_message} 生成延迟器参数。"
            "\n参数：Feedback 0.00~1.00；Delay 1.00~400.00 ms；Mix 0.00~1.00。"
            "\n风格映射："
            "\n- ‘ambient / post-rock / cinematic’：Delay 300~400ms (1/2 或 dotted 1/4 感)，Feedback 0.45~0.70，Mix 0.35~0.55。"
            "\n- ‘modern lead sustain’：Delay 280~360ms，Feedback 0.30~0.50，Mix 0.25~0.40。"
            "\n- ‘tight rhythmic / prog metal’：Delay 90~160ms (slap / support)，Feedback 0.18~0.30，Mix 0.12~0.25。"
            "\n- ‘blues/expressive subtle’：Delay 180~260ms，Feedback 0.22~0.38，Mix 0.15~0.28。"
            "\n中性默认：Delay 320ms, Feedback 0.35, Mix 0.30。"
            '\n输出 JSON: {"DelayOn":{"Feedback":<float>,"Delay":<float>,"Mix":<float>}}'
            "\n数值 2~3 位小数，只输出 JSON。"
        )
    },
    {
        "name": "reverb",
        "example_with": '{"ReverbOn":{"Size":0.40,"Damping":0.32,"Width":0.70,"Mix":0.36}}',
        "prompt_with": (
            f"基于 {song_style} 与 {chat_message} 生成混响器参数。"
            "\n参数范围：Size 0.00~1.00（空间尺度），Damping 0.00~1.00（高频吸收），Width 0.00~1.00（立体扩展），Mix 0.00~1.00。"
            "\n风格映射："
            "\n- ‘ambient / cinematic / atmospheric_post_rock’：Size 0.65~0.90，Damping 中等(0.40~0.60)，Width 0.70~0.95，Mix 0.40~0.60。"
            "\n- ‘tight prog / metal lead’：Size 0.25~0.45，Damping 0.35~0.55，Width 0.55~0.75，Mix 0.18~0.32。"
            "\n- ‘vintage blues / classic rock’：Size 0.30~0.55，Damping 0.45~0.70，Width 0.50~0.70，Mix 0.20~0.35。"
            "\n- ‘fusion articulate’：Size 0.25~0.40，Damping 0.30~0.50，Width 0.55~0.75，Mix 0.15~0.28。"
            "\n默认中性：Size 0.40, Damping 0.32, Width 0.70, Mix 0.30。"
            '\n输出 JSON: {"ReverbOn":{"Size":<float>,"Damping":<float>,"Width":<float>,"Mix":<float>}}'
            "\n只输出 JSON。"
        )
    },
    {
        "name": "chorus",
        "example_with": '{"ChorusOn":{"Delay":0.028,"Depth":0.30,"Frequency":0.55,"Width":0.032}}',
        "prompt_with": (
            f"基于 {song_style} 与 {chat_message} 生成合唱(Chorus)参数。"
            "\n参数范围：Delay 0.010~0.050；Depth 0.00~1.00；Frequency 0.05~2.00；Width 0.010~0.050。"
            "\n风格映射："
            "\n- ‘80s vibe / ambient shimmer’：Depth 0.45~0.70，Delay 0.028~0.040，Frequency 0.25~0.60，Width 0.030~0.045。"
            "\n- ‘subtle thickening (modern lead)’：Depth 0.15~0.35，Delay 0.022~0.030，Frequency 0.35~0.85，Width 0.020~0.032。"
            "\n- ‘clean melodic chorus pop’：Depth 0.35~0.55，Delay 0.030~0.042，Frequency 0.40~0.90，Width 0.028~0.040。"
            "\n- ‘avoid modulation (dry preference)’：Depth <0.12，Mix 可由后端控制（此处不含 Mix 字段）。"
            "\n默认：Delay 0.028，Depth 0.30，Frequency 0.55，Width 0.032。"
            '\n输出 JSON: {"ChorusOn":{"Delay":<float>,"Depth":<float>,"Frequency":<float>,"Width":<float>}}'
            "\n只输出 JSON。"
        )
    },
    {
        "name": "flanger",
        "example_with": '{"FlangerOn":{"Delay":0.012,"Depth":0.40,"Feedback":0.22,"Frequency":0.55,"Width":0.012}}',
        "prompt_with": (
            f"基于 {song_style} 与 {chat_message} 生成镶边(Flanger)参数。"
            "\n参数：Delay 0.00100~0.02000；Depth 0.00~1.00；Feedback 0.00~0.50；Frequency 0.05~2.00；Width 0.001~0.020。"
            "\n风格映射："
            "\n- ‘dramatic jet / classic flanger sweep’：Depth 0.55~0.85，Feedback 0.30~0.45，Delay 0.010~0.016。"
            "\n- ‘subtle movement for ambient’：Depth 0.15~0.35，Feedback 0.08~0.20，Delay 0.006~0.012，Frequency 0.15~0.40。"
            "\n- ‘rhythmic metallic texture’：Depth 0.35~0.55，Feedback 0.18~0.30，Frequency 0.50~0.90。"
            "\n- ‘minimal coloring’：Depth 0.08~0.18，Feedback 0.05~0.12，Frequency 0.20~0.50。"
            "\n默认：Delay 0.012, Depth 0.40, Feedback 0.22, Frequency 0.55, Width 0.012。"
            '\n输出 JSON: {"FlangerOn":{"Delay":<float>,"Depth":<float>,"Feedback":<float>,"Frequency":<float>,"Width":<float>}}'
            "\n只输出 JSON。"
        )
    },
    {
        "name": "equalization",
        "example_with": '{"EqualiserOn":{"100hz":-1.5,"200hz":0.0,"400hz":0.5,"800hz":1.0,"1600hz":1.2,"3200hz":2.0,"6400hz":1.8,"Level":0.0}}',
        "prompt_with": (
            f"基于 {song_style} 与 {chat_message} 生成均衡(EQ) 7 段近似示例（100/200/400/800/1600/3200/6400 Hz + Level）。"
            "\n各频段范围：-15.00~15.00 dB。Level 为整体补偿（-15~15）。"
            "\n风格映射："
            "\n- ‘tight metal / djent’：100hz -4~-2（收紧低频），200hz -3~-1 控浑浊，400hz -2~0，800hz 0~+1，1600/3200hz +1~+3 增存在与攻击，6400hz +1~+4 清晰；Level 视需求微调。"
            "\n- ‘blues / vintage rock’：100hz -1~+1，200hz 0~+1 温暖，400hz +0.5~+1.5（躯干），800hz -0.5~0.5，1600hz +0.5~+1.5，3200hz +1~+2，6400hz +0.5~+1.5。"
            "\n- ‘ambient / atmospheric’：极少极端削增，更多轻度雕刻：100hz -2~0，200hz -1~+0.5，400hz 0~+0.5，800hz 0~+0.8，1600hz +0.5~+1.2，3200hz +1~+2.2，6400hz +1~+2.5。"
            "\n- ‘fusion articulate’：低频轻微收紧，存在与高频适度提升。"
            "\n若无法确定，输出中性微雕：全部 0。"
            '\n输出 JSON: {"EqualiserOn":{"100hz":<float>,"200hz":<float>,"400hz":<float>,"800hz":<float>,"1600hz":<float>,"3200hz":<float>,"6400hz":<float>,"Level":<float>}}'
            "\n只输出 JSON。"
        )
    },
    {
        "name": "phase",
        "example_with": '{"PhaserOn":{"Depth":0.70,"Feedback":0.55,"Frequency":0.60,"Width":1200}}',
        "prompt_with": (
            f"基于 {song_style} 与 {chat_message} 生成相位(Phaser)参数。"
            "\n参数范围：Depth 0.00~1.00；Feedback 0.00~0.90；Frequency 0.05~2.00；Width 50~3000 (表示扫频跨度单位假设为 Hz 区间或内部刻度)。"
            "\n风格映射："
            "\n- ‘psychedelic / classic phase swirl’：Depth 0.60~0.85，Feedback 0.40~0.70，Frequency 0.30~0.70，Width 1200~2200。"
            "\n- ‘subtle motion (modern clean / ambient)’：Depth 0.20~0.40，Feedback 0.15~0.35，Frequency 0.20~0.50，Width 800~1400。"
            "\n- ‘pronounced modulation leads’：Depth 0.50~0.70，Feedback 0.30~0.55，Frequency 0.40~0.90，Width 1600~2400。"
            "\n- ‘minimal coloring’：Depth 0.10~0.25，Feedback 0.05~0.15，Frequency 0.25~0.45，Width 600~1200。"
            "\n默认：Depth 0.70, Feedback 0.55, Frequency 0.60, Width 1500。"
            '\n输出 JSON: {"PhaserOn":{"Depth":<float>,"Feedback":<float>,"Frequency":<float>,"Width":<int>}}'
            "\n只输出 JSON。"
        )
    }
]

final_result = {}


# 定义向量余弦相似度计算函数
def vector_cosine_similarity(vec1, vec2):
    """计算两个向量的余弦相似度"""
    dot_product = np.dot(vec1, vec2)
    norm_vec1 = np.linalg.norm(vec1)
    norm_vec2 = np.linalg.norm(vec2)
    if norm_vec1 == 0 or norm_vec2 == 0:
        return 0.0
    return dot_product / (norm_vec1 * norm_vec2)


# 初始化三个参考数据源
audio_vector_params = []  # audio_vector 表的参考参数
preference_params = []  # music_responses 表中用户偏好参数
user_text_reference = {
    "style_tags": song_style,
    "description": guitar_features
}  # 用户输入和文本分析结果

# 获取音频向量参考参数（无论记忆模块是否开启）
if file_path and file_path.strip() and vector is not None:
    # 查询audio_vector表
    audio_cursor.execute("SELECT Parameters, Vector FROM audio_vector")
    audio_rows = audio_cursor.fetchall()

    for audio_row in audio_rows:
        audio_params = audio_row[0]
        audio_vector_str = audio_row[1]

        try:
            # 计算音频向量相似度
            db_vector = np.array([float(x.strip()) for x in audio_vector_str.split(',')])
            similarity = vector_cosine_similarity(vector, db_vector)

            if similarity > 0.3:  # 相似度阈值
                audio_vector_params.append(json.loads(audio_params))
                print(f"音频向量相似度: {similarity:.4f}, 参数数量: {len(audio_vector_params)}")
        except (ValueError, TypeError) as e:
            print(f"处理音频向量参数时出错: {e}")

# 如果记忆模块开启，获取用户偏好参考参数
if memoryEnabled == "true":
    # 查询music_responses表
    cursor.execute("SELECT SongName, Parameters, Preferences, Style, Feature FROM music_responses")
    preference_rows = cursor.fetchall()

    print(f"查询到 {len(preference_rows)} 条用户偏好记录")

    # 直接使用result2中的tags和description作为检索内容
    target_tags = set(result2.get("tags", []))
    target_description = " ".join(result2.get("description", []))
    for pref_row in preference_rows:
        song_name = pref_row[0]
        param_str = pref_row[1]
        preference = pref_row[2]
        style_str = pref_row[3]
        feature_str = pref_row[4]

        print(f"处理记录: 歌曲={song_name}, 偏好={preference}")

        # 检查歌曲名是否和当前用户输入相同，相同则跳过
        if song_name == chat_message:
            print(f"跳过相同歌曲: {song_name}")
            continue

        try:
            if param_str and param_str.strip():
                param_data = json.loads(param_str)
                print(f"解析参数: {type(param_data)} - {param_data}")

                # 解析历史记录的风格标签和描述特征
                try:
                    hist_style = json.loads(style_str) if style_str else []
                    hist_features = json.loads(feature_str) if feature_str else []
                except json.JSONDecodeError:
                    hist_style = []
                    hist_features = []

                # 计算相似度
                tags_similarity = jaccard_similarity(set(target_tags), set(hist_style)) if target_tags and hist_style else 0.0
                
                # 改进的描述相似度计算：考虑多个句子的匹配程度
                if target_description and hist_features:
                    # 计算每个历史描述句子与目标描述的相似度
                    desc_similarities = []
                    for hist_feature in hist_features:
                        if hist_feature.strip():  # 忽略空句子
                            sim = text_similarity(target_description, hist_feature)
                            desc_similarities.append(sim)
                    
                    # 取最大相似度作为描述相似度（至少有一个句子匹配就算有效）
                    desc_similarity = max(desc_similarities) if desc_similarities else 0.0
                    
                    # 如果历史记录有多个描述句子，给予额外奖励
                    if len(hist_features) > 1:
                        desc_similarity = min(desc_similarity * 1.1, 1.0)  # 最高不超过1.0
                else:
                    desc_similarity = 0.0
                
                # 加权总体相似度：标签相似度权重0.6，描述相似度权重0.4
                overall_similarity = tags_similarity * 0.6 + desc_similarity * 0.4
                
                print(f"相似度计算 - 标签相似度: {tags_similarity:.4f}, 描述相似度: {desc_similarity:.4f}, 总相似度: {overall_similarity:.4f}")
                
                # 只有当相似度大于0.15时才处理这个偏好记录
                if overall_similarity > 0.3:
                    # 如果偏好为空，默认为accept
                    actual_preference = preference if preference else "accept"

                    if actual_preference == "accept":
                        # accept参数优先级最高
                        preference_params.insert(0, {
                            "type": "accept",
                            "parameters": param_data,
                            "similarity": overall_similarity
                        })
                        print(f"添加accept参数到列表开头 (相似度: {overall_similarity:.4f})")
                    elif actual_preference == "edit":
                        # edit参数次之，放在accept后面
                        if not any(p["type"] == "edit" for p in preference_params):
                            preference_params.append({
                                "type": "edit",
                                "parameters": param_data,
                                "similarity": overall_similarity
                            })
                            print(f"添加edit参数 (相似度: {overall_similarity:.4f})")
                    elif actual_preference == "reject":
                        # reject参数单独存储，用于避免
                        preference_params.append({
                            "type": "reject",
                            "parameters": param_data,
                            "similarity": overall_similarity
                        })
                        print(f"添加reject参数 (相似度: {overall_similarity:.4f})")
                else:
                    print(f"跳过记录，相似度不足: {overall_similarity:.4f}")
        except json.JSONDecodeError as e:
            print(f"处理用户偏好参数时出错: {e}")
        except Exception as e:
            print(f"处理记录时发生错误: {e}")

# 初始化偏好参数列表
# similar_songs 和 resu 已被新的三参考系统替代，不再需要

# 打印信息
print("相似歌曲搜索功能已禁用，使用新的三参考系统")
print(f"收集到的偏好参数: {len(preference_params)} 条")
print(f"音频向量参数: {len(audio_vector_params)} 条")

# 无论记忆模块是否开启，文本分析结果始终包含在参考中
user_text_ref = f"""
用户文本分析结果:
风格标签: {json.dumps(song_style, ensure_ascii=False)}
描述特征: {json.dumps(guitar_features, ensure_ascii=False)}
文本权重: {text_Weight if text_Weight else "0.5"}
"""

# 创建系统提示模板，包含三个参考类型
system_prompt_template = f"""
你是音效参数专家。输入可能包含：
- 歌曲名（若有）
- 描述 / 情绪 / 场景
- 风格标签 / 技巧 / 语义关键词
文本：[{chat_message}]
外部风格标签（可选）：{song_style}

参考数据：
1. 文本分析参考（始终可用）:
   {user_text_ref}
2. 音频向量参考（{"相似度>0.3时启用" if file_path and file_path.strip() and vector is not None else "未检测到音频文件"}）:
   {json.dumps(audio_vector_params, ensure_ascii=False) if audio_vector_params else "[]"}
3. 用户偏好参考（{"已启用" if memoryEnabled == "true" else "记忆模块未开启"}）:
   {json.dumps(preference_params, ensure_ascii=False) if preference_params else "[]"}

权重设置：
- 文本分析权重: {text_Weight if text_Weight else "0.5"}
- 音频向量权重: {audio_Weight if audio_Weight else "0.3"}
- 用户偏好权重: {preference_Weight if preference_Weight else "0.2"}

任务：只输出 10 个音效模块启用与否的固定顺序 JSON（yes/no），无其它字符：
{{
  "overload": "yes|no",
  "distortion": "yes|no",
  "delay": "yes|no",
  "reverb": "yes|no",
  "compression": "yes|no",
  "phase": "yes|no",
  "chorus": "yes|no",
  "flanger": "yes|no",
  "equalization": "yes|no",
  "noise_gate": "yes|no"
}}

优先级顺序（高到低）：
显式文本锁定 > 清洁强约束(acoustic|fingerstyle|unplugged|pure clean) > 参考硬触发(hard ref) > 参考普遍开启(prevalent ref) > 风格基线/标签推导 > 技巧/语义补强 > 低密度补全/回退

流程：
0) 标题直判锁定
0.R1) 参考模块硬触发解析 (hard ref)
0.R2) 参考模块普遍开启统计 (prevalent ref, >=60% 默认阈值，可调为 prevalence_threshold=0.60)
0.1) 冲突纠偏 SC1~SC8
0.2) 显式效果锁定 (locked_text)
1) 描述与风格标签补全（含风格基线）
2) 技巧 / 语义关键词补强
3) 互斥 / 约束裁剪
4) 噪声门判定
6A) 基线 & 单一调制 / 低密度补全
5) 回退（最小集合）
6) 未决填充 no + 调制互斥终检（显式豁免 + locked_ref 优先）

=== 参考模块解析规则 ===
参考输入中可能出现形如 XXXOn 的键。按下列映射与级别处理：
模块->效果映射：
  CompressorOn -> compression
  DriverOn / DistortionOn / HighGainOn / PreampHighGainOn / FuzzOn -> distortion（DriverOn 有阈值）
  ScreamerOn / OverdriveOn / BoostOn / ODOn -> overload
  DelayOn -> delay
  ReverbOn -> reverb
  ChorusOn -> chorus
  PhaserOn -> phase
  FlangerOn -> flanger
  EqualiserOn -> equalization
  NoiseGateOn / GateOn -> noise_gate

0.R1 硬触发 (hard ref) 逻辑：
  - DriverOn:
      若存在 Distortion/Gain/Drive 参数 >=0.40 -> distortion=yes (locked_ref)
      若 0.20 <= 数值 <0.40 -> overload=yes (仅轻推动, soft_ref)，不直接触发 distortion
  - DistortionOn / HighGainOn / PreampHighGainOn / FuzzOn -> distortion=yes (locked_ref)
  - FuzzOn 始终视为失真硬触发，忽略 mid_gain 抑制
  - ScreamerOn / OverdriveOn / BoostOn / ODOn -> overload=yes (soft_ref；若与硬失真同在，可并存)
  - CompressorOn -> compression=yes (soft_ref；可被显式 no 或清洁强约束覆盖)
  - ReverbOn: 若 Mix>0.02 -> reverb=yes (soft_ref 但强可信)；Mix<=0.02 -> weak_ref（后续可被裁剪）
  - DelayOn: 若 Mix>0.05 且 Delay>0 -> delay=yes (soft_ref)；否则 weak_ref
  - ChorusOn / PhaserOn / FlangerOn：加入调制候选；若多个 On，先记录，最终互斥处理
  - EqualiserOn -> equalization=yes (soft_ref)
  - NoiseGateOn / GateOn -> noise_gate=yes (soft_ref；若最终失真链不足，可回退为 no)
  - 同时存在 ScreamerOn + DriverOn 且 DriverOn Distortion>=0.40 -> overload=yes + distortion=yes
  - mid_gain|crunch 不再否决 locked_ref 的 distortion
  - 清洁强约束(acoustic|fingerstyle|unplugged|pure clean) 仍可覆盖失真相关：distortion=no overload=no noise_gate=no（除显式文本直接要求失真）

0.R2 普遍开启统计 (prevalent ref)：
  对每一效果类别统计参考列表中对应"On"模块的开启比例：
    prevalence = (该效果相关 On 模块出现次数) / (参考条目数量)
  若 prevalence >= prevalence_threshold(默认0.60) 且该效果尚未被显式 / 清洁 / 硬触发明确为 no：
    将该效果标记为 yes (ref_prevalent，soft_ref)
  调制（chorus/phase/flanger）如多项同时达到普遍开启，后续仍按 chorus > phase > flanger 优先级单一保留（若无显式多锁）
  对 delay/reverb 若普遍开启但多数实例 Mix 近 0，可降级为 weak_prevalent，可在后续裁剪

=== 三个参考类型的特殊处理规则 ===
1. 文本分析参考（权重: {text_Weight if text_Weight else "0.5"}）:
   - 基于风格标签和描述特征进行风格推断
   - 直接影响基础模块启用决策（如ambient->reverb+delay，metal->distortion）
   - 作为参数生成的基础参考

2. 音频向量参考（权重: {audio_Weight if audio_Weight else "0.3"}）:
   {"- 当相似度>0.3时启用，提供高质量标准参数参考" if audio_vector_params else "- 当前无可用音频向量参考"}
   - 参数值经过验证和优化，适合当前音频风格
   - 优先使用accept类型的参数数据

3. 用户偏好参考（权重: {preference_Weight if preference_Weight else "0.2"}）:
   - accept类型：高优先级，必须优先参考
   - edit类型：中优先级，包含用户修改后的参数建议
   - reject类型：低优先级，必须避免重复
   - 综合参考时：{"有用户历史数据" if memoryEnabled == "true" and preference_params else "无用户历史数据"}

用户偏好数据说明：
{json.dumps(preference_params, ensure_ascii=False) if preference_params else "无用户历史数据可用"}

特殊规则：
- 如果用户偏好中有accept类型参数，优先参考accept数据
- 如果用户偏好中有reject类型参数，避免生成相同参数
- 如果用户偏好中有edit类型参数，在accept基础上进行调整

显式效果锁定 (0.2)：
  匹配："with a/an <effect> effect" "<effect> effect" "use <effect>" "<effect> sound/tone"
  effect: overdrive/drive/boost(=overload), distortion, delay, reverb, compression/comp, chorus, flanger, phaser(=phase), eq/eqing/equalizer(=equalization), gate(=noise_gate)
  -> 设 yes + locked_text；仅清洁/噪声明显纠偏可改。

风格 / 标签与语义：
- metal/djent/thrash/death/core/grind/heavy (+ chug|palm mute|tight|high gain 可选) -> distortion=yes；若 boost/drive/overdrive/tight/chug -> overload=yes
- mid_gain|mid-gain|crunch|classic_rock|blues|vintage|hard_rock -> overload=yes（轻） distortion=no（若无 locked_ref）
- ambient|atmospheric|post-rock|shoegaze|cinematic -> reverb=yes delay=yes；dreamy|lush->chorus；psychedelic|spacey|swirl->phase
- acoustic|fingerstyle|folk|unplugged -> reverb=yes compression=yes equalization=yes；distortion/overload/noise_gate=no
- melodic|emotional|lyrical|sustain|solo|lead -> delay=yes；reverb=yes（若未）
- boost|overdrive|screamer|od -> overload=yes
- fuzz|wall|massive|dense|saturated -> distortion=yes
- lush|dreamy|shimmer|80s -> chorus=yes
- psychedelic|spacey|swirl -> phase=yes（若 chorus 非显式锁定）
- jet|swoosh|metallic -> flanger=yes
- ambient|space|swell|pad|ethereal -> reverb+delay=yes
- hiss|noise|gate|gating|unwanted noise 且 distortion=yes -> noise_gate=yes
- melodic_bassline -> compression=yes equalization=yes
- clean_to_distorted -> 无高增益词：overload=yes（轻） distortion保持 no（若无 locked_ref）

风格基线 (grunge | alternative_rock | clean_to_distorted | (rock 且无高增益词)):
- distortion 未被高增益触发且非 locked_ref -> overload=yes compression=yes reverb=yes equalization=yes
- melodic_bassline 额外确保 compression & equalization=yes

技巧补强与细化：
- tapping/sweep/shred/fast/legato + 高增益语境 -> distortion=yes
- chug/djent/palm mute/tight/percussive -> distortion=yes；若出现 drive/overdrive/boost -> overload=yes
- wall/massive/dense/saturated/fuzz -> distortion=yes
- clean sparkle/glassy -> compression=yes
- droning/drone -> reverb=yes；有旋律词且 delay 未设 -> delay=yes
- 噪声词 (hiss/noise/gating...) + 失真链 -> noise_gate=yes

互斥 / 约束：
- 调制仅一：chorus > phase > flanger（显式锁定多保留；否则按优先级保留最高来源：locked_text > locked_ref > ref_prevalent > soft_ref > weak_ref）
- distortion=no 且 overload=no -> noise_gate=no
- distortion=yes 且 chug|djent|tight|palm mute|boost -> overload=yes & noise_gate=yes
- acoustic|fingerstyle|unplugged|pure clean -> distortion/overload/noise_gate=no（即使 locked_ref，但显式文本要求失真可豁免）
- mid_gain|crunch 且无高增益词 -> distortion=no（若非 locked_ref）
- overload 不推导 distortion；轻推动不触发噪声门

噪声门：
noise_gate=yes 当：
  distortion=yes 且 metal|djent|chug|tight|palm mute|thrash|death|core|high gain|heavy
  或 hiss|noise|gate|gating|unwanted noise
参数细化：
  若 distortion 来源仅 DriverOn 且 Distortion<0.55 且无上述高增益/噪声词 -> noise_gate=no

6A 单一调制 / 低密度补全：
- 若仅 1 调制=yes 且未声明 dry：
  equalization=yes；reverb=yes；compression=yes（若含 grunge|alternative_rock|rock|mid_tempo|melodic|melodic_bassline|clean_to_distorted）
  overload=yes（若基线条件成立且 distortion=no）
- 若最终 yes 数 <2 且非 dry -> 至少 equalization=yes

回退：
- 全部 no/未定 -> equalization=yes
- lead/solo/melodic/emotional 且 delay 未设 -> delay=yes
- ambient|space|atmospheric 且 reverb 未设 -> reverb=yes
- 仍 <2 yes 且非 dry -> equalization=yes

终检：
- 未定->no
- 调制互斥（显式豁免 + locked_ref 优先）
- locked_ref 的 distortion 不被 mid_gain/crunch 否决
- distortion=no 且 overload=no -> noise_gate=no
- 若 distortion=yes 但来源 locked_ref 且(DriverOn Distortion 0.40~0.55) 且无高增益/噪声语义 -> noise_gate=no
- 禁止额外文本

附加：
- 显式指令优先
- 情绪词不触发增益或噪声门
- clean_to_distorted 默认轻推动
- 单一调制不孤岛：需 EQ+Reverb（+Compression 视风格）
- 参考硬触发优先于普遍开启；普遍开启为 soft_ref 可被更高优先级覆盖
- 普遍开启统计：prevalence >=0.60（可调），不足阈值不强制
- weak_ref（Mix≈0 / 参数近零）可在互斥或终检阶段被移除
- ScreamerOn + DriverOn (Distortion>=0.40) -> overload=yes + distortion=yes
- FuzzOn 永远视为 distortion=yes（硬触发）
- 不因单纯 prevalent equalization 而否定 explicit no（若显式要求 no，可保持 no）

输出：仅输出 JSON（键顺序固定）：
{{
  "overload": "yes|no",
  "distortion": "yes|no",
  "delay": "yes|no",
  "reverb": "yes|no",
  "compression": "yes|no",
  "phase": "yes|no",
  "chorus": "yes|no",
  "flanger": "yes|no",
  "equalization": "yes|no",
  "noise_gate": "yes|no"
}}
"""

# 使用更新后的系统提示模板
print(f"system_prompt_template:{system_prompt_template}")
system_prompt = system_prompt_template
user_prompt1 = chat_message

# 保存系统消息
system_message = {"role": "system", "content": system_prompt}
conversation_history.append(system_message)
# 保存用户消息
user_message = {"role": "user", "content": user_prompt1}
conversation_history.append(user_message)
# 发送请求
response1 = client.chat.completions.create(
    model="deepseek-chat",
    messages=[system_message, user_message],
    stream=False
)
# 保存助手回复
assistant_message = {
    "role": "assistant",
    "content": response1.choices[0].message.content
}
conversation_history.append(assistant_message)

# 获取 response1 响应数据并转换为 JSON
response_content1 = response1.choices[0].message.content
# 提取有效的JSON部分
start_index = response_content1.find("{")
end_index = response_content1.rfind("}") + 1
if start_index != -1 and end_index != -1:
    cleaned_content1 = response_content1[start_index:end_index]
else:
    print("Error: 未找到有效的JSON内容")
    sys.exit(1)

try:
    result1 = json.loads(cleaned_content1)
    print(json.dumps(result1, ensure_ascii=False, indent=2))
except json.JSONDecodeError:
    print(f"Error: 无效的JSON响应: {cleaned_content1}")
    sys.exit(1)

# 使用 for 循环处理不同的音效模块
for effector in effectors:
    effector_name = effector["name"]
    if result1.get(effector_name) == "yes":
        # 构建包含音频向量参考参数的系统提示（无论记忆是否开启）
        audio_ref_info = f"音频向量参考参数: {json.dumps(audio_vector_params, ensure_ascii=False) if audio_vector_params else '[]'}"

        if memoryEnabled == "true":  # 简化条件检查
            system_prompt = f"""
你是一位专业音效调整师。目标：针对当前单一音效模块，基于相似歌曲参考参数 {audio_vector_params} 与用户偏好，输出该模块的 JSON 参数。示例格式（仅参考结构，不参考数值）：{effector["example_with"]}

严格输出要求：
1. 只输出一个 JSON 对象，禁止添加说明文字 / 额外字段 / 前后缀。
2. 若判定模块需要启用：键名使用示例中的 *On 形式（如 CompressorOn、DelayOn）。若判定关闭：使用 *Off（如 CompressorOff）并赋空对象 {{}}。
3. 不要直接照搬示例数值；也不要逐字复刻 {audio_vector_params} 中单条参数值。必须在参考基础上做小幅调整。
4. 只输出与该模块相关的键，禁止额外模块或多余层级。

参考数据（用户偏好参数，多条 JSON 片段或数组形式）：{preference_params}
{audio_ref_info}

解析规则：
- 识别该模块的 On/Off：出现 <ModuleName>On 视为开启；<ModuleName>Off 视为关闭。
- 模块名称与本次处理对象由外部上下文 effector 决定，不需你猜测其它模块。
- 若参考中出现多个版本（如 CompressorOn 与 CompressorOff 混杂），统计：On_count 与 Off_count。
  - On_count > Off_count → 判定开启
  - Off_count > On_count → 判定关闭
  - 平票或均未出现 → 进入"启发式判定"

启发式判定（仅在平票或无信息时适用）：
- 若模块属于常规基础链路（例如均衡、压缩、轻度空间处理）且该风格常见 → 可开启
- 若模块属于调制（chorus/phaser/flanger）且参考无迹象 → 默认关闭
- 若无明确风格或信息不足 → 默认关闭（除非是 EQ 等基础模块）

参数生成逻辑（仅当判定开启）：
1. 参考所有 On 样本该模块的参数值集合（来自{audio_vector_params}），计算每个参数的基准值（默认使用中位数；若无法解析则使用第一条 On 样本）。
2. 基于基准值生成新值：保持"合理、接近、不过度漂移"：
   - 0~1 归一化参数：偏移幅度 ±(0.03~0.10)，裁剪到 [0,1]
   - 时间参数（ms、宽度等）：±5%~12%（若原值极小 <1，可加一个最小微调 0.001~0.01）
   - dB 参数：±(5%~15%) 或 ±(1~3 dB) 取更小；阈值类（极负数）可在 ±(2~6 dB)
   - 比率（Ratio）：若 <10 → ±(0.2~0.8)；若 ≥10 → ±(0.5~2.0)，不低于 1
   - 延迟时间 Delay：保持在 1.00~400.00 范围内
   - 仅整数参数（如某些 Width）可四舍五入
3. 确保不与基准值完全相同；若随机漂移后仍相同则再做一次微小增减 (最小步进 0.01 或 1 单位)。
4. 保持参数间逻辑一致（如 Attack 不应远大于 Release 若语义不符；若无规则忽略）。
5. 若{audio_vector_params}没有任何 On 样本但启发式判定开启 → 使用该模块的中性默认：
   - Compressor: Threshold=-24, Ratio=3, Attack=0.010~0.050, Release=0.120~0.250, Makeup=4, Mix=0.70
   - Distortion/Driver: Distortion=0.55, Volume=-12
   - Overdrive/Screamer: Drive=0.55, Tone=0.52, Level=-12
   - Delay: Feedback=0.35, Delay=320, Mix=0.30
   - Reverb: Size=0.40, Damping=0.30, Width=0.70, Mix=0.30
   - Chorus: Delay=0.028, Depth=0.30, Frequency=0.60, Width=0.030
   - Flanger: Delay=0.012, Depth=0.40, Feedback=0.22, Frequency=0.55, Width=0.012
   - Phaser: Depth=0.60, Feedback=0.40, Frequency=0.60, Width=1500
   - EQ: 全频段=0（Level=0）
   - NoiseGate（若适用）：Threshold=-50~ -60, Release=0.10~0.25 （仅示例，若模块定义不同可忽略）

关闭状态：
- 输出 {{"<ModuleName>Off": {{}}}} 不包含参数键。
- 不输出任何与参数取值相关的提示。

输出格式：
- 只允许一个最外层键（On 或 Off）
- 所有数值型保持数字类型（不要加引号）；字符串参数原样即可
- 保留 2~3 位小数（整数参数可为 int）

禁止事项：
- 不得输出说明文字、理由、注释
- 不得包含除该模块键以外的任何顶层键
- 不得输出 null / None / NaN / Infinity
- 不得使用与示例完全一样的参数集（数值需有差异）

现在请根据上述规则输出该模块最终 JSON。
"""
        else:
            system_prompt = f"""
你是一位专业音效调整师。基于音频向量参考参数 {audio_ref_info} 和内部通用经验输出该模块的 JSON。示例结构（仅参考格式，不参考数值）：{effector["example_with"]}

判定：
- 若该模块为基础核心（均衡、压缩、主音延迟、主音混响、必要增益级） → 默认开启
- 若为调制/特效（chorus, flanger, phaser）且无风格上下文 → 默认关闭
- 若为高增益相关（distortion/overdrive）且无上下文 → 默认关闭
- 可选策略：如模块名包含 "Equaliser" 则一定开启；"Compressor" 视为可开启；"Delay""Reverb" 可中性轻度开启以提供空间；其余关闭

参考数据：{audio_ref_info}

参数生成逻辑：
1. 参考所有 On 样本该模块的参数值集合（来自{audio_vector_params}），计算每个参数的基准值（默认使用中位数；若无法解析则使用中性默认）。
2. 基于基准值生成新值：保持"合理、接近、不过度漂移"：
   - 0~1 归一化参数：偏移幅度 ±(0.03~0.10)，裁剪到 [0,1]
   - 时间参数（ms、宽度等）：±5%~12%（若原值极小 <1，可加一个最小微调 0.001~0.01）
   - dB 参数：±(5%~15%) 或 ±(1~3 dB) 取更小；阈值类（极负数）可在 ±(2~6 dB)
   - 比率（Ratio）：若 <10 → ±(0.2~0.8)；若 ≥10 → ±(0.5~2.0)，不低于 1
   - 延迟时间 Delay：保持在 1.00~400.00 范围内
   - 仅整数参数（如某些 Width）可四舍五入
3. 若{audio_vector_params}没有任何 On 样本 → 使用该模块的中性默认：
   - Compressor: Threshold=-24, Ratio=3, Attack=0.010~0.050, Release=0.120~0.250, Makeup=4, Mix=0.70
   - Distortion/Driver: Distortion=0.55, Volume=-12
   - Overdrive/Screamer: Drive=0.55, Tone=0.52, Level=-12
   - Delay: Feedback=0.35, Delay=320, Mix=0.30
   - Reverb: Size=0.40, Damping=0.30, Width=0.70, Mix=0.30
   - Chorus: Delay=0.028, Depth=0.30, Frequency=0.60, Width=0.030
   - Flanger: Delay=0.012, Depth=0.40, Feedback=0.22, Frequency=0.55, Width=0.012
   - Phaser: Depth=0.60, Feedback=0.40, Frequency=0.60, Width=1500
   - EQ: 全频段=0（Level=0）

输出要求：
1. 只输出 JSON，一个顶层键（On 或 Off），禁止添加任何说明文字或额外字段。
2. 数值参数保持数字类型，不添加引号。
3. 参数范围符合模块要求（如 Delay 时间 1.00~400.00）。
4. 禁止输出 null、None、NaN 或 Infinity。
5. 若判定为关闭，则输出如 {{"CompressorOff": {{}}}}。

现在请根据上述规则输出该模块 JSON。
"""
        print(f"system_prompt:{system_prompt}")
        user_prompt = effector["prompt_with"] + effector["example_with"]
        # 保存系统消息
        system_message = {"role": "system", "content": system_prompt}
        conversation_history.append(system_message)
        # 保存用户消息
        user_message = {"role": "user", "content": user_prompt}
        conversation_history.append(user_message)
        # 发送请求
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[system_message, user_message],
            stream=False
        )
        # 保存助手回复
        assistant_message = {
            "role": "assistant",
            "content": response.choices[0].message.content
        }
        conversation_history.append(assistant_message)

        # 获取响应数据并转换为 JSON
        response_content = response.choices[0].message.content
        # 去除前后的代码块标记和换行
        cleaned_content = response_content.replace("```json", "").replace("```", "").strip()
        try:
            result = json.loads(cleaned_content)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            final_result.update(result)
        except json.JSONDecodeError:
            print(f"Error: 无效的JSON响应: {cleaned_content}")
            sys.exit(1)
    elif result1.get(effector_name) == "no":
        if effector_name == "compression":
            final_result["CompressorOff"] = {"Threshold": "-128.00", "Ratio": "1", "Attack": "0.00", "Release": "0.00",
                                             "Makeup": "-12.00", "Mix": "0.00"}
        elif effector_name == "distortion":
            final_result["DriverOff"] = {"Distortion": "0.00", "Volume": "-64.0"}
        elif effector_name == "overload":
            final_result["ScreamerOff"] = {"Drive": "0.00", "Tone": "0.00", "Level": "-64.0000000"}
        elif effector_name == "delay":
            final_result["DelayOff"] = {"Feedback": "0.00", "Delay": "1.00", "Mix": "0.00"}
        elif effector_name == "reverb":
            final_result["ReverbOff"] = {"Size": "0.00", "Damping": "0.00", "Width": "0.00", "Mix": "0.00"}
        elif effector_name == "chorus":
            final_result["ChorusOff"] = {"Delay": "0.010", "Depth": "0.00", "Frequency": "0.05", "Width": "0.010"}
        elif effector_name == "flanger":
            final_result["FlangerOff"] = {"Delay": "0.00100", "Depth": "0.00", "Feedback": "0.00", "Frequency": "0.05",
                                          "Width": "0.001"}
        elif effector_name == "equalization":
            final_result["EqualiserOff"] = {"100hz": "0.00", "200hz": "0.00", "400hz": "0.00", "800hz": "0.00",
                                            "1600hz": "0.00", "3200hz": "0.00", "6400hz": "0.00", "Level": "0.00"}
        elif effector_name == "phase":
            final_result["PhaserOff"] = {"Depth": "0.00", "Feedback": "0.00", "Frequency": "0.05", "Width": "50"}

# 将最终结果转换为字符串
result_str = json.dumps(final_result, ensure_ascii=False)
# 打印相关信息
print(f"输入的歌曲名称: {chat_message}")
print(f"对应的风格和特点:{result2_str}")
print(f"对应的参数:{result_str}")
print("-" * 50)
# 将列表转换为JSON字符串
song_style_str = json.dumps(song_style, ensure_ascii=False)
guitar_features_str = json.dumps(guitar_features, ensure_ascii=False)

print(f"完整的对话历史：{conversation_history}")
# 系统提示
system_prompt3 = f'''
You are a professional intelligent music effects assistant with extensive knowledge in music production and audio processing. Your role is to:

1. Analyze user's musical input and technical requirements
2. Generate professional, precise effects parameters based on AI analysis
3. Provide clear explanations of parameter selections with musical theory foundations
4. Customize solutions according to user's style preferences and reference tracks

Based on the complete conversation history which includes:
- Original user input: "{chat_message}"
- AI style analysis: {result2_str}
- Effects module decisions: {result1}
- Generated parameters: {result_str}
- Three-reference system parameters: {preference_params}

Your response must be professional, technically accurate, and educational. Use only English.
'''

user_prompt3 = f'''
Provide a comprehensive analysis of the music style preferences and effects parameters generated. Include:

1. **Musical Style Analysis**
   - Interpret the extracted style tags: {song_style}
   - Explain the genre characteristics and playing techniques
   - Describe the overall sonic texture and mood

2. **Effects Parameters Breakdown**
   - For each enabled effect ({[k for k, v in result1.items() if v == "yes"]}):
     * Explain the purpose and sonic contribution
     * Detail how each parameter affects the sound
     * Describe the musical theory behind the settings

3. **Reference Tracks Analysis**
   - Three-reference system: Text analysis, Audio vectors, User preferences
   - Style characteristics from text analysis: {song_style}
   - User preference parameters: {preference_params}
   - Audio vector parameters: {audio_vector_params}

4. **Parameter Interaction & Signal Flow**
   - Explain how effects work together in the signal chain
   - Describe any complementary or conflicting interactions
   - Explain the order of operations rationale

5. **Fine-tuning Recommendations**
   - Provide 2-3 specific adjustment suggestions for different scenarios
   - Explain what sonic changes each adjustment would produce
   - Give context-specific advice for the identified style

6. **Technical Implementation Notes**
   - Any special considerations for the genre/style
   - Common pitfalls to avoid
   - Alternative parameter approaches for different tones

Your response must start with "Parameter generation complete!\n" followed by a well-structured, professional analysis that demonstrates deep music production expertise.
'''

# 保存系统消息
system_message = {"role": "system", "content": system_prompt3}
# 保存用户消息
user_message = {"role": "user", "content": user_prompt3}
# 发送请求
response3 = client.chat.completions.create(
    model="deepseek-chat",
    messages=[system_message, user_message],
    stream=False
)
response3_content = response3.choices[0].message.content
print(f"清理后的响应：{response3_content}")

# 先将向量转换为字符串格式（与查询代码对应）
vector_str = ','.join(map(str, vector)) if vector is not None else ''

# 数据合法性检查
valid = True
error_msg = []

# 检查歌曲名是否为空
if not chat_message or chat_message.strip() == '':
    valid = False
    error_msg.append("歌曲名不能为空")

# 检查风格和特征字段是否为有效JSON
try:
    if song_style_str:
        json.loads(song_style_str)
    if guitar_features_str:
        json.loads(guitar_features_str)
except json.JSONDecodeError as e:
    valid = False
    error_msg.append(f"风格或特征字段JSON格式错误: {str(e)}")

# 检查向量格式（如果存在）
if vector_str:
    try:
        # 验证能否还原为浮点数列表
        [float(x) for x in vector_str.split(',')]
    except ValueError:
        valid = False
        error_msg.append("音频向量包含非数字值")

if not valid:
    print(f"数据验证失败: {'; '.join(error_msg)}")
    sys.exit(1)

# 将风格结果字符串写入文件
safe_write_file("result1.txt", song_style_str)

# 将特征结果字符串写入文件
safe_write_file("result2.txt", guitar_features_str)

# 将参数结果字符串写入文件
safe_write_file("result.txt", result_str)

# 将参数结果字符串写入文件
safe_write_file("result3.txt", response3_content)

# 关闭数据库连接
conn.close()
audio_conn.close()

# 新增：等待用户输入后再关闭窗口
#input("程序执行完毕，按回车键关闭窗口...")