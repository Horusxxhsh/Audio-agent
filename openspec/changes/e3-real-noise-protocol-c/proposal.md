## 为什么

IEEE TMM 审稿人明确否定原有 Protocol-C 设计 **C4: "噪声鲁棒性设定不真实"** —— "Noisy Audio 通过对 TRR embedding 加高斯噪声来模拟音频退化，这不是现实噪声模型...表 VIII 中 97%/95% 改善容易成为人为设置导致的胜利"。审稿人要求换成对输入音频加噪/压缩/混响/截断并重新编码，而非对 embedding 加噪。本实验是回应 C4 的必须重做项，不做会导致 Reject。

## 变更内容

### 新增内容
- **Audio Degradation Pipeline**: 实现 4 类真实音频退化
  - **AWGN**: 加性高斯白噪声 (SNR: 20dB, 10dB, 5dB)
  - **MP3 Compression**: MP3 压缩 (比特率: 128k, 64k, 32k)
  - **Reverberation**: 房间混响 (RT60: 0.3s 小房间, 0.6s 中房间, 1.0s 大厅)
  - **Truncation**: 音频截断 (保留 50%, 30%)

- **Protocol-C Redesign**: 完全重做鲁棒性测试协议
  - 对原始音频施加退化
  - 重新通过 Wav2Vec2 → Gram 矩阵编码
  - 对比自适应融合 vs 固定权重的性能差异

### 关键修改
- 不再对 embedding 空间加噪（被审稿人明确否定）
- 退化后重新编码，模拟真实场景

## 功能 (Capabilities)

### 新增功能
- `audio-degradation`: 音频退化处理模块（AWGN、MP3、混响、截断）
- `real-noise-protocol-c`: 真实噪声 Protocol-C 实验
- `synthetic-rir-generator`: 合成房间脉冲响应生成器（无需外部 RIR 数据）
- `robustness-analysis`: 鲁棒性分析框架，对比不同退化条件下的性能

### 修改功能
- 无现有功能修改（纯新增实验）

## 影响

### 代码影响
- **新增文件**: `Experiments/E3_ProtocolC/audio_degrader.py` (~300 行)
- **新增文件**: `Experiments/E3_ProtocolC/protocol_c_experiment.py` (~400 行)

### 系统依赖
- **ffmpeg**: 用于 MP3 编解码 (`brew install ffmpeg`)
- **pydub**: Python 音频处理库
- **scipy.signal**: 用于混响卷积

### 计算资源
- **GPU**: RTX 3090 运行 6-8 小时（Wav2Vec2 重新编码）
- **无 API 调用**
- **存储**: ~10GB 用于缓存退化音频

### 论文影响
- **Sec 4.4**: 完全替换原有 Protocol-C 结果
- **Table VIII**: 更新为真实噪声条件下的性能数据
- **Response Letter**: 核心证据回应 C4 质疑
- **关键预期**: 自适应融合仍有优势，但改善幅度可能比 embedding 加噪小（这是正常的）

### 外部数据
- **无需下载 RIR 数据集**: 代码内置合成 RIR 生成器
- 如需要真实 RIR，可用 MIT RIR 数据集 (~50MB)

## 预期结果

### 成功标准
- 自适应融合在各类真实退化下保持性能优势
- 重度退化 (SNR=5dB, MP3-32k) 下性能下降在可接受范围
- 与 embedding 加噪结果有合理差异（验证审稿人质疑的正确性）

### 风险应对
- **如果自适应优势消失**: 检查自适应权重计算逻辑，调整温度参数
- **如果性能崩溃**: 这是预期内的，重点展示自适应融合的相对优势
