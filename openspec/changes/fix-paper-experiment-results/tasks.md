## 1. 移除 CLAP 基线

- [ ] 1.1 在 Paper/content.tex 的 Table I (main_results) 中移除 CLAP (KNN) 行（约第 427 行）
- [ ] 1.2 更新 Table I 中 "Improvement over Text-RAG" 的数值（移除 CLAP 后重新计算）

## 2. 使用 N=5 的 LLM 修正成功结果

- [ ] 2.1 在 Paper/content.tex 的 Table II (llm_enhancement) 中替换为 N=5 的数据（约第 500 行）
  - 纯 TRR 检索: L2=0.4104, Acc=0.7381, Recall=0.7101, Cosine=0.7430, Module=0.7833
  - TRR+LLM: L2=0.2631, Acc=0.8156, Recall=0.7101, Cosine=0.8115, Module=1.0000
  - Pure Text Retrieval: L2=0.4396, Acc=0.6645, Recall=0.5717, Cosine=0.6425, Module=0.6833
  - Text+LLM: L2=0.2769, Acc=0.7180, Recall=0.6178, Cosine=0.7821, Module=1.0000
- [ ] 2.2 在 Section 4.2 中添加说明这是基于 5 个代表性样本的 Pilot Study 结果
- [ ] 2.3 更新 LLM 改善效果的描述：
  - L2 误差降低 35.9% (从 0.4104 降至 0.2631)
  - Module Consistency 从 78.33% 提升至 100%
  - 准确率提升 10.5% (从 0.7381 升至 0.8156)

## 3. 说明 Fusion 在标准场景下的表现

- [ ] 3.1 在 Paper/content.tex 的 Section 4.3 中添加 Fusion 在 Standard 场景下的表现说明（约第 621 行后）
  - 添加：Standard 场景下 0 个查询表现更好
  - 添加：Standard 场景下 18 个查询表现更差
  - 说明：Fusion 的优势主要体现在降质场景 (Vague Text, Noisy Audio)

## 4. 在 Limitations 中添加 LLM 修正的样本量限制

- [ ] 4.1 在 Paper/content.tex 的 Section 6 (Limitations) 中添加关于 LLM 修正样本量的讨论
  - 说明当前的 LLM 修正成功结果基于 N=5 样本
  - 讨论扩展到更大样本集 (N=211) 时的挑战
  - 说明需要进一步研究以提高 LLM 修正在大规模数据上的稳定性

## 5. 验证和编译

- [ ] 5.1 编译 Paper/main.tex 确保 LaTeX 无错误
- [ ] 5.2 检查所有修改后的表格和段落格式正确
- [ ] 5.3 验证参考文献和交叉引用正确
