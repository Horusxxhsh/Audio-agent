# Audio-Agent RAG 系统文档

## 概述

本项目现已集成完整的 **RAG (Retrieval-Augmented Generation)** 系统，用于增强音乐风格识别和参数推荐功能。

## 主要特性

### 🎯 核心功能

1. **向量数据库存储**
   - 使用 ChromaDB 持久化音乐知识和参数预设
   - 自动向量化文本描述
   - 支持高效的相似度检索

2. **智能知识检索**
   - 基于用户查询检索相关音乐风格知识
   - 推荐相似的参数预设
   - 考虑历史用户评价

3. **增强生成 (RAG)**
   - 结合检索的上下文生成更准确的建议
   - 提供基于知识库的专业分析
   - 支持风格特征的深度理解

4. **持续学习**
   - 自动存储用户生成的参数配置
   - 记录用户反馈 (accept/edit/reject)
   - 逐步积累个性化知识库

## 文件结构

```
Source/
├── rag_system.py           # 核心 RAG 系统实现
├── rag_integration.py      # 与现有系统的集成接口
├── test_rag.py            # 测试和使用示例
├── requirements_rag.txt    # RAG 依赖包
└── llm.py                 # 原有的 LLM 系统 (可集成)
```

## 安装

### 1. 安装依赖

```bash
pip install -r requirements_rag.txt
```

主要依赖：
- `chromadb` - 向量数据库
- `numpy` - 数值计算
- `nltk` - 文本处理 (可选)
- `faiss-cpu` - 高性能向量搜索 (可选)

### 2. 验证安装

```bash
python test_rag.py
```

## 使用方法

### 基本使用

```python
from rag_system import AudioRAGSystem, initialize_knowledge_base

# 1. 初始化 RAG 系统
rag = AudioRAGSystem(
    api_key="your-api-key",
    base_url="https://api.deepseek.com"
)

# 2. 初始化知识库（首次使用）
initialize_knowledge_base(rag)

# 3. 检索相关知识
results = rag.retrieve_similar_knowledge(
    query="atmospheric guitar with reverb",
    n_results=3,
    collection_type="music"
)

# 4. 推荐参数
recommendations = rag.recommend_parameters(
    style_tags=["post_rock", "atmospheric"],
    user_description="spacious sound with lots of reverb",
    n_recommendations=3
)

# 5. RAG 增强生成
response = rag.generate_with_rag(
    user_query="How to create shoegaze tone?",
    style_tags=["shoegaze", "dreamy"],
    context_type="both"
)
```

### 集成到现有系统

```python
from rag_integration import integrate_rag_with_existing_system

# 使用 RAG 增强现有流程
rag_context = integrate_rag_with_existing_system(
    chat_message="atmospheric post-rock guitar",
    song_style=["post_rock", "atmospheric"],
    guitar_features=["reverb", "delay", "clean"],
    memoryEnabled="true"
)

# 使用 RAG 上下文
if rag_context:
    print(f"检索到 {len(rag_context['music_context'])} 条相关知识")
    print(f"推荐 {len(rag_context['parameter_recommendations'])} 个参数预设")
    print(f"RAG 分析: {rag_context['rag_analysis']}")
```

### 添加新知识

```python
# 添加音乐风格知识
rag.add_music_knowledge(
    style="math_rock",
    description="Math rock features complex time signatures and intricate guitar work",
    features=["complex_rhythms", "clean_tone", "tapping", "polyrhythmic"],
    examples=["Don Caballero", "Battles", "TTNG"]
)

# 添加参数预设
rag.add_parameter_preset(
    preset_name="My Awesome Tone",
    parameters={
        "ReverbOn": {"Size": 0.75, "Mix": 0.45},
        "DelayOn": {"Delay": 380, "Feedback": 0.35}
    },
    style_tags=["ambient", "atmospheric"],
    description="Spacious ambient tone with reverb and delay",
    user_rating="accept"
)
```

## 工作原理

### 1. 向量化 (Embedding)

```
用户查询 → 文本向量化 → 384维向量
  ↓
存储的知识 → 文本向量化 → 384维向量
```

### 2. 相似度检索

```
查询向量 → 余弦相似度计算 → 排序 → Top-K 结果
```

### 3. RAG 增强生成

```
用户查询 → 检索相关上下文 → 构建增强提示词 → LLM 生成 → 增强回答
```

### 4. 知识积累

```
用户输入 → 生成参数 → 用户反馈 → 存储到向量库 → 持续改进
```

## 数据存储

### 向量数据库位置

默认路径：`C:\Users\Public\Documents\Supertonal DSP\vector_db\`

可通过环境变量 `SUPERTONAL_DIR` 自定义。

### 集合结构

1. **music_knowledge** - 音乐风格知识
   - 风格描述
   - 特征列表
   - 示例歌曲
   - 元数据

2. **parameter_presets** - 参数预设
   - 预设名称
   - 参数配置
   - 风格标签
   - 用户评价

## 性能优化

### 1. 向量维度

默认使用 384 维向量（平衡精度和速度）

### 2. 批量操作

```python
# 批量添加知识
for style in music_styles:
    rag.add_music_knowledge(**style)
```

### 3. 缓存机制

ChromaDB 自动缓存查询结果，重复查询更快。

### 4. 可选 FAISS 加速

对于大规模数据（>10000 条），可使用 FAISS：

```bash
pip install faiss-cpu  # 或 faiss-gpu
```

## API 参考

### AudioRAGSystem

**初始化**
```python
__init__(api_key: str, base_url: str, persist_directory: Optional[str])
```

**主要方法**

- `add_music_knowledge()` - 添加音乐知识
- `add_parameter_preset()` - 添加参数预设
- `retrieve_similar_knowledge()` - 检索相似知识
- `recommend_parameters()` - 推荐参数
- `generate_with_rag()` - RAG 增强生成
- `get_collection_stats()` - 获取统计信息

### 集成函数

- `integrate_rag_with_existing_system()` - 集成到现有系统
- `add_preset_to_rag()` - 添加预设到 RAG
- `enhance_system_prompt_with_rag()` - 增强系统提示词

## 测试

运行完整测试套件：

```bash
python test_rag.py
```

测试包括：
1. ✅ RAG 系统基本功能
2. ✅ 参数预设添加和检索
3. ✅ RAG 增强生成
4. ✅ 完整集成工作流程
5. ✅ 交互式测试（可选）

## 示例场景

### 场景 1: 新用户首次使用

```python
# 初始化并加载预置知识库
rag = AudioRAGSystem(api_key="xxx")
initialize_knowledge_base(rag)  # 加载 6 种基础风格

# 用户输入
user_input = "I want shoegaze guitar tone"

# 检索并推荐
results = rag.retrieve_similar_knowledge(user_input)
recommendations = rag.recommend_parameters(["shoegaze"], user_input)
```

### 场景 2: 高级用户添加自定义预设

```python
# 用户保存了自己的配置
rag.add_parameter_preset(
    preset_name="My Signature Sound",
    parameters=my_custom_params,
    style_tags=["custom", "experimental"],
    description="Unique blend of ambient and metal",
    user_rating="accept"
)
```

### 场景 3: 持续学习

```python
# 每次用户生成参数后
add_preset_to_rag(
    rag_system=rag,
    preset_name=user_description,
    parameters=generated_params,
    style_tags=detected_styles,
    features=extracted_features,
    user_rating=user_feedback  # "accept", "edit", or "reject"
)
```

## 故障排除

### 问题 1: ChromaDB 连接错误

**解决方案：**
```python
# 清空并重建
rag.clear_collection("music")
rag.clear_collection("parameter")
```

### 问题 2: 向量化失败

**原因：** API 不支持 embedding 接口

**解决方案：** 系统自动降级使用简单嵌入方法

### 问题 3: 检索结果为空

**原因：** 知识库未初始化

**解决方案：**
```python
initialize_knowledge_base(rag)
```

## 未来扩展

### 计划功能

- [ ] 多语言支持
- [ ] 音频文件直接向量化
- [ ] 更高级的特征提取
- [ ] 用户偏好学习
- [ ] A/B 测试框架
- [ ] 云端同步

## 贡献

欢迎贡献新的音乐风格知识和参数预设！

格式参考：
```python
{
    "style": "风格名",
    "description": "详细描述",
    "features": ["特征1", "特征2"],
    "examples": ["艺术家1", "艺术家2"]
}
```

## 许可证

与主项目相同。

---

**维护者**: Audio-Agent Team  
**更新日期**: 2025-11  
**版本**: 1.0.0
