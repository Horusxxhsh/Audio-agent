# Audio-Agent 论文合规审计与证据映射（避免学术不端）

本文件用于把 `Paper/main.tex` 中的**每一条关键主张**映射到**必须具备的证据产物**（代码、数据、实验日志、统计检验、听测材料），并给出**保守替代表述**。原则：**没有证据就不写成结论**，只能写“我们计划/我们正在进行/我们提出”。  

> 审计范围：当前仓库版本下的 `Paper/main.tex`（IEEEtran 模板草稿）。

---

## 1. 快速结论（当前最需要修正的风险点）

- 摘要中出现 “subjective listening tests demonstrate ...” 的确定性陈述，但仓库内未见听测数据/统计脚本/结果文件：`Paper/main.tex:31`
- 贡献点中出现 “ensuring ...” “significantly reducing ...” 等**强因果/显著性**措辞，但缺少与之绑定的结果表与统计：`Paper/main.tex:54`
- TRR 小节中使用 “The results demonstrate ... confirming ...” 的结论性措辞，且表格数值未在论文中链接到可复现实验产物：`Paper/main.tex:109`

---

## 2. 主张-证据对照表（Claim → Evidence → 当前状态 → 建议写法）

> “当前状态”分为：
> - **代码可支撑**：仓库中存在实现，论文可以写“我们提出/我们实现了”
> - **实验可支撑（需固化）**：已有实验脚本/分析草案，但需补齐可复现日志与配置
> - **缺证据**：仓库内没有对应产物，不能写成结论

### 2.1 摘要（Abstract）

1) **主张**：进行了“extensive objective experiments and subjective listening tests”，并“demonstrate”优于基线。  
   - 位置：`Paper/main.tex:31`  
   - 需要证据：
     - 客观实验：可复现实验命令、固定数据划分、seed、输出表（CSV/JSON）、绘图脚本
     - 主观听测：受试者招募标准、刺激音频集、随机化协议、评分表、统计检验（p 值/效应量）
   - 当前状态：**客观实验：实验脚本存在但需固化；主观听测：缺证据**
   - 安全替代表述（建议直接改摘要）：
     - “Objective evaluations show …; subjective listening tests are planned / are ongoing.”
     - 或 “We conduct objective evaluations and release a protocol for subjective tests.”

### 2.2 贡献点（Contributions）

2) **主张**：架构“ensuring that all outputs are fully improved and editable”。  
   - 位置：`Paper/main.tex:54`  
   - 需要证据：这属于不可证的“全称保证”，除非你定义“improved”的客观指标并在所有测试集上成立。  
   - 当前状态：**缺证据**（且不建议做全称保证）
   - 安全替代表述：
     - “enabling fully editable, standard DAW-compatible parameter outputs”

3) **主张**：Dual-Modal RAG “significantly reducing parameter hallucination”。  
   - 位置：`Paper/main.tex:55`  
   - 需要证据：
     - 定义“hallucination”度量（如：约束违背率、无效参数率、Active Recall、与参考参数距离）
     - 与基线对比 + 显著性/置信区间
   - 当前状态：**实验可支撑（需固化）**（仓库有 baseline/ablation 脚本，但论文未绑定具体结果）
   - 安全替代表述：
     - “helps reduce invalid or incoherent parameter settings by grounding generation in retrieved exemplars”

4) **主张**：Adaptive Preference Learning “updates its retrieval weights online”。  
   - 位置：`Paper/main.tex:56`  
   - 需要证据：代码实现 + 交互评测协议（多轮收敛曲线/满意度）。  
   - 当前状态：**代码可支撑**（accept/edit/reject 与偏好排序存在），但“在线更新权重”的精确定义需与实现一致。  
   - 写作注意：
     - 若实现只是“排序优先级”或“写入新样本”，不要写成“学习到最优权重/优化”。

### 2.3 实验与 TRR 小节

5) **主张**：TRR 小节“conducted a comparative experiment…”，并用表格数值支撑结论。  
   - 位置：`Paper/main.tex:109`  
   - 需要证据：
     - 实验脚本 + 配置（数据如何合成、seed、评测函数）
     - 结果输出文件与生成表格的脚本（从原始结果生成 LaTeX table）
   - 当前状态：**实验可支撑（需固化）**（仓库存在 TRR demo/合成数据脚本，但论文未指向产物）
   - 安全替代表述：
     - “We report preliminary results on synthetic data, suggesting …”

6) **主张**：解释性因果（“failed likely due to mean-pooling …”）。  
   - 位置：`Paper/main.tex:127`  
   - 需要证据：这属于“机理解释”，建议用更弱的措辞或提供额外分析（例如特征可视化、检索分布、消融）。  
   - 当前状态：**实验可支撑（需固化）**
   - 安全替代表述：
     - “We hypothesize that …; additional analysis is provided in Sec. X / Appendix.”

---

## 3. 你们现在可以“合法写”的内容（无需额外实验即可陈述）

以下属于“实现型事实”，只要代码存在且与你们描述一致，就可以写在论文里：

- RAG 使用向量库（ChromaDB）管理音乐知识与参数预设：`Source/rag_system.py:1`
- 有 RAG 集成接口与上下文拼接策略：`Source/rag_integration.py:1`
- 有 accept/edit/reject 反馈字段与排序/存储逻辑：`Source/rag_integration.py:206`、`Source/llm.py:774`
- 有 TRR/texture 编码与 demo 脚本：`Experiments/TextureResonance/texture_encoder.py:1`、`Experiments/TextureResonance/run_trr_demo.py:1`
- 有 baseline/ablation 运行脚本框架：`Experiments/BaselineComparison/run_baseline.py:1`、`Experiments/AblationStudies/run_ablation.py:1`

写作建议：这类内容用 “we implement / we build / we introduce a system that …” 的措辞，避免 “we demonstrate SOTA / significant”。

---

## 4. 需要补齐的“证据产物”清单（做到这些才可写强结论）

### 4.0 投稿就绪核对表（建议按勾选推进）

- [ ] 固定数据划分（train/val/test）并写入 `Experiments/common/dataset_loader.py` 的配置或一个独立配置文件
- [ ] 每次实验输出原始逐样本结果（`results.csv`/`results.jsonl`），包含样本 ID、prompt、reference、预测参数、GT 参数、各指标
- [ ] 从原始结果自动生成论文表格（脚本生成 `Paper/figures/` 与 LaTeX table），避免手填数字
- [ ] 报告均值 + 置信区间/标准差，并在论文中写明统计方法
- [ ] 若主张“显著提升/显著降低幻觉”：提供显著性检验或 bootstrap CI
- [ ] 若主张“听感更好”：完成 MOS/MUSHRA，保存匿名化评分表与统计脚本
- [ ] 若主张“个性化有效”：完成多轮交互实验并报告收敛曲线
- [ ] 记录运行环境（依赖版本、模型版本、随机种子、硬件），保证可复现

### 4.1 客观实验（必需）

- 固定数据划分与版本号（train/val/test；避免同源泄漏）
- 固定随机种子（seed）并记录
- 统一评测脚本输出 `results.csv`（每个样本一行）
- 表格/图从 `results.csv` 自动生成（保证可追溯）

### 4.2 主观听测（若投 TASLP/强音频期刊，强烈建议）

- 受试者数量与经验分层
- 刺激集合与随机化顺序
- MUSHRA/MOS 表单与统计检验（Wilcoxon/t-test；报告 p 值 + 效应量）

### 4.3 强基线（建议，能显著降低被否定概率）

- 更强音频 embedding 检索（如 CLAP/PANNs/PaSST）或
- 黑盒参数优化（CMA-ES/BayesOpt）作为“物理匹配对照/上界”

---

## 5. 建议的“保守写法模板”（可直接复制到论文）

- **没做听测**：  
  “We conduct objective evaluations on X; a subjective listening study is planned/ongoing following the protocol in Appendix.”

- **有脚本但结果未固化**：  
  “We report preliminary results using our current experimental pipeline; we will release the full configuration and logs upon publication.”

- **机理解释**：  
  “We hypothesize that …, supported by …; further analysis is left for future work.”

---

## 6. 建议的下一步（最小改动即可显著降低不端风险）

1. 先把 `Paper/main.tex` 中的强结论降级为保守措辞（特别是摘要与贡献点）。  
2. 把 TRR/ablation 的表格从“手写数字”改为“脚本生成”，并在附录给出复现实验命令。  
3. 在完成听测前，不要在摘要/结论中写 “subjective listening tests demonstrate …”。  
