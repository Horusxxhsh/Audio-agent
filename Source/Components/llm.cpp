#include "llm.h"
#include <cstdlib>
#include <sstream>
#include <string>
#include <fstream>
#include <juce_core/juce_core.h>
#include "../PluginPresetManager.h"
#include <windows.h> 

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
    memoryToggleButton("MemoryOff")  // 初始化为 MemoryOff
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
    responseEditor.setMultiLine(true);
    responseEditor.setReadOnly(true);

    // Initialize audio file selection button
    addAndMakeVisible(audioFileButton);
    audioFileButton.addListener(this);  // Listen for button clicks
    audioFileButton.setTooltip("Select audio file (supports wav, mp3, aif, flac, etc.)");

    // Initialize audio file path label (optional, used to display selected file)
    addAndMakeVisible(audioFileLabel);
    audioFileLabel.setColour(juce::Label::textColourId, juce::Colours::darkgrey);

    // 初始化取消按钮
    addAndMakeVisible(cancelAudioButton);
    cancelAudioButton.addListener(this);
    cancelAudioButton.setTooltip("Clear selected audio file");
    cancelAudioButton.setEnabled(false);  // 初始状态下禁用，因为没有文件被选择

    // 初始化记忆开关按钮
    addAndMakeVisible(memoryToggleButton);
    memoryToggleButton.addListener(this);
    memoryToggleButton.setClickingTogglesState(true);  // 设置为开关按钮
    memoryToggleButton.setColour(juce::TextButton::buttonOnColourId, juce::Colours::green);  // 开启状态颜色
    memoryToggleButton.setTooltip("Toggle memory feature on/off");

    setSize(600, 400);
}


// Implement the resized method of ChatComponent class
void ChatComponent::resized()
{
    auto area = getLocalBounds().reduced(8);


    // 为记忆开关按钮分配空间（放在顶部）
    auto topButtonArea = area.removeFromTop(30);  // 为顶部按钮预留空间
    memoryToggleButton.setBounds(topButtonArea.removeFromRight(100).reduced(2));  // 记忆开关按钮

    // 音频文件选择区域
    auto audioArea = area.removeFromTop(40);
    // 分配空间给音频文件选择按钮和取消按钮
    audioFileButton.setBounds(audioArea.removeFromLeft(150).reduced(2));  // 减小宽度以适应取消按钮
    cancelAudioButton.setBounds(audioArea.removeFromLeft(120).reduced(2));  // 为取消按钮分配空间
    audioFileLabel.setBounds(audioArea.reduced(2));  // 标签占据剩余区域

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
            inputEditor.clear();
            startThread();  // Start thread
        }
    }else if (button == &audioFileButton) {
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
                    }
                }
            });
    }

    //根据juce版本调节代码
    //else if (button == &audioFileButton) {
    //    // Create file chooser, specify title and default path (here, user's desktop)
    //    juce::FileChooser fileChooser("Select audio file",
    //        juce::File::getSpecialLocation(juce::File::userDesktopDirectory),
    //        "Audio files (*.wav;*.WAV;*.mp3;*.MP3;*.aif;*.AIF;*.flac;*.FLAC)");  // Supported formats

    //    // Show open file dialog (modal window)
    //    if (fileChooser.browseForFileToOpen())
    //    {
    //        // Get selected file path
    //        juce::File selectedFile = fileChooser.getResult();
    //        audioFilePath = selectedFile.getFullPathName();

    //        // Update label to display selected file name (or full path)
    //        audioFileLabel.setText("Selected: " + selectedFile.getFileName(), juce::dontSendNotification);

    //        // Optional: Add file validation logic here (e.g., check file size, format, etc.)
    //        if (selectedFile.getSize() == 0)
    //        {
    //            juce::AlertWindow::showMessageBoxAsync(juce::AlertWindow::WarningIcon,
    //                "Error",
    //                "The selected file is empty!");
    //            audioFilePath.clear();
    //            audioFileLabel.setText("No file selected", juce::dontSendNotification);
    //        }
    //    }
    //}
    else if (button == &cancelAudioButton) {
        // 取消按钮的处理逻辑
        audioFilePath.clear();  // 清除文件路径
        storeEnvWithType("audio_File_Path", "", "string");  // 清除环境变量
        audioFileLabel.setText("No file selected", juce::dontSendNotification);  // 重置标签
        cancelAudioButton.setEnabled(false);  // 禁用取消按钮，因为没有文件可以取消

        // 记录日志
        juce::Logger::writeToLog("Audio file selection cleared");
    }
    else if (button == &memoryToggleButton) {
        // 切换记忆状态
        memoryEnabled = memoryToggleButton.getToggleState();
        // 根据状态更新按钮文本
        if (memoryEnabled) {
            memoryToggleButton.setButtonText("MemoryOn");
            storeEnvWithType("memory_Enabled", "true", "string");
        }
        else {
            memoryToggleButton.setButtonText("MemoryOff");
            storeEnvWithType("memory_Enabled", "false", "string");
        }

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

    if (memoryEnabled) {
        juce::Logger::writeToLog("Memory feature is enabled");
        //storeEnvWithType("memory_Enabled", "true", "bool");
    }
    else {
        juce::Logger::writeToLog("Memory feature is disabled");
        //storeEnvWithType("memory_Enabled", "false", "bool");
    }

    //// 方法一：假设您知道项目根目录与当前工作目录的关系
    //juce::File currentDir = juce::File::getCurrentWorkingDirectory();
    //juce::Logger::writeToLog("Current working directory: " + currentDir.getFullPathName());

    //// 如果当前目录是 Builds，则向上一级再找到 supertonal 目录
    //juce::File projectDir = currentDir;
    //while (projectDir.getFileName() != "supertonal" && projectDir.getParentDirectory() != projectDir) {
    //    projectDir = projectDir.getParentDirectory();
    //}

    //juce::Logger::writeToLog("Project directory: " + projectDir.getFullPathName());

    //// Python 解释器路径
    //juce::File pythonInterpreterFile = projectDir.getChildFile("Source/Components/PythonApplication/env/Scripts/python.exe");
    //const juce::String pythonInterpreterPath = pythonInterpreterFile.getFullPathName();

    //// Python 脚本路径
    //juce::File pythonScriptFile = projectDir.getChildFile("Source/llm.py");
    //const juce::String pythonScriptPath = pythonScriptFile.getFullPathName();

    //// 记录路径用于调试
    //juce::Logger::writeToLog("Python interpreter path: " + pythonInterpreterPath);
    //juce::Logger::writeToLog("Python script path: " + pythonScriptPath);

    //// 方法二：定义 Python 解释器和脚本路径
    //const char* pythonInterpreterPath = R"(C:\Users\80753\Documents\GitHub\Audio-agent\Source\Components\PythonApplication\env\Scripts\python.exe)";
    //const char* pythonScriptPath = R"(C:\Users\80753\Documents\GitHub\Audio-agent\Source\llm.py)";
    
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

    // 添加用户消息参数（用引号包裹，处理空格）
    command << " \"" << userMessage << "\"";

    // 添加记忆状态参数（作为第三个参数）
    command << " \"" << (memoryEnabled ? "true" : "false") << "\"";

    // 添加音频文件路径参数（若存在，用引号包裹）
    if (!audioFilePath.isEmpty()) {
        command << " \"" << audioFilePath << "\"";
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

        juce::String resultStr = juce::String::fromUTF8(resultBytes.data(), resultBytes.size());
        EffectParameters params = extractParameters(resultStr);
        callAsync(juce::String(params.toString()));
    }
}




// 实现 ChatComponent 类的 updateStatus 方法
void ChatComponent::updateStatus(const juce::String& text)
{
    juce::MessageManager::callAsync(
        [this, text]() { statusLabel.setText(text, juce::dontSendNotification); });
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