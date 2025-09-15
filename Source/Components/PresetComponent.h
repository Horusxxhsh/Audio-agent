#include <JuceHeader.h>
#include "../PluginPresetManager.h"
#include "../PluginAudioProcessor.h"
#include "llm.h"
#include <cstdlib>
#include <sstream>
#include <string>
#include <fstream>
#include <juce_core/juce_core.h>
#include "DelayComponent.h"

// Windows 特定头文件
#ifdef _WIN32
#include <windows.h>
#undef min  // 避免与 std::min 冲突
#undef max  // 避免与 std::max 冲突
#endif

class PresetComponent : public juce::Component, juce::Button::Listener, juce::ComboBox::Listener
{
public:
    PresetComponent(PluginAudioProcessor& processor, PluginPresetManager& pm, juce::UndoManager& um)
        : audioProcessor(processor), presetManager(pm), undoManager(um)
    {
        configureButton(undoButton, "Undo");
        configureButton(redoButton, "Redo");
        configureButton(saveButton, "Save");
        configureButton(sqlButton, "sql");
        configureButton(deleteButton, "Delete");
        configureButton(previousPresetButton, "<");
        configureButton(nextPresetButton, ">");
        configureButton(resetButton, "Reset");

        presetList.setTextWhenNothingSelected("No Preset Selected");
        presetList.setMouseCursor(juce::MouseCursor::PointingHandCursor);
        presetList.setColour(juce::ComboBox::textColourId, juce::Colours::black);
        presetList.setColour(juce::ComboBox::backgroundColourId, juce::Colour::fromRGB(0xB0, 0xB0, 0xB0));
        presetList.setColour(juce::ComboBox::arrowColourId, juce::Colours::black);
        presetList.setColour(juce::ComboBox::outlineColourId, juce::Colour::fromRGB(0xB0, 0xC4, 0xD9));

        addAndMakeVisible(presetList);
        presetList.addListener(this);

        loadPresetList();
    }

    ~PresetComponent()
    {
        undoButton.removeListener(this);
        redoButton.removeListener(this);
        saveButton.removeListener(this);
        sqlButton.removeListener(this);
        deleteButton.removeListener(this);
        resetButton.removeListener(this);
        previousPresetButton.removeListener(this);
        nextPresetButton.removeListener(this);
        presetList.removeListener(this);
    }

    void resized() override
    {
        const auto localBounds = getLocalBounds();
        auto bounds = localBounds;

        undoButton.setBounds(bounds.removeFromLeft(localBounds.proportionOfWidth(0.1f)));
        redoButton.setBounds(bounds.removeFromLeft(localBounds.proportionOfWidth(0.1f)));
        saveButton.setBounds(bounds.removeFromLeft(localBounds.proportionOfWidth(0.1f)));
        sqlButton.setBounds(bounds.removeFromLeft(localBounds.proportionOfWidth(0.1f)));
        previousPresetButton.setBounds(bounds.removeFromLeft(localBounds.proportionOfWidth(0.1f)));
        presetList.setBounds(bounds.removeFromLeft(localBounds.proportionOfWidth(0.2f)));
        nextPresetButton.setBounds(bounds.removeFromLeft(localBounds.proportionOfWidth(0.1f)));
        deleteButton.setBounds(bounds.removeFromLeft(localBounds.proportionOfWidth(0.1f)));
        resetButton.setBounds(bounds.removeFromLeft(localBounds.proportionOfWidth(0.1f)));
    }

private:
    void buttonClicked(juce::Button* button) override
    {
        if (button == &saveButton)
        {
            fileChooser = std::make_unique<juce::FileChooser>(
                "Please enter the name of the preset to save",
                PluginPresetManager::defaultDirectory,
                "*." + PluginPresetManager::extension
            );
            fileChooser->launchAsync(juce::FileBrowserComponent::saveMode, [&](const juce::FileChooser& chooser)
                {
                    const auto resultFile = chooser.getResult();
                    presetManager.savePreset(resultFile.getFileNameWithoutExtension());
                    loadPresetList();
                });
        }
        if (button == &sqlButton)
        {
            std::string userMessage = readEnvWithType<std::string>("user_Message");
            std::string audioPath = readEnvWithType<std::string>("audio_File_Path");
            double text_Weight = readEnvWithType<double>("text_Weight");
            double audio_Weight = readEnvWithType<double>("audio_Weight");
            double preference_Weight = readEnvWithType<double>("preference_Weight");
            std::string text_Weight_str = std::to_string(text_Weight);
            std::string audio_Weight_str = std::to_string(audio_Weight);
            std::string preference_Weight_str = std::to_string(preference_Weight);

            juce::Logger::writeToLog("text_Weight:" + text_Weight_str);
            juce::Logger::writeToLog("audio_Weight:" + audio_Weight_str);
            juce::Logger::writeToLog("preference_Weight:" + preference_Weight_str);

            std::string memoryEnabled = readEnvWithType<std::string>("memory_Enabled");
            if (memoryEnabled == "") {
                memoryEnabled = "false";
            }

            juce::Logger::writeToLog("memoryEnabled (raw):" + juce::String(memoryEnabled));
            juce::Logger::writeToLog("userMessage:" + juce::String(userMessage));

            std::string currentPresetName = presetManager.getCurrentPreset().toStdString();
            juce::Logger::writeToLog("currentPresetName:" + juce::String(currentPresetName));

            if (userMessage.empty() && currentPresetName.empty()) {
                juce::Logger::writeToLog("userMessage and currentPresetName are both empty");
                return;
            }

            // 收集所有效果器的开关状态
            const auto index1 = presetManager.getParameterValue("pre_compressor_on");
            const auto index2 = presetManager.getParameterValue("tube_screamer_on");
            const auto index3 = presetManager.getParameterValue("mouse_drive_on");
            const auto index4 = presetManager.getParameterValue("delay_on");
            const auto index5 = presetManager.getParameterValue("room_on");
            const auto index6 = presetManager.getParameterValue("chorus_on");
            const auto index7 = presetManager.getParameterValue("flanger_on");
            const auto index8 = presetManager.getParameterValue("phaser_on");
            const auto index9 = presetManager.getParameterValue("pre_eq_on");

            // 构建参数字符串，以开关状态开始
            std::string paramString = std::to_string(index1) + "," + std::to_string(index2) + ","
                + std::to_string(index3) + "," + std::to_string(index4) + ","
                + std::to_string(index5) + "," + std::to_string(index6) + ","
                + std::to_string(index7) + "," + std::to_string(index8) + ","
                + std::to_string(index9);

            // 用于跟踪已添加的参数数量
            int paramCount = 9; // 初始为9个开关状态参数

            // 根据开关状态添加对应效果器的参数
            //1 - Compressor
            if (index1 == true) {
                const auto comp1 = presetManager.getParameterValue("pre_comp_thresh");
                juce::Logger::writeToLog("pre_comp_thresh:" + juce::String(comp1));
                const auto comp2 = presetManager.getParameterValue("pre_comp_attack");
                const auto comp3 = presetManager.getParameterValue("pre_comp_ratio");
                const auto comp4 = presetManager.getParameterValue("pre_comp_release");
                const auto comp5 = presetManager.getParameterValue("pre_comp_gain");
                const auto comp6 = presetManager.getParameterValue("pre_comp_blend");
                paramString += "," + std::to_string(comp1) + "," + std::to_string(comp2)
                    + "," + std::to_string(comp3) + "," + std::to_string(comp4)
                    + "," + std::to_string(comp5) + "," + std::to_string(comp6);
                paramCount += 6;
            }
            else {
                const auto comp1 = -128.00;
                const auto comp2 = 0.00;
                const auto comp3 = 1;
                const auto comp4 = 0.00;
                const auto comp5 = -12.00;
                const auto comp6 = 0.00;
                paramString += "," + std::to_string(comp1) + "," + std::to_string(comp2)
                    + "," + std::to_string(comp3) + "," + std::to_string(comp4)
                    + "," + std::to_string(comp5) + "," + std::to_string(comp6);
                paramCount += 6;
            }

            //2 - Tube Screamer
            if (index2 == true) {
                const auto screamer1 = presetManager.getParameterValue("tube_screamer_drive");
                const auto screamer2 = presetManager.getParameterValue("tube_screamer_level");
                const auto screamer3 = presetManager.getParameterValue("tube_screamer_tone");
                paramString += "," + std::to_string(screamer1) + "," + std::to_string(screamer2)
                    + "," + std::to_string(screamer3);
                paramCount += 3;
            }
            else {
                const auto screamer1 = 0.00;
                const auto screamer2 = -64.0000000;
                const auto screamer3 = 0.00;
                paramString += "," + std::to_string(screamer1) + "," + std::to_string(screamer2)
                    + "," + std::to_string(screamer3);
                paramCount += 3;
            }

            //3 - Mouse Drive
            if (index3 == true) {
                const auto drive1 = presetManager.getParameterValue("mouse_drive_distortion");
                const auto drive2 = presetManager.getParameterValue("mouse_drive_volume");
                paramString += "," + std::to_string(drive1) + "," + std::to_string(drive2);
                paramCount += 2;
            }
            else {
                const auto drive1 = 0.00;
                const auto drive2 = -64.0;
                paramString += "," + std::to_string(drive1) + "," + std::to_string(drive2);
                paramCount += 2;
            }

            //4 - Delay
            if (index4 == true) {
                const auto delay1 = presetManager.getParameterValue("delay_feedback");
                const auto delay2 = presetManager.getParameterValue("delay_left_millisecond");
                const auto delay3 = presetManager.getParameterValue("delay_mix");
                paramString += "," + std::to_string(delay1) + "," + std::to_string(delay2)
                    + "," + std::to_string(delay3);
                paramCount += 3;
            }
            else {
                const auto delay1 = 0.00;
                const auto delay2 = 1.00;
                const auto delay3 = 0.00;
                paramString += "," + std::to_string(delay1) + "," + std::to_string(delay2)
                    + "," + std::to_string(delay3);
                paramCount += 3;
            }

            //5 - Room
            if (index5 == true) {
                const auto room1 = presetManager.getParameterValue("room_size");
                const auto room2 = presetManager.getParameterValue("room_damping");
                const auto room3 = presetManager.getParameterValue("room_width");
                const auto room4 = presetManager.getParameterValue("room_mix");
                paramString += "," + std::to_string(room1) + "," + std::to_string(room2)
                    + "," + std::to_string(room3) + "," + std::to_string(room4);
                paramCount += 4;
            }
            else {
                const auto room1 = 0.00;
                const auto room2 = 0.00;
                const auto room3 = 0.00;
                const auto room4 = 0.00;
                paramString += "," + std::to_string(room1) + "," + std::to_string(room2)
                    + "," + std::to_string(room3) + "," + std::to_string(room4);
                paramCount += 4;
            }

            //6 - Chorus
            if (index6 == true) {
                const auto chorus1 = presetManager.getParameterValue("chorus_delay");
                const auto chorus2 = presetManager.getParameterValue("chorus_depth");
                const auto chorus3 = presetManager.getParameterValue("chorus_feedback");
                const auto chorus4 = presetManager.getParameterValue("chorus_width");
                paramString += "," + std::to_string(chorus1) + "," + std::to_string(chorus2)
                    + "," + std::to_string(chorus3) + "," + std::to_string(chorus4);
                paramCount += 4;
            }
            else {
                const auto chorus1 = 0.010;
                const auto chorus2 = 0.00;
                const auto chorus3 = 0.05;
                const auto chorus4 = 0.010;
                paramString += "," + std::to_string(chorus1) + "," + std::to_string(chorus2)
                    + "," + std::to_string(chorus3) + "," + std::to_string(chorus4);
                paramCount += 4;
            }

            //7 - Flanger
            if (index7 == true) {
                const auto flanger1 = presetManager.getParameterValue("flanger_delay");
                const auto flanger2 = presetManager.getParameterValue("flanger_depth");
                const auto flanger3 = presetManager.getParameterValue("flanger_feedback");
                const auto flanger4 = presetManager.getParameterValue("flanger_frequency");
                const auto flanger5 = presetManager.getParameterValue("flanger_width");
                paramString += "," + std::to_string(flanger1) + "," + std::to_string(flanger2)
                    + "," + std::to_string(flanger3) + "," + std::to_string(flanger4)
                    + "," + std::to_string(flanger5);
                paramCount += 5;
            }
            else {
                const auto flanger1 = 0.00100;
                const auto flanger2 = 0.00;
                const auto flanger3 = 0.00;
                const auto flanger4 = 0.05;
                const auto flanger5 = 0.001;
                paramString += "," + std::to_string(flanger1) + "," + std::to_string(flanger2)
                    + "," + std::to_string(flanger3) + "," + std::to_string(flanger4)
                    + "," + std::to_string(flanger5);
                paramCount += 5;
            }

            //8 - Phaser
            if (index8 == true) {
                const auto phaser1 = presetManager.getParameterValue("phaser_depth");
                const auto phaser2 = presetManager.getParameterValue("phaser_feedback");
                const auto phaser3 = presetManager.getParameterValue("phaser_frequency");
                const auto phaser4 = presetManager.getParameterValue("phaser_width");
                paramString += "," + std::to_string(phaser1) + "," + std::to_string(phaser2)
                    + "," + std::to_string(phaser3) + "," + std::to_string(phaser4);
                paramCount += 4;
            }
            else {
                const auto phaser1 = 0.00;
                const auto phaser2 = 0.00;
                const auto phaser3 = 0.05;
                const auto phaser4 = 50;
                paramString += "," + std::to_string(phaser1) + "," + std::to_string(phaser2)
                    + "," + std::to_string(phaser3) + "," + std::to_string(phaser4);
                paramCount += 4;
            }

            //9 - EQ
            if (index9 == true) {
                const auto eq1 = presetManager.getParameterValue("pre_eq_100_gain");
                const auto eq2 = presetManager.getParameterValue("pre_eq_200_gain");
                const auto eq3 = presetManager.getParameterValue("pre_eq_400_gain");
                const auto eq4 = presetManager.getParameterValue("pre_eq_800_gain");
                const auto eq5 = presetManager.getParameterValue("pre_eq_1600_gain");
                const auto eq6 = presetManager.getParameterValue("pre_eq_3200_gain");
                const auto eq7 = presetManager.getParameterValue("pre_eq_6400_gain");
                const auto eq8 = presetManager.getParameterValue("pre_eq_level_gain");
                paramString += "," + std::to_string(eq1) + "," + std::to_string(eq2)
                    + "," + std::to_string(eq3) + "," + std::to_string(eq4)
                    + "," + std::to_string(eq5) + "," + std::to_string(eq6)
                    + "," + std::to_string(eq7) + "," + std::to_string(eq8);
                paramCount += 8;
            }
            else {
                const auto eq1 = 0.00;
                const auto eq2 = 0.00;
                const auto eq3 = 0.00;
                const auto eq4 = 0.00;
                const auto eq5 = 0.00;
                const auto eq6 = 0.00;
                const auto eq7 = 0.00;
                const auto eq8 = 0.00;
                paramString += "," + std::to_string(eq1) + "," + std::to_string(eq2)
                    + "," + std::to_string(eq3) + "," + std::to_string(eq4)
                    + "," + std::to_string(eq5) + "," + std::to_string(eq6)
                    + "," + std::to_string(eq7) + "," + std::to_string(eq8);
                paramCount += 8;
            }

            juce::Logger::writeToLog("paramCount:" + juce::String(paramCount));

            // 添加参数总数作为最后一个元素
            paramString += "," + std::to_string(paramCount);
            juce::Logger::writeToLog("paramString:" + juce::String(paramString));

            // 获取 Python 解释器和脚本路径
            juce::File pythonInterpreterFile;
            juce::File pythonScriptFile;

            const char* pythonInterpreterEnv = std::getenv("SUPERTONAL_PYTHON_INTERPRETER");
            const char* pythonScriptEnv = std::getenv("SUPERTONAL_PYTHON_SCRIPT2");

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

            // 构建完整的命令行
            std::string command = "\"" + pythonInterpreterPath.toStdString() + "\" \"" + pythonScriptPath.toStdString() + "\"";
            command += " \"" + paramString + "\"";                    // 第一个参数: 所有效果器参数
            command += " \"" + userMessage + "\"";                    // 第二个参数: 用户消息
            command += " \"" + currentPresetName + "\"";              // 第三个参数: 当前预设名称
            command += " \"" + memoryEnabled + "\"";                  // 第四个参数: 记忆功能状态
            command += " \"" + audioPath + "\"";                      // 第五个参数: 音频文件路径
            command += " " + text_Weight_str;                         // 第六个参数: 文字权重
            command += " " + audio_Weight_str;                        // 第七个参数: 音频权重
            command += " " + preference_Weight_str;                   // 第八个参数: 偏好权重

            juce::Logger::writeToLog("Executing command: " + juce::String(command));

#ifdef _WIN32
            // Windows 特定的进程创建代码
            STARTUPINFOA si = { sizeof(si) };
            PROCESS_INFORMATION pi = { 0 };

            // 设置启动信息，隐藏窗口
            si.dwFlags = STARTF_USESHOWWINDOW;
            si.wShowWindow = SW_HIDE;

            // 创建进程
            if (!CreateProcessA(
                NULL,                                    // 应用程序名称
                const_cast<LPSTR>(command.c_str()),     // 命令行
                NULL,                                    // 进程安全属性
                NULL,                                    // 线程安全属性
                FALSE,                                   // 不继承句柄
                CREATE_NO_WINDOW,                        // 创建标志：无窗口
                NULL,                                    // 环境变量
                NULL,                                    // 当前目录
                &si,                                     // 启动信息
                &pi                                      // 进程信息
            )) {
                DWORD error = GetLastError();
                std::cerr << "CreateProcess failed with error: " << error << std::endl;
                juce::Logger::writeToLog("Failed to execute Python script with error: " + juce::String(error));

                // 如果 CreateProcess 失败，尝试使用 system() 作为备用方案
                juce::Logger::writeToLog("Falling back to system() call");
                int returnCode = std::system(command.c_str());
                juce::Logger::writeToLog("System call return code: " + juce::String(returnCode));
                return;
            }

            juce::Logger::writeToLog("Python process created successfully");

            // 等待进程完成
            DWORD waitResult = WaitForSingleObject(pi.hProcess, 30000); // 30秒超时

            if (waitResult == WAIT_TIMEOUT) {
                juce::Logger::writeToLog("Python process timed out, terminating...");
                TerminateProcess(pi.hProcess, 1);
                CloseHandle(pi.hProcess);
                CloseHandle(pi.hThread);
                return;
            }
            else if (waitResult == WAIT_FAILED) {
                DWORD error = GetLastError();
                juce::Logger::writeToLog("Wait failed with error: " + juce::String(error));
            }

            // 获取进程退出码
            DWORD exitCode;
            if (GetExitCodeProcess(pi.hProcess, &exitCode)) {
                int returnCode = static_cast<int>(exitCode);
                juce::Logger::writeToLog("Python script executed with return code: " + juce::String(returnCode));

                if (returnCode != 0) {
                    juce::Logger::writeToLog("Python script execution failed");
                }
                else {
                    juce::Logger::writeToLog("Python script executed successfully");
                }
            }
            else {
                DWORD error = GetLastError();
                juce::Logger::writeToLog("GetExitCodeProcess failed with error: " + juce::String(error));
            }

            // 清理句柄
            CloseHandle(pi.hProcess);
            CloseHandle(pi.hThread);

#else
            // 非 Windows 系统使用 system() 调用
            juce::Logger::writeToLog("Using system() call for non-Windows platform");
            int returnCode = std::system(command.c_str());

            juce::Logger::writeToLog("Python script executed with return code: " + juce::String(returnCode));

            if (returnCode != 0) {
                juce::Logger::writeToLog("Python script execution failed");
            }
            else {
                juce::Logger::writeToLog("Python script executed successfully");
            }
#endif
        }

        if (button == &previousPresetButton)
        {
            const auto index = presetManager.loadPreviousPreset();
            presetList.setSelectedItemIndex(index, juce::dontSendNotification);
        }
        if (button == &nextPresetButton)
        {
            const auto index = presetManager.loadNextPreset();
            presetList.setSelectedItemIndex(index, juce::dontSendNotification);
        }
        if (button == &deleteButton)
        {
            presetManager.deletePreset(presetManager.getCurrentPreset());
            loadPresetList();
        }
        if (button == &undoButton)
        {
            undoManager.undo();
        }
        if (button == &redoButton)
        {
            undoManager.redo();
        }
        if (button == &resetButton)
        {
            audioProcessor.resetParametersToDefault();
        }
    }

    void comboBoxChanged(juce::ComboBox* comboBoxThatHasChanged) override
    {
        if (comboBoxThatHasChanged == &presetList)
        {
            presetManager.loadPreset(presetList.getItemText(presetList.getSelectedItemIndex()));
        }
    }

    void configureButton(juce::Button& button, const juce::String& buttonText)
    {
        button.setButtonText(buttonText);
        button.addListener(this);
        button.setColour(juce::TextButton::buttonColourId, juce::Colour(220, 235, 250));
        button.setColour(juce::TextButton::buttonOnColourId, juce::Colour(255, 175, 100));
        button.setColour(juce::TextButton::textColourOffId, juce::Colour(255, 160, 80));
        addAndMakeVisible(button);
    }

    void loadPresetList()
    {
        presetList.clear(juce::dontSendNotification);
        const auto allPresets = presetManager.getAllPresets();
        const auto currentPreset = presetManager.getCurrentPreset();
        presetList.addItemList(allPresets, 1);
        presetList.setSelectedItemIndex(allPresets.indexOf(currentPreset), juce::dontSendNotification);
    }

    PluginAudioProcessor& audioProcessor;
    PluginPresetManager& presetManager;
    juce::UndoManager& undoManager;
    juce::TextButton undoButton, redoButton, saveButton, sqlButton, deleteButton, previousPresetButton, nextPresetButton, resetButton;
    juce::ComboBox presetList;
    std::unique_ptr<juce::FileChooser> fileChooser;
    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(PresetComponent)
};