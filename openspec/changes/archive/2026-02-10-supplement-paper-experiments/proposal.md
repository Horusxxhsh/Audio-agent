# 补充论文实验部分

## 为什么

论文目前存在以下实验数据缺失问题：

1. **MUSHRA 主观听测实验完全缺失**：已完成 26 名被试、910 个评分样本的实验，但论文 Sec 4.5 仅标注为 "Planned"
2. **TRR 与其他方法的详细对比缺失**：实验目录包含 TRR vs MFCC vs Modulation Spectrogram 的对比数据，但论文未展示
3. **Fusion 融合权重的实际分布数据缺失**：有理论框架但缺乏实际权重分布的可视化分析
4. **TRR 层选择分析结果缺失**：Wav2Vec2 不同层的性能对比（为何第 9 层最优）未在论文展示

这些问题导致论文的实验验证不够充分，可能影响 IEEE TMM 的审稿结果。

## 变更内容

### 新增内容

1. **Sec 4.5 MUSHRA 主观听测** (新增完整章节)
   - Trial 1: 风格匹配度评分 (均值 72.92, 参考 86.85)
   - Trial 2-5: 吉他 solo 对比评分 (HCAP 71.55 vs 手动 51.72)
   - Trial 6-10: 相似度评分 (HCAP 42.31, MusicGen 41.29)
   - 26 名被试的统计分析结果

2. **Sec 4.2 TRR 方法对比** (扩展现有内容)
   - TRR vs MFCC vs Modulation Spectrogram 的 L2 误差对比
   - Wav2Vec2 层选择分析结果 (第 9 层最优原因)
   - 添加对比表格

3. **Sec 4.3 Fusion 权重分析** (扩展现有内容)
   - 熵权重的实际分布统计
   - 融合前后性能对比的量化结果
   - 添加权重分布可视化图表

4. **Sec 4.1 实验设置更新** (修正)
   - 更正测试样本数量 (从 5 个更新为 31 个)
   - 补充 MusicGen 生成数据的说明

### 修改内容

- **Paper/main.tex**: Sec 4 实验章节的全面补充
- **Paper/figures/**: 添加新的实验结果图表
- **Paper/math_commands.tex**: 可能需要添加新的数学符号

## 功能 (Capabilities)

### 新增功能

- `mushra-subsection`: MUSHRA 主观听测结果的论文展示
  - 包含 3 个 Trial 的评分统计
  - 系统级箱线图和统计表格
  - 与基线方法 (MusicGen, 手动调参) 的对比

### 修改功能

- `trr-analysis-section`: TRR 方法分析的扩展
  - 现有: 基本 Gram 矩阵算法描述
  - 变更: 添加层选择分析和对比基线数据

- `fusion-analysis-section`: Fusion 融合分析的扩展
  - 现有: 理论框架和熵加权公式
  - 变更: 添加实际权重分布数据和性能对比

## 影响

### 文件影响

- **Paper/main.tex**: Sec 4 实验章节将增加约 2-3 页内容
- **Paper/figures/**: 需要生成 3-4 个新图表
  - MUSHRA 评分箱线图 (已有数据)
  - TRR 层选择性能曲线 (需从实验数据生成)
  - Fusion 权重分布图 (需从实验数据生成)

### 引用影响

- 需要补充 MUSHRA 方法论引用
- 可能需要补充 Wav2Vec2 层分析相关引用

### 页面影响

- 当前论文约 13 页 (ICLR 格式)
- 补充后约 15-16 页，符合 IEEE TMM 初稿要求 (≤13 页可能需要精简其他部分)

### 依赖关系

- 依赖 `Experiments/mushura/results_report.md` 中的实验数据
- 依赖 `Experiments/TextureResonance/` 中的层选择分析结果
- 依赖 `Experiments/Fusion/` 中的权重可视化代码
