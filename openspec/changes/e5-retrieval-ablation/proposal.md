## 为什么

IEEE TMM 审稿人关切 **C2: "RAG/生成主张与实验覆盖不匹配"** —— "文中强调 'Retrieval-Augmented Generation'，但 Protocol-A 的核心结果是 retrieval-only 的 top-1 对比...并没有展示检索 + LLM 生成/约束投影相对 '仅检索' 的增益"。本实验通过对比 "纯检索" vs "检索+约束投影"，验证 Agent 架构中各组件的贡献，支撑 "Agent 架构" 重新定位后的 claim。

## 变更内容

### 新增内容
- **Retrieval Ablation Study**: Retrieval 消融实验
  - **Condition A**: Pure Retrieval（纯 Top-K 检索，无后处理）
  - **Condition B**: Retrieval + Projection（检索 + 约束投影）
  - 量化投影模块对性能和约束满足率的贡献

### 简化设计（1周时间线约束）
- **跳过**: 复杂的 LLM 生成组件（与审稿人达成共识：retrieval 是核心）
- **聚焦**: 验证约束投影的价值（参数合法性、范围约束）
- **指标**: 约束满足率 (constraint_satisfied) 是关键指标

## 功能 (Capabilities)

### 新增功能
- `retrieval-ablation`: Retrieval 消融实验框架
- `constraint-projection`: 约束投影模块（clamping + 插值）
- `constraint-satisfaction-calculator`: 约束满足率计算器
- `ablation-visualization`: 消融实验可视化（对比柱状图）

### 修改功能
- `rag-system`: 添加 projection 模式切换

## 影响

### 代码影响
- **新增文件**: `Experiments/E5_Ablations/ablation_study.py` (~400 行)
- **修改文件**: `Source/rag_system.py` (添加 projection 开关)

### 计算资源
- **DeepSeek API**: ~500 次调用（预估成本 ￥1-2）
- **GPU**: 2-3 小时（快速实验）
- **存储**: 可忽略

### 论文影响
- **Sec 4.3**: 新增 "Ablation Study" 子节
- **Table X**: 消融实验对比表
- **Response Letter**: 支撑 "Agent 架构" claim，说明 retrieval 是核心能力

### 预期结果与风险
| 结果 | 解读 | 应对策略 |
|------|------|----------|
| Projection 带来 5-15% 增益 | ✅ 正常结果，projection 有边际价值 | 强调 "retrieval 是核心，projection 确保可执行性" |
| Projection 无显著增益 | ⚠️ 强调约束满足率提升（合法性 > 性能） | 调整 claim 为 "确保可执行性" 而非 "提升性能" |
| Projection 导致性能下降 | 🚨 检查投影是否过度约束 | 调整投影策略（更宽松的约束） |

## 预期结果

### 成功标准
- 纯检索达到 ~80% 的最终性能（证明 retrieval 是核心）
- Projection 带来 5-15% 额外改善（边际增益）
- 约束满足率显著提升（从 ~85% 到 ~98%）

### 论文价值
本实验支撑论文重新定位后的核心 narrative：
> "Agent 的核心能力是 texture-aware retrieval，projection 确保输出可执行"

而非原稿的 overclaim：
> "RAG 生成系统"
