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
        presetList.setColour(juce::ComboBox::textColourId, juce::Colours::black); // 浅橘色文本
        presetList.setColour(juce::ComboBox::backgroundColourId, juce::Colour::fromRGB(0xB0, 0xB0, 0xB0));
        presetList.setColour(juce::ComboBox::arrowColourId, juce::Colours::black);
		presetList.setColour(juce::ComboBox::outlineColourId, juce::Colour::fromRGB(0xB0, 0xC4, 0xD9)); // 边框颜色

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
            // 记录实际读取到的 memoryEnabled 值
            juce::Logger::writeToLog("memoryEnabled (raw):" + juce::String(memoryEnabled));
            // 在日志中打印 userMessage 的值
            juce::Logger::writeToLog("userMessage:" + juce::String(userMessage));
            std::string currentPresetName = presetManager.getCurrentPreset().toStdString();
            juce::Logger::writeToLog("currentPresetName:" + juce::String(currentPresetName));
            if (userMessage.empty() && currentPresetName.empty()) {
                // 在日志中打印相关信息
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
            //1
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
                juce::Logger::writeToLog("pre_comp_thresh:" + juce::String(comp1));
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
            //2
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
            //3
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
            //4
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
            //5
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
            //6
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
            //7
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
            //8
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
            //9
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
            else{
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
            
            //// 定义 Python 解释器路径和 Python 脚本路径
            //const char* pythonInterpreterPath = R"(C:\Users\80753\Documents\GitHub\supertonal\Source\Components\PythonApplication\env\Scripts\python.exe)";
            ////const char* pythonScriptPath = R"(E:\c++\juceproject\juceEffector\supertonal\Source\Components\PythonApplication\sql.py)";
            //const char* pythonScriptPath = R"("C:\Users\80753\Documents\GitHub\supertonal\Source\sql.py")";

            //// 假设您知道项目根目录与当前工作目录的关系
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
            //juce::File pythonScriptFile = projectDir.getChildFile("Source/sql.py");
            //const juce::String pythonScriptPath = pythonScriptFile.getFullPathName();

            //// 记录路径用于调试
            //juce::Logger::writeToLog("Python interpreter path: " + pythonInterpreterPath);
            //juce::Logger::writeToLog("Python script path: " + pythonScriptPath);

            // 定义 Python 解释器和脚本的文件对象
            juce::File pythonInterpreterFile;
            juce::File pythonScriptFile;
            // 获取环境变量并记录原始值
            const char* pythonInterpreterEnv = std::getenv("SUPERTONAL_PYTHON_INTERPRETER");
            const char* pythonScriptEnv = std::getenv("SUPERTONAL_PYTHON_SCRIPT2"); // 修正名称，添加了"1"

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

            /// 构建执行 Python 脚本的命令，将所有参数传递给 Python 脚本
            std::string command = pythonInterpreterPath.toStdString(); // 使用 toStdString() 进行转换
            command += " ";
            command += pythonScriptPath.toStdString(); // 使用 toStdString() 进行转换
            command += " \"" + paramString + "\"";  // 第一个参数: 所有效果器参数
            command += " \"" + userMessage + "\"";  // 第二个参数: 用户消息
            command += " \"" + currentPresetName + "\"";  // 第三个参数: 当前预设名称
            command += " \"" + memoryEnabled + "\"";  // 第四个参数: 记忆功能状态
            command += " \"" + audioPath + "\"";  // 第五个参数: 音频文件路径
			command += " " + text_Weight_str;  // 第六个参数: 文字权重
			command += " " + audio_Weight_str;  // 第七个参数: 音频权重
			command += " " + preference_Weight_str;  // 第八个参数: 偏好权重

            // 执行 Python 脚本
            int returnCode = std::system(command.c_str());
            juce::Logger::writeToLog("command: " + juce::String(command) + ", return code: " + juce::String(returnCode));
            if (returnCode != 0) {
                std::cerr << "Python script execution failed, return code: " << returnCode << std::endl;
                std::cerr << "执行的命令: " << command << std::endl;
                //updateStatus("Python script execution failed");
            }
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
            // 调用 PluginAudioProcessor 的方法重置参数
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
        // 设置浅蓝色背景
        button.setColour(juce::TextButton::buttonColourId, juce::Colour(220, 235, 250)); // 浅蓝色背景

        // 设置按下时为橘色
        button.setColour(juce::TextButton::buttonOnColourId, juce::Colour(255, 175, 100)); // 橘色

        // 设置文本为浅橘色
        button.setColour(juce::TextButton::textColourOffId, juce::Colour(255, 160, 80)); // 浅橘色文本

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