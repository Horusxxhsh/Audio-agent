# 离线渲染系统设计文档

## 概述

本文档描述了 Audio-Agent 插件中离线渲染功能的正确实现方式。该系统允许插件自动处理 AI 生成的音频文件，并应用当前的效果器参数。

## 架构设计

### 核心原则

1. **共享效果器实例**：离线渲染和实时处理使用相同的效果器实例，确保参数和音质一致
2. **状态管理**：在离线渲染前后正确重置有状态效果器
3. **DC offset 防护**：使用高通滤波器防止直流偏移累积
4. **线程安全**：避免阻塞实时音频线程
5. **简洁性**：直接复用 `processBlock()` 逻辑

## 实现细节

### 1. 处理流程

```
用户输入 → Python 生成参数和音频 → C++ 检测文件变化 
           → 调用 processOffline() → 输出渲染结果
```

### 2. processOffline() 函数结构

```cpp
void PluginAudioProcessor::processOffline()
{
    // ① 输入验证
    // ② 防止重入
    // ③ 创建工作缓冲区
    // ④ 重置有状态效果器
    // ⑤ 创建 DC 阻断滤波器
    // ⑥ 分块处理循环
    //    - 应用 DC 阻断（前）
    //    - 调用 processBlock()
    //    - 应用 DC 阻断（后）
    //    - 安全限幅
    // ⑦ 保存输出文件
    // ⑧ 再次重置效果器
}
```

### 3. DC Offset 防护

**问题根源**：
- Delay 反馈循环累积直流分量
- Convolution IR 可能包含 DC
- 某些效果器的数值误差累积

**解决方案**：
```cpp
// 5Hz 高通滤波器（对人耳听觉无影响）
dcBlocker.state = juce::dsp::IIR::Coefficients<float>::makeHighPass(32000.0, 5.0f);

// 在效果链前后各应用一次
dcBlocker.process(preContext);   // 清理输入
processBlock(tempBlock, emptyMidi);
dcBlocker.process(postContext);  // 清理输出
```

### 4. 状态管理

**需要重置的效果器**：
- `DelayLine`（累积反馈）
- `Reverb`（混响尾音）
- `Convolution`（重叠相加缓冲区）
- `Chorus/Phaser/Flanger`（LFO 相位）
- `DryWetMixer`（干湿混合缓冲区）

**重置时机**：
```cpp
// 离线渲染前
mDelayLineLeftPtr->reset();
// ... 处理音频 ...
// 离线渲染后（再次重置以清除离线残留）
mDelayLineLeftPtr->reset();
```

### 5. 线程安全考虑

**避免的操作**：
```cpp
// ? 错误：在音频线程中持有锁
{
    const ScopedLock audioLock(getCallbackLock());
    // 长时间操作...
}

// ? 错误：在音频路径中 sleep
juce::Thread::sleep(50);
```

**正确的做法**：
```cpp
// ? JUCE DSP 的 reset() 是线程安全的
mDelayLineLeftPtr->reset();  // 不需要锁

// ? 使用原子变量防止重入
std::atomic<bool> mIsProcessingOffline{false};
```

## 参数设置

### 离线渲染参数

```cpp
const int blockSize = 512;          // 固定块大小
const double sampleRate = 32000.0;  // 固定采样率（避免重采样误差）
```

### DC 阻断滤波器参数

```cpp
cutoffFrequency = 5.0 Hz   // 低于人耳听觉范围（20Hz）
filterType = HighPass      // 移除 DC 和超低频
order = 2                  // IIR 二阶滤波器（默认）
```

## 文件路径

### 输入文件

```
C:\Users\Public\Documents\Supertonal\Audio-agent\
├── generated_input.wav     ← Python 生成（MusicGen）
└── import_params.json      ← Python 生成（LLM 参数）
```

### 输出文件

```
C:\Users\Public\Documents\Supertonal\Audio-agent\
└── final_output.wav        ← C++ 渲染结果
```

## 使用流程

### 1. 启用音频生成

```cmd
set SUPERTONAL_AUDIO_GEN=true
```

或在 Python 代码中：
```python
os.environ['SUPERTONAL_AUDIO_GEN'] = 'true'
```

### 2. 用户输入

在插件 UI 中输入：
```
"atmospheric post-rock guitar with ambient reverb"
```

### 3. 自动流程

```
Python (llm.py):
  ① 分析描述 → 生成参数 JSON
  ② MusicGen 生成音频 → generated_input.wav
  
C++ (checkImportFile):
  ① 检测 generated_input.wav 变化
  ② 调用 processOffline()
  ③ 应用效果器链
  ④ 输出 final_output.wav
```

## 调试指南

### 查看日志

在 Visual Studio 的 **Output** 窗口查看：

```
=== OFFLINE RENDERING START ===
Input: 320000 samples, 2 channels
Resetting stateful processors...
DC blocker initialized
Processing loop completed: 320000 samples
Final DC offset - L: 0.000023, R: -0.000018  ← 应接近 0
SUCCESS: Saved to C:\...\final_output.wav
=== OFFLINE RENDERING END ===
```

### 诊断 DC Offset 问题

**正常**：
```
Final DC offset - L: 0.000012, R: -0.000008  ? < 0.001
```

**异常**：
```
Final DC offset - L: 0.892341, R: 0.876522  ? 接近 1.0
```

**排查步骤**：
1. 检查 Delay 反馈参数（`mDelayFeedback`）是否 > 0.8
2. 检查 Convolution IR 文件是否包含 DC
3. 逐个禁用效果器找出问题源

### 性能监控

```cpp
DBG("Processing time: " + juce::String(elapsedMs) + " ms");
```

**预期性能**：
- 10 秒音频（320,000 采样）
- 处理时间：< 1 秒（现代 CPU）

## 故障排除

### 问题：输出文件无声

**原因**：效果器全部 bypass
**解决**：检查参数是否正确加载

### 问题：输出有严重失真

**原因**：增益过高或限幅失效
**解决**：
```cpp
// 增加安全限幅
data[s] = juce::jlimit(-1.0f, 1.0f, data[s]);
```

### 问题：渲染后实时音频异常

**原因**：效果器状态未恢复
**解决**：确保离线渲染后调用 `reset()`

## 最佳实践

1. **始终在非实时线程调用**：
   ```cpp
   // ? 在 Timer 回调中调用
   void timerCallback() override { processOffline(); }
   
   // ? 不要在 processBlock 中调用
   ```

2. **验证输入有效性**：
   ```cpp
   if (mGeneratedAudioBuffer.getNumSamples() <= 0) return;
   ```

3. **添加进度反馈**（可选）：
   ```cpp
   for (int start = 0; start < numSamples; start += blockSize) {
       float progress = (float)start / numSamples;
       // 通知 UI 更新进度条
   }
   ```

4. **保存诊断信息**：
   ```cpp
   juce::Logger::writeToLog("DC offset: " + juce::String(dcOffset));
   ```

## 性能优化建议

1. **使用较小的块大小**：512 采样是实时和效率的平衡
2. **固定采样率**：避免重采样开销
3. **简化效果链**：禁用不需要的效果器
4. **使用发布版本编译**：Debug 版本慢 10+ 倍

## 未来改进方向

1. **进度通知**：向 UI 发送渲染进度
2. **异步渲染**：在后台线程中处理
3. **批量渲染**：支持多个文件队列
4. **可配置输出格式**：支持 MP3/OGG 等格式

## 参考资料

- [JUCE DSP Tutorial](https://docs.juce.com/master/tutorial_dsp_introduction.html)
- [JUCE Convolution Documentation](https://docs.juce.com/master/classdsp_1_1Convolution.html)
- [Audio Programming Best Practices](https://github.com/cstack/db_tutorial)
