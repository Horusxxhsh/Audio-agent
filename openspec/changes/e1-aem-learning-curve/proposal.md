## 为什么

IEEE TMM 审稿人质疑论文核心贡献的新颖性（C1: "Gram矩阵是经典套路"）以及 RAG 主张与实验覆盖不匹配（C2: "多数结果本质是 Top-1 检索"）。本实验通过验证 Adaptive Executable Memory (AEM) 的自学习能力，为 "Agent 架构" 重新定位提供关键支撑。实验将证明：系统通过用户交互累积记忆，能够个性化参数检索并随时间改善性能，这是单纯的检索系统无法实现的能力。

## 变更内容

### 新增内容
- **AEM Learning Curve Experiment**: 实现完整的记忆学习曲线实验
  - 测试多种记忆库大小配置 (0, 5, 10, 20, 50 条)
  - 模拟用户多轮交互反馈（10 轮/查询）
  - 记录 L2 误差、记忆命中率等指标随交互的演变
  - 统计分析：配对 t 检验验证改善的显著性 (p < 0.05)

- **实验结果可视化**: 生成学习曲线图和对比表
  - 每轮误差变化曲线
  - 不同记忆大小的最终性能对比
  - 统计显著性标记

### 修改内容
- **Source/rag_system.py**: 添加 `max_memory_size` 参数控制记忆库容量
- **Source/simulate_user_feedback.py**: 扩展用户模拟器支持多轮交互

## 功能 (Capabilities)

### 新增功能
- `aem-learning-curve`: AEM 记忆学习曲线实验，验证系统随用户交互自适应改善的能力
- `memory-size-controller`: 记忆库大小控制器，支持 LRU 淘汰策略
- `multi-turn-interaction-simulator`: 多轮交互模拟器，模拟用户反馈累积过程

### 修改功能
- `rag-system`: 扩展记忆管理接口，支持查询记忆条目数量和清空记忆

## 影响

### 代码影响
- **新增文件**: `Experiments/E1_AEM/memory_learning_curve.py` (~400 行)
- **修改文件**: `Source/rag_system.py` (记忆管理扩展)
- **修改文件**: `Source/simulate_user_feedback.py` (多轮交互支持)

### API 调用
- DeepSeek API: ~2,500 次调用（预估成本 ￥5-6）

### 论文影响
- **Sec 4.2**: 新增 "AEM Personalization" 子节，插入学习曲线图表
- **Response Letter**: 新增 E1 实验结果回应 C2 质疑
- **Abstract**: 更新 "Adaptive" 能力描述

### 依赖
- 依赖现有 `AudioRAGSystem` 的记忆功能
- 依赖 `simulate_user_feedback.py` 的用户模拟器
- 依赖 DeepSeek API 进行参数推荐

## 预期结果

### 成功标准
- 记忆大小=50 的 L2 误差比 baseline (无记忆) 降低 20-40%
- 记忆命中率随轮次从 0% 提升至 60%
- 统计显著性：配对 t 检验 p < 0.05

### 风险应对
- **如果改善 < 10%**: 调整 learning_rate 参数或增加交互轮次
- **如果曲线不单调**: 检查记忆覆盖策略，调整 max_memory_size 逻辑
