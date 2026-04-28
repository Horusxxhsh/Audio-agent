## 为什么

IEEE TMM 审稿意见要求 Major Revision，指出五个主要问题（M1–M5）和八个次要问题（m1–m8）。核心缺陷集中在：(1) 数据集仅覆盖吉他、规模小；(2) 缺少 PaSST/PANNs/回归基线；(3) TRR 的投影维度与层选择缺少消融实验；(4) 参数空间度量未归一化；(5) 听觉测试设计缺陷。现在必须逐条回应才能推进修订稿。

## 变更内容

### M1 – 数据多样性与近重复敏感性（Sec 4.1, Sec 6）
- 在当前吉他数据集上补充 **近重复敏感性分析** (near-duplicate sensitivity)：移除 200 对近重复后重新评估 Protocol-A，量化其对各指标的影响。
- 在 Limitations 中明确新增分析的结论。

### M2 – 增加强基线（Sec 4.2, Table 3）
- 增加 **PANNs** 和 **PaSST** 作为音频表示基线（提取 embedding → cosine 检索 → 同指标评估）。
- 增加至少一个 **直接参数回归基线**（MLP regressor: audio embedding → parameter vector）。
- 在 Table 3 (Protocol-A) 中更新结果。

### M3 – TRR 消融实验（Sec 4, 新增 Ablation 子节）
- **投影维度消融**: 对比 $d \in \{32, 64, 128, 256\}$ 对 Protocol-A 各指标的影响。
- **层选择消融**: 对比 single-layer ($\ell=4$, $5$, $6$), 当前组合 $\{4,5,6\}$, 及更深层组合 $\{7,8,9\}$ 和全层平均。
- **投影矩阵来源说明**: 在方法论中明确 $P$ 是随机初始化/PCA/学习的。

### M4 – 归一化参数指标（Sec 4.2, Sec 4.3）
- 对所有参数按各自取值范围进行 min-max 归一化后重新计算 L2, Acc@0.1 等指标。
- 在主表中同时报告 raw 与 normalized 指标，或以 normalized 为主表、raw 移至补充材料。
- 补充 per-parameter 误差分布分析和至少一个具体预设案例解读。

### M5 – 听觉测试改进（Sec 4.5, Supplementary）
- Trials 2–5 (vs manual) 结果 **降级为补充材料**，正文仅保留简要引用。
- 正文听觉测试聚焦 Trial 1 (style matching) 和 Trials 6–10 (vs MusicGen)。
- 补充参与者音乐经验分布统计。

### m1 – 精简 over-hedging
- 全文精简重复的限定性措辞，集中保留在 Limitations 一节。

### m2 – BibTeX 修复
- 补全所有引用的作者列表、booktitle/journal、DOI、页码。
- 修正 entry type 错误（如 `deemanat2025latent`）。

### m3 – 架构图补充
- 在 Figure 1 描述中增加效果链拓扑和参数验证机制的文字说明。

### m4 – 移除个性化模块
- 删除 Sec 4.4 (Preliminary Personalization Extension) 及相关讨论段落。

### m5 – 写作去重
- 合并重复的"异步运行"描述、删除 Table 1 改为行内文字、精简 Limitations。

### m6 – L2 量级解读
- 在 Results 后增加一个具体预设的参数对比实例（ground-truth vs TRR-retrieved vs baseline-retrieved）。

### m7 – Fusion 机制公式化
- 在 Sec 4.6 补充 fusion rule 的数学公式和伪代码。

### m8 – 增加可视化
- 新增 TRR embedding 的 t-SNE/UMAP 可视化图。
- 新增 Gram matrix 热力图示例。

## 功能 (Capabilities)

### 新增功能
- `near-duplicate-sensitivity`: 近重复敏感性分析实验——移除 200 对近重复后 Protocol-A 指标变化
- `stronger-baselines`: PANNs/PaSST/MLP-regressor 基线实验——新基线的 embedding 提取、检索评估脚本与结果
- `trr-ablation`: TRR 超参消融实验——投影维度 & 层选择的系统消融
- `normalized-metrics`: 归一化参数度量——min-max 归一化后的度量计算与 per-parameter 分析
- `trr-visualization`: TRR 嵌入与 Gram matrix 可视化——t-SNE/UMAP 图 + Gram 热力图

### 修改功能
- `mushra-subsection`: 听觉测试重组——Trials 2–5 降级至补充材料，正文聚焦 Trial 1 和 Trials 6–10
- `trr-analysis-section`: TRR 方法论完善——明确投影矩阵来源、增加消融实验结果
- `paper-ieee-template`: 论文格式与写作质量——BibTeX 修复、over-hedging 精简、写作去重、融合公式化

## 影响

- **Paper/content.tex**: 主论文内容大幅修订（Sec 3.2, 4.1–4.5, 5, 6, 7 均受影响）
- **Paper/supplementary.tex**: 补充材料新增消融表格、归一化指标表、Trials 2–5 完整结果
- **Paper/reference.bib**: 修复和补全所有 BibTeX 条目
- **Paper/figures/**: 新增 t-SNE/UMAP 图、Gram 热力图、per-parameter 误差分布图
- **Experiments/E5_Ablations/**: TRR 消融实验脚本与结果
- **Experiments/E2_SOTABaselines/**: PANNs/PaSST/MLP 基线脚本与结果
- **Experiments/common/evaluate.py**: 增加归一化度量计算逻辑
- **Experiments/TextureResonance/**: t-SNE 可视化脚本、Gram 热力图生成
