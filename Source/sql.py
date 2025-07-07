# -*- coding: gbk -*-
import sys
import json
import sqlite3
import math
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from openai import OpenAI

# 定义 MemoryNote 类
class MemoryNote:
    def __init__(self, id, songName, style, feature, parameter):
        self.id = id
        self.songName = songName
        self.style = style
        self.feature = feature
        self.parameter = parameter

    def __str__(self):
        return f"ID: {self.id}, Song Name: {self.songName}, Style: {self.style}, Feature: {self.feature}, Parameter: {self.parameter}"

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

try:
    # 读取 result1.txt 文件
    with open(r"C:\Users\80753\Desktop\result1.txt", 'r', encoding='utf-8') as file:
        result1_str = file.read()
        # 将字符串转换为集合
        result1_set = set(result1_str.split(',')) if result1_str else set()
except FileNotFoundError:
    print("无法打开 result1.txt 文件")

try:
    # 读取 result2.txt 文件
    with open(r"C:\Users\80753\Desktop\result2.txt", 'r', encoding='utf-8') as file:
        result2_str = file.read()
except FileNotFoundError:
    print("无法打开 result2.txt 文件")

def get_ratio(value):
    mapping = {
        0.000000: 1,
        0.118416: 2,
        0.197404: 3,
        0.256761: 4,
        0.304328: 5,
        0.344022: 6,
        0.378081: 7,
        0.407910: 8,
        0.434443: 9,
        0.458337: 10,
    }
    return mapping.get(value)

try:
    # 连接到数据库
    #测试路径
    #conn = sqlite3.connect(r'E:\c++\day11\PythonApplication\music_info.db')
    #实验路径
    conn = sqlite3.connect(r'E:\c++\juceproject\juceEffector\supertonal\Builds\VisualStudio2022\music_info.db')
    cursor = conn.cursor()

    # 获取index的值
    if len(sys.argv) > 2:
        chat_message = sys.argv[1]  # 获取命令行中c++程序传入的第一个参数
        print(f"Chat message: {chat_message}")

        # 从数据库中获取所有歌曲信息并计算相似度
        cursor.execute("SELECT SongName, Style, Feature, Parameters FROM music_responses")
        rows = cursor.fetchall()
        similar_songs = []
        memory_notes = []  # 存储 MemoryNote 实例的列表

        
        for index, row in enumerate(rows, start=1):
            song_name = row[0]
            style_str = row[1]
            feature_str = row[2]
            parameter_str = row[3]
            if song_name != sys.argv[2]:
                try:
                    style = json.loads(style_str)
                    feature = json.loads(feature_str)
        
                    # 计算标签相似度
                    tags = set(style)
                    tag_similarity = jaccard_similarity(result1_set, tags)
        
                    # 计算描述相似度
                    description = " ".join(feature)
                    desc_similarity = text_similarity(result2_str, description)
        
                    # 综合相似度 (权重可以调整)
                    similarity = 0.7 * tag_similarity + 0.3 * desc_similarity
        
                    if similarity> 0:
                        similar_songs.append((song_name, similarity, style_str, feature_str, parameter_str))
                        # 存储检索到的歌曲的信息
                        note = MemoryNote(index, song_name, style, feature, parameter_str)
                        memory_notes.append(note)

                except json.JSONDecodeError:
                        print(f"Error: 无效的JSON响应: {style_str}")
        # 打印 MemoryNote 实例的信息
        for note in memory_notes:
            print(note)
        parts = chat_message.split(',')
        if len(parts) < 48:
            print("命令行参数分割后列表长度不足 48，请检查输入。")
        else:
            first_47 = parts[:48]
            try:
                # 将 first_47[0] 到 first_47[8] 转换为浮点数
                for i in range(9):
                    first_47[i] = float(first_47[i])

                # 获取userMessageToSend的值并进行处理
                userMessageToSend = sys.argv[2]  # 获取命令行中c++程序传入的第二个参数
                print(f"userMessageToSend: {userMessageToSend}")

                # 查询匹配的记录
                cursor.execute("SELECT SongName, Style, Feature, Parameters FROM music_responses WHERE SongName =?", (userMessageToSend,))
                row = cursor.fetchone()

                if row:
                    song_name = row[0]
                    try:
                        style = json.loads(row[1])
                        parameters = json.loads(row[3])

                        # 当 first_47[0] == 1.0 时，将 "CompressorOff" 替换为 "CompressorOn"
                        if first_47[0] == 1.0 and 'CompressorOff' in parameters:
                            compressor_settings = parameters.pop('CompressorOff')
                            parameters['CompressorOn'] = compressor_settings
                        if first_47[0] == 0.0 and 'CompressorOn' in parameters:
                            compressor_settings = parameters.pop('CompressorOn')   
                            parameters['CompressorOff'] = compressor_settings
                        if 'CompressorOff' in parameters:
                            parameters['CompressorOff']['Threshold'] = -128.00  
                            parameters['CompressorOff']['Ratio'] = 1
                            parameters['CompressorOff']['Attack'] = 0.00
                            parameters['CompressorOff']['Release'] = 0.00  
                            parameters['CompressorOff']['Makeup'] = -12.00
                            parameters['CompressorOff']['Mix'] = 0.00

                           # 当 first_47[1] == 1.0 时，将 "ScreamerOff" 替换为 "ScreamerOn"
                        if first_47[1] == 1.0 and 'ScreamerOff' in parameters:
                            compressor_settings = parameters.pop('ScreamerOff')
                            parameters['ScreamerOn'] = compressor_settings 
                        if first_47[1] == 0.0 and 'ScreamerOn' in parameters:
                            compressor_settings = parameters.pop('ScreamerOn')
                            parameters['ScreamerOff'] = compressor_settings
                        if 'ScreamerOff' in parameters:
                            parameters['ScreamerOff']['Drive'] = 0.00 
                            parameters['ScreamerOff']['Tone'] = 0.00
                            parameters['ScreamerOff']['Level'] = -64.0000000
                        
                           # 当 first_47[2] == 1.0 时，将 "DriverOff" 替换为 "DriverOn"
                        if first_47[2] == 1.0 and 'DriverOff' in parameters:
                            compressor_settings = parameters.pop('DriverOff')
                            parameters['DriverOn'] = compressor_settings
                        if first_47[2] == 0.0 and 'DriverOn' in parameters:
                            compressor_settings = parameters.pop('DriverOn')
                            parameters['DriverOff'] = compressor_settings
                        if 'DriverOff' in parameters:
                            parameters['DriverOff']['Distortion'] = 0.00 
                            parameters['DriverOff']['Volume'] = -64.0
                            

                            # 当 first_47[3] == 1.0 时，将 "DelayOff" 替换为 "DelayOn"
                        if first_47[3] == 1.0 and 'DelayOff' in parameters:
                            compressor_settings = parameters.pop('DelayOff')
                            parameters['DelayOn'] = compressor_settings                           
                        if first_47[3] == 0.0 and 'DelayOn' in parameters:
                            compressor_settings = parameters.pop('DelayOn')
                            parameters['DelayOff'] = compressor_settings
                        if 'DelayOff' in parameters:
                            parameters['DelayOff']['Feedback'] = 0.00 
                            parameters['DelayOff']['Delay'] = 1.00
                            parameters['DelayOff']['Mix'] = 0.00 

                           # 当 first_47[4] == 1.0 时，将 "ReverbOff" 替换为 "ReverbOn"
                        if first_47[4] == 1.0 and 'ReverbOff' in parameters:
                            compressor_settings = parameters.pop('ReverbOff')
                            parameters['ReverbOn'] = compressor_settings
                        if first_47[4] == 0.0 and 'ReverbOn' in parameters:
                            compressor_settings = parameters.pop('ReverbOn')
                            parameters['ReverbOff'] = compressor_settings
                        if 'ReverbOff' in parameters:
                            parameters['ReverbOff']['Size'] = 0.00 
                            parameters['ReverbOff']['Damping'] = 0.00
                            parameters['ReverbOff']['Width'] = 0.00
                            parameters['ReverbOff']['Mix'] = 0.00                   
                            

                            # 当 first_47[5] == 1.0 时，将 "ChorusOff" 替换为 "ChorusOn"
                        if first_47[5] == 1.0 and 'ChorusOff' in parameters:
                            compressor_settings = parameters.pop('ChorusOff')
                            parameters['ChorusOn'] = compressor_settings
                        if first_47[5] == 0.0 and 'ChorusOn' in parameters:
                            compressor_settings = parameters.pop('ChorusOn')
                            parameters['ChorusOff'] = compressor_settings
                        if 'ChorusOff' in parameters:
                            parameters['ChorusOff']['Delay'] = 0.010 
                            parameters['ChorusOff']['Depth'] = 0.00
                            parameters['ChorusOff']['Frequency'] = 0.05
                            parameters['ChorusOff']['Width'] = 0.010

                            # 当 first_47[6] == 1.0 时，将 "FlangerOff" 替换为 "FlangerOn"
                        if first_47[6] == 1.0 and 'FlangerOff' in parameters:
                            compressor_settings = parameters.pop('FlangerOff')
                            parameters['FlangerOn'] = compressor_settings
                        if first_47[6] == 0.0 and 'FlangerOn' in parameters:
                            compressor_settings = parameters.pop('FlangerOn')
                            parameters['FlangerOff'] = compressor_settings
                        if 'FlangerOff' in parameters:  
                            parameters['FlangerOff']['Delay'] = 0.00100 
                            parameters['FlangerOff']['Depth'] = 0.00
                            parameters['FlangerOff']['Feedback'] = 0.00
                            parameters['FlangerOff']['Frequency'] = 0.05
                            parameters['FlangerOff']['Width'] = 0.001

                           # 当 first_47[7] == 1.0 时，将 "PhaserOff" 替换为 "PhaserOn"
                        if first_47[7] == 1.0 and 'PhaserOff' in parameters:
                            compressor_settings = parameters.pop('PhaserOff')
                            parameters['PhaserOn'] = compressor_settings
                        if first_47[7] == 0.0 and 'PhaserOn' in parameters:
                            compressor_settings = parameters.pop('PhaserOn')
                            parameters['PhaserOff'] = compressor_settings
                        if 'PhaserOff' in parameters:
                            parameters['PhaserOff']['Depth'] = 0.00 
                            parameters['PhaserOff']['Feedback'] = 0.00
                            parameters['PhaserOff']['Frequency'] = -64.0000000
                            parameters['PhaserOff']['Width'] = -64.0000000

                           # 当 first_47[8] == 1.0 时，将 "EqualiserOff" 替换为 "EqualiserOn"
                        if first_47[8] == 1.0 and 'EqualiserOff' in parameters:
                            compressor_settings = parameters.pop('EqualiserOff')
                            parameters['EqualiserOn'] = compressor_settings
                        if first_47[8] == 0.0 and 'EqualiserOn' in parameters:
                            compressor_settings = parameters.pop('EqualiserOn')
                            parameters['EqualiserOff'] = compressor_settings
                        if 'EqualiserOff' in parameters:
                            parameters['EqualiserOff']['100hz'] = 0.00
                            parameters['EqualiserOff']['200hz'] = 0.00
                            parameters['EqualiserOff']['400hz'] = 0.00
                            parameters['EqualiserOff']['800hz'] = 0.00
                            parameters['EqualiserOff']['1600hz'] = 0.00
                            parameters['EqualiserOff']['3200hz'] = 0.00
                            parameters['EqualiserOff']['6400hz'] = 0.00
                            parameters['EqualiserOff']['Level'] = 0.00
                            

                            # 更新数据库中的参数值
                        if first_47[0] == 1.0:
                            if 'CompressorOn' in parameters:
                               
                               # 将 first_47[9] 转换为 Threshold 范围的值
                                first_47[9] = float(first_47[9])
                                threshold = -128 + (0 - (-128)) * first_47[9]                               
                                parameters['CompressorOn']['Threshold'] = threshold
                               
                               # 获取 Ratio 值
                                first_47[11] = float(first_47[11])
                                ratio = get_ratio(first_47[11])
                                if ratio is not None:
                                    parameters['CompressorOn']['Ratio'] = ratio
                                else:
                                    print(f"未找到 first_47[11] = {first_47[11]} 对应的 Ratio 值")

                                parameters['CompressorOn']['Attack'] = first_47[10]
                                parameters['CompressorOn']['Release'] = first_47[12]

                                 # 将 first_47[13] 转换为 Makeup 范围的值
                                first_47[13] = float(first_47[13])
                                makeup = -128 + (64 - (-128)) * first_47[13]
                                parameters['CompressorOn']['Makeup'] = makeup

                                parameters['CompressorOn']['Mix'] = first_47[14]

                        if first_47[2] == 1.0:
                            if 'DriverOn' in parameters:
                                parameters['DriverOn']['Distortion'] = first_47[18]
                                # 将 first_47[19] 转换为 Volume 范围的值
                                first_47[19] = float(first_47[19])
                                volume = -64 + (0 - (-64)) * first_47[19]                               
                                parameters['DriverOn']['Volume'] = volume                        

                        if first_47[1] == 1.0:
                            if 'ScreamerOn' in parameters:
                                parameters['ScreamerOn']['Drive'] = first_47[15]
                                parameters['ScreamerOn']['Tone'] = first_47[17]
                                # 将 first_47[16] 转换为 Volume 范围的值
                                first_47[16] = float(first_47[16])
                                volume = -64 + (0 - (-64)) * first_47[16]                               
                                parameters['ScreamerOn']['Level'] = volume                                

                        if first_47[3] == 1.0:
                            if 'DelayOn' in parameters:
                                parameters['DelayOn']['Feedback'] = first_47[20]
                                
                                parameters['DelayOn']['Delay'] = "450.00"
                                
                                parameters['DelayOn']['Mix'] = first_47[22]

                        if first_47[4] == 1.0:
                            if 'ReverbOn' in parameters:
                                parameters['ReverbOn']['Size'] = first_47[23]
                                parameters['ReverbOn']['Damping'] = first_47[24]
                                parameters['ReverbOn']['Width'] = first_47[25]
                                parameters['ReverbOn']['Mix'] = first_47[26]

                        if first_47[8] == 1.0:
                            if 'EqualiserOn' in parameters:
                                if len(first_47) > 46:
                                    # 将 first_47[40] 转换为 Frequency 范围的值
                                    first_47[40] = float(first_47[40])
                                    fz = -15.00 + (15.00 - (-15.00)) * first_47[40] 
                                    parameters['EqualiserOn']['100hz'] = fz
                                   
                                   # 将 first_47[41] 转换为 Frequency 范围的值
                                    first_47[41] = float(first_47[41])
                                    fz = -15.00 + (15.00 - (-15.00)) * first_47[41] 
                                    parameters['EqualiserOn']['200hz'] = fz
                                    

                                    # 将 first_47[42] 转换为 Frequency 范围的值
                                    first_47[42] = float(first_47[42])
                                    fz = -15.00 + (15.00 - (-15.00)) * first_47[42] 
                                    parameters['EqualiserOn']['400hz'] = fz
                                    

                                    # 将 first_47[43] 转换为 Frequency 范围的值
                                    first_47[43] = float(first_47[43])
                                    fz = -15.00 + (15.00 - (-15.00)) * first_47[43] 
                                    parameters['EqualiserOn']['800hz'] = fz
                                    

                                    # 将 first_47[44] 转换为 Frequency 范围的值
                                    first_47[44] = float(first_47[44])
                                    fz = -15.00 + (15.00 - (-15.00)) * first_47[44] 
                                    parameters['EqualiserOn']['1600hz'] = fz
                                    

                                    # 将 first_47[45] 转换为 Frequency 范围的值
                                    first_47[45] = float(first_47[45])
                                    fz = -15.00 + (15.00 - (-15.00)) * first_47[45] 
                                    parameters['EqualiserOn']['3200hz'] = fz
                                    

                                    # 将 first_47[46] 转换为 Frequency 范围的值
                                    first_47[46] = float(first_47[46])
                                    fz = -15.00 + (15.00 - (-15.00)) * first_47[46] 
                                    parameters['EqualiserOn']['6400hz'] = fz
                                if len(first_47) > 47:
                                   
                                   # 将 first_47[47] 转换为 Frequency 范围的值
                                    first_47[47] = float(first_47[47])
                                    fz = -15.00 + (15.00 - (-15.00)) * first_47[47] 
                                    parameters['EqualiserOn']['Level'] = fz

                        if first_47[5] == 1.0:
                            if 'ChorusOn' in parameters:
                                # 将 first_47[27] 转换为 Depth 范围的值
                                first_47[27] = float(first_47[27])
                                depth = 0.010 + (0.050 - 0.010) * first_47[27]  
                                parameters['ChorusOn']['Delay'] = depth
                                
                                parameters['ChorusOn']['Depth'] = first_47[28]
                              
                              # 将 first_47[29] 转换为 Frequency 范围的值
                                first_47[29] = float(first_47[29])
                                frequency = 0.05 + (2.00 - 0.05) * first_47[29]  
                                parameters['ChorusOn']['Frequency'] = frequency
                               
                               # 将 first_47[30] 转换为 Width 范围的值
                                first_47[30] = float(first_47[30])
                                width = 0.010 + (0.050 - 0.010) * first_47[30]  
                                parameters['ChorusOn']['Width'] = width

                        if first_47[6] == 1.0:
                            if 'FlangerOn' in parameters:

                                # 将 first_47[31] 转换为 Delay 范围的值
                                first_47[31] = float(first_47[31])
                                delay = 0.00100 + (0.02000 - 0.00100) * first_47[31] 
                                parameters['FlangerOn']['Delay'] = delay
                                
                                parameters['FlangerOn']['Depth'] = first_47[32]

                                # 将 first_47[33] 转换为 Feedback 范围的值
                                first_47[33] = float(first_47[33])
                                feedback = 0.00 + (0.50 - 0.00) * first_47[33] 
                                parameters['FlangerOn']['Feedback'] = feedback
                                
                                # 将 first_47[34] 转换为 Frequency 范围的值
                                first_47[34] = float(first_47[34])
                                frequency = 0.05 + (2.00 - 0.05) * first_47[34] 
                                parameters['FlangerOn']['Frequency'] = frequency

                                # 将 first_47[35] 转换为 Width 范围的值
                                first_47[35] = float(first_47[35])
                                width = 0.001 + (0.020 - 0.001) * first_47[35] 
                                parameters['FlangerOn']['Width'] = width

                        if first_47[7] == 1.0:
                            if 'PhaserOn' in parameters:
                                parameters['PhaserOn']['Depth'] = first_47[36]

                                # 将 first_47[37] 转换为 Feedback 范围的值
                                first_47[37] = float(first_47[37])
                                feedback = 0.00 + (0.09 - 0.00) * first_47[37]  
                                parameters['PhaserOn']['Feedback'] = feedback

                                # 将 first_47[38] 转换为 Frequency 范围的值
                                first_47[38] = float(first_47[38])
                                frequency = 0.00 + (2.00 - 0.00) * first_47[38]  
                                parameters['PhaserOn']['Frequency'] = frequency

                                # 将 first_47[39] 转换为 Width 范围的值
                                first_47[39] = float(first_47[39])
                                width = 50 + (3000 - 50) * first_47[39]  
                                parameters['PhaserOn']['Width'] = width

                        # 将更新后的参数转换为字符串
                        updated_parameters_str = json.dumps(parameters, ensure_ascii=False)

                        # 更新数据库中的记录
                        cursor.execute("UPDATE music_responses SET Parameters =? WHERE SongName =?", (updated_parameters_str, song_name))
                        conn.commit()

                        # 打印更新后的信息
                        print(f"SongName: {song_name}")
                        print(f"Style: {json.dumps(style, ensure_ascii=False, indent=2)}")
                        print(f"Parameters: {json.dumps(parameters, ensure_ascii=False, indent=2)}")
                        print("-" * 50)
                       
                        sqlParameters = json.dumps(parameters, ensure_ascii=False, indent=2)
                        # 格式化 system_prompt3
                        memory_notes_str = "\n".join([str(note) for note in memory_notes])
                        system_prompt3 = f'''
                                You are an AI memory evolution agent responsible for managing and evolving a knowledge base.
                                Analyze the the new memory note according to style, feature and parameter, also with their several nearest neighbors memory.
                                Make decisions about its evolution.  

                                The new memory name:
                                {song_name}
                                style: {result1_str}
                                feature: {result2_str}
                                parameter: {sqlParameters}

                                The nearest neighbors memories:
                                {memory_notes_str}

                                Based on this information, determine:
                                1. Should this memory be evolved? Consider its relationships with other memories.
                                2. What specific actions should be taken (strengthen, update_neighbor)?
                                   2.1 If choose to strengthen the connection, which memory should it be connected to? Can you give the updated tags of this memory?
                                   2.2 If choose to update_neighbor, you can update the parameter of these memories based on the understanding of these memories. If the parameter is not updated, the new parameter should be the same as the original ones. Generate the new parameter in the sequential order of the input neighbors.
                                Parameter should be determined by the content of these characteristic of these memories, which can be used to retrieve them later and categorize them.
                                Return your decision in JSON format with the following structure:
                                {{
                                    "should_evolve": True or False,
                                    "actions": ["strengthen", "update_neighbor"],
                                    "suggested_connections": ["neighbor_memory_ids"],
                                    "new_parameter_neighborhood": [
                                            [parameters_1],  // 对应第一首歌曲
                                            ..............,
                                            [parameters_n]   // 对应第n首歌曲
  ]
                                }}
                        '''
                        print(f"system_prompt3:{system_prompt3}")
                        client = OpenAI(api_key="sk-1b73586fde854a329ec187dc371f53ef", base_url="https://api.deepseek.com")
                        user_prompt3 = f''
                        response3 = client.chat.completions.create(
                                      model="deepseek-chat",
                                      messages=[
                                          {"role": "system", "content": system_prompt3},
                                          {"role": "user", "content": user_prompt3},
                                      ],
                                      stream=False
                        )

                        # 获取 response4 响应数据并转换为 JSON
                        response_content3 = response3.choices[0].message.content
                        # 去除前后的代码块标记和换行
                        cleaned_content3 = response_content3.replace("```json", "").replace("```", "").strip()
                        try:
                            result3 = json.loads(cleaned_content3)
                            result3_str = json.dumps(result3, ensure_ascii=False)
                            # 获取是否更新记忆
                            should_evolve = result3.get("should_evolve", [])
                            # 获取动作
                            actions = result3.get("actions", [])
                            # 获取连接建议
                            suggested_connections = result3.get("suggested_connections", [])
                            # 获取邻居的新参数
                            new_parameter_neighborhood = result3.get("new_parameter_neighborhood", [])
                            # 打印信息
                            print(f"记忆更新模型响应: {result3_str}")
                            #print(f"吉他演奏的特点: {guitar_features}")


                            # 在获取 OpenAI 响应并解析 JSON 之后添加以下代码
                            if 'new_parameter_neighborhood' in result3:
                                new_params_list = result3['new_parameter_neighborhood']
                                total_updates = 0
    
                                # 遍历所有相似歌曲
                                for i, (song_name, similarity, _, _, _) in enumerate(similar_songs):
                                    # 检查是否有对应的新参数
                                    if i < len(new_params_list):
                                        new_params = new_params_list[i]
                                        try:
                                            # 将参数转换为 JSON 字符串
                                            new_params_str = json.dumps(new_params, ensure_ascii=False)
                                            cursor.execute("UPDATE music_responses SET Parameters =? WHERE SongName =?", 
                                                            (new_params_str, song_name))
                                            conn.commit()
                                            print(f"成功更新 '{song_name}' 的参数 (相似度: {similarity:.4f})")
                                            total_updates += 1
                                        except Exception as e:
                                            print(f"更新 '{song_name}' 参数时出错: {e}")
                                            conn.rollback()
    
                                print(f"总共更新了 {total_updates} 首歌曲的参数")
    
                                if total_updates < len(similar_songs):
                                    print(f"注意: 有 {len(similar_songs) - total_updates} 首歌曲没有对应的新参数")
                            else:
                                print("未找到 new_parameter_neighborhood 数据，无法更新参数")

                           
                        except json.JSONDecodeError:
                               print(f"Error: 无效的JSON响应: {cleaned_content3}")
                               sys.exit(1)
                    except json.JSONDecodeError:
                        print("从数据库读取的 JSON 数据格式错误，请检查数据库数据。")
                else:
                    print(f"未找到与 {userMessageToSend} 匹配的记录")
            except ValueError:
                print("命令行参数无法转换为数字，请检查输入。")
    else:
        print("命令行参数不足，请提供必要的参数")
except sqlite3.Error as e:
    print(f"数据库操作出错: {e}")
finally:
    if 'conn' in locals() and conn:
        conn.close()
