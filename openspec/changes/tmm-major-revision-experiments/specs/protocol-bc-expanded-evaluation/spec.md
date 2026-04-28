# `protocol-bc-expanded-evaluation` 规范

## ADDED Requirements

### 需求:Protocol-B/Protocol-C 必须默认在 held-out N=211 上评测

LLM+Projection（Protocol-B）与 stress tests（Protocol-C）必须默认使用与 Protocol-A 相同的 held-out query pool（N=211），以满足统计功效与可比性要求；历史 N=5/N=30 子集仅允许作为诊断用途（不得作为主表证据）。

#### 场景:默认运行即为 N=211

- **当** 作者在无额外参数情况下运行 Protocol-B/Protocol-C 的实验脚本
- **那么** 脚本必须默认选择 held-out pool（N=211）作为测试集
- **并且** 在控制台与输出工件中显式记录 `N_test=211` 与 `N_kb=1267-211`

#### 场景:允许覆写测试集但必须显式声明

- **当** 作者通过 `--test_list`（或等价参数）覆写测试集
- **那么** 脚本必须在输出工件中记录测试集来源（文件路径或 split 名称）
- **并且** 论文表注必须同步声明该表使用的具体测试集口径

### 需求:Protocol-B/Protocol-C 必须输出逐 query CSV 并生成统计报告

Protocol-B/Protocol-C 的每个实验必须输出逐 query 指标工件（CSV），并基于逐 query 数据生成统计报告（至少包含 95% CI 与 paired 显著性检验结果）。

#### 场景:逐 query CSV 与统计报告可复算

- **当** 作者完成一次 Protocol-B 或 Protocol-C 评测
- **那么** 必须产出：
  - 逐 query CSV（每个 query × method 一行）
  - 统计报告（Markdown 或 JSON），包含：
    - 主指标 `L2` 的 95% CI
    - paired 显著性检验的 p-value
    - 多重比较校正后的 p-value（Holm 或等价方法）

### 需求:跨协议禁止比较绝对 L2

论文与表注必须明确：`L2` 等绝对数值仅在同一 protocol 内可比，跨 protocol 仅允许比较“同协议内的相对变化”或使用独立的归一化/比值指标。

#### 场景:表注双重封堵

- **当** 论文中出现 Protocol-A/B/C 的多张结果表
- **那么** 每张表的 caption 必须标注协议标签（例如 `Protocol-A/B/C`）
- **并且** 正文必须包含统一声明：禁止跨协议横向对比绝对 `L2`

