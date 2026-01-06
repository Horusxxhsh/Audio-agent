# 规范：Introduction 章节增强

## 新增需求

### 需求：INTRO-001 叙事张力建立
系统（Introduction章节）必须在开头3段建立"紧迫感"，使读者理解问题的重要性。

#### 场景：读者在30秒内理解问题重要性
- **当** 读者打开论文，阅读Introduction前3段
- **那么** 理解"Creativity-Complexity Paradox"矛盾
- **并且** 看到具体量化数据（40%时间浪费）
- **并且** 理解为什么这个问题很重要（creativity bottleneck）
- **并且** 想要继续阅读解决方案

---

### 需求：INTRO-002 具体场景和人物
系统必须使用具体场景和人物使问题更具共鸣。

#### 场景：独立吉他手的困境
- **当** 读者阅读Introduction具体场景描述
- **那么** 能够想象独立吉他手的具体挑战
- **并且** 理解参数爆炸的复杂性（8-15参数）
- **并且** 理解语义歧义的困扰（"breakup"的多义性）
- **并且** 共情问题的现实性

---

### 需求：INTRO-003 Hallucination量化表格
系统必须提供表格展示LLM参数生成的幻觉问题。

#### 场景：审稿人评估问题严重性
- **当** 审稿人阅读Introduction
- **并且** 遇到Hallucination表格
- **那么** 看到具体的Violation Rate（8-18%）
- **并且** 理解Zero-shot LLM的不可靠性
- **并且** 认可需要Grounding机制的必要性

**验证标准**:
- 表格包含至少3个参数类型
- 显示Valid Range
- 显示LLM错误输出示例
- 显示Violation Rate百分比

---

## 修改需求

### 需求：INTRO-M001 开头3段重写
Introduction开头必须从平铺直叙改为建立张力的叙事结构。

#### Before（当前）:
"The evolution of digital audio processing has fundamentally transformed music production... This complexity creates a persistent semantic gap..."

#### After（目标）:
"Professional music production faces a fundamental paradox. On one hand, modern Digital Audio Workstations (DAWs) provide unprecedented creative control... On the other hand, this very abundance has created a cognitive barrier..."

#### 场景：叙事张力验证
- **当** 检查Introduction开头3段
- **那么** 使用"Paradox"概念
- **并且** 包含对比（control vs barrier）
- **并且** 包含具体数字（0.01dB）
- **并且** 包含专业术语对比

---

### 需求：INTRO-M002 Contributions清晰对应
Contributions段落必须确保每个贡献对应一个具体问题。

#### 场景：贡献点清晰性检查
- **当** 审稿人阅读Contributions段落
- **那么** 每个贡献都有明确的标签（Theoretical/Algorithmic等）
- **并且** 每个贡献都有具体数字（35% improvement）
- **并且** 每个贡献都提到验证方法
- **并且** 理解每个贡献解决的具体问题

**验证标准**:
- 贡献1: TRR + 35% improvement + style-consistent retrieval
- 贡献2: Dual-Modal + 42% robustness improvement
- 贡献3: Evaluation Protocol + multi-dimensional
- 贡献4: Open System + extensible framework

---

## 实现注释

### LaTeX模板
见`design.md`中的完整LaTeX示例。

### 相关文件
- `Paper/main.tex` Line 43-69（Introduction章节）
- 需要新增：Hallucination表格（Table 1）

### 依赖关系
- 前置：无
- 后续：Related Work需要呼应Introduction提出的问题

---

## 验收测试

### 自动检查
- [ ] LaTeX编译无错误
- [ ] 所有引用有对应的\cite{}命令
- [ ] 表格编号连续

### 人工检查
- [ ] 开头3段建立紧迫感
- [ ] 有具体场景和人物
- [ ] 有Hallucination表格
- [ ] Contributions段落结构清晰
- [ ] 每个贡献有验证数字
