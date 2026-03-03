# `mushra-subsection` 规范（增量）

## MODIFIED Requirements

### 需求：论文必须包含完整的 MUSHRA 主观听测结果

论文 Sec 4.5 必须基于现有 `Experiments/mushura/mushra.csv` 报告主观评分结果，但术语必须收敛为 **Multiple‑Stimulus Listening Test with Hidden Reference**（由于缺少标准低通 anchor，禁止在正文中将其表述为标准 ITU‑R BS.1534 MUSHRA）。结果必须按 Trial 分组展示，并补齐重复测量统计检验与多重比较校正。

#### 场景：术语与设计边界声明

- **当** 读者阅读 Sec 4.5 的实验命名与设置
- **那么** 必须看到：
  - 术语：Multiple‑Stimulus Listening Test with Hidden Reference
  - 明确声明：未包含显式低质量 anchor（因此非标准 MUSHRA）
  - 隐藏参考（Hidden Reference）的存在与用途说明

#### 场景：Trial 分组结果 + 重复测量统计

- **当** 读者阅读 Sec 4.5 的 Trial 结果（Trial 1、Trial 2–5、Trial 6–10）
- **那么** 每组必须包含：
  - 描述性统计（mean/median/std）与样本量说明
  - 系统级对比（基于被试内均值或等价重复测量口径）
  - 重复测量统计检验：
    - Friedman 总检验（或等价重复测量非参数检验）
    - 若总检验显著，post‑hoc 的 paired Wilcoxon signed‑rank（或等价），并进行 Holm 校正
  - 至少报告核心对比对（例如 HCAP vs baseline）的校正后 p-value 与效应量

### 需求：必须包含 MUSHRA 方法论说明

论文必须在 Sec 4.5 方法段落中补齐听音测试的方法论披露：参与者背景、训练流程、随机化、时长控制与评分解释；并提供听音界面截图作为补充材料。

#### 场景：方法论披露完整

- **当** 读者阅读 Sec 4.5 的方法论说明
- **那么** 必须看到：
  - 参与者人数与基本背景（例如音乐/音频经验分布）
  - 训练/练习试次说明
  - 刺激呈现与系统顺序的随机化策略
  - 单次实验的时长控制与完成标准
  - 数据清洗规则（例如去除误入表头行）

#### 场景：界面截图可审计

- **当** 作者在补充材料中提供听音实验细节
- **那么** 必须包含至少一张界面截图（或等价 UI 描述），能够让审稿人理解：
  - Hidden Reference 的呈现方式
  - 评分滑块范围（0–100）
  - 系统命名与刺激排列方式

### 需求：图表必须符合 IEEE TMM 格式要求

所有听音结果图表必须符合 IEEE TMM 格式要求，并在图注中标注 Trial 组别与统计口径（被试内聚合口径、CI/p-value 披露位置）。

#### 场景：图注包含统计口径

- **当** 论文引用系统级箱线图（例如 `system_boxplot_*.png`）
- **那么** 图注必须标明：
  - 对应 Trial 组别
  - 统计口径（被试内均值、重复测量）
  - 统计检验结果所在位置（主文或补充材料）

