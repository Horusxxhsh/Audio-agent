# 离线渲染崩溃修复记录

## 问题描述
点击 Auto-Import 按钮后崩溃：
```
0xC0000005: 读取位置 0x0000000000000000 时发生访问冲突
```

## 根本原因
`checkImportFile()` 函数中存在**重复的变量声明**：
```cpp
auto paramId = property.name.toString();        // 第一次声明
auto paramId = property.name.toString().toStdString();  // 重复声明 ?
```

这导致编译器生成的代码中空指针访问。

## 修复方案
移除重复声明，保留正确的版本：
```cpp
auto paramId = property.name.toString().toStdString();  // ? 正确
```

## 验证步骤
1. 编译成功 ?
2. 启动插件
3. 点击 Auto-Import
4. 检查日志输出

## 预期日志
```
Loaded audio file: C:\Users\Public\Documents\Supertonal\Audio-agent\generated_input.wav
=== OFFLINE RENDERING START ===
Input: 320000 samples, 2 channels
Sample rate: 44100.0
DC blocker initialized
Processing loop completed: 320000 samples
Final DC offset - L: 0.000012, R: -0.000008
SUCCESS: Saved to C:\...\final_output.wav
=== OFFLINE RENDERING END ===
```

## 注意事项
- 确保 `generated_input.wav` 存在
- 确保 `import_params.json` 存在
- 确保 Auto-Import 开关已启用

## 相关文件
- `..\..\Source\PluginAudioProcessor.cpp` - 主要修复位置
- `..\..\Docs\OfflineRendering.md` - 离线渲染文档
- `..\..\Docs\OfflineRenderingDebugGuide.md` - 调试指南
