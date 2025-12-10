# 实验实施计划

## 目标
实现 `experimental_design.md` 中描述的实验设计，在 `Experiments/` 目录下创建一系列 Python 脚本，用于加载数据、运行基线模型、模拟 RAG 系统以及计算评估指标。

## 拟议变更

### `Experiments/` 目录结构

#### [NEW] `dataset_loader.py`
- **目的**: 从 `music_info.db` 和 `audio_info.db` 加载并合并数据。
- **逻辑**:
    - 连接到两个 SQLite 数据库。
    - 获取所有记录。
    - 基于 `Parameters` 字符串（期望完全匹配）合并记录。
    - 返回包含 `{SongName, Parameters, Style, Feature, Vector}` 的字典列表。
    - 将数据划分为“知识库”（用于检索）和“测试集”（用于评估）——如果数据集较小（50条），目前先进行模拟划分，或使用留一法（Leave-One-Out）。

#### [NEW] `baselines.py`
- **目的**: 实现基线模型的生成/检索逻辑。
- **类**:
    - `BaselineA`: 直接 LLM (Zero-shot)。
        - *输入*: 文本提示词 `T`。
        - *输出*: 通过 OpenAI API 生成 JSON 参数（如果 key 可用则调用，否则使用桩代码/Mock）。
    - `BaselineB`: 纯文本 RAG。
        - *索引*: 简单的 (文本, 参数) 列表。
        - *检索*: 基于 TF-IDF 或嵌入的相似度（使用 `scikit-learn` 或 `sentence-transformers`）。
        - *输出*: Top-1 检索到的参数。

#### [NEW] `rag_system_sim.py` (Ours)
- **目的**: 为了离线评估而模拟的双模态 RAG 全流程。
- **逻辑**:
    - *索引*: (文本, 音频向量, 参数)。
    - *检索*: 文本相似度 + 音频相似度（基于 `Vector` 的余弦相似度）的加权和。
    - *精炼器*: (可选) 调用 LLM 对检索到的参数进行微调（可以使用桩代码）。

#### [NEW] `evaluate.py`
- **目的**: 计算客观指标。
- **指标**:
    - `ParameterDistance`: 归一化参数向量的 L2 范数。
    - `RetrievalRecall`: 检查 Ground Truth ID 是否出现在 Top-K 结果中。
    - `FAD`: 占位符 —— 需要音频生成，没有 C++ 引擎无法离线完成。将记录日志“音频生成已跳过”。

#### [NEW] `run_experiment.py`
- **目的**: 编排整个流程。
    1. 加载数据。
    2. 在测试集上运行 Baseline A, B 和 Ours。
    3. 计算指标。
    4. 将结果保存到 `results.json` 并打印摘要。

## 验证计划

### 自动化测试
- 运行 `python Experiments/run_experiment.py`。
- **通过条件**:
    - 脚本运行无错误。
    - 打印出结果表格（Recall@1, ParamDistance）。
    - 生成 `results.json` 文件。

### 人工验证
- 检查 `Experiments/results.json` 确保数值统一且合理（不是全零）。
