# `latency-profiling` 规范

## ADDED Requirements

### 需求:必须报告端到端与分模块 latency（median/p95）

论文必须补充系统延迟评估：在标准硬件上报告端到端 latency 与关键子模块耗时（至少包含 Gram/TRR 计算、KNN 检索、LLM 调用、Projection、DSP 渲染），并同时报告 median 与 p95。

#### 场景:生成可直接写入论文的 latency 表

- **当** 作者运行 latency profiling 脚本
- **那么** 必须产出一份表格数据（CSV/JSON/Markdown 均可）包含：
  - 每个模块的 median (ms) 与 p95 (ms)
  - 端到端 median (ms) 与 p95 (ms)
  - 运行次数（repetitions）与 warm-up 次数
  - 硬件信息（CPU/GPU/内存）与软件环境（OS/Python 版本）

#### 场景:LLM latency 必须可控且可复现

- **当** latency 表包含 LLM 调用耗时
- **那么** 必须同时提供：
  - “使用缓存输出（无网络）”的耗时
  - “真实 API 调用（含网络）”的耗时（如作者选择报告）
- **并且** 论文必须声明该耗时受网络与 API 端波动影响的边界

