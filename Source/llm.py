# -*- coding: gbk -*-
from asyncio.windows_events import NULL
import sys
import json
import sqlite3
from openai import OpenAI
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import torch
import librosa
from transformers import Wav2Vec2Processor, Wav2Vec2Model
import numpy as np

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
# 删除表
'''
try:
    cursor.execute("DROP TABLE IF EXISTS music_responses")
    conn.commit()
    print("Table 'music_responses' has been dropped successfully.")
except sqlite3.Error as e:
    print(f"An error occurred while dropping the table: {e}")
'''
# 修改表结构，添加 Vector 字段
cursor.execute('''
CREATE TABLE IF NOT EXISTS music_responses (
    SongName TEXT PRIMARY KEY,
    Style TEXT,
    Feature TEXT,
    Parameters TEXT,
    Vector TEXT  -- 新增字段存储音频向量（以字符串形式）
)
''')
conn.commit()

client = OpenAI(api_key="sk-1b73586fde854a329ec187dc371f53ef", base_url="https://api.deepseek.com")

import platform

if len(sys.argv) > 3:
    if platform.system() == "Windows":
        # Windows命令行通常使用GBK编码
        chat_message = sys.argv[1].encode('cp936').decode('utf-8', errors='replace')
        memoryEnabled = sys.argv[2]
        file_path = sys.argv[3].encode('cp936').decode('utf-8', errors='replace')
    else:
        # Linux/macOS通常使用UTF-8
        chat_message = sys.argv[1]
        memoryEnabled = sys.argv[2]
        file_path = sys.argv[3]
else:
    chat_message = sys.argv[1].encode('cp936').decode('utf-8', errors='replace')
    memoryEnabled = sys.argv[2]
    file_path = ""
print(f"Chat message: {chat_message}")
print(f"memoryEnabled: {memoryEnabled}")
print(f"File path: {file_path}")
if file_path and file_path.strip():
   vector = audio_to_vector(file_path)
   print("音频向量形状：", vector)
else:
    vector = None  # 或空列表[]，根据后续使用场景确定
    print("未提供有效的文件路径，音频向量为空")

# 第二个系统提示
system_prompt2 = f'你是音乐分析师，需要根据用户输入的歌曲名称判断该歌曲的风格(尽量具体)，并描述该歌曲中吉他solo的演奏特点，返回这些信息的 JSON 格式的参数列表，例如: {{"tags": ["tag_1",..."tag_n"],"description":["..."]}}'
user_prompt2 = f'请分析歌曲{chat_message}的风格，并描述该歌曲中吉他solo的演奏特点，请用英文回答'
response2 = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": system_prompt2},
        {"role": "user", "content": user_prompt2},
    ],
    stream=False
)

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
    # print(f"歌曲的风格: {song_style}")
    # print(f"吉他演奏的特点: {guitar_features}")
except json.JSONDecodeError:
    print(f"Error: 无效的JSON响应: {cleaned_content2}")
    sys.exit(1)

# 音效模块列表
effectors = [
    {
        "name": "compression",
        "example_with": '{"CompressorOn": {"Threshold": "0.00", "Ratio": "2", "Attack": 68.12, "Release": "154.34", "Makeup": "21.49", "Mix": "0.25"}}',
        "prompt_with": f'对于歌曲{chat_message}，应该如何设置专业的音效模块中的压缩器的参数，专业的压缩器模块中可能的参数为Ratio，Attack，Release，Makeup和Threshold，Threshold的可能范围为-128.00db~0.00db，Ratio的可能范围为1~100，Attack的可能范围为0.00ms~1.00ms，Release的可能范围为0.00ms~1.00ms，Makeup的可能范围为-128.00db~64.00db,Mix的可能范围为0.00~1.00，请以JSON格式详细输出'
    },
    {
        "name": "distortion",
        "example_with": '{"DriverOn":{"Distortion":"0.68","Volume":-18.4352685}}',
        "prompt_with": f'对于歌曲{chat_message}，应该如何设置专业的音效模块中的失真器的参数，专业的失真器模块中可能的参数为Distortion(Gain)，Volume，Distortion(Gain)的可能范围为0.00~1.00，Volume的可能范围为-64.0000000~0.0000000，请以JSON格式详细输出'
    },
    {
        "name": "overload",
        "example_with": '{"ScreamerOn":{"Drive":"0.81","Tone":"0.52","Level":"-24.3199567"}}',
        "prompt_with": f'对于歌曲{chat_message}，应该如何设置专业的音效模块中的过载器的参数，专业的过载器模块中可能的参数为Drive，Tone，Level，Drive的可能范围为0.00~1.00，Tone的可能范围为0.00~1.00，Level的可能范围为-64.0000000~0.0000000，请以JSON格式详细输出'
    },
    {
        "name": "delay",
        "example_with": ' {"DelayOn":{"Feedback":"0.25","Delay":450.00,"Mix":"0.52"}}',
        "prompt_with": f'对于歌曲{chat_message}，应该如何设置专业的音效模块中的延迟器的参数，专业的延迟器模块中可能的参数为Feedback，Delay，Mix，Feedback的可能范围为0.00~1.00，Delay(Time)的可能范围为1.00ms~400.00ms，Mix的可能范围为0.00~1.00，请以JSON格式详细输出'
    },
    {
        "name": "reverb",
        "example_with": ' {"ReverbOn":{"Size":"0.25","Damping":0.25,"Width":"0.52","Mix":"0.56"}}',
        "prompt_with": f'对于歌曲{chat_message}，应该如何设置专业的音效模块中的混响器的参数，专业的混响器模块中可能的参数为Size，Damping，Width，Mix，Size的可能范围为0.00~1.00，Damping的可能范围为0.00~1.00，Width的可能范围为0.00~1.00，Mix的可能范围为0.00~1.00，请以JSON格式详细输出'
    },
    {
        "name": "chorus",
        "example_with": ' {"ChorusOn":{"Delay":"0.025","Depth":0.25,"Frequency":"0.51","Width":"0.024"}}',
        "prompt_with": f'对于歌曲{chat_message}，应该如何设置专业的音效模块中的合唱器的参数，专业的合唱器模块中可能的参数为Delay，Depth，Frequency，Width，Delay的可能范围为0.010~0.050，Depth的可能范围为0.00~1.00，Frequency的可能范围为0.05~2.00，Width的可能范围为0.010~0.050，请以JSON格式详细输出'
    },
    {
        "name": "flanger",
        "example_with": ' {"FlangerOn":{"Delay":"0.01179","Depth":0.38,"Feedback":"0.25","Frequency":"1.26","Width":"0.011"}}',
        "prompt_with": f'对于歌曲{chat_message}，应该如何设置专业的音效模块中的镶边器的参数，专业的镶边器模块中可能的参数为Delay，Depth，Feedback，Frequency，Width，Delay的可能范围为0.00100~0.02000，Depth的可能范围为0.00~1.00，Feedback的可能范围为0.00~0.50，Frequency的可能范围为0.05~2.00，Width的可能范围为0.001~0.020，请以JSON格式详细输出'
    },
    {
        "name": "equalization",
        "example_with": '{"EqualiserOn":{"100hz":"0.00","200hz":"0.00","400hz":"0.00","800hz":"0.00","1600hz":"0.00","3200hz":"0.00","6400hz":"0.00","Level":"0.00"}}',
        "prompt_with": f'对于歌曲{chat_message}，应该如何设置专业的音效模块中的均衡器的参数，专业的均衡器模块中可能的参数为100hz，200hz，400hz，800hz，1600hz，3200hz，6400hz，Level，100hz的可能范围为-15.00~15.00，200hz的可能范围为-15.00~15.00，400hz的可能范围为-15.00~15.00，800hz的可能范围为-15.00~15.00，1600hz的可能范围为-15.00~15.00，3200hz的可能范围为-15.00~15.00，6400hz的可能范围为-15.00~15.00，Level的可能范围为-15.00~15.00，请以JSON格式详细输出'
    },
    {
        "name": "phase",
        "example_with": ' {"PhaserOn":{"Depth":"1.00","Feedback":"0.70","Frequency":"0.51","Width":"1366"}}',
        "prompt_with": f'对于歌曲{chat_message}，应该如何设置专业的音效模块中的相位器的参数，专业的相位器模块中可能的参数为Depth，Feedback，Frequency，Width，Depth的可能范围为0.00~1.00，Feedback的可能范围为0.00~0.90，Frequency的可能范围为0.05~2.00，Width的可能范围为50~3000，请以JSON格式详细输出'
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

# 直接使用result2中的tags和description作为检索内容
target_tags = set(result2.get("tags", []))
target_description = " ".join(result2.get("description", []))

# 从数据库中获取所有歌曲信息并计算相似度（包含向量）
cursor.execute("SELECT SongName, Style, Feature, Parameters, Vector FROM music_responses")
rows = cursor.fetchall()
similar_songs = []

for index, row in enumerate(rows, start=1):
    song_name = row[0]
    style_str = row[1]
    feature_str = row[2]
    parameter_str = row[3]
    vector_str = row[4]  # 获取数据库中的音频向量字符串
    
    try:
        style = json.loads(style_str)
        feature = json.loads(feature_str)

        # 计算标签相似度
        tags = set(style)
        tag_similarity = jaccard_similarity(target_tags, tags)

        # 计算描述相似度
        description = " ".join(feature)
        desc_similarity = text_similarity(target_description, description)

        # 计算向量相似度（如果file_path不为空且向量存在）
        vector_similarity = 0.0
        if file_path and file_path.strip() and vector_str:
            try:
                # 将数据库中的向量字符串转换为numpy数组
                db_vector = np.array([float(x.strip()) for x in vector_str.split(',')])
                # 计算与目标音频向量的余弦相似度
                vector_similarity = vector_cosine_similarity(vector, db_vector)
            except (ValueError, TypeError) as e:
                print(f"处理歌曲 {song_name} 的向量时出错: {e}")

        # 综合相似度（根据是否有向量调整权重）
        if file_path and file_path.strip() and vector_str:
            # 有音频向量时，增加向量相似度的权重
            similarity = 0.3 * tag_similarity + 0.2 * desc_similarity + 0.5 * vector_similarity
        else:
            # 无音频向量时使用原权重
            similarity = 0.7 * tag_similarity + 0.3 * desc_similarity

        if similarity > 0.2:
            similar_songs.append((song_name, similarity, style_str, feature_str, parameter_str))

    except json.JSONDecodeError:
        print(f"Error: 无效的JSON响应: {style_str}")

# 按相似度排序
similar_songs.sort(key=lambda x: x[1], reverse=True)
similar_songs = similar_songs[:3]

# 打印相似度结果
found_similar = False
resu = []
for song in similar_songs:
    song_name = song[0]
    if song_name != chat_message and song[1] > 0:
        found_similar = True
        similarity = song[1]
        style = json.loads(song[2])
        feature = json.loads(song[3])
        resu.append(json.loads(song[4]))
        print(f"相似歌曲: {song_name}")
        print(f"相似度: {similarity:.4f}")

if not found_similar:
    print("未找到相似歌曲")

# 第一个系统提示
system_prompt1 = f'你是音效参数专家，需要从用户输入的歌曲名称判断给歌曲添加哪些音效模块，这些模块包括过载，失真，延迟，混响，压缩，相位，合唱，镶边，均衡，噪声门，返回这些音效的 JSON 格式的参数列表，例如: {{"overload": "yes", "distortion": "yes", "delay": "yes", "reverb": "yes", "compression": "no", "phase": "no", "chorus": "no", "flanger": "no", "equalization": "yes", "noise_gate": "no"}}用户输入的歌曲是: {chat_message}，返回结果格式严格参照给的例子。具体参数可以参考{resu}中的内容，这些参数是用户查询的歌曲的相似歌曲所配置的参数（参数值结合了用户的喜好，你需要从中学习用户喜好，比如该歌曲中没有镶边模块，但是参考的数据中有FlangerOn，那就要考虑开启镶边模块），其中CompressorOn表示需要开启压缩模块，CompressorOff表示关闭压缩模块，其他模块同理。如果参考中的参数值不一致（比如第一个参数有CompressorOn而第二个是CompressorOff）则以第一个的参数值为基准。'
user_prompt1 = chat_message
response1 = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": system_prompt1},
        {"role": "user", "content": user_prompt1},
    ],
    stream=False
)

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
        if memoryEnabled == "true" and resu is not None:
            system_prompt = f'你是一位专业音效调整师，请返回该音效的 JSON 格式的参数列表，例如: {effector["example_with"]}，你只需要参考格式，请不要参考列表中的任何参数值，你的回答需要在列表之中，不要有任何多余数据。具体参数值可以参考{resu}中的内容，这些参数是用户查询的歌曲的相似歌曲所配置的参数（参数值结合了用户的喜好，你需要从中学习用户喜好，比如该歌曲中没有镶边模块，但是参考的数据中有FlangerOn，那就要考虑开启镶边模块），其中CompressorOn表示需要开启压缩模块，CompressorOff表示关闭压缩模块，其他模块同理。如果参考中的模块关闭则不需要参考里面具体的参数。如果参考中的模块开启则考虑也开启该模块，并为模块生成具体参数值，这些参数值尽量要和参考中的参数值不相同（波动范围不要太大）。如果参考中的参数值不一致（比如第一个参数有CompressorOn而第二个是CompressorOff）则以第一个的参数值为基准。'
        else:
            system_prompt = f'你是一位专业音效调整师，请返回该音效的 JSON 格式的参数列表，例如: {effector["example_with"]}，你只需要参考格式，请不要参考列表中的任何参数值，你的回答需要在列表之中，不要有任何多余数据。'
        print(f"system_prompt:{system_prompt}")
        user_prompt = effector["prompt_with"] + effector["example_with"]
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            stream=False
        )

        # 获取响应数据并转换为 JSON
        response_content = response.choices[0].message.content
        # 去除前后的代码块标记和换行
        cleaned_content = response_content.replace("```json", "").replace("```", "").strip()
        try:
            result = json.loads(cleaned_content)
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

# 检查 chat_message 是否已经存在于数据库中
cursor.execute("SELECT SongName FROM music_responses WHERE SongName =?", (chat_message,))
existing_song = cursor.fetchone()

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

# 数据库操作带事务处理
try:
    if existing_song:
        # 已存在则更新（添加 Vector 字段）
        cursor.execute("""
            UPDATE music_responses 
            SET Style =?, Feature =?, Parameters =?, Vector =? 
            WHERE SongName =?
        """, (song_style_str, guitar_features_str, result_str, vector_str, chat_message))
        print(f"已更新歌曲: {chat_message} 的信息")
    else:
        # 新增记录（添加 Vector 字段）
        cursor.execute("""
            INSERT INTO music_responses (SongName, Style, Feature, Parameters, Vector) 
            VALUES (?,?,?,?,?)
        """, (chat_message, song_style_str, guitar_features_str, result_str, vector_str))
        print(f"已添加新歌曲: {chat_message} 到数据库")

    # 提交事务
    conn.commit()
except sqlite3.Error as e:
    # 发生错误时回滚
    conn.rollback()
    print(f"数据库操作失败: {str(e)}")
    sys.exit(1)

# 将风格结果字符串写入文件
with open("result1.txt", 'w', encoding='utf-8') as f:
    f.write(song_style_str)
# 将特征结果字符串写入文件
with open("result2.txt", 'w', encoding='utf-8') as f:
    f.write(guitar_features_str)
# 将参数结果字符串写入文件
with open("result.txt", 'w', encoding='utf-8') as f:
    f.write(result_str)

# 关闭数据库连接
conn.close()

# 新增：等待用户输入后再关闭窗口
input("程序执行完毕，按回车键关闭窗口...")