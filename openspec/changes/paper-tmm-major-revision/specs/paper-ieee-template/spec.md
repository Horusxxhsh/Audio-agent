## MODIFIED Requirements

### 需求：论文必须使用官方 IEEE Transactions LaTeX 模板并锁定版本

（保持原始需求不变）

#### 场景：模板版本固定
- **当** 用户在任意机器上编译论文
- **那么** `Paper/main.tex` 必须优先使用仓库内的 `Paper/IEEEtran.cls`

## ADDED Requirements

### 需求:必须修复所有 BibTeX 条目质量问题

`Paper/reference.bib` 中所有引用必须包含完整的作者列表（禁止用 "others" 省略已知作者）、正确的 entry type（article vs inproceedings）、DOI/页码/卷号（如可获取）。

#### 场景:BibTeX 质量检查
- **当** 在 `reference.bib` 中搜索 "others"
- **那么** 匹配数量必须为 0（所有作者列表已补全或使用标准 "and others" 仅在作者超过 6 人时）
- **当** 检查 entry 类型
- **那么** 期刊论文必须使用 `@article`，会议论文必须使用 `@inproceedings`，预印本必须使用 `@misc`

### 需求:必须精简论文中的 over-hedging 措辞

论文全文必须精简重复性限定措辞。以下短语在正文中出现次数禁止超过合理阈值：
- "currently evaluated" — 最多 2 次
- "pilot benchmark" — 最多 1 次
- "boundary-condition analysis" — 最多 2 次
- "supportive perceptual context" — 最多 1 次

#### 场景:over-hedging 精简验证
- **当** 对论文正文全文搜索上述短语
- **那么** 每个短语的出现次数必须不超过指定阈值

### 需求:必须消除论文中的重复描述

论文必须消除以下重复内容：(1) "检索系统异步运行"在 Sec 4.1 和 Sec 4.5 中重复出现——必须合并为仅在一处保留；(2) Table 1（Parameter-Waveform Duality）必须删除并改为行内文字描述。

#### 场景:重复内容消除验证
- **当** 在论文中搜索"asynchronous"或"异步"
- **那么** 相关描述必须仅出现在一处（Sec 4.1 的 Design Principle 2）
- **当** 检查 Table 1
- **那么** 该表格必须被删除，其内容以行内文字形式融入 Sec 2 的讨论中

### 需求:必须为 fusion 机制补充数学公式

论文 Sec 4.6（Multimodal Fusion）必须包含 fusion rule 的数学公式或伪代码，而非仅描述为"quality-aware fallback rule"。

#### 场景:Fusion 公式呈现
- **当** 读者阅读 Sec 4.6
- **那么** 必须看到 fusion 权重计算的数学公式（如 $w_{\text{text}} = f(\cdot)$, $w_{\text{audio}} = g(\cdot)$）和最终 score 的组合方式

### 需求:必须删除个性化模块描述

论文正文必须删除 Sec 4.4（Preliminary Personalization Extension）及其在 Discussion 和 Limitations 中的所有引用。

#### 场景:个性化模块移除验证
- **当** 在论文正文中搜索 "personalization" 或 "memory mechanism"
- **那么** 匹配结果必须为 0（除非在 Future Work 中有一句简要提及）

### 需求:必须在架构图描述中补充效果链细节

Figure 1 的 caption 或正文描述必须补充说明 DSP engine 的具体效果链拓扑和参数验证机制。

#### 场景:架构图文字丰富化
- **当** 读者阅读 Figure 1 的 caption 和周围文字
- **那么** 必须能理解：(1) 效果链包含哪些模块（如 EQ → Compressor → Delay → Reverb）；(2) 参数验证的具体方式（clamping + constraint check）
