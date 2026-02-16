# Spec: Experimental Evaluation Expansion

## 概述
扩展实验评估，解决缺少音频质量评估、数据集规模不足、基线方法选择不当、过高性能可信度等问题。

---

## 新增需求

### 需求：音频质量客观指标计算

**优先级**: 必须
**风险**: 中（需要学习新的评估工具）
**依赖**: 无

#### 场景：评估生成音频的感知质量

**Given**：审稿人指出"仅使用参数距离评估不够，需要音频质量指标"

**When**：评估Audio-Agent生成音频的质量

**Then**：
- 计算Frechet Audio Distance (FAD) between generated和target audio
- 计算Mel-Cepstral Distortion (MCD)作为补充指标
- 在所有50个测试样本上计算指标

**Acceptance Criteria**:
- [ ] FAD实现并验证（使用参考实现）
- [ ] MCD实现并验证
- [ ] 结果表格显示Audio-Agent和所有baselines的FAD/MCD
- [ ] 分析Audio-Agent是否在音频质量上也优于baselines

**技术细节**:
```python
# FAD calculation (示例)
from frechet_audio_distance import FrechetAudioDistance
fid = FrechetAudioDistance(
    model_name="vggish",
    use_pca=False,
)
fad_score = fid.calculate(
    background_stats,  # from target audio
    test_stats         # from generated audio
)
```

---

### 需求：生成音频示例

**优先级**: 必须
**风险**: 低
**依赖**: 无

#### 场景：提供可听的音频证据

**Given**：审稿人希望听到生成音频的质量

**When**：阅读论文后想验证claims

**Then**：
- 选择20-30个代表性样本
- 生成Audio-Agent和baseline方法的音频
- 提供在线播放页面

**Acceptance Criteria**:
- [ ] 至少20个音频样本可在线访问
- [ ] 每个样本有target, Audio-Agent, baseline1, baseline2四个版本
- [ ] 音频格式：44.1kHz, stereo, WAV或MP3
- [ ] 提供批量下载zip文件

**样本选择策略**:
- Stratified sampling by style (clean, distortion, modulation, etc.)
- 确保覆盖Audio-Agent和baselines的性能范围
- 包含一些interesting failure cases

---

### 需求：小规模MUSHRA主观测试

**优先级**: 可选（如果时间允许）
**风险**: 中（需要招募测试者）
**依赖**: 生成音频示例

#### 场景：获取主观听感评分

**Given**：客观指标（FAD, MCD）不能完全反映感知质量

**When**：需要验证生成音频在human listeners的感知质量

**Then**：
- 设计MUSHRA测试协议
- 招募5-10名测试者（音乐背景）
- 收集和分析主观评分

**Acceptance Criteria**:
- [ ] 测试协议文档（包括instructions, training, scoring）
- [ ] 至少5名测试者完成测试
- [ ] 统计分析显示Audio-Agent是否显著优于baselines
- [ ] 补充材料中报告MUSHRA结果

**MUSHRA设计**:
- 每个测试者听20个样本
- 每个样本有4个版本（target, hidden reference, Audio-Agent, baseline）
- 评分范围：0-100（bad to excellent）
- 训练阶段：3个practice samples

---

### 需求：数据集扩展至200+样本

**优先级**: 必须
**风险**: 高（数据收集可能困难）
**依赖**: 无

#### 场景：提高数据集的统计显著性和代表性

**Given**：审稿人指出"50样本不足以支撑统计显著性结论"

**When**：重新训练和评估系统

**Then**：
- 收集150+新样本（总计200+）
- 确保覆盖多种乐器和效果类型
- 在扩展数据集上重新评估所有方法

**Acceptance Criteria**:
- [ ] Dataset size ≥ 200 samples
- [ ] 覆盖至少4种乐器（guitar, bass, keyboard, vocal）
- [ ] 覆盖至少5种效果类型（distortion, modulation, delay, reverb, compression）
- [ ] 新实验结果表格（Table 2 updated）

**数据来源**:
- Guitar Pedal Archives (online presets)
- Neural DSP presets (commercial)
- Self-collected presets (if allowed)

**质量控制**:
- 每个preset有清晰的style tag
- 每个preset有可播放的音频demo
- 排除质量差的音频（noise, clipping）

---

### 需求：Train/Test Split策略明确化

**优先级**: 必须
**风险**: 低
**依赖**: 数据集扩展

#### 场景：确保无data leakage

**Given**：审稿人担心"过高的性能可能是data leakage导致的"

**When**：设计实验的train/test split

**Then**：
- 使用artist-based split（80/20 artists）
- 验证test preset的风格不在train中出现
- 报告split策略

**Acceptance Criteria**:
- [ ] Split策略文档在Methodology或Experiments章节
- [ ] 验证脚本确认无overlap
- [ ] 报告train/test/val的size和distribution

**验证方法**:
1. Check preset name overlap
2. Check audio similarity (cosine similarity < 0.95)
3. Check parameter similarity (L2 distance > 0.1)

---

### 需求：Cross-Validation评估

**优先级**: 强烈建议
**风险**: 中（计算成本高）
**依赖**: 数据集扩展

#### 场景：评估性能的稳定性

**Given**：单次split的结果可能偶然

**When**：需要证明性能稳定可靠

**Then**：
- 实现5-fold cross-validation
- 报告mean ± std across folds
- 分析性能的方差

**Acceptance Criteria**:
- [ ] 5-fold cross-validation完成
- [ ] 结果表格显示mean ± std
- [ ] std < 0.1 (stable performance)
- [ ] 分析哪些folds性能最好/最差及原因

**Cross-validation设计**:
- 每个fold保持artist-based split
- 每个fold有stratified sampling by style
- 报告per-fold results在supplementary material

---

### 需求：DDSP-SFX Baseline实现

**优先级**: 强烈建议
**风险**: 中（复现可能困难）
**依赖**: 无

#### 场景：与最新的blind parameter estimation方法比较

**Given**：peladeau2024blind提出了blind audio effect parameter estimation

**When**：评估Audio-Agent的相对性能

**Then**：
- 复现DDSP-SFX方法
- 适配到我们的setting（如果有reference audio）
- 在我们的数据集上测试

**Acceptance Criteria**:
- [ ] DDSP-SFX baseline可运行
- [ ] 结果表格显示DDSP-SFX的性能
- [ ] 分析DDSP-SFX与Audio-Agent的优缺点

**适配策略**:
- 原始方法：audio → parameters (blind)
- 适配版本：如果有reference audio，直接用；如果只有text，用text-to-audio模型生成reference

---

### 需求：ST-ITO Baseline实现

**优先级**: 强烈建议
**风险**: 中（optimization slow）
**依赖**: 无

#### 场景：与inference-time optimization方法比较

**Given**：benetos2024stito提出了optimization-based parameter inference

**When**：评估optimization是否优于retrieval

**Then**：
- 复现ST-ITO方法
- 使用TRR作为pre-trained representation加速
- 在我们的数据集上测试

**Acceptance Criteria**:
- [ ] ST-ITO baseline可运行
- [ ] 结果表格显示ST-ITO的性能
- [ ] 分析optimization time vs. quality trade-off

**简化策略**:
- 完整ST-ITO需要每分钟音频10+分钟优化
- 简化版：先用TRR找到top-1 neighbor，再用ST-ITO微调
- 预期：秒级完成

---

### 需求：Supervised Regression Baseline

**优先级**: 建议
**风险**: 低
**依赖**: 无

#### 场景：与纯监督学习方法比较

**Given**：Retrieval-based方法可能不如直接regression

**When**：评估regression baseline

**Then**：
- 训练一个regression model（MLP或gradient boosting）
- 从text/audio features直接预测参数
- 在我们的数据集上测试

**Acceptance Criteria**:
- [ ] Regression baseline训练完成
- [ ] 结果表格显示regression的性能
- [ ] 分析regression为何优于/劣于retrieval

**Model design**:
- Input: SBERT text embedding + Wav2Vec2 audio embedding
- Output: Parameter vector (concatenated)
- Loss: L2 distance
- Training: 80% data, testing: 20% data

---

## 实施顺序

### Phase 1: 基础评估（必须）
1. 音频质量客观指标 → 可立即开始
2. 生成音频示例 → 可并行进行

### Phase 2: 数据集扩展（必须）
3. 数据集扩展 → 需要时间，优先开始
4. Train/Test Split策略 → 依赖数据集扩展
5. Cross-Validation → 依赖数据集扩展

### Phase 3: Baseline补充（强烈建议）
6. DDSP-SFX Baseline → 可与Phase 1-2并行
7. ST-ITO Baseline → 可与Phase 1-2并行
8. Supervised Regression → 可与Phase 1-2并行

### Phase 4: 主观测试（可选）
9. MUSHRA测试 → 依赖生成音频示例

---

## 验证清单

### 实验完整性
- [ ] 至少2个objective audio metrics已计算
- [ ] 至少20个audio samples可访问
- [ ] Dataset size ≥ 200
- [ ] 至少2个新baselines已比较
- [ ] Cross-validation结果显示性能稳定

### 结果可信度
- [ ] Split策略已文档化
- [ ] Data leakage已验证排除
- [ ] 所有实验可复现（参数设置完整）

### 结果报告
- [ ] 所有新结果已添加到论文
- [ ] Table 2已更新（包含新baselines和新数据集）
- [ ] 补充材料包含音频示例链接
