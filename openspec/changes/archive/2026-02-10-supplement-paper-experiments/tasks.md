# 论文实验补充任务清单

## 1. MUSHRA 主观听测结果 (Sec 4.5)

- [x] 1.1 从 `Experiments/mushura/results_report.md` 提取 Trial 1 统计数据
- [x] 1.2 从 `Experiments/mushura/results_report.md` 提取 Trial 2-5 统计数据
- [x] 1.3 从 `Experiments/mushura/results_report.md` 提取 Trial 6-10 统计数据
- [x] 1.4 在 Paper/main.tex 中创建 Sec 4.5 MUSHRA 结果章节
- [x] 1.5 添加 Trial 1 风格匹配度评分表格和箱线图引用
- [x] 1.6 添加 Trial 2-5 吉他 solo 对比评分表格和箱线图引用
- [x] 1.7 添加 Trial 6-10 相似度评分表格和箱线图引用
- [x] 1.8 添加 MUSHRA 方法论说明（被试、流程、评分标准）
- [x] 1.9 复制箱线图到 Paper/figures/ 目录 (如需要)

## 2. TRR 方法分析扩展 (Sec 4.2)

- [x] 2.1 运行 `Experiments/TextureResonance/compare_texture_representations.py` 获取对比数据
- [x] 2.2 运行 `Experiments/TextureResonance/layer_selection_analysis.py` 获取层选择数据
- [x] 2.3 生成 TRR vs 基线方法对比表格
- [x] 2.4 生成 Wav2Vec2 层选择性能曲线图
- [x] 2.5 在 Sec 4.2 中添加基线对比表格
- [x] 2.6 在 Sec 4.2 中添加层选择分析说明和图表
- [x] 2.7 在 Sec 4.2 中添加 TRR 计算复杂度分析

## 3. Fusion 融合分析扩展 (Sec 4.3)

- [x] 3.1 运行 `Experiments/Fusion/fusion_weight_visualization.py` 生成权重分布数据
- [x] 3.2 生成文本-音频模态权重统计表（均值、标准差、范围）
- [x] 3.3 生成融合权重分布可视化图（箱线图或小提琴图）
- [x] 3.4 运行消融实验获取 Text-only、Audio-only、Fusion 的性能对比
- [x] 3.5 生成融合前后性能对比表格
- [x] 3.6 在 Sec 4.3 中添加权重分布统计和图表
- [x] 3.7 在 Sec 4.3 中添加融合效果对比表格
- [x] 3.8 添加不确定性量化分析（高/低不确定性场景的权重分配）

## 4. 实验设置修正 (Sec 4.1)

- [x] 4.1 在 Sec 4.1 中更新测试样本数量描述（5 → 31）
- [x] 4.2 添加 MusicGen 生成数据的说明
- [x] 4.3 检查并更新所有相关的样本数量引用

## 5. 图表生成和整理

- [x] 5.1 生成 TRR 层选择性能曲线图 → `Paper/figures/trr_layer_selection.pdf`
- [x] 5.2 生成 Fusion 权重分布图 → `Paper/figures/fusion_weight_distribution.pdf`
- [x] 5.3 复制 MUSHRA 箱线图到 `Paper/figures/` 目录
- [x] 5.4 检查所有图表符合 IEEE TMM 格式（标题、轴标签、分辨率）

## 6. 格式调整和优化

- [x] 6.1 转换论文为 IEEE TMM 模板（如需要）
- [x] 6.2 调整图表尺寸适应双栏格式
- [x] 6.3 检查页数是否符合 ≤13 页要求
- [x] 6.4 如超出页数，精简 Sec 2 Related Work
- [x] 6.5 整理补充材料（详细统计、额外图表）
- [x] 6.6 检查所有图表编号连续
- [x] 6.7 检查所有公式、定理编号正确

## 7. 验证和检查

- [x] 7.1 编译 Paper/main.tex 检查无错误
- [x] 7.2 检查所有图表引用正确
- [x] 7.3 检查所有表格数据正确
- [x] 7.4 对照规范 `specs/mushra-subsection/spec.md` 验证 Sec 4.5
- [x] 7.5 对照规范 `specs/trr-analysis-section/spec.md` 验证 Sec 4.2
- [x] 7.6 对照规范 `specs/fusion-analysis-section/spec.md` 验证 Sec 4.3
- [x] 7.7 检查 IEEE TMM 投稿要求（EDICS、ORCID、摘要长度）
