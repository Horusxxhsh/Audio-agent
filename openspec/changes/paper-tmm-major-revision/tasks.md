## 1. 实验基础设施准备

- [x] 1.1 在 `Experiments/common/evaluate.py` 中增加归一化度量模式：读取参数范围配置，支持 min-max 归一化后计算 L2/Acc@0.1/Recall/Cosine/Module
- [x] 1.2 创建参数范围配置文件 `Experiments/common/param_ranges.json`，从 `Source/PluginAudioParameters.h` 提取每个参数的 [min, max]
- [x] 1.3 实现 near-duplicate 识别工具 `Experiments/common/near_dup_filter.py`：基于 cheap fingerprint 识别并输出 near-dup 对列表

## 2. M1 – 近重复敏感性分析

- [x] 2.1 编写 `Experiments/E5_Ablations/near_dup_sensitivity.py`：加载 Protocol-A split → 移除 near-dup → 对 5 种方法重新检索 → 输出去重前后对比表
- [ ] 2.2 运行实验并保存结果到 `Experiments/E5_Ablations/near_dup_sensitivity_report.md`
- [x] 2.3 在 `Paper/content.tex` Sec 4.1 新增近重复敏感性段落，引用对比表格
- [x] 2.4 在 `Paper/supplementary.tex` 新增近重复分析的完整统计表（含 bootstrap CI）

## 3. M2 – 新增强基线

- [x] 3.1 编写 `Experiments/E2_SOTABaselines/panns_baseline.py`：加载预训练 CNN14 → 提取 KB+query embedding → cosine 检索 → Protocol-A 评估
- [x] 3.2 编写 `Experiments/E2_SOTABaselines/passt_baseline.py`：加载预训练 PaSST → 提取 embedding → cosine 检索 → Protocol-A 评估
- [x] 3.3 编写 `Experiments/E2_SOTABaselines/mlp_regressor_baseline.py`：Wav2Vec2 mean-pooled → MLP → flattened params → Protocol-A 评估（KB-only 训练）
- [ ] 3.4 运行三个基线实验，保存结果到 `Experiments/E2_SOTABaselines/sota_baselines_report.md`
- [x] 3.5 更新 `Paper/content.tex` Table 3（Protocol-A 主表）新增 PANNs/PaSST/MLP-Regressor 三行
- [x] 3.6 更新 `Paper/supplementary.tex` 中对应的 CI 表和显著性检验表

## 4. M3 – TRR 消融实验

- [x] 4.1 编写 `Experiments/E5_Ablations/trr_projection_dim_ablation.py`：对比 d∈{32,64,128,256} 的 Protocol-A 性能
- [x] 4.2 编写 `Experiments/E5_Ablations/trr_layer_selection_ablation.py`：对比 6 种层组合的 Protocol-A 性能
- [x] 4.3 编写 `Experiments/E5_Ablations/trr_projection_type_ablation.py`：对比 PCA vs random projection
- [ ] 4.4 运行所有消融实验，保存结果到 `Experiments/E5_Ablations/trr_ablation_report.md`
- [x] 4.5 在 `Paper/content.tex` Sec 4 新增消融实验子节（Sec 4.X Ablation Studies），包含三个消融表格
- [x] 4.6 在 `Paper/content.tex` Sec 3.2 (TRR 方法描述) 中明确投影矩阵 P 为 frozen random projection，修正维度为 32

## 5. M4 – 归一化指标与案例解读

- [ ] 5.1 使用归一化模式重新运行 Protocol-A 所有方法的评估，保存结果
- [x] 5.2 生成 per-parameter 误差分布分析脚本 `Experiments/E5_Ablations/per_param_analysis.py`
- [ ] 5.3 运行 per-parameter 分析，生成按参数类别分组的误差图保存到 `Paper/figures/per_param_error_dist.pdf`
- [x] 5.4 更新 `Paper/content.tex` Protocol-A 主表：使用归一化指标或同时报告 raw+normalized
- [x] 5.5 在 `Paper/content.tex` Results 段落新增具体预设案例解读（ground-truth vs TRR vs baseline 的参数值对比）

## 6. M5 – 听觉测试重组

- [x] 6.1 将 `Paper/content.tex` 中 Trials 2–5 的完整结果（表格+统计+图）移至 `Paper/supplementary.tex`
- [x] 6.2 在 `Paper/content.tex` 正文听觉测试部分替换为一句引用 supplementary 的简要说明
- [x] 6.3 在正文 Trial 1 和 Trials 6–10 描述中补充参与者音乐经验分布统计
- [x] 6.4 检查听测日志提取参与者自报告音乐经验数据（如有），更新脚本 `Experiments/mushura/mushra_analysis.py`

## 7. 可视化新增 (m8)

- [x] 7.1 编写 `Experiments/TextureResonance/trr_tsne_visualization.py`：生成 TRR vs Wav2Vec2 mean-pooled 的 t-SNE 对比图
- [x] 7.2 编写 `Experiments/TextureResonance/gram_matrix_heatmap.py`：生成代表性查询的 Gram matrix 热力图
- [ ] 7.3 运行可视化脚本，保存图到 `Paper/figures/trr_vs_wav2vec_tsne.pdf` 和 `Paper/figures/gram_matrix_examples.pdf`
- [x] 7.4 在 `Paper/content.tex` 中引用两个新 Figure（t-SNE 在 Results/Discussion，Gram 热力图在 Methodology）

## 8. 论文写作修订 (m1–m7)

- [x] 8.1 精简 `Paper/content.tex` 中 over-hedging 措辞：将重复限定词减少到阈值以内
- [x] 8.2 修复 `Paper/reference.bib` 所有条目：补全作者列表、修正 entry type、增加 DOI/页码
- [x] 8.3 在 Figure 1 描述文字中补充 DSP 效果链拓扑和参数验证机制
- [x] 8.4 删除 `Paper/content.tex` Sec 3.3（Preliminary Personalization Extension）及相关引用
- [x] 8.5 消除重复描述：合并"异步运行"为仅在 Design Principle 2 处保留；删除 Table 1 改为行内文字
- [x] 8.6 在 Sec 4.6 (Fusion) 补充 fusion rule 的数学公式和伪代码
- [x] 8.7 更新 Abstract 以反映修订后的实验内容（新基线、消融、归一化指标）

## 9. 最终检查

- [ ] 9.1 编译 `Paper/main.tex` 确认无 LaTeX 错误、所有图表引用正确
- [ ] 9.2 检查修订稿页数不超过 16 页（双栏 10pt）
- [ ] 9.3 运行 over-hedging 短语计数脚本验证阈值
- [x] 9.4 起草 Response to Reviewers letter 框架（逐条对应 M1–M5, m1–m8）
