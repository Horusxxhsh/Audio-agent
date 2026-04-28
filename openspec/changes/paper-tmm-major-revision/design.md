## 上下文

IEEE TMM 审稿意见要求 Major Revision。审稿人提出 5 个主要问题（M1–M5）和 8 个次要问题（m1–m8）。当前论文版本（`Paper/content.tex`）使用 Protocol-A（204 queries, 1063 KB）在吉他效果数据集上评估 TRR，但基线不够强、缺少消融实验、指标未归一化、听觉测试设计有缺陷。修订稿页数上限为 16 页（双栏 10pt），比初稿多 3 页。

当前实验基础设施：
- `Experiments/common/evaluate.py` — 度量计算
- `Experiments/common/dataset_loader.py` — 数据集加载
- `Experiments/TextureResonance/texture_encoder.py` — TRR 编码器
- `Experiments/AblationStudies/direct_retrieval_comparison.py` — 检索对比
- `Experiments/mushura/mushra_analysis.py` — 听测分析

## 目标 / 非目标

**目标：**
1. 回应所有 M1–M5 主要审稿意见，使论文可被接收
2. 在现有吉他数据集上新增 near-duplicate 敏感性分析（M1）
3. 新增 PANNs、PaSST、MLP-regressor 三个基线（M2）
4. 完成 TRR 投影维度和层选择的消融实验（M3）
5. 实现归一化参数度量并报告 per-parameter 分析（M4）
6. 重组听觉测试结果的论文呈现（M5）
7. 回应所有 m1–m8 次要问题
8. 论文修订后不超过 16 页

**非目标：**
- 收集新的非吉他乐器数据集（工作量过大，在 response letter 中作为 future work 说明）
- 重新招募参与者进行新的听觉测试
- 实现端到端可微训练
- 改变 TRR 的核心算法设计

## 决策

### D1: Near-duplicate 处理策略
**选择**: 在现有 Protocol-A split 上进行敏感性分析（移除 near-dup 后对比指标变化），而非重新收集数据。
**理由**: 审稿人要求"量化影响"而非消除，且当前数据集无法轻易扩展。移除 near-dup 后如果 TRR 仍优于基线，结论更强。
**替代方案**: (A) 收集新数据集 — 时间成本太高；(B) 忽略 — 无法通过审稿。

### D2: 新基线的实现方案
**选择**: 使用 HuggingFace 预训练的 PANNs (CNN14) 和 PaSST 提取 embedding，作为 cosine 检索基线；使用 sklearn MLP 作为回归基线（输入: Wav2Vec2 mean-pooled → 输出: flattened params）。
**理由**: 与现有检索框架一致，最小代码改动；MLP 回归是最简单的 direct estimation baseline，足以说明检索 vs 回归的对比。
**替代方案**: (A) 微调模型 — 小数据集上容易过拟合且不公平；(B) 使用更复杂的回归架构 — 回归基线只需展示范式差异，不需要最优化。

### D3: 归一化方案
**选择**: 对每个参数按其 DSP 定义的物理范围 `[l_i, u_i]` 进行 min-max 归一化至 [0,1]，然后计算归一化 L2/Acc@0.1 等指标。
**理由**: 使用 DSP 物理范围而非数据观测范围更有工程意义且可复现。`PluginAudioParameters.h` 已定义所有参数范围。
**替代方案**: (A) 数据驱动归一化 — 依赖数据分布，可复现性差；(B) Z-score — 需要假设正态分布，不适合有界参数。

### D4: 消融实验设计
**选择**: 在 Protocol-A split 上做消融，每个变体使用相同的 204 test queries。投影维度 $d \in \{32, 64, 128, 256\}$；层组合: single $\{4\}, \{5\}, \{6\}$, combined $\{4,5,6\}$, deep $\{7,8,9\}$, all-layer average。投影矩阵均为 PCA（从 KB 的 Wav2Vec2 激活上拟合）。
**理由**: Protocol-A 已审计过，保持一致；PCA 是无监督的，不引入标签泄露。

### D5: 论文重组策略
**选择**: 正文保留 Trial 1 + Trials 6–10；Trials 2–5 整体移至 supplementary；删除 Sec 4.4（个性化模块）；新增 Sec 4.X（消融实验）子节。
**理由**: 节省正文空间给新实验，同时诚实保留 Trials 2–5 数据在补充材料中。

### D6: 可视化方案
**选择**: (1) t-SNE 对 TRR embedding vs Wav2Vec2 mean-pooled 的对比图（按效果类型着色）；(2) 单个代表性查询的 Gram matrix 64×64 热力图。使用 matplotlib 生成，保存为 PDF 矢量图。
**理由**: t-SNE 能直观展示 TRR 的聚类效果；Gram 热力图帮助读者理解二阶统计的含义。

## 风险 / 权衡

- **[近重复移除后样本量过小]** → 报告移除前后的样本量和 CI，如果 CI 重叠则说明结论稳健。
- **[PANNs/PaSST 在小数据集上表现可能接近 TRR]** → 如果差异不显著，诚实报告，并在讨论中解释（预训练域差异）。
- **[归一化后 TRR 优势可能缩小]** → 这恰恰是审稿人想看到的诚实结果；如果仍然显著则更有说服力。
- **[16 页限制]** → 通过删除个性化模块和精简 over-hedging 释放约 1.5 页；消融 + 新基线 + 可视化约占 2 页；整体可控。
- **[投影矩阵 PCA vs random]** → 消融实验可以顺便对比 PCA vs random projection，若有余力可加入。
