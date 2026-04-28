## 1. 记忆模块基础设施 (TAM)

- [ ] 1.1 在 ChromaDB 中创建 `user_preference_memory` 集合
- [ ] 1.2 在 `AudioRAGSystem` 中实现 `save_to_memory` 方法，支持三元组存储
- [ ] 1.3 修改检索逻辑，实现 Memory-First 并行搜索与排序

## 2. 伪用户仿真框架

- [ ] 2.1 编写 `Source/simulate_user_feedback.py` 脚本
- [ ] 2.2 实现 L2 距离驱动的反馈函数 $	heta_{new} = 0.5 	heta_{ret} + 0.5 	heta_{target}$
- [ ] 2.3 实现多轮迭代（5-10轮）的自动化评估循环

## 3. 个性化实验与数据产出

- [ ] 3.1 运行个性化收敛实验，记录 Turn vs. L2 数据
- [ ] 3.2 运行跨会话泛化实验，验证纹理相似输入的记忆命中率
- [ ] 3.3 运行索引策略消融实验 (TRR vs. Text vs. Mean-pooling)
- [ ] 3.4 产出 CSV 报告并使用 `matplotlib` 生成收敛曲线图

## 4. 论文叙事与架构更新

- [ ] 4.1 更新 `Paper/content.tex` 中的系统总览图（Figure 1），增加闭环箭头
- [ ] 4.2 在 Methodology 章节增加 3.5 节 "Adaptive Executable Memory"
- [ ] 4.3 在 Experiments 章节增加 4.6 节 "Memory & Personalization Analysis"
- [ ] 4.4 全文批量将 "Audio-Agent" 更新为 "Adaptive Audio-Agent" 并修正摘要
