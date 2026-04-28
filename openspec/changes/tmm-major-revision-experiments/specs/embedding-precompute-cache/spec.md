# `embedding-precompute-cache` 规范

## ADDED Requirements

### 需求:必须提供 PaSST/PANNs embedding 的离线预计算与缓存工具

系统必须提供一个可复现的离线预计算脚本，用于在现有音频资产上生成 PaSST 与 PANNs 的音频 embedding 缓存，并在后续检索评测中复用缓存以避免重复计算。

该工具禁止改变数据集样本本身（不新增/删除音频，不改写 `Parameters` 与历史 `Vectors`）；仅允许生成新的本地缓存工件（例如 `*.npy`）。

#### 场景:对 `Data/Audio_Synthetic/*.wav` 生成 sidecar 缓存

- **当** 作者指定音频目录 `Data/Audio_Synthetic/` 并运行预计算脚本
- **那么** 脚本必须为每个可处理的 wav 生成可复用缓存（命名需确定性），至少包括：
  - `*.wav.passt.npy`
  - `*.wav.panns.npy`
- **并且** 缓存的 embedding 维度必须在脚本输出中明确打印/记录（便于复现与 sanity check）

#### 场景:断点续跑与覆盖率报告

- **当** 预计算脚本在中途被中断后再次运行
- **那么** 脚本必须默认跳过已存在且可读的缓存文件，仅计算缺失项（可通过显式参数强制重算）
- **并且** 输出覆盖率报告：
  - 总 wav 数
  - PaSST 缓存命中数/缺失数
  - PANNs 缓存命中数/缺失数
  - 缺失项列表（可选，至少支持写入到文件）

#### 场景:缓存不进入 Git（默认策略）

- **当** 脚本生成 embedding 缓存
- **那么** 项目必须提供默认的忽略策略（例如 `.gitignore`）以防止大体量缓存被误提交到 Git

