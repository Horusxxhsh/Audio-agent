## 为什么

当前 Audio-Agent 系统在处理用户个性化偏好和多轮交互时缺乏演进能力。系统目前是一个“静态检索器”，对于同一查询始终返回相同结果，且无法记录和复用用户的手动微调（Manual Tweaks）。在学术叙事上，增加 Memory 模块可以将系统从简单的“工具”拔高为“具有演进能力的智能体 (Adaptive Agent)”，并能有效解决 TRR 检索结果虽在纹理上接近但可能不完全符合用户特定审美偏好的问题。通过引入基于纹理感知的记忆机制，系统可以实现“越用越聪明”的闭环。

## 变更内容

本变更将引入一套全自动的自适应记忆 RAG (Adaptive Memory RAG) 框架：
1. **记忆存储协议**：设计并实现 TAM (Texture-Aware Memory) 模块，支持存储 (TRR-Vector, Text-Query, User-Adjusted-Params) 三元组。
2. **检索演进逻辑**：修改 `AudioRAGSystem`，在检索时并行搜索静态知识库 (KB) 和 TAM 缓冲区，并优先推荐 Memory 中的记录。
3. **仿真实验框架**：编写全自动模拟脚本，通过“伪用户模拟”产生 L2 收敛曲线、跨会话泛化矩阵以及索引策略消融数据。
4. **论文叙事更新**：在 `Paper/main.tex` 中增加 "Adaptive Executable Memory" 章节，并将系统重命名为 "Adaptive Audio-Agent"。

## 功能 (Capabilities)

### 新增功能
- `texture-aware-memory`: 负责存储和索引用户的音频处理偏好，使用二阶统计特征 (Gram Matrix) 作为关键索引。
- `pseudo-user-simulation`: 自动化的评估环境，模拟人类反馈循环以生成科研数据。

### 修改功能
- `trr-analysis-section`: 将 TRR 从单一检索算法扩展为支持动态记忆的检索骨干。
- `neuro-symbolic-architecture`: 在系统架构中显式增加闭环反馈（Feedback Loop）和记忆缓冲区（Memory Buffer）。

## 影响

- **系统架构**：`AudioRAGSystem` 类将新增对 TAM 集合的操作逻辑。
- **科研产出**：将产生新的实验结果报告 `Experiments/llm_cache/memory_convergence_report.md` 及对应的 LaTeX 图表。
- **依赖项**：ChromaDB 需要增加新的 Collection 以支持 TAM 存储。
