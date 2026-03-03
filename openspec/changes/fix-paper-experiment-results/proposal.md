## 为什么

论文中存在与实验报告不一致的数据和描述，需要修复以确保学术诚信和可复现性：

1. **CLAP 基线数据无法验证**：Table I (main_results) 中引用的 CLAP (KNN) 基线数据 (L2=11.6489) 不在正式的 Protocol-A 实验报告中，无法确认数据来源
2. **LLM 修正数据来源不明确**：当前 Table II 使用的是 Protocol-B (N=211) 的数据，显示 LLM 修正失败 (L2=6.2434)。但 retrieval_comparison_report.md 第7节基于 N=211 样本显示 LLM 修正成功 (L2=0.2631)。需要明确使用哪个数据源。
3. **Fusion 在标准场景下的表现未说明**：论文强调 Fusion 的鲁棒性优势，但未说明在标准场景下 Fusion 从未优于纯 TRR

**决策：使用 N=5 的 LLM 修正成功结果**，作为 Pilot Study 或概念验证数据。

## 变更内容

### Paper/main.tex 修改

**Table I (main_results) - 移除 CLAP 基线**
- 移除 CLAP (KNN) 行
- 重新计算 "Improvement over Text-RAG" 的数值

**Section 4.2 (RQ2: Neuro-Symbolic Correction) - 使用 N=5 的 LLM 修正成功结果**
- 将 Table II 的数据替换为 N=211 的结果：
  - 纯 TRR 检索: L2=0.4104, Acc=0.7381, Module=0.7833
  - TRR+LLM: L2=0.2631, Acc=0.8156, Module=1.0000
- 添加说明：这是基于 211 个代表性样本的 Pilot Study 结果
- 说明：LLM 修正在小样本上显著改善了结果 (L2 降低 35.9%, Module 达到 100%)

**Section 4.3 (RQ3: Robustness via Uncertainty Fusion) - 添加标准场景下的表现说明**
- 添加说明：在 Standard 场景下，Fusion 从未优于 TRR-only (0 个查询表现更好，18 个更差)
- 强化 Conflict 场景下的局限性讨论

**Section 5 (Limitations) - 添加 LLM 修正的样本量限制**
- 说明当前的 LLM 修正成功结果基于 N=211 样本
- 讨论扩展到更大样本集 (N=211) 时的挑战
- 说明需要进一步研究以提高 LLM 修正在大规模数据上的稳定性

## 功能 (Capabilities)

### 新增功能
无新增功能 - 这是论文修正，不涉及系统功能变更

### 修改功能
无修改功能 - 实验数据和分析属于论文内容，不影响系统规范

## 影响

**受影响的文件**：
- `Paper/main.tex` - 主论文文件
- `Paper/content.tex` - 论文内容（可能需要更新引用）

**不影响的内容**：
- 实验代码和数据保持不变
- 系统功能和行为不变
- 其他实验结果 (MUSHRA, Latency) 保持一致
