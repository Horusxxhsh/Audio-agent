#include "llm.h"
#include <cstdlib>
#include <sstream>
#include <string>
#include <fstream>
#include <juce_core/juce_core.h>
#include "../PluginPresetManager.h"
#include <windows.h> 
#include <algorithm>
// 存储环境变量时添加引号并转义内部引号
void storeEnvWithType(const std::string& key, const juce::String& value, const std::string& type) {
    std::string escapedValue = value.toStdString();
    // 转义字符串中的引号
    size_t pos = 0;
    while ((pos = escapedValue.find('"', pos)) != std::string::npos) {
        escapedValue.insert(pos, "\\");
        pos += 2;
    }
    // 使用双引号包裹字符串，确保空格被保留
    std::string envStr = key + "=" + type + ":\"" + escapedValue + "\"";

    // 使用 putenv，但先复制字符串以避免悬空指针问题
    char* envCopy = new char[envStr.size() + 1];
    std::strcpy(envCopy, envStr.c_str());

    // 存储指针以便后续清理
    static std::vector<char*> allocatedEnvVars;
    allocatedEnvVars.push_back(envCopy);

    // 设置环境变量
    if (putenv(envCopy) != 0) {
        std::cerr << "Failed to set environment variable: " << key << std::endl;
    }

    juce::Logger::writeToLog("Stored Environment Variable: " + juce::String(envStr));
}


EffectParameters extractParameters(const juce::String& jsonString) {
    EffectParameters params;

    // 解析 JSON 字符串
    auto jsonVar = juce::JSON::parse(jsonString);
    if (jsonVar.isVoid()) {
        std::cerr << "Failed to parse JSON." << std::endl;
        return params;
    }

    // 输出解析后的 JSON 数据用于调试
    juce::Logger::writeToLog("Parsed JSON for parameter extraction: " + juce::JSON::toString(jsonVar, true));

    // 获取压缩效果器的参数
    if (jsonVar["CompressorOn"].isObject()) {
        params.Compressor_on = 1;
        //     storeEnvWithType("Compressor_on", juce::String(params.Compressor_on), "int");
        if (auto* compressor = jsonVar["CompressorOn"].getDynamicObject()) {
            if (compressor->hasProperty("Threshold")) {
                params.co_threshold = compressor->getProperty("Threshold");
                storeEnvWithType("co_Threshold", juce::String(params.co_threshold), "double");
            }
            if (compressor->hasProperty("Ratio")) {
                params.co_ratio = compressor->getProperty("Ratio");
                storeEnvWithType("co_Ratio", juce::String(params.co_ratio), "int");
            }
            if (compressor->hasProperty("Attack")) {
                params.co_attack = compressor->getProperty("Attack");
                storeEnvWithType("co_Attack", juce::String(params.co_attack), "double");
            }
            if (compressor->hasProperty("Release")) {
                params.co_release = compressor->getProperty("Release");
                storeEnvWithType("co_Release", juce::String(params.co_release), "double");
            }
            if (compressor->hasProperty("Makeup")) {
                params.co_makeup = compressor->getProperty("Makeup");
                storeEnvWithType("co_Makeup", juce::String(params.co_makeup), "double");
            }
            if (compressor->hasProperty("Mix")) {
                params.co_mix = compressor->getProperty("Mix");
                storeEnvWithType("co_Mix", juce::String(params.co_mix), "double");
            }
        }
    }
    else {
        params.Compressor_on = 0;
        params.co_threshold = -128;
        params.co_ratio = 1;
        params.co_attack = 0;
        params.co_release = 0;
        params.co_makeup = -12;
        params.co_mix = 0;
        //     storeEnvWithType("Compressor_on", juce::String(params.Compressor_on), "int");
    }

    // 获取失真效果器的参数
    if (jsonVar["DriverOn"].isObject()) {
        params.Driver_on = 1;
        //      storeEnvWithType("Driver_on", juce::String(params.Driver_on), "int");
        if (auto* distortion = jsonVar["DriverOn"].getDynamicObject()) {
            if (distortion->hasProperty("Distortion")) {
                params.dr_distortion = distortion->getProperty("Distortion");
                storeEnvWithType("dr_Distortion", juce::String(params.dr_distortion), "double");
            }
            if (distortion->hasProperty("Volume")) {
                params.dr_volume = distortion->getProperty("Volume");
                storeEnvWithType("dr_Volume", juce::String(params.dr_volume), "double");
            }
        }
    }
    else {
        params.Driver_on = 0;
        //    storeEnvWithType("Driver_on", juce::String(params.Driver_on), "int");
        params.dr_distortion = 0;
        params.dr_volume = -64;
    }

    // 获取过载效果器的参数Screamer
    if (jsonVar["ScreamerOn"].isObject()) {
        params.Screamer_on = 1;
        //     storeEnvWithType("Screamer_on", juce::String(params.Screamer_on), "int");
        if (auto* overdrive = jsonVar["ScreamerOn"].getDynamicObject()) {
            if (overdrive->hasProperty("Drive")) {
                params.s_drive = overdrive->getProperty("Drive");
                storeEnvWithType("s_Drive", juce::String(params.s_drive), "double");
            }
            if (overdrive->hasProperty("Tone")) {
                params.s_tone = overdrive->getProperty("Tone");
                storeEnvWithType("s_Tone", juce::String(params.s_tone), "double");
            }
            if (overdrive->hasProperty("Level")) {
                params.s_level = overdrive->getProperty("Level");
                storeEnvWithType("s_Level", juce::String(params.s_level), "double");
            }
        }
    }
    else {
        params.Screamer_on = 0;
        params.s_drive = 0;
        params.s_tone = 0;
        params.s_level = -64;
        //       storeEnvWithType("Screamer_on", juce::String(params.Screamer_on), "int");
    }

    // 获取延迟效果器的参数
    if (jsonVar["DelayOn"].isObject()) {
        params.Delay_on = 1;
        //    storeEnvWithType("Delay_on", juce::String(params.Delay_on), "int");
        if (auto* delayEffect = jsonVar["DelayOn"].getDynamicObject()) {
            if (delayEffect->hasProperty("Feedback")) {
                params.de_feedback = delayEffect->getProperty("Feedback");
                storeEnvWithType("de_Feedback", juce::String(params.de_feedback), "double");
            }
            if (delayEffect->hasProperty("Delay")) {
                params.de_delay = delayEffect->getProperty("Delay");
                storeEnvWithType("de_Delay", juce::String(params.de_delay), "double");
            }
            if (delayEffect->hasProperty("Mix")) {
                params.de_mix = delayEffect->getProperty("Mix");
                storeEnvWithType("de_Mix", juce::String(params.de_mix), "double");
            }
        }
    }
    else {
        params.Delay_on = 0;
        params.de_feedback = 0;
        params.de_delay = 1;
        params.de_mix = 0;
        //   storeEnvWithType("Delay_on", juce::String(params.Delay_on), "int");
    }

    // 获取混响效果器的参数

    if (jsonVar["ReverbOn"].isObject()) {
        params.Reverb_on = 1;
        // storeEnvWithType("Reverb_on", juce::String(params.Reverb_on), "int");
        if (auto* reverb = jsonVar["ReverbOn"].getDynamicObject()) {
            if (reverb->hasProperty("Size")) {
                params.r_size = reverb->getProperty("Size");
                storeEnvWithType("r_Size", juce::String(params.r_size), "double");
            }
            if (reverb->hasProperty("Damping")) {
                params.r_damping = reverb->getProperty("Damping");
                storeEnvWithType("r_Damping", juce::String(params.r_damping), "double");
            }
            if (reverb->hasProperty("Width")) {
                params.r_width = reverb->getProperty("Width");
                storeEnvWithType("r_Width", juce::String(params.r_width), "double");
            }
            if (reverb->hasProperty("Mix")) {
                params.r_mix = reverb->getProperty("Mix");
                storeEnvWithType("r_Mix", juce::String(params.r_mix), "double");
            }
        }
    }
    else {
        params.Reverb_on = 0;
        params.r_size = 0;
        params.r_damping = 0;
        params.r_width = 0;
        params.r_mix = 0;
        //  storeEnvWithType("Reverb_on", juce::String(params.Reverb_on), "int");
    }

    // 获取合唱效果器的参数，此处逻辑未根据提供的 JSON 数据更新，保留原样
    if (jsonVar["ChorusOn"].isObject()) {
        params.Chorus_on = 1;
        //   storeEnvWithType("Chorus_on", juce::String(params.Chorus_on), "int");
        if (auto* chorus = jsonVar["ChorusOn"].getDynamicObject()) {
            if (chorus->hasProperty("Delay")) {
                params.ch_delay = chorus->getProperty("Delay");
                storeEnvWithType("ch_Delay", juce::String(params.ch_delay), "double");
            }
            if (chorus->hasProperty("Depth")) {
                params.ch_depth = chorus->getProperty("Depth");
                storeEnvWithType("ch_Depth", juce::String(params.ch_depth), "double");
            }
            if (chorus->hasProperty("Frequency")) {
                params.ch_frequency = chorus->getProperty("Frequency");
                storeEnvWithType("ch_Frequency", juce::String(params.ch_frequency), "double");
            }
            if (chorus->hasProperty("Width")) {
                params.ch_width = chorus->getProperty("Width");
                storeEnvWithType("ch_Width", juce::String(params.ch_width), "double");
            }
        }
    }
    else {
        params.Chorus_on = 0;
        params.ch_delay = 0.01;
        params.ch_depth = 0;
        params.ch_frequency = 0.05;
        params.ch_width = 0.01;
        //  storeEnvWithType("Chorus_on", juce::String(params.Chorus_on), "int");
    }

    // 获取镶边效果器的参数

    if (jsonVar["FlangerOn"].isObject()) {
        params.Flanger_on = 1;
        // storeEnvWithType("Flanger_on", juce::String(params.Flanger_on), "int");
        if (auto* flanger = jsonVar["FlangerOn"].getDynamicObject()) {
            if (flanger->hasProperty("Delay")) {
                params.f_delay = flanger->getProperty("Delay");
                storeEnvWithType("f_Delay", juce::String(params.f_delay), "double");
            }
            if (flanger->hasProperty("Depth")) {
                params.f_depth = flanger->getProperty("Depth");
                storeEnvWithType("f_Depth", juce::String(params.f_depth), "double");
            }
            if (flanger->hasProperty("Feedback")) {
                params.f_feedback = flanger->getProperty("Feedback");
                storeEnvWithType("f_Feedback", juce::String(params.f_feedback), "double");
            }
            if (flanger->hasProperty("Frequency")) {
                params.f_frequency = flanger->getProperty("Frequency");
                storeEnvWithType("f_Frequency", juce::String(params.f_frequency), "double");
            }
            if (flanger->hasProperty("Width")) {
                params.f_width = flanger->getProperty("Width");
                storeEnvWithType("f_Width", juce::String(params.f_width), "double");
            }
        }
    }
    else {
        params.Flanger_on = 0;
        params.f_delay = 0.001;
        params.f_depth = 0;
        params.f_feedback = 0;
        params.f_frequency = 0.05;
        params.f_width = 0.001;
        //   storeEnvWithType("Flanger_on", juce::String(params.Flanger_on), "int");
    }

    // 获取相位效果器的参数

    if (jsonVar["PhaserOn"].isObject()) {
        params.Phaser_on = 1;
        //  storeEnvWithType("Phaser_on", juce::String(params.Phaser_on), "int");
        if (auto* phaser = jsonVar["PhaserOn"].getDynamicObject()) {
            if (phaser->hasProperty("Depth")) {
                params.p_depth = phaser->getProperty("Depth");
                storeEnvWithType("p_Depth", juce::String(params.p_depth), "double");
            }
            if (phaser->hasProperty("Feedback")) {
                params.p_feedback = phaser->getProperty("Feedback");
                storeEnvWithType("p_Feedback", juce::String(params.p_feedback), "double");
            }
            if (phaser->hasProperty("Frequency")) {
                params.p_frequency = phaser->getProperty("Frequency");
                storeEnvWithType("p_Frequency", juce::String(params.p_frequency), "double");
            }
            if (phaser->hasProperty("Width")) {
                params.p_width = phaser->getProperty("Width");
                storeEnvWithType("p_Width", juce::String(params.p_width), "int");
            }
        }
    }
    else {
        params.Phaser_on = 0;
        params.p_depth = 0;
        params.p_feedback = 0;
        params.p_frequency = 0.05;
        params.p_width = 50;
        //storeEnvWithType("Phaser_on", juce::String(params.Phaser_on), "int");
    }

    // 获取均衡效果器的参数

    if (jsonVar["EqualiserOn"].isObject()) {
        params.Equaliser_on = 1;
        //  storeEnvWithType("Phaser_on", juce::String(params.Phaser_on), "int");
        if (auto* equaliser = jsonVar["EqualiserOn"].getDynamicObject()) {
            if (equaliser->hasProperty("100hz")) {
                params.e_1 = equaliser->getProperty("100hz");
                storeEnvWithType("e_1", juce::String(params.e_1), "double");
            }
            if (equaliser->hasProperty("200hz")) {
                params.e_2 = equaliser->getProperty("200hz");
                storeEnvWithType("e_2", juce::String(params.e_2), "double");
            }
            if (equaliser->hasProperty("400hz")) {
                params.e_4 = equaliser->getProperty("400hz");
                storeEnvWithType("e_4", juce::String(params.e_4), "double");
            }
            if (equaliser->hasProperty("800hz")) {
                params.e_8 = equaliser->getProperty("800hz");
                storeEnvWithType("e_8", juce::String(params.e_8), "double");
            }
            if (equaliser->hasProperty("1600hz")) {
                params.e_16 = equaliser->getProperty("1600hz");
                storeEnvWithType("e_16", juce::String(params.e_16), "double");
            }
            if (equaliser->hasProperty("3200hz")) {
                params.e_32 = equaliser->getProperty("3200hz");
                storeEnvWithType("e_32", juce::String(params.e_32), "double");
            }
            if (equaliser->hasProperty("6400hz")) {
                params.e_64 = equaliser->getProperty("6400hz");
                storeEnvWithType("e_64", juce::String(params.e_64), "double");
            }
            if (equaliser->hasProperty("Level")) {
                params.e_level = equaliser->getProperty("Level");
                storeEnvWithType("e_Level", juce::String(params.e_level), "double");
            }
        }
    }
    else {
        params.Equaliser_on = 0;
        params.e_1 = 0;
        params.e_2 = 0;
        params.e_4 = 0;
        params.e_8 = 0;
        params.e_16 = 0;
        params.e_32 = 0;
        params.e_64 = 0;
        params.e_level = 0;
        //storeEnvWithType("Phaser_on", juce::String(params.Phaser_on), "int");
    }

    // 获取噪声门效果器的参数

    if (jsonVar["NoiseGate"].isObject()) {
        params.NoiseGate_on = 1;
        //  storeEnvWithType("Phaser_on", juce::String(params.Phaser_on), "int");
        if (auto* noisegate = jsonVar["NoiseGate"].getDynamicObject()) {
            if (noisegate->hasProperty("NoiseGateThreshold")) {
                params.n_noisegatethreshold = noisegate->getProperty("NoiseGateThreshold");
                storeEnvWithType("p_NoiseGateThreshold", juce::String(params.n_noisegatethreshold), "double");
            }
        }
    }
    else {
        params.NoiseGate_on = 0;
        params.n_noisegatethreshold = -128;
        //storeEnvWithType("Phaser_on", juce::String(params.Phaser_on), "int");
    }

    if (params.Compressor_on == 1) {
        bool Compressor_on = true;
        storeEnvWithType("Compressor_on", juce::String(params.Compressor_on), "bool");
    }
    else
    {
        bool Compressor_on = false;
        storeEnvWithType("Compressor_on", juce::String(params.Compressor_on), "bool");
    }
    if (params.Driver_on == 1) {
        bool Driver_on = true;
        storeEnvWithType("Driver_on", juce::String(params.Driver_on), "bool");
    }
    else
    {
        bool Driver_on = false;
        storeEnvWithType("Driver_on", juce::String(params.Driver_on), "bool");
    }
    if (params.Screamer_on == 1) {
        bool Screamer_on = true;
        storeEnvWithType("Screamer_on", juce::String(params.Screamer_on), "bool");
    }
    else
    {
        bool Screamer_on = false;
        storeEnvWithType("Screamer_on", juce::String(params.Screamer_on), "bool");
    }
    if (params.Delay_on == 1) {
        bool Delay_on = true;
        storeEnvWithType("Delay_on", juce::String(params.Delay_on), "bool");
    }
    else
    {
        bool Delay_on = false;
        storeEnvWithType("Delay_on", juce::String(params.Delay_on), "bool");
    }
    if (params.Reverb_on == 1) {
        bool Reverb_on = true;
        storeEnvWithType("Reverb_on", juce::String(params.Reverb_on), "bool");
    }
    else
    {
        bool Reverb_on = false;
        storeEnvWithType("Reverb_on", juce::String(params.Reverb_on), "bool");
    }
    if (params.Chorus_on == 1) {
        bool Chorus_on = true;
        storeEnvWithType("Chorus_on", juce::String(params.Chorus_on), "bool");
    }
    else
    {
        bool Chorus_on = false;
        storeEnvWithType("Chorus_on", juce::String(params.Chorus_on), "bool");
    }
    if (params.Flanger_on == 1) {
        bool Flanger_on = true;
        storeEnvWithType("Flanger_on", juce::String(params.Flanger_on), "bool");
    }
    else
    {
        bool Flanger_on = false;
        storeEnvWithType("Flanger_on", juce::String(params.Flanger_on), "bool");
    }
    if (params.Phaser_on == 1) {
        bool Phaser_on = true;
        storeEnvWithType("Phaser_on", juce::String(params.Phaser_on), "bool");
    }
    else
    {
        bool Phaser_on = false;
        storeEnvWithType("Phaser_on", juce::String(params.Phaser_on), "bool");
    }
    if (params.Equaliser_on == 1) {
        bool Equaliser_on = true;
        storeEnvWithType("Equaliser_on", juce::String(params.Equaliser_on), "bool");
    }
    else
    {
        bool Equaliser_on = false;
        storeEnvWithType("Equaliser_on", juce::String(params.Equaliser_on), "bool");
    }
    if (params.NoiseGate_on == 1) {
        bool NoiseGate_on = true;
        storeEnvWithType("NoiseGate_on", juce::String(params.NoiseGate_on), "bool");
    }
    else
    {
        bool NoiseGate_on = false;
        storeEnvWithType("NoiseGate_on", juce::String(params.NoiseGate_on), "bool");
    }

    return params;
}

// Implement the constructor of ChatComponent class
ChatComponent::ChatComponent(PluginPresetManager& pm)
    : juce::Thread("NetworkThread"),  // Initialize network thread
    presetManager(pm),
    sendButton("Send"),
    statusLabel("Status", "Ready"),
    audioFileLabel("AudioFileLabel", "No file selected"),  // Initialize label
    audioFileButton("Select audio file"),
    cancelAudioButton("Clear selection"),  // 新增取消按钮
    acceptAudioButton("Accept"),  // 接受音频文件
    rejectAudioButton("Reject"),  // 拒绝音频文件
    memoryToggleButton("MemoryOff"),  // 初始化为 MemoryOff
    textWeightLabel("Text Weight:", "Text:"),  // 修改：添加文本内容
    preferenceWeightLabel("Preference Weight:", "Preference:"),  // 修改：添加文本内容
    audioWeightLabel("Audio Weight:", "Audio:")  // 修改：添加文本内容
{
    currentPresetName = presetManager.getCurrentPreset();
    // Initialize UI components
    addAndMakeVisible(inputEditor);
    addAndMakeVisible(sendButton);
    addAndMakeVisible(responseEditor);
    addAndMakeVisible(statusLabel);

    sendButton.addListener(this);
    sendButton.setEnabled(true);

    inputEditor.setMultiLine(true);
    //inputEditor.setColour(juce::TextEditor::backgroundColourId, juce::Colours::lightyellow);
    responseEditor.setMultiLine(true);
    responseEditor.setReadOnly(true);
    //responseEditor.setColour(juce::TextEditor::backgroundColourId, juce::Colours::lightyellow);

    // Initialize audio file selection button
    addAndMakeVisible(audioFileButton);
    audioFileButton.addListener(this);  // Listen for button clicks
    audioFileButton.setTooltip("Select audio file (supports wav, mp3, aif, flac, etc.)");

    // Initialize audio file path label (optional, used to display selected file)
    addAndMakeVisible(audioFileLabel);
    audioFileLabel.setColour(juce::Label::textColourId, juce::Colours::darkgrey);

    // Set status label text color to black
    statusLabel.setColour(juce::Label::textColourId, juce::Colours::black);

    // 初始化取消按钮
    addAndMakeVisible(cancelAudioButton);
    cancelAudioButton.addListener(this);
    cancelAudioButton.setTooltip("Clear selected audio file");
    cancelAudioButton.setEnabled(false);  // 初始状态下禁用，因为没有文件被选择

    // 初始化接受和拒绝按钮
    addAndMakeVisible(acceptAudioButton);
    acceptAudioButton.addListener(this);
    acceptAudioButton.setTooltip("Accept selected audio file");
    acceptAudioButton.setEnabled(true);  // 初始状态下禁用，因为没有文件被选择
    acceptAudioButton.setColour(juce::TextButton::buttonOnColourId, juce::Colours::green);  // 接受状态颜色

    addAndMakeVisible(rejectAudioButton);
    rejectAudioButton.addListener(this);
    rejectAudioButton.setTooltip("Reject selected audio file");
    rejectAudioButton.setEnabled(true);  // 初始状态下禁用，因为没有文件被选择
    rejectAudioButton.setColour(juce::TextButton::buttonOnColourId, juce::Colours::red);  // 拒绝状态颜色

    // 初始化记忆开关按钮
    addAndMakeVisible(memoryToggleButton);
    memoryToggleButton.addListener(this);
    memoryToggleButton.setClickingTogglesState(true);  // 设置为开关按钮
    memoryToggleButton.setColour(juce::TextButton::buttonOnColourId, juce::Colours::green);  // 开启状态颜色
    memoryToggleButton.setTooltip("Toggle memory feature on/off");

    // 初始化权重标签和输入框
    // 修改：使用addChildComponent，并设置标签文本对齐方式
    textWeightLabel.setJustificationType(juce::Justification::right);
    preferenceWeightLabel.setJustificationType(juce::Justification::right);
    audioWeightLabel.setJustificationType(juce::Justification::right);

    addChildComponent(textWeightLabel);
    addChildComponent(preferenceWeightLabel);
    addChildComponent(audioWeightLabel);

    addChildComponent(textWeightEditor);
    textWeightEditor.setText("0.0");  // 设置默认值
    textWeightEditor.setTooltip("Enter weight value for style (e.g., 1.0)");
	//styleWeightEditor.setColour(juce::TextEditor::backgroundColourId, juce::Colours::lightyellow);

    addChildComponent(preferenceWeightEditor);
    preferenceWeightEditor.setText("0.0");  // 设置默认值
    preferenceWeightEditor.setTooltip("Enter weight value for audio (e.g., 1.0)");
    //audioWeightEditor.setColour(juce::TextEditor::backgroundColourId, juce::Colours::lightyellow);

    addChildComponent(audioWeightEditor);
    audioWeightEditor.setText("0.0");  // 设置默认值
    audioWeightEditor.setTooltip("Enter weight value for feature (e.g., 1.0)");
    //featureWeightEditor.setColour(juce::TextEditor::backgroundColourId, juce::Colours::lightyellow);

    textWeightEditor.addListener(this);
    preferenceWeightEditor.addListener(this);
    audioWeightEditor.addListener(this);

    // 设置输入框只接受数字和小数点
    textWeightEditor.setInputRestrictions(10, "0123456789.");  // 限制为10个字符，只允许数字和小数点
    preferenceWeightEditor.setInputRestrictions(10, "0123456789.");
    audioWeightEditor.setInputRestrictions(10, "0123456789.");

    setSize(600, 400);
    // ---- 统一设置编辑框的颜色（背景白色 / 边框黑色） ----
    inputEditor.setColour(juce::TextEditor::backgroundColourId, juce::Colours::white);
    inputEditor.setColour(juce::TextEditor::outlineColourId, juce::Colours::black);
    inputEditor.setColour(juce::TextEditor::focusedOutlineColourId, juce::Colours::black);
    inputEditor.setColour(juce::TextEditor::textColourId, juce::Colours::black);
    inputEditor.setColour(juce::TextEditor::highlightColourId, juce::Colours::lightblue);
    //inputEditor.setColour(juce::TextEditor::caretColourId, juce::Colours::black);

    responseEditor.setColour(juce::TextEditor::backgroundColourId, juce::Colours::white);
    responseEditor.setColour(juce::TextEditor::outlineColourId, juce::Colours::black);
    responseEditor.setColour(juce::TextEditor::focusedOutlineColourId, juce::Colours::black);
    responseEditor.setColour(juce::TextEditor::textColourId, juce::Colours::black);
    responseEditor.setColour(juce::TextEditor::highlightColourId, juce::Colours::lightblue);
    //responseEditor.setColour(juce::TextEditor::caretColourId, juce::Colours::black);

    textWeightEditor.setColour(juce::TextEditor::backgroundColourId, juce::Colours::white);
    textWeightEditor.setColour(juce::TextEditor::outlineColourId, juce::Colours::black);
    textWeightEditor.setColour(juce::TextEditor::focusedOutlineColourId, juce::Colours::black);
    textWeightEditor.setColour(juce::TextEditor::textColourId, juce::Colours::black);
    //styleWeightEditor.setColour(juce::TextEditor::caretColourId, juce::Colours::black);

    preferenceWeightEditor.setColour(juce::TextEditor::backgroundColourId, juce::Colours::white);
    preferenceWeightEditor.setColour(juce::TextEditor::outlineColourId, juce::Colours::black);
    preferenceWeightEditor.setColour(juce::TextEditor::focusedOutlineColourId, juce::Colours::black);
    preferenceWeightEditor.setColour(juce::TextEditor::textColourId, juce::Colours::black);
    //audioWeightEditor.setColour(juce::TextEditor::caretColourId, juce::Colours::black);

    audioWeightEditor.setColour(juce::TextEditor::backgroundColourId, juce::Colours::white);
    audioWeightEditor.setColour(juce::TextEditor::outlineColourId, juce::Colours::black);
    audioWeightEditor.setColour(juce::TextEditor::focusedOutlineColourId, juce::Colours::black);
    audioWeightEditor.setColour(juce::TextEditor::textColourId, juce::Colours::black);
    //featureWeightEditor.setColour(juce::TextEditor::caretColourId, juce::Colours::black);

    textWeightLabel.setColour(juce::Label::textColourId, juce::Colours::black);
    preferenceWeightLabel.setColour(juce::Label::textColourId, juce::Colours::black);
    audioWeightLabel.setColour(juce::Label::textColourId, juce::Colours::black);

}


// Implement the resized method of ChatComponent class
void ChatComponent::resized()
{
    auto area = getLocalBounds().reduced(8);

    // 为记忆开关按钮分配空间（放在顶部）
    auto topButtonArea = area.removeFromTop(30);  // 为顶部按钮预留空间
    memoryToggleButton.setBounds(topButtonArea.removeFromRight(100).reduced(2));  // 记忆开关按钮

    // 权重输入区域 - 修改布局以确保标签和输入框正确显示
    auto weightsArea = area.removeFromTop(30);

    // 将区域分为三等份
    int oneThird = weightsArea.getWidth() / 3;

    // 风格权重区域
    auto styleWeightArea = weightsArea.removeFromLeft(oneThird);
    textWeightLabel.setBounds(styleWeightArea.removeFromLeft(80).reduced(2));
    textWeightEditor.setBounds(styleWeightArea.reduced(2));

    // 音频权重区域
	auto preferenceWeightArea = weightsArea.removeFromLeft(oneThird);
    preferenceWeightLabel.setBounds(preferenceWeightArea.removeFromLeft(80).reduced(2));
    preferenceWeightEditor.setBounds(preferenceWeightArea.reduced(2));

    // 特征权重区域
    auto featureWeightArea = weightsArea.removeFromLeft(oneThird);
    audioWeightLabel.setBounds(featureWeightArea.removeFromLeft(80).reduced(2));
    audioWeightEditor.setBounds(featureWeightArea.reduced(2));

    

    // 音频文件选择区域
    auto audioArea = area.removeFromTop(40);
    // 分配空间给音频文件选择按钮
    audioFileButton.setBounds(audioArea.removeFromLeft(150).reduced(2));  // 选择文件按钮
    cancelAudioButton.setBounds(audioArea.removeFromLeft(120).reduced(2));  // 取消按钮
    audioFileLabel.setBounds(audioArea.reduced(2));  // 标签占据剩余区域
    
    // 将接受和拒绝按钮移到最右边
    rejectAudioButton.setBounds(audioArea.removeFromRight(80).reduced(2));  // 拒绝按钮
    acceptAudioButton.setBounds(audioArea.removeFromRight(80).reduced(2));  // 接受按钮

    // Allocate remaining area to original input area, button area, etc. (keep original logic)
    auto inputArea = area.removeFromTop(100);
    auto buttonArea = area.removeFromTop(24);
    auto responseArea = area;

    inputEditor.setBounds(inputArea);
    sendButton.setBounds(buttonArea.removeFromRight(80).reduced(2));
    statusLabel.setBounds(buttonArea.reduced(2));
    responseEditor.setBounds(responseArea.reduced(2));
}




void ChatComponent::callAsync(const juce::String& response)
{
    // Use callAsync to ensure UI update on main thread
    juce::MessageManager::callAsync([this, response]() {
        responseEditor.setText(response, juce::dontSendNotification); // Update response content to responseEditor
        juce::Logger::writeToLog("Response updated in UI: " + response); // Print log
        });
}

// Implement the buttonClicked method of ChatComponent class
void ChatComponent::buttonClicked(juce::Button* button)
{
    if (button == &sendButton)
    {
        auto message = inputEditor.getText();
        if (message.isNotEmpty())
        {
            userMessageToSend = message; // Save user message

            // 如果记忆功能开启，存储权重值到环境变量
            storeEnvWithType("text_Weight", "0.0", "double");
            storeEnvWithType("audio_Weight", "0.0", "double");
            storeEnvWithType("preference_Weight", "0.0", "double");
            if (memoryEnabled) {
                storeEnvWithType("text_Weight", textWeightEditor.getText(), "double");
                storeEnvWithType("audio_Weight", audioWeightEditor.getText(), "double");
                storeEnvWithType("preference_Weight", preferenceWeightEditor.getText(), "double");
            }

            inputEditor.clear();
            startThread();  // Start thread
        }
    }
    else if (button == &audioFileButton) {
        // 现有代码...
        std::shared_ptr<juce::FileChooser> chooser = std::make_shared<juce::FileChooser>(
            "Select audio file",
            juce::File::getSpecialLocation(juce::File::userDesktopDirectory),
            "Audio files (*.wav;*.WAV;*.mp3;*.MP3;*.aif;*.AIF;*.flac;*.FLAC)");

        chooser->launchAsync(juce::FileBrowserComponent::openMode |
            juce::FileBrowserComponent::canSelectFiles,
            [this, chooser](const juce::FileChooser& fc) {
                auto result = fc.getResult();
                if (result.existsAsFile()) {
                    audioFilePath = result.getFullPathName();
                    storeEnvWithType("audio_File_Path", audioFilePath, "string");
                    audioFileLabel.setText("Selected: " + result.getFileName(),
                        juce::dontSendNotification);

                    // 启用取消按钮，因为现在有文件被选择
                    cancelAudioButton.setEnabled(true);

                    if (result.getSize() == 0) {
                        juce::AlertWindow::showMessageBoxAsync(juce::AlertWindow::WarningIcon,
                            "Error",
                            "The selected file is empty!");
                        audioFilePath.clear();
                        audioFileLabel.setText("No file selected", juce::dontSendNotification);
                        cancelAudioButton.setEnabled(false);  // 禁用取消按钮
                        //acceptAudioButton.setEnabled(false);  // 禁用接受按钮
                        //rejectAudioButton.setEnabled(false);  // 禁用拒绝按钮

                        // 隐藏音频权重控件，因为没有有效的音频文件
                        audioWeightLabel.setVisible(false);
                        audioWeightEditor.setVisible(false);
                    }
                    else {
                        // 启用接受和拒绝按钮，允许用户确认或拒绝文件
                        //acceptAudioButton.setEnabled(true);
                        //rejectAudioButton.setEnabled(true);
                        //cancelAudioButton.setEnabled(false);  // 暂时禁用取消按钮

                        // 如果记忆功能已开启，显示音频权重控件
                        updateAudioWeightVisibility();
                        storeEnvWithType("text_Weight", textWeightEditor.getText(), "double");
                        storeEnvWithType("audio_Weight", audioWeightEditor.getText(), "double");
                        storeEnvWithType("preference_Weight", preferenceWeightEditor.getText(), "double");
                    }
                }
            });
    }
    else if (button == &cancelAudioButton) {
        // 取消按钮的处理逻辑
        audioFilePath.clear();  // 清除文件路径
        storeEnvWithType("audio_File_Path", "", "string");  // 清除环境变量
        audioFileLabel.setText("No file selected", juce::dontSendNotification);  // 重置标签
        cancelAudioButton.setEnabled(false);  // 禁用取消按钮，因为没有文件可以取消

        // 隐藏音频权重控件，因为没有音频文件
        audioWeightLabel.setVisible(false);
        audioWeightEditor.setVisible(false);

        // 记录日志
        juce::Logger::writeToLog("Audio file selection cleared");
    }
    else if (button == &acceptAudioButton) {
        auto userMessage = userMessageToSend;
        juce::Logger::writeToLog("userMessage: " + juce::String(userMessage));
        if (userMessage.isNotEmpty()) {
            // 接受按钮的处理逻辑 - 确认当前选择的音频文件
            juce::Logger::writeToLog("accept ");
            // 方法三：定义 Python 解释器和脚本的文件对象
            juce::File pythonInterpreterFile;
            juce::File pythonScriptFile;
            // 获取环境变量并记录原始值
            const char* pythonInterpreterEnv = std::getenv("SUPERTONAL_PYTHON_INTERPRETER");
            const char* pythonScriptEnv = std::getenv("SUPERTONAL_PYTHON_SCRIPT3"); // 修正名称，添加了"1"
            // 记录环境变量的原始值
            juce::Logger::writeToLog("Raw interpreter env value: " +
                (pythonInterpreterEnv != nullptr ? juce::String(pythonInterpreterEnv) : "null"));
            juce::Logger::writeToLog("Raw script env value: " +
                (pythonScriptEnv != nullptr ? juce::String(pythonScriptEnv) : "null"));
            pythonInterpreterFile = juce::File(pythonInterpreterEnv);
            pythonScriptFile = juce::File(pythonScriptEnv);
            const juce::String pythonInterpreterPath = pythonInterpreterFile.getFullPathName();
            const juce::String pythonScriptPath = pythonScriptFile.getFullPathName();
            juce::Logger::writeToLog("Python interpreter path: " + pythonInterpreterPath);
            juce::Logger::writeToLog("Python script path: " + pythonScriptPath);

            // 构建命令行：解释器 + 脚本 + 用户消息 + 音频路径（若有）+ 记忆状态
            juce::String command;
            command << pythonInterpreterPath.toStdString() << " " << pythonScriptPath.toStdString();

            // 添加用户消息参数（作为第一个参数）
            command << " \"" << userMessage << "\"";

            // 执行命令
            std::string utf8Command = command.toStdString();
            int returnCode = std::system(utf8Command.c_str());
            juce::Logger::writeToLog("commandWithErrorCapture: " + juce::String(utf8Command) + ", return code: " + juce::String(returnCode));
            if (returnCode != 0) {
                std::cerr << "Python script execution failed, return code: " << returnCode << std::endl;
                std::cerr << "执行的命令: " << command << std::endl;
                updateStatus("Python script execution failed");
            }
            else {
                updateStatus("accepted");
            }
        }
        else {
            updateStatus("No input");
        }
    }
    else if (button == &rejectAudioButton) {
        // 拒绝按钮的处理逻辑 - 清除当前选择的音频文件
        auto userMessage = userMessageToSend;
        if (userMessage.isNotEmpty()) {
            // 接受按钮的处理逻辑 - 确认当前选择的音频文件
            juce::Logger::writeToLog("reject");
            // 方法三：定义 Python 解释器和脚本的文件对象
            juce::File pythonInterpreterFile;
            juce::File pythonScriptFile;
            // 获取环境变量并记录原始值
            const char* pythonInterpreterEnv = std::getenv("SUPERTONAL_PYTHON_INTERPRETER");
            const char* pythonScriptEnv = std::getenv("SUPERTONAL_PYTHON_SCRIPT4"); // 修正名称，添加了"1"
            // 记录环境变量的原始值
            juce::Logger::writeToLog("Raw interpreter env value: " +
                (pythonInterpreterEnv != nullptr ? juce::String(pythonInterpreterEnv) : "null"));
            juce::Logger::writeToLog("Raw script env value: " +
                (pythonScriptEnv != nullptr ? juce::String(pythonScriptEnv) : "null"));
            pythonInterpreterFile = juce::File(pythonInterpreterEnv);
            pythonScriptFile = juce::File(pythonScriptEnv);
            const juce::String pythonInterpreterPath = pythonInterpreterFile.getFullPathName();
            const juce::String pythonScriptPath = pythonScriptFile.getFullPathName();
            juce::Logger::writeToLog("Python interpreter path: " + pythonInterpreterPath);
            juce::Logger::writeToLog("Python script path: " + pythonScriptPath);

            // 构建命令行：解释器 + 脚本 + 用户消息 + 音频路径（若有）+ 记忆状态
            juce::String command;
            command << pythonInterpreterPath.toStdString() << " " << pythonScriptPath.toStdString();

            // 添加用户消息参数（作为第一个参数）
            command << " \"" << userMessage << "\"";

            // 执行命令
            std::string utf8Command = command.toStdString();
            int returnCode = std::system(utf8Command.c_str());
            juce::Logger::writeToLog("commandWithErrorCapture: " + juce::String(utf8Command) + ", return code: " + juce::String(returnCode));
            if (returnCode != 0) {
                std::cerr << "Python script execution failed, return code: " << returnCode << std::endl;
                std::cerr << "执行的命令: " << command << std::endl;
                updateStatus("Python script execution failed");
            }
            else {
                updateStatus("rejected");
            }
        }
        else {
            updateStatus("No input");
        }
    }
    else if (button == &memoryToggleButton) {
        // 切换记忆状态
        memoryEnabled = memoryToggleButton.getToggleState();
        // 根据状态更新按钮文本
        if (memoryEnabled) {
            memoryToggleButton.setButtonText("MemoryOn");

            // 显示风格和特征权重输入控件
            textWeightLabel.setVisible(true);
            preferenceWeightLabel.setVisible(true);
            textWeightEditor.setVisible(true);
            preferenceWeightEditor.setVisible(true);

            // 只有当有音频文件时才显示音频权重控件
            updateAudioWeightVisibility();
            storeEnvWithType("memory_Enabled", "true", "string");
            storeEnvWithType("text_Weight", textWeightEditor.getText(), "double");
            storeEnvWithType("audio_Weight", audioWeightEditor.getText(), "double");
            storeEnvWithType("preference_Weight", preferenceWeightEditor.getText(), "double");
        }
        else {
            memoryToggleButton.setButtonText("MemoryOff");
            storeEnvWithType("memory_Enabled", "false", "string");
            storeEnvWithType("text_Weight", "0.0", "double");
            storeEnvWithType("audio_Weight", "0.0", "double");
            storeEnvWithType("preference_Weight", "0.0", "double");
            // 隐藏所有权重输入控件
            textWeightLabel.setVisible(false);
            preferenceWeightLabel.setVisible(false);
            audioWeightLabel.setVisible(false);
            textWeightEditor.setVisible(false);
            preferenceWeightEditor.setVisible(false);
            audioWeightEditor.setVisible(false);
        }
    }
}

// 添加一个新的辅助方法来更新音频权重控件的可见性
void ChatComponent::updateAudioWeightVisibility()
{
    // 只有当记忆功能开启且有音频文件时，才显示音频权重控件
    bool shouldShowAudioWeight = memoryEnabled && !audioFilePath.isEmpty();

    audioWeightLabel.setVisible(shouldShowAudioWeight);
    audioWeightEditor.setVisible(shouldShowAudioWeight);

    // 如果需要显示音频权重，确保权重值合理调整
    if (shouldShowAudioWeight) {
        // 重新计算权重，确保总和为1
        adjustWeightsForAudio(true);
    }
    else {
        // 如果不显示音频权重，则将权重重新分配给其他两个
        adjustWeightsForAudio(false);
    }
}

// 添加一个方法来调整权重值
void ChatComponent::adjustWeightsForAudio(bool includeAudio)
{
    if (!memoryEnabled) return;

    double textWeight = textWeightEditor.getText().getDoubleValue();
    double audioWeight = includeAudio ? audioWeightEditor.getText().getDoubleValue() : 0.0;
    double preferenceWeight = preferenceWeightEditor.getText().getDoubleValue();

    // 确保权重不为负
    if (textWeight < 0.0) textWeight = 0.0;
    if (audioWeight < 0.0) audioWeight = 0.0;
    if (preferenceWeight < 0.0) preferenceWeight = 0.0;

    double totalWeight = textWeight + audioWeight + preferenceWeight;

    // 如果总和接近0，设置默认值
    if (totalWeight < 0.001) {
        if (includeAudio) {
            // 三个权重均等
            textWeight = audioWeight = preferenceWeight = 1.0 / 3.0;
        }
        else {
            // 两个权重均等
            textWeight = preferenceWeight = 0.5;
            audioWeight = 0.0;
        }
    }
    else {
        // 归一化权重
        textWeight /= totalWeight;
        preferenceWeight /= totalWeight;
        if (includeAudio) {
            audioWeight /= totalWeight;
        }
        else {
            audioWeight = 0.0;
        }
    }

    // 更新UI
    textWeightEditor.setText(juce::String(textWeight, 2), false);
    if (includeAudio) {
        audioWeightEditor.setText(juce::String(audioWeight, 2), false);
    }
    preferenceWeightEditor.setText(juce::String(preferenceWeight, 2), false);
}

// 当文本内容改变时调用（实时监听）
void ChatComponent::textEditorTextChanged(juce::TextEditor& editor)
{
    // 如果记忆功能未开启，不处理
    if (!memoryEnabled) {
        return;
    }

    // 根据是哪个编辑器来更新对应的环境变量
    if (&editor == &textWeightEditor) {
        storeEnvWithType("text_Weight", editor.getText(), "double");
        juce::Logger::writeToLog("Text weight updated: " + editor.getText());
    }
    else if (&editor == &preferenceWeightEditor) {
        storeEnvWithType("preference_Weight", editor.getText(), "double");
        juce::Logger::writeToLog("Preference weight updated: " + editor.getText());
    }
    else if (&editor == &audioWeightEditor) {
        storeEnvWithType("audio_Weight", editor.getText(), "double");
        juce::Logger::writeToLog("Audio weight updated: " + editor.getText());
    }
}


// 实现 ChatComponent 类的 run 方法
void ChatComponent::run() {
    // 获取用户消息
    updateStatus("sending request");
    auto userMessage = userMessageToSend;
    if (userMessage.isNotEmpty()) {
        juce::Logger::writeToLog("send request: " + userMessage);
        juce::Logger::writeToLog("currentPresetName: " + currentPresetName);
    }

    // 检查音频文件路径是否存在
    if (!audioFilePath.isEmpty()) {
        juce::Logger::writeToLog("Audio file path: " + audioFilePath);
    }
    else {
        juce::Logger::writeToLog("No audio file selected");
    }
    auto text_Weight = textWeightEditor.getText();
    auto audio_Weight = audioWeightEditor.getText();
    auto preference_Weight = preferenceWeightEditor.getText();
    juce::Logger::writeToLog("textWeight:" + text_Weight);
    juce::Logger::writeToLog("audioWeight:" + audio_Weight);
    juce::Logger::writeToLog("preferenceWeight:" + preference_Weight);
    if (memoryEnabled) {
        juce::Logger::writeToLog("Memory feature is enabled");
        //storeEnvWithType("memory_Enabled", "true", "bool");
        double audioWeight = 0.0;
        // 获取权重值
        double textWeight = textWeightEditor.getText().getDoubleValue();
        double preferenceWeight = preferenceWeightEditor.getText().getDoubleValue();
        if (!audioFilePath.isEmpty()) {
            audioWeight = audioWeightEditor.getText().getDoubleValue();
        }
        // 计算总和
        double totalWeight = textWeight + preferenceWeight + audioWeight;
        if (std::abs(totalWeight - 1.0) > 0.001) {
            updateStatus("The sum of weights must be one, Please enter again");
            return;
        }
    }
    else {
        juce::Logger::writeToLog("Memory feature is disabled");
        //storeEnvWithType("memory_Enabled", "false", "bool");
    }
    
    // 方法三：定义 Python 解释器和脚本的文件对象
    juce::File pythonInterpreterFile;
    juce::File pythonScriptFile;
    // 获取环境变量并记录原始值
    const char* pythonInterpreterEnv = std::getenv("SUPERTONAL_PYTHON_INTERPRETER");
    const char* pythonScriptEnv = std::getenv("SUPERTONAL_PYTHON_SCRIPT1"); // 修正名称，添加了"1"

    // 记录环境变量的原始值
    juce::Logger::writeToLog("Raw interpreter env value: " +
        (pythonInterpreterEnv != nullptr ? juce::String(pythonInterpreterEnv) : "null"));
    juce::Logger::writeToLog("Raw script env value: " +
        (pythonScriptEnv != nullptr ? juce::String(pythonScriptEnv) : "null"));
   
    if (pythonInterpreterEnv != nullptr && pythonInterpreterEnv[0] != '\0') {
        pythonInterpreterFile = juce::File(pythonInterpreterEnv);
    }
    else {
        juce::File currentDir = juce::File::getCurrentWorkingDirectory();
        juce::File projectDir = currentDir;
        while (projectDir.getFileName() != "supertonal" && projectDir.getParentDirectory() != projectDir) {
            projectDir = projectDir.getParentDirectory();
        }
        pythonInterpreterFile = projectDir.getChildFile("Source/Components/PythonApplication/env/Scripts/python.exe");
    }
    
    if (pythonScriptEnv != nullptr && pythonScriptEnv[0] != '\0') {
        pythonScriptFile = juce::File(pythonScriptEnv);
    }
    else {
        juce::File currentDir = juce::File::getCurrentWorkingDirectory();
        juce::File projectDir = currentDir;
        while (projectDir.getFileName() != "supertonal" && projectDir.getParentDirectory() != projectDir) {
            projectDir = projectDir.getParentDirectory();
        }
        pythonScriptFile = projectDir.getChildFile("Source/sql.py");
    }
	const juce::String pythonInterpreterPath = pythonInterpreterFile.getFullPathName();
	const juce::String pythonScriptPath = pythonScriptFile.getFullPathName();
    juce::Logger::writeToLog("Python interpreter path: " + pythonInterpreterPath);
    juce::Logger::writeToLog("Python script path: " + pythonScriptPath);
    

    // 构建命令行：解释器 + 脚本 + 用户消息 + 音频路径（若有）+ 记忆状态
    juce::String command;
    command << pythonInterpreterPath.toStdString() << " " << pythonScriptPath.toStdString();

    // 添加用户消息参数（作为第一个参数）
    command << " \"" << userMessage << "\"";

    // 添加记忆状态参数（作为第二个参数）
    command << " \"" << (memoryEnabled ? "true" : "false") << "\"";

    if (!audioFilePath.isEmpty()) {
        command << " \"" << audioFilePath << "\"";
    }
    if (memoryEnabled) {
        // 添加文本权重参数（作为第三个参数）
        command << " \"" << text_Weight << "\"";
        // 添加用户偏好权重参数（作为第四个参数）
        command << " \"" << preference_Weight << "\"";
                // 添加音频权重参数（用引号包裹，处理空格）
        command << " \"" << audio_Weight << "\"";

    }




    // 存储环境变量（可选，也可仅通过命令行传递）
    storeEnvWithType("user_Message", userMessage, "string");
    if (!audioFilePath.isEmpty()) {
        storeEnvWithType("audio_File_Path", audioFilePath, "string");
    }

   

    // 执行命令
    std::string utf8Command = command.toStdString();
    int returnCode = std::system(utf8Command.c_str());
    juce::Logger::writeToLog("commandWithErrorCapture: " + juce::String(utf8Command) + ", return code: " + juce::String(returnCode));
    if (returnCode != 0) {
        std::cerr << "Python script execution failed, return code: " << returnCode << std::endl;
        std::cerr << "执行的命令: " << command << std::endl;
        updateStatus("Python script execution failed");
    }
    else {
        updateStatus("Python script executed successfully");

        // 读取并处理结果
        std::ifstream file(R"(result.txt)", std::ios::binary);
        if (!file.is_open()) {
            std::cerr << "Failed to open result.txt" << std::endl;
            file.close(); // 确保关闭之前的尝试

            // 使用JUCE的SystemStats来获取环境变量
            juce::String documentsPath = juce::SystemStats::getEnvironmentVariable("DOCUMENTS_DIR", "");

            if (documentsPath.isEmpty()) {
                // 如果环境变量未设置，记录警告
                std::cerr << "DOCUMENTS_DIR environment variable not set" << std::endl;
                updateStatus("Failed to open DOCUMENTS_DIR");
            }
            else {
                // 使用JUCE的File类构建路径
                juce::File resultFile = juce::File(documentsPath).getChildFile("result.txt");
                file.open(resultFile.getFullPathName().toStdString(), std::ios::binary);
            }

            if (!file.is_open()) {
                std::cerr << "Failed to open file from alternative location" << std::endl;
                updateStatus("Failed to open result file from all locations");
                return; // 或者尝试其他位置
            }
        }

        std::stringstream buffer;
        buffer << file.rdbuf();
        std::string resultBytes = buffer.str();
        file.close();

        // 读取并处理result3.txt
        std::ifstream file3(R"(result3.txt)", std::ios::binary);
        if (!file3.is_open()) {
            std::cerr << "Failed to open result3.txt" << std::endl;
            file3.close(); // 确保关闭之前的尝试

            // 使用JUCE的SystemStats来获取环境变量
            juce::String documentsPath = juce::SystemStats::getEnvironmentVariable("DOCUMENTS_DIR", "");

            if (!documentsPath.isEmpty()) {
                // 使用JUCE的File类构建路径
                juce::File result3File = juce::File(documentsPath).getChildFile("result3.txt");
                file3.open(result3File.getFullPathName().toStdString(), std::ios::binary);
            }

            if (!file3.is_open()) {
                std::cerr << "Failed to open result3.txt from alternative location" << std::endl;
                // 这里我们不返回，因为我们已经有了result.txt的数据
            }
        }
        // 如果成功打开了result3.txt，则读取其内容
        std::string result3Bytes;
        if (file3.is_open()) {
            std::stringstream buffer3;
            buffer3 << file3.rdbuf();
            result3Bytes = buffer3.str();
            file3.close();
        }
        else {
			result3Bytes = "No data"; // 或者其他默认值
        }
        juce::String resultStr = juce::String::fromUTF8(resultBytes.data(), resultBytes.size());
        EffectParameters params = extractParameters(resultStr);
        juce::String result3Str = juce::String::fromUTF8(result3Bytes.data(), result3Bytes.size());
        callAsync(juce::String(result3Str));
    }
}




// 实现 ChatComponent 类的 updateStatus 方法
void ChatComponent::updateStatus(const juce::String& text)
{
    juce::MessageManager::callAsync([this, text]() {
        statusLabel.setColour(juce::Label::textColourId, juce::Colours::black);
        statusLabel.setText(text, juce::dontSendNotification);
        });
}


// 实现MainWindow构造函数，用参数初始化presetManager引用
MainWindow::MainWindow(PluginPresetManager& pm)
    : DocumentWindow("DeepSeek Chat",
        juce::Colours::lightgrey,
        DocumentWindow::allButtons), // 注意移除错误的presetManager(pm)初始化
    presetManager(pm) // 正确初始化引用成员
{
    tabbedComponent = std::make_unique<juce::TabbedComponent>(juce::TabbedButtonBar::TabsAtTop);
    // 现在可以使用初始化后的presetManager了
    tabbedComponent->addTab("Chat", juce::Colours::lightblue, new ChatComponent(presetManager), true);

    setContentOwned(tabbedComponent.get(), true);
    centreWithSize(800, 600);
    setVisible(true);
}

// 实现 MainWindow 类的 closeButtonPressed 方法
void MainWindow::closeButtonPressed()
{
    // 确认关闭应用程序
    juce::JUCEApplication::quit();
}