![Alt text](Screenshots/wide.JPG "Audio agent")

# Audio agent

Audio agent is a smart guitar multi-effects processor.

Take a listen to a [sample](https://github.com/pauljonescodes/supertonal/tree/master/Sounds).

It's capabilities, in a rough order:

- A tuner
- Gain staging
- Metering
- Noise gate
- Compression (multiple)
- A "screamer"
- A "mouse drive"
- Equilisation (multiple)
- Multi-stage wave-shaping
- Delay
- Chorus
- Phaser
- Flanger
- Bitcrusher
- Cabinet simulation with IR-loading
- Lo-fi mode
- Limiting

# Work Progress:
1. Added a large language model interaction interface, implementing AI-generated parameter functionality.

![Alt text](Screenshots/chat.png "CHAT UI")

After a successful response, click the reset button to transfer parameters with one click.

2. Added a music memory module, achieving personalized learning.By turning the memory function on/off (MemoryOn/Off), you can decide whether to enable personalized generation.You can simultaneously upload the target song's audio file, which will be stored in the database. This serves as a metric for retrieving similar songs.
   
(Click the SQL button to update the database information. If the memory function is enabled, it will update parameters of similar songs stored in the database based on your preferences.)

# Experiment Preparation:

## Environment Setup:
1. Open supertonal/Source/Components/PythonApplication/PythonApplication.sln with Visual Studio.
2. Add a virtual environment and install the following packages:
   - scikit-learn
   - openai
   - pandas
   - torch
   - librosa
   - transformers
   - networkx

## Environment Variable Configuration:
1. Add the following four items to your system environment variables:
   - SUPERTONAL_PYTHON_INTERPRETER: "C:\path\to\your\python\env\Scripts\python.exe"
   - SUPERTONAL_PYTHON_SCRIPT1: "C:\path\to\your\Audio-agent\Source\llm.py"
   - SUPERTONAL_PYTHON_SCRIPT2: "C:\path\to\your\Audio-agent\Source\sql.py"
   - SUPERTONAL_PYTHON_SCRIPT3: "C:\path\to\your\Audio-agent\Source\Components\accept.py"
   - SUPERTONAL_PYTHON_SCRIPT4: "C:\path\to\your\Audio-agent\Source\Components\reject.py"
   - SUPERTONAL_DIR: "C:\path\to\your\Audio-agent"
   - DOCUMENTS_DIR: "C:\path\to\your\Documents"

Note: Please replace the paths with your actual paths.
It is a work in progress, but I've made a strong effort to keep it portable and buildable with basic knowledge of JUCE. To get it working, simply:

```bash
git clone -b master --single-branch --recurse-submodules https://github.com/Horusxxhsh/Audio-agent.git
```

Then you should be able to open up the `.jucer` file and work in your environment of choice.

---

## 重构说明 (v2.0)

### 新增模块化架构 (`Source_new/`)

原 `Source/llm.py`（1686 行）和 `Source/sql.py`（1023 行）已拆分为以下模块：

| 模块 | 职责 | 行数 |
|------|------|------|
| `config/config_manager.py` | 路径、API 密钥、MusicGen 配置 | ~150 |
| `core/audio_features.py` | Wav2Vec2 音频特征提取 | ~80 |
| `core/musicgen_generator.py` | MusicGen 音频生成 | ~100 |
| `core/llm_client.py` | OpenAI 兼容 LLM 客户端 | ~70 |
| `core/parameters.py` | 效果器配置 + 参数 On/Off 切换 | ~200 |
| `core/prompt_builder.py` | 三阶段 Prompt 组装 | ~150 |
| `core/rag_bridge.py` | RAG 系统桥接（修复集成链路） | ~80 |
| `database/music_db.py` | SQLite CRUD（参数化查询） | ~140 |
| `llm.py` | 精简管道编排入口 | ~320 |
| `sql.py` | 参数更新入口 | ~115 |

### 已修复的问题

1. **单一职责**: 将 2709 行代码拆分为 8 个职责清晰的模块
2. **重复代码消除**: 9 个效果器的 On/Off 切换逻辑从 8 组复制粘贴缩减为数据驱动配置（`EFFECTOR_CONFIG`）
3. **跨平台兼容**: 所有硬编码 Windows 路径替换为 `Config.Paths` 自动解析
4. **RAG 集成修复**: `RAGBridge` 实际集成到主流程中（原为断开的死代码）
5. **依赖管理**: `pyproject.toml` + 精简 `requirements.txt`（替代 Anaconda 全量快照）
6. **测试覆盖**: 41 个 pytest 单元测试（原为 0）
7. **代码质量**: Ruff linter 配置（`ruff.toml`）
8. **安全改进**: 全部使用参数化 SQL 查询、API 密钥存在性校验

### 使用方式

```bash
# 安装依赖
pip install -r Source_new/requirements.txt

# 运行测试
cd Source_new && python3 -m pytest tests/ -v

# 运行 LLM 管道
python Source_new/llm.py "<chat_message>" <memory_enabled> [file_path] [weights...]

# 运行参数更新
python Source_new/sql.py "<chat_message>" "<user_message>" "<preset>" <memory_enabled>
```

### 数据元数据

数据集元数据文件位于 `Data/dataset_metadata.json`，记录了 4 种特征提取模型及其参数。
