# 离线渲染空指针异常修复指南

## 问题描述

在点击 Auto-Import 按钮后，插件崩溃并报错：

```
0xC0000005: 读取位置 0x0000000000000000 时发生访问冲突
```

## 根本原因

当 `processOffline()` 被调用时，某些效果器指针尚未通过 `prepareToPlay()` 初始化，导致在 `processBlock()` 中访问空指针。

**触发时机**：
- 插件刚启动但音频流尚未开始
- Auto-Import 被激活且检测到 `generated_input.wav`
- 此时 `getSampleRate()` 可能返回 0
- 效果器的 `prepare()` 方法未被调用

## 修复策略

### 1. **采样率验证**
```cpp
const double offlineSampleRate = getSampleRate() > 0 ? getSampleRate() : 44100.0;

if (offlineSampleRate < 1000.0)
{
    DBG("ERROR: Invalid sample rate, calling prepareToPlay()...");
    prepareToPlay(44100.0, 512);
}
```

### 2. **关键指针检查**
```cpp
if (!mInputGainPtr || !mOutputGainPtr || !mDelayLineLeftPtr || !mDelayLineRightPtr)
{
    DBG("ERROR: Critical processors not initialized!");
    mIsProcessingOffline = false;
    return;
}
```

### 3. **异常捕获**
```cpp
try
{
    for (int start = 0; start < numSamples; start += blockSize)
    {
        // 处理音频...
        processBlock(tempBlock, emptyMidi);
    }
}
catch (const std::exception& e)
{
    DBG("EXCEPTION: " + juce::String(e.what()));
    mIsProcessingOffline = false;
    return;
}
```

## 调试步骤

### 1. **启用调试日志**

在 Visual Studio 中查看 **Output** 窗口，检查以下关键信息：

```
=== OFFLINE RENDERING START ===
Input: 320000 samples, 2 channels
Sample rate: 44100.0
DC blocker initialized
Processing loop completed: 320000 samples
Final DC offset - L: 0.000012, R: -0.000008
SUCCESS: Saved to C:\...\final_output.wav
=== OFFLINE RENDERING END ===
```

### 2. **检查异常日志**

如果崩溃，日志会显示：

```
ERROR: Invalid sample rate, calling prepareToPlay()...
ERROR: Critical processors not initialized!
```

或：

```
EXCEPTION during processing: ...
UNKNOWN EXCEPTION during processing
```

### 3. **断点调试位置**

在 Visual Studio 中设置断点：

1. `processOffline()` 开始：检查 `getSampleRate()` 值
2. 空指针检查：验证所有 `mXxxPtr` 非空
3. `processBlock()` 调用前：确认 `tempBlock` 有效
4. 异常 catch 块：捕获崩溃信息

## 常见问题排查

### 问题 A：Sample Rate = 0

**症状**：日志显示 `Sample rate: 0.0`

**原因**：音频设备尚未初始化

**解决**：代码会自动调用 `prepareToPlay(44100.0, 512)`

---

### 问题 B：关键指针为 nullptr

**症状**：日志显示 `ERROR: Critical processors not initialized!`

**原因**：构造函数中某些 `std::make_unique<>()` 失败

**解决**：
1. 检查 JUCE 模块是否正确链接
2. 确认所有 `Processors/` 目录下的类可编译
3. 查看构造函数中是否有异常抛出

---

### 问题 C：某个效果器崩溃

**症状**：日志显示 `EXCEPTION during processing: ...`

**解决**：
1. 临时禁用该效果器（在 `processBlock()` 中注释）
2. 逐个启用效果器找出问题源
3. 检查该效果器的 `prepare()` 和 `reset()` 方法

---

### 问题 D：仍然崩溃但没有日志

**原因**：崩溃发生在日志输出之前

**解决**：
```cpp
// 在 processOffline() 最开始添加：
__try
{
    // 所有代码...
}
__except (EXCEPTION_EXECUTE_HANDLER)
{
    DBG("FATAL EXCEPTION CODE: " + juce::String(GetExceptionCode()));
    mIsProcessingOffline = false;
    return;
}
```

## 预防措施

### 1. **延迟启动 Timer**

在构造函数中延迟启动文件监控：

```cpp
PluginAudioProcessor::PluginAudioProcessor()
{
    // ... 初始化代码 ...
    
    // 延迟 2 秒启动 Timer，确保 prepareToPlay 已调用
    juce::Timer::callAfterDelay(2000, [this]()
    {
        startTimer(500);
    });
}
```

### 2. **智能指针初始化检查**

在构造函数末尾添加：

```cpp
// 验证关键指针
jassert(mInputGainPtr != nullptr);
jassert(mDelayLineLeftPtr != nullptr);
jassert(mReverbPtr != nullptr);
// ...
```

### 3. **自动禁用 Auto-Import**

如果插件未准备好，自动禁用功能：

```cpp
void PluginAudioProcessor::checkImportFile()
{
    // 检查插件是否就绪
    if (getSampleRate() <= 0.0)
    {
        DBG("Plugin not ready, skipping import check");
        return;
    }
    
    // ... 现有代码 ...
}
```

## 测试清单

在发布前测试以下场景：

- [ ] 插件刚启动时立即点击 Auto-Import
- [ ] 在 DAW 中未开始播放时点击 Auto-Import
- [ ] 在离线渲染期间再次点击 Auto-Import（应被阻止）
- [ ] 在离线渲染期间关闭插件（应安全退出）
- [ ] 连续快速点击 Auto-Import（应被防抖）

## 性能监控

添加性能日志：

```cpp
void PluginAudioProcessor::processOffline()
{
    auto startTime = juce::Time::getMillisecondCounterHiRes();
    
    // ... 处理代码 ...
    
    auto elapsedMs = juce::Time::getMillisecondCounterHiRes() - startTime;
    DBG("Processing time: " + juce::String(elapsedMs, 1) + " ms");
}
```

**预期性能**：
- 10 秒音频（320,000 采样）
- 处理时间：< 1000 ms（现代 CPU）
- 如果 > 5000 ms，考虑优化效果器链

## 参考资料

- [JUCE AudioProcessor 文档](https://docs.juce.com/master/classAudioProcessor.html)
- [JUCE 线程安全指南](https://docs.juce.com/master/tutorial_synth_level_control.html)
- [Windows 异常代码](https://docs.microsoft.com/en-us/windows/win32/debug/exception-handling-reference)

## 更新日志

### v1.0 (2024-01-XX)
- 初始版本：添加空指针检查和异常捕获
- 添加采样率验证和自动初始化
- 添加关键指针验证逻辑

### v1.1 (待发布)
- 计划添加：Timer 延迟启动
- 计划添加：更详细的崩溃报告
- 计划添加：自动恢复机制
