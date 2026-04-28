# `llm-ablations-and-leakage-audit` 规范

## ADDED Requirements

### 需求:必须披露 LLM prompt、输出 schema 与 token 统计，并提供可复现缓存

论文与仓库必须提供可复核的 LLM 推理细节：prompt 模板（含 few-shot 示例）、输出 JSON schema、以及输入/输出 token 长度统计；LLM 的逐 query 输出必须可缓存并可在无网络条件下复现后续分析。

#### 场景:LLM 配置走环境变量且默认不触发网络

- **当** 运行包含 LLM 的实验脚本（Protocol-B/Protocol-C）
- **那么** API Key 与 base_url 必须从环境变量读取（禁止硬编码在脚本中）
- **并且** 默认配置下不应自动发起 211 次网络调用（必须提供显式开关或缓存优先策略）

#### 场景:逐 query LLM 输出缓存

- **当** 脚本对某个 query 发起一次 LLM 推理并得到输出
- **那么** 必须将该输出以可追踪格式缓存到本地（例如 JSON），并包含：
  - query 标识（SongName 或等价 ID）
  - 使用的 prompt 版本/哈希
  - 模型名称与关键参数（温度等）
  - 原始文本输出与解析后的结构化输出

### 需求:必须增加 “Top-K mean/weighted mean” 对照以验证 LLM 推理有效性

为了回答“LLM 是否仅起到平滑作用”的质疑，Protocol-B 必须包含一个不调用 LLM 的强对照：对检索得到的 Top-K 参数做均值/加权均值聚合并投影（Projection），与 “LLM rewrite + Projection” 在同一 held-out pool（N=211）上进行配对对比与统计检验。

#### 场景:LLM vs 非 LLM 聚合对照

- **当** 作者运行 Protocol-B 的消融实验
- **那么** 输出结果必须至少包含三组方法：
  - `retrieval + projection`（不使用 LLM）
  - `top-k mean/weighted-mean + projection`（不使用 LLM）
  - `LLM rewrite + projection`
- **并且** 报告三者在 `L2`（主指标）上的 paired 检验与 95% CI

### 需求:必须提供 few-shot 泄漏审计与 w/o few-shot 对照

为了排查 few-shot / prompt 泄漏，仓库必须提供自动化审计脚本验证：
- few-shot 示例与 held-out queries 完全去重（文本与样本 ID 层面）
- 报告 overlap=0 的审计输出

同时必须提供一个 “w/o few-shot” 的对照实验，用于量化 few-shot 对结果的影响边界。

#### 场景:泄漏审计输出可追溯

- **当** 作者运行泄漏审计脚本
- **那么** 脚本必须输出一份可存档的报告（JSON/MD），至少包含：
  - few-shot 样本列表
  - held-out 测试集列表（N=211）
  - overlap 统计（应为 0）
  - 如非 0，列出冲突项并使 CI 阶段失败（非零即阻断）

