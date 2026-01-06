# 规范：Related Work 批判性综述

## 新增需求

### 需求：RW-001 批判性分析框架
Related Work章节不能只是文献罗列，每段必须指出"根本性局限"。

#### 场景：审稿人检查批判性深度
- **当** 审稿人阅读Related Work
- **并且** 逐个检查段落
- **那么** 每段都有"What they did"描述
- **并且** 每段都有"Fundamental limitation"分析
- **并且** 每段都有"Our differentiation"说明
- **并且** 理解为什么需要新方法

#### 场景：读者建立领域认知
- **当** 非领域专家读者阅读Related Work
- **那么** 理解领域的发展脉络
- **并且** 理解现有方法的根本性局限
- **并且** 理解新方法的必要性
- **并且** 知道新方法与现有工作的区别

**验证标准**:
- 每个领域段落至少3-5个相关工作
- 每段都有明确的"Fundamental limitation"语句
- 每段都有"Our positioning"或"Our distinction"

---

### 需求：RW-002 概念框架建立
系统必须引入新的概念/框架来定位工作。

#### 场景：概念清晰性检查
- **当** 读者阅读Related Work
- **并且** 遇到新概念
- **那么** 理解"Parameter-Waveform Duality"
- **并且** 理解"Audio Modality Gap"
- **并且** 理解"Retrieval-grounded reasoning"范式
- **并且** 能够用这些概念解释工作定位

**验证标准**:
- 至少引入2个新概念/框架
- 每个概念有清晰定义
- 每个概念有具体应用示例

---

### 需求：RW-003 Positioning Table
系统必须在Related Work末尾添加对比表格。

#### 场景：快速定位检查
- **当** 审稿人或读者查看Positioning Table
- **那么** 一目了然看到5-6个相关工作
- **并且** 看到每个工作的Input/Output/Grounding/Editability
- **并且** 清楚Audio-Agent的独特性
- **并且** 理解"空白"是什么

**验证标准**:
- 表格包含5-6行（相关工作）
- 表格包含4-5列（关键维度）
- Audio-Agent行加粗或高亮
- 表格后有解释性段落

---

## 修改需求

### 需求：RW-M001 IMP领域段落重构
IMP领域段落必须从文献罗列改为批判性综述。

#### Before（避免的写法）:
"SAFE was proposed by Stables et al. for semantic audio descriptors.
Martinez et al. used deep learning for automatic mixing.
MEGAMI models mixing as a generative task..."

#### After（目标写法）:
"The challenge of translating perceptual descriptions into technical
parameters was formally characterized by Stables et al., whose SAFE
project demonstrated the feasibility of semantic-to-parameter mapping
but \textbf{did not solve} the generalization problem...

Subsequent work pursued two main directions:
\textbf{Audio Analysis Approaches}. Martinez et al. trained deep
networks... However, this approach \textit{assumes the target audio
already exists}—it cannot generate parameters from scratch...

\textbf{The LLM Frontier}. LLM2Fx investigated zero-shot LLM
prediction... While demonstrating surprising capability, these
approaches suffer from severe hallucination—up to 35\% of generated
parameters are outside valid ranges...

\textbf{Our Positioning}. Unlike prior work that treats parameter
prediction as a \textit{regression problem}, we frame it as a
\textit{retrieval-grounded reasoning problem}..."

#### 场景：批判性分析检查
- **当** 审稿人阅读IMP领域段落
- **那么** 看到对SAFE工作的分析（"did not solve generalization"）
- **并且** 看到对Audio Analysis工作的批判（"assumes target audio exists"）
- **并且** 看到对LLM工作的局限分析（"35% hallucination"）
- **并且** 理解"retrieval-grounded reasoning"范式差异

**验证标准**:
- 每个子段落有批判性分析
- 使用加粗强调关键局限
- 使用斜体强调关键概念
- 以"Our Positioning"结尾

---

### 需求：RW-M002 概念框架引入
Related Work必须引入新的概念/框架来定位Audio-Agent。

#### 需要添加的概念:
1. **Parameter-Waveform Duality** (Neural Audio段落)
   - Waveform-level: 最大灵活性，但不可编辑
   - Parameter-level: 完全可编辑，但需要领域知识
   - Audio-Agent: 结合两者优势

2. **Audio Modality Gap** (RAG段落)
   - 现有RAG: Text-only或Audio-only
   - 缺失: Dual-modal for parameter grounding
   - TRR: 解决functional similarity问题

3. **Retrieval-Grounded Reasoning** (IMP段落)
   - 传统: Regression (学习映射)
   - 生成: Generative (自回归生成)
   - 我们: Retrieval + Adaptation (检索+适应)

#### 场景：概念理解检查
- **当** 读者阅读Related Work
- **并且** 遇到新概念（Parameter-Waveform Duality等）
- **那么** 理解"Parameter-Waveform Duality"的定义和意义
- **并且** 理解"Audio Modality Gap"指代的问题
- **并且** 理解"Retrieval-Grounded Reasoning"范式
- **并且** 能够用这些概念解释Audio-Agent的定位

---

### 需求：RW-M003 Positioning Table添加
Related Work末尾必须添加对比表格。

#### 表格结构:
| Work | Input | Output | Grounding | Editability |
|------|-------|--------|-----------|------------|
| SAFE | Text | Parameters | None | Yes |
| DDSP | Audio | Parameters | None | Yes |
| LLM2Fx | Text | Parameters | None | Yes |
| AudioLDM | Text | Waveform | Pretrained | No |
| HM-RAG | Text+Doc | Text | Retrieval | N/A |
| **Audio-Agent** | **Text+Audio** | **Parameters** | **Dual-Modal RAG** | **Yes** |

#### 后续解释段落:
"Table X summarizes our positioning against prior work. Our unique
contribution is the combination of (1) \textit{dual-modal} grounding
for parameter generation, (2) \textit{texture-aware} audio retrieval
via TRR, and (3) \textit{uncertainty-aware} dynamic fusion for
robustness under degraded inputs."

#### 场景：快速定位检查
- **当** Positioning Table被查看
- **那么** 看到至少5个相关工作的对比
- **并且** 看到Input/Output/Grounding/Editability维度
- **并且** 一目了然Audio-Agent的独特性
- **并且** 理解当前研究的"空白"是什么

---

## 实现注释

### LaTeX模板
见`design.md`中的完整LaTeX示例。

### 相关文件
- `Paper/main.tex` Line 71-100（Related Work章节）
- 需要新增：Positioning Table（Table X）

### 引用检查
确保以下引用都有对应条目：
- SAFE: \citep{stables2014semantic}
- DDSP: \citep{engel2020ddsp}
- LLM2Fx: \citep{doh2025llm2fx}
- AudioLDM: \citep{liu2023audioldm}
- HM-RAG: \citep{liu2025hmrag}

---

## 验收测试

### 自动检查
- [ ] LaTeX编译无错误
- [ ] 所有\citep{}有对应条目
- [ ] Positioning Table格式正确

### 人工检查
- [ ] 每个领域段落都有批判性分析
- [ ] 每段都有"Fundamental limitation"
- [ ] 每段都有"Our positioning"
- [ ] 引入至少2个新概念
- [ ] 有Positioning Table
- [ ] Table后有解释性段落

### 内容质量检查
- [ ] 读者能理解为什么现有方法不够
- [ ] 读者能理解Audio-Agent的独特贡献
- [ ] 概念框架清晰可理解
- [ ] Positioning Table一目了然
