# Design: 修复ESWA审稿意见中的关键Gap

## 架构概览

本文档记录修复审稿gap过程中的关键架构决策和技术选择。

---

## 1. 理论论证增强

### 1.1 TRR理论依据

#### 设计决策：采用多层论证策略

**问题**：审稿人质疑为何图像领域的Gram矩阵可以直接迁移到音频域。

**方案**：从三个角度论证TRR的合理性

1. **信号处理角度**：
   - 音频纹理的定义：time-invariant的统计特性
   - 二阶统计（correlation）比一阶统计（mean）更能捕获texture
   - 类比：modulation spectrogram也是捕获temporal modulation patterns

2. **神经科学角度**：
   - auditory cortex对声音的texture编码类似于visual cortex对texture的编码
   - 引用文献：McDermott et al. (2013) "Auditory texture perception"

3. **实证角度**：
   - 消融实验：Gram matrix vs. mean pooling vs. MFCC temporal patterns
   - 案例研究：Stadium Rock等texture-sensitive样本

**权衡**：
- ✅ **优点**：多角度论证更有说服力
- ❌ **缺点**：需要更多文献调研和实验
- 📊 **影响**：增加1-2页Methodology内容

#### 设计决策：层选择分析

**问题**：为何选择Wav2Vec2的第9层？

**方案**：系统性实验 + 理论解释

1. **实验**：测试第6、7、8、9、10层的检索性能
2. **解释**：
   - 浅层（1-5）：low-level特征，过于generic
   - 中层（6-9）：mid-level特征，平衡semantic和acoustic
   - 深层（10+）：high-level语义，丢失texture细节
3. **结论**：第9层在semantic和texture之间达到最佳平衡

**数据需求**：
- 在50个样本上测试5层 = 250次检索实验
- 计算成本：约2-3小时GPU时间

### 1.2 Dual-Modal Fusion机制

#### 设计决策：Uncertainty量化方法

**问题**：如何量化retrieval uncertainty？

**方案选择**：使用entropy of similarity distribution

```
Given: top-K similarities s_1, s_2, ..., s_K
Step 1: Normalize to probabilities: p_i = s_i / Σ_j s_j
Step 2: Compute entropy: u = -Σ_i p_i * log(p_i)
```

**为什么选择entropy**：
- ✅ 理论基础：information theory的标准uncertainty度量
- ✅ 计算简单：O(K) time complexity
- ✅ 可解释：高entropy = flat distribution = uncertain

**替代方案（未采用）**：
- Variance of similarities：对分布形状敏感，不够robust
- Gap between top-1 and top-2：只考虑top-2，浪费信息

#### 设计决策：Fusion weight计算

**方案**：Exponential decay with temperature β

```
w_text = exp(-β * u_text)
w_audio = exp(-β * u_audio)
normalize: w_text + w_audio = 1
```

**参数设置**：
- β = 1.0（默认值，可调整）
- β越大 → 对uncertainty越敏感
- β = 0 → 等权重（不考虑uncertainty）

**为何Module Consistency可能下降**：
- Hypothesis 1：当两个模态都uncertain时，fusion可能引入噪声
- Hypothesis 2：某些样本text和audio原本就矛盾，强制fusion有害
- **需要验证**：分析失败案例

### 1.3 Constraint Repair

#### 设计决策：Interpolation策略

**问题**：如何将invalid parameter投影回valid space？

**方案**：Gradient-free interpolation towards nearest valid neighbor

```
Algorithm:
1. Identify violated constraints
2. Find nearest valid neighbor in database (by L2 distance)
3. Interpolate: θ_new = (1-α)*θ_invalid + α*θ_neighbor
4. Repeat until all constraints satisfied or α < threshold
```

**参数**：
- α = 0.1（interpolation step size）
- threshold = 0.01（convergence criterion）

**为何不用gradient-based方法**：
- ❌ DSP parameter space不一定可微（离散参数）
- ❌ 需要定义可微的constraint函数（complex）
- ✅ Database-lookup方法简单、可解释、保证收敛

**正确性保证**：
- **Property 1**: 算法在有限步内收敛
- **证明**：每次迭代都向valid space靠近，且database有限

---

## 2. 实验评估扩展

### 2.1 音频质量评估

#### 设计决策：选择哪些客观指标？

**方案**：组合使用多个互补指标

| 指标 | 全称 | 测量什么 | 为什么选择 |
|------|------|---------|-----------|
| FAD | Frechet Audio Distance | overall perceptual similarity | state-of-the-art for audio generation |
| MCD | Mel-Cepstral Distortion | spectral envelope similarity | sensitive to timbre changes |
| LSD | Log-Spectral Distance | spectral shape similarity | interpretable (dB scale) |

**为什么不选择其他指标**：
- SNR/SSNR：需要clean reference，不适用于creative audio effects
- PESQ：设计用于speech quality，不适用于music
- STOI：设计用于speech intelligibility，不适用于music

**实现细节**：
```python
# FAD计算
from frechet_audio_distance import FrechetAudioDistance
fid = FrechetAudioDistance(
    model_name="vggish",  # 或 "enet"
    use_pca=False,
    use_activation=True,
)
fad_score = fid(background_embeddings, test_embeddings)
```

#### 设计决策：音频示例选择策略

**问题**：从200+样本中选择20-30个作为示例

**方案**：Stratified sampling by style categories

1. **分类**：将样本按风格分组（clean, distortion, modulation, etc.）
2. **采样**：从每个类别随机选择2-3个样本
3. **覆盖**：确保覆盖Audio-Agent和所有baseline方法

**展示格式**：
- 在线HTML页面：每个样本有4个音频（target, Audio-Agent, baseline1, baseline2）
- 提供下载链接：zip文件包含所有wav文件
- **可选**：添加blind test模式（隐藏label）

### 2.2 数据集扩展

#### 设计决策：扩展策略

**目标**：从50样本扩展至200+样本

**方案**：Purposive sampling + random sampling

1. **Purposive sampling（100样本）**：
   - 确保覆盖under-represented效果类型
   - 例如：增加modulation effects（chorus, phaser, tremolo）
   - 增加 multi-effect chains（同时使用2-3个效果）

2. **Random sampling（50+样本）**：
   - 从更大的preset库中随机抽取
   - 确保distribution的真实性

**新样本来源**：
- Guitar Pedal Archives（在线preset数据库）
- Neural DSP presets（commercial presets）
- Self-collected presets（如果允许）

**质量控制**：
- 每个preset必须有清晰的style tag
- 每个preset必须有可播放的音频demo
- 排除质量差的音频（noise, clipping）

#### 设计决策：Split策略

**问题**：如何确保train/test split无data leakage？

**方案**：Artist-based split

1. **Grouping**：将preset按artist/album分组
2. **Split**：80% artists in train, 20% artists in test
3. **验证**：确保test preset的风格不在train中出现

**为什么不用random split**：
- ❌ Random split可能导致similar presets在train和test中
- ❌ 会inflated performance（overestimate generalization）

**Cross-validation**：
- 5-fold cross-validation
- 每个fold保持artist-based split
- 报告mean ± std across folds

### 2.3 Baseline补充

#### 设计决策：如何实现DDSP-SFX baseline？

**挑战**：peladeau2024blind是blind estimation，不需要text/audio query

**方案**：Adapter to our setting

1. **原始方法**：audio → parameters（blind）
2. **适配**：使用reference audio的style作为condition
   - 如果有reference audio：直接用DDSP-SFX估计
   - 如果只有text：使用text-to-audio模型（如AudioLDM）生成reference

**为什么这个adapter合理**：
- DDSP-SFX本身是audio-to-parameter
- 我们的RAG也是基于audio reference
- Fair comparison：都是基于audio的parameter estimation

#### 设计决策：如何实现ST-ITO baseline？

**挑战**：benetos2024stito需要inference-time optimization

**方案**：Simplified version for fair comparison

1. **原始方法**：optimization loop + pre-trained audio representation
2. **简化**：使用我们的TRR作为pre-trained representation
3. **步骤**：
   - 用TRR找到top-1 neighbor
   - 用ST-ITO的optimization微调参数

**为什么简化**：
- 完整ST-ITO需要每分钟音频10+分钟优化时间
- 简化版可以在秒级完成
- 仍是valid baseline：显示optimization是否带来提升

### 2.4 过高性能问题排查

#### 设计决策：如何验证无data leakage？

**方案**：多层次的验证

1. **Level 1: Check preset overlap**
   - 确保test preset name不在train database中

2. **Level 2: Check audio similarity**
   - 计算test audio和所有train audio的similarity
   - 如果max similarity > 0.95 → flag as potential leak

3. **Level 3: Check parameter similarity**
   - 计算test parameters和所有train parameters的L2 distance
   - 如果min distance < 0.01 → flag as potential leak

4. **Level 4: Human verification**
   - 随机抽样10个test cases
   - 人工检查是否有similar train cases

**如果发现leakage**：
- 重新做split
- 更严格地grouping
- 报告honest analysis（即使影响性能）

---

## 3. 文献综述更新

### 3.1 文献搜索策略

#### 设计决策：如何系统性地搜索最新工作？

**方案**：Multi-source search + snowballing

**Primary sources**：
1. **arXiv**：
   - Keywords: "neural audio effects", "parameter estimation", "audio texture"
   - Categories: cs.SD, eess.AS
   - Time range: 2023-2024

2. **Google Scholar**：
   - Keywords: "audio DSP parameter learning", "neural audio synthesis"
   - Filter: "Since 2023"

3. **Conference proceedings**：
   - NeurIPS 2023, 2024 (audio/music track)
   - ICLR 2024 (audio/music papers)
   - ICML 2024 (audio/music papers)

**Snowballing**：
- 从找到的论文的references中搜索
- Forward search: 哪些论文citing these papers

**筛选标准**：
- 必须与parameter estimation或audio texture相关
- 必须有实验结果（不是purely theoretical）
- 优先选择peer-reviewed papers

### 3.2 分类框架

#### 设计决策：如何组织新引用？

**方案**：按research direction分类

1. **Neural Audio Effect Parameter Estimation**：
   - DDSP-SFX, ST-ITO, 及其后续工作
   - Focus on inverse problem

2. **Neural Audio Synthesis**：
   - AudioLDM 2, AudioCraft, 及2024年的新模型
   - Focus on controllability

3. **Audio Representation Learning**：
   - CLAP variants (ReCLAP, M2D-CLAP之后的工作)
   - Focus on text-audio alignment

4. **LLM Agents for Audio**：
   - 新兴的LLM-as-agent framework
   - Focus on tool use and reasoning

**在论文中的位置**：
- Section 2.1: IMP（补充parameter estimation新工作）
- Section 2.2: Neural Audio Synthesis（更新2024年工作）
- Section 2.3: LLM Agents（新增subsection）

---

## 4. 写作质量改进

### 4.1 数据一致性

#### 设计决策：如何统一Abstract和Table的数据？

**方案**：Single source of truth

1. **创建results_summary.yaml**：
   ```yaml
   zero_shot:
     param_distance: 42.67
     acc_01: 0.12
     cosine: 0.45
     module_consistency: 0.48
   audio_agent:
     param_distance: 0.0980
     acc_01: 0.7271
     cosine: 0.9706
     module_consistency: 0.9333
   ```

2. **从YAML生成LaTeX表格和Abstract文本**
   - 确保一致性
   - 易于更新

**改进百分比计算**：
- 明确是relative improvement: (old - new) / old
- 例如：(42.67 - 0.0980) / 42.67 = 99.77%
- 不使用模糊的"35%"（除非明确基准）

### 4.2 Limitations结构

#### 设计决策：如何组织Limitations章节？

**方案**：6个独立limitations，每个都包含impact和mitigation

1. **Dataset coverage**：
   - 限制：仅限guitar effects
   - 影响：泛化到其他乐器未知
   - 缓解：未来work扩展到其他乐器

2. **Parameter identifiability**：
   - 限制：many-to-one mapping（不同参数可能产生相似声音）
   - 影响：parameter distance不是perfect proxy
   - 缓解：结合subjective evaluation

3. **Computational cost**：
   - 限制：TRR extraction和retrieval需要GPU
   - 影响：实时性受限
   - 缓解：cache embeddings，优化retrieval

4. **Subjectivity of tone quality**：
   - 限制："good" sound depends on context
   - 影响：objective metrics不能capture全部
   - 缓解：user study with musicians

5. **Editability-synthesis trade-off**：
   - 限制：参数level控制牺牲了波形level的灵活性
   - 影响：无法生成全新的声音
   - 缓解：结合waveform synthesis作为补充

6. **Dependence on database quality**：
   - 限制：retrieval quality depends on preset database diversity
   - 影响：out-of-distribution tones可能失败
   - 缓解：持续扩展database

### 4.3 图表设计

#### Figure 2: Experimental Setup Pipeline

**设计决策**：4-quadrant layout

```
┌─────────────────┬─────────────────┐
│  Top-Left:      │  Top-Right:     │
│  Parameter DB   │  Audio DB       │
│  (CSV/JSON)     │  (Vectors + TRR)│
├─────────────────┼─────────────────┤
│  Bottom-Left:   │  Bottom-Right:  │
│  Dataset Const. │  Eval Pipeline  │
│  (Merge + Split)│  (RAG → Metrics)│
└─────────────────┴─────────────────┘
```

**Color coding**：
- Parameter data: Blue
- Audio data: Orange
- Processing: Green
- Evaluation: Red

#### Figure 4: Metric Computation

**设计决策**：2x2 grid, one per metric

```
┌─────────────────┬─────────────────┐
│  Parameter      │  Acc@0.1        │
│  Distance       │                 │
├─────────────────┼─────────────────┤
│  Cosine Sim     │  Active Recall  │
│                 │                 │
└─────────────────┴─────────────────┘
```

**每个子图包含**：
- 公式
- 几何解释（如果是distance/similarity）
- 示例向量
- 结果值示例

---

## 5. 风险缓解策略

### 5.1 时间风险

**风险**：新实验可能超出预期时间

**缓解**：
- MVP approach：先实现minimum viable improvements
- Parallelization：尽可能并行独立任务
- Time boxing：为每个任务设置time limit
- **Fallback**：如果时间不够，优先Phase 1和2，Phase 3可简化

### 5.2 结果风险

**风险**：新实验可能不支持现有结论

**缓解**：
- 诚实报告：即使结果negative也要report
- 分析原因：解释为何新实验结果不同
- 调整claim：适度降低某些strong claim
- **Fallback**：如果结果严重矛盾，考虑major revision of approach

### 5.3 资源风险

**风险**：音频质量评估需要计算资源

**缓解**：
- Pre-trained models：使用existing FAD implementation
- Subsampling：不需要在所有200+样本上计算
- Cloud resources：使用Google Colab或AWS
- **Fallback**：如果不能计算FAD，用更简单的指标替代

---

## 6. 成功标准

### 6.1 Phase 1成功标准

- [ ] TRR理论论证至少有2篇文献支撑
- [ ] 消融实验显示TRR相对mean pooling有>10%改进
- [ ] Fusion算法有完整数学公式
- [ ] Constraint Repair有algorithm pseudocode

### 6.2 Phase 2成功标准

- [ ] 至少2个objective audio metrics已计算
- [ ] 至少20个audio samples可访问
- [ ] Dataset size ≥ 200
- [ ] 至少2个新baselines已比较
- [ ] Cross-validation std < 0.1 (stable performance)

### 6.3 Phase 3成功标准

- [ ] Related Work增加≥10篇2023-2024论文
- [ ] 每个新方向有≥2篇代表性论文

### 6.4 Phase 4成功标准

- [ ] 所有identified issues已修正
- [ ] 所有missing figures已补充
- [ ] 全文数据一致性验证通过

---

## 7. 未来扩展（可选）

如果时间允许，考虑以下扩展：

1. **User Study**：
   - 招募10-20名guitarists
   - 测试Audio-Agent的实用性和满意度
   - 预期时间：2-3周

2. **Real-time Demo**：
   - 创建interactive demo网站
   - 用户可以输入text/upload audio，听到generated audio
   - 预期时间：1-2周

3. **开源Release**：
   - 整理代码并开源
   - 发布dataset和pre-trained models
   - 预期时间：1周

4. **扩展到其他乐器**：
   - 收集bass, keyboard, vocal的presets
   - 验证方法在其他乐器上的泛化性
   - 预期时间：3-4周
