#include "llm.h"
#include <cstdlib>
#include <sstream>
#include <string>
#include <fstream>
#include <juce_core/juce_core.h>
#include "../PluginPresetManager.h"
#include <windows.h> 
#include <algorithm>

void storeEnvWithType(const std::string& key, const juce::String& value, const std::string& type) {
    std::string escapedValue = value.toStdString();
    size_t pos = 0;
    while ((pos = escapedValue.find('"', pos)) != std::string::npos) {
        escapedValue.insert(pos, "\\");
        pos += 2;
    }
    std::string envStr = key + "=" + type + ":\"" + escapedValue + "\"";

    char* envCopy = new char[envStr.size() + 1];
    std::strcpy(envCopy, envStr.c_str());

    static std::vector<char*> allocatedEnvVars;
    allocatedEnvVars.push_back(envCopy);

    if (putenv(envCopy) != 0) {
        std::cerr << "Failed to set environment variable: " << key << std::endl;
    }

    juce::Logger::writeToLog("Stored Environment Variable: " + juce::String(envStr));
}

EffectParameters extractParameters(const juce::String& jsonString) {
    EffectParameters params;

    auto jsonVar = juce::JSON::parse(jsonString);
    if (jsonVar.isVoid()) {
        std::cerr << "Failed to parse JSON." << std::endl;
        return params;
    }

    juce::Logger::writeToLog("Parsed JSON for parameter extraction: " + juce::JSON::toString(jsonVar, true));

    if (jsonVar["CompressorOn"].isObject()) {
        params.Compressor_on = 1;
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
    }

    if (jsonVar["DriverOn"].isObject()) {
        params.Driver_on = 1;
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
        params.dr_distortion = 0;
        params.dr_volume = -64;
    }

    if (jsonVar["ScreamerOn"].isObject()) {
        params.Screamer_on = 1;
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
    }

    if (jsonVar["DelayOn"].isObject()) {
        params.Delay_on = 1;
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
    }

    if (jsonVar["ReverbOn"].isObject()) {
        params.Reverb_on = 1;
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
    }

    if (jsonVar["ChorusOn"].isObject()) {
        params.Chorus_on = 1;
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
    }

    if (jsonVar["FlangerOn"].isObject()) {
        params.Flanger_on = 1;
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
    }

    if (jsonVar["PhaserOn"].isObject()) {
        params.Phaser_on = 1;
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
    }

    if (jsonVar["EqualiserOn"].isObject()) {
        params.Equaliser_on = 1;
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
    }

    if (jsonVar["NoiseGate"].isObject()) {
        params.NoiseGate_on = 1;
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

ChatComponent::ChatComponent(PluginPresetManager& pm)
    : juce::Thread("NetworkThread"),
    presetManager(pm),
    sendButton("Send"),
    statusLabel("Status", "Ready"),
    audioFileLabel("AudioFileLabel", "No file selected"),
    audioFileButton("Select audio file"),
    cancelAudioButton("Clear selection"),
    acceptAudioButton("Accept"),
    rejectAudioButton("Reject"),
    memoryToggleButton("MemoryOn"),
    textWeightLabel("Text Weight:", "Text:"),
    preferenceWeightLabel("Preference Weight:", "Preference:"),
    audioWeightLabel("Audio Weight:", "Audio:")
{
    memoryEnabled = true;
    memoryToggleButton.setToggleState(true, juce::dontSendNotification);
    currentPresetName = presetManager.getCurrentPreset();
    
    storeEnvWithType("memory_Enabled", "true", "string");
    
    storeEnvWithType("text_Weight", "0.0", "double");
    storeEnvWithType("audio_Weight", "0.0", "double");
    storeEnvWithType("preference_Weight", "0.0", "double");
    
    addAndMakeVisible(inputEditor);
    addAndMakeVisible(sendButton);
    addAndMakeVisible(responseEditor);
    addAndMakeVisible(statusLabel);

    sendButton.addListener(this);
    sendButton.setEnabled(true);

    inputEditor.setMultiLine(true);
    responseEditor.setMultiLine(true);
    responseEditor.setReadOnly(true);

    addAndMakeVisible(audioFileButton);
    audioFileButton.addListener(this);
    audioFileButton.setTooltip("Select audio file (supports wav, mp3, aif, flac, etc.)");

    addAndMakeVisible(audioFileLabel);
    audioFileLabel.setColour(juce::Label::textColourId, juce::Colours::darkgrey);

    statusLabel.setColour(juce::Label::textColourId, juce::Colours::black);

    addAndMakeVisible(cancelAudioButton);
    cancelAudioButton.addListener(this);
    cancelAudioButton.setTooltip("Clear selected audio file");
    cancelAudioButton.setEnabled(true);

    addAndMakeVisible(acceptAudioButton);
    acceptAudioButton.addListener(this);
    acceptAudioButton.setTooltip("Accept selected audio file");
    acceptAudioButton.setEnabled(true);
    acceptAudioButton.setColour(juce::TextButton::buttonOnColourId, juce::Colours::green);

    addAndMakeVisible(rejectAudioButton);
    rejectAudioButton.addListener(this);
    rejectAudioButton.setTooltip("Reject selected audio file");
    rejectAudioButton.setEnabled(true);
    rejectAudioButton.setColour(juce::TextButton::buttonOnColourId, juce::Colours::red);

    addAndMakeVisible(memoryToggleButton);
    memoryToggleButton.addListener(this);
    memoryToggleButton.setClickingTogglesState(true);
    memoryToggleButton.setColour(juce::TextButton::buttonOnColourId, juce::Colours::green);
    memoryToggleButton.setTooltip("Toggle memory feature on/off");
    
    textWeightEditor.setColour(juce::TextEditor::textColourId, juce::Colours::black);
    textWeightEditor.setColour(juce::TextEditor::highlightedTextColourId, juce::Colours::black);
    
    preferenceWeightEditor.setColour(juce::TextEditor::textColourId, juce::Colours::black);
    preferenceWeightEditor.setColour(juce::TextEditor::highlightedTextColourId, juce::Colours::black);
    
    audioWeightEditor.setColour(juce::TextEditor::textColourId, juce::Colours::black);
    audioWeightEditor.setColour(juce::TextEditor::highlightedTextColourId, juce::Colours::black);
    
    textWeightLabel.setVisible(true);
    preferenceWeightLabel.setVisible(true);
    textWeightEditor.setVisible(true);
    preferenceWeightEditor.setVisible(true);
    updateAudioWeightVisibility();
    
    textWeightEditor.repaint();
    preferenceWeightEditor.repaint();
    audioWeightEditor.repaint();

    textWeightLabel.setJustificationType(juce::Justification::right);
    preferenceWeightLabel.setJustificationType(juce::Justification::right);
    audioWeightLabel.setJustificationType(juce::Justification::right);

    addChildComponent(textWeightLabel);
    addChildComponent(preferenceWeightLabel);
    addChildComponent(audioWeightLabel);

    addChildComponent(textWeightEditor);
    addChildComponent(preferenceWeightEditor);
    addChildComponent(audioWeightEditor);

    textWeightEditor.setText("0.0");
    textWeightEditor.setTooltip("Enter weight value for style (e.g., 1.0)");

    preferenceWeightEditor.setText("0.0");
    preferenceWeightEditor.setTooltip("Enter weight value for audio (e.g., 1.0)");

    audioWeightEditor.setText("0.0");
    audioWeightEditor.setTooltip("Enter weight value for feature (e.g., 1.0)");

    textWeightEditor.addListener(this);
    preferenceWeightEditor.addListener(this);
    audioWeightEditor.addListener(this);

    textWeightEditor.setInputRestrictions(10, "0123456789.");
    preferenceWeightEditor.setInputRestrictions(10, "0123456789.");
    audioWeightEditor.setInputRestrictions(10, "0123456789.");

    setSize(600, 400);
    
    inputEditor.setColour(juce::TextEditor::backgroundColourId, juce::Colours::white);
    inputEditor.setColour(juce::TextEditor::outlineColourId, juce::Colours::black);
    inputEditor.setColour(juce::TextEditor::focusedOutlineColourId, juce::Colours::black);
    inputEditor.setColour(juce::TextEditor::textColourId, juce::Colours::black);
    inputEditor.setColour(juce::TextEditor::highlightColourId, juce::Colours::lightblue);

    responseEditor.setColour(juce::TextEditor::backgroundColourId, juce::Colours::white);
    responseEditor.setColour(juce::TextEditor::outlineColourId, juce::Colours::black);
    responseEditor.setColour(juce::TextEditor::focusedOutlineColourId, juce::Colours::black);
    responseEditor.setColour(juce::TextEditor::textColourId, juce::Colours::black);
    responseEditor.setColour(juce::TextEditor::highlightColourId, juce::Colours::lightblue);

    textWeightEditor.setColour(juce::TextEditor::textColourId, juce::Colours::black);
    textWeightEditor.setColour(juce::TextEditor::highlightedTextColourId, juce::Colours::black);
    
    preferenceWeightEditor.setColour(juce::TextEditor::textColourId, juce::Colours::black);
    preferenceWeightEditor.setColour(juce::TextEditor::highlightedTextColourId, juce::Colours::black);
    
    audioWeightEditor.setColour(juce::TextEditor::textColourId, juce::Colours::black);
    audioWeightEditor.setColour(juce::TextEditor::highlightedTextColourId, juce::Colours::black);

    textWeightEditor.setColour(juce::TextEditor::backgroundColourId, juce::Colours::white);
    textWeightEditor.setColour(juce::TextEditor::outlineColourId, juce::Colours::black);
    textWeightEditor.setColour(juce::TextEditor::focusedOutlineColourId, juce::Colours::black);
    textWeightEditor.setColour(juce::TextEditor::highlightColourId, juce::Colours::lightblue);

    preferenceWeightEditor.setColour(juce::TextEditor::backgroundColourId, juce::Colours::white);
    preferenceWeightEditor.setColour(juce::TextEditor::outlineColourId, juce::Colours::black);
    preferenceWeightEditor.setColour(juce::TextEditor::focusedOutlineColourId, juce::Colours::black);
    preferenceWeightEditor.setColour(juce::TextEditor::highlightColourId, juce::Colours::lightblue);

    audioWeightEditor.setColour(juce::TextEditor::backgroundColourId, juce::Colours::white);
    audioWeightEditor.setColour(juce::TextEditor::outlineColourId, juce::Colours::black);
    audioWeightEditor.setColour(juce::TextEditor::focusedOutlineColourId, juce::Colours::black);
    audioWeightEditor.setColour(juce::TextEditor::highlightColourId, juce::Colours::lightblue);

    textWeightLabel.setColour(juce::Label::textColourId, juce::Colours::black);
    preferenceWeightLabel.setColour(juce::Label::textColourId, juce::Colours::black);
    audioWeightLabel.setColour(juce::Label::textColourId, juce::Colours::black);

    addAndMakeVisible(autoImportButton);
    autoImportButton.setClickingTogglesState(true);
    autoImportButton.setColour(juce::ToggleButton::tickColourId, juce::Colours::darkgrey);
    autoImportButton.setColour(juce::ToggleButton::tickDisabledColourId, juce::Colours::lightgrey);
    
    // Set initial state from presetManager
    autoImportButton.setToggleState(presetManager.getAutoImportEnabled(), juce::dontSendNotification);

    autoImportButton.onClick = [this]()
    {
        presetManager.setAutoImportEnabled(autoImportButton.getToggleState());
        juce::Logger::writeToLog("Auto-Import toggled: " + juce::String(autoImportButton.getToggleState() ? "On" : "Off"));
    };
}

void ChatComponent::resized()
{
    auto area = getLocalBounds().reduced(8);

    auto topButtonArea = area.removeFromTop(30);
    memoryToggleButton.setBounds(topButtonArea.removeFromRight(100).reduced(2));
    autoImportButton.setBounds(topButtonArea.removeFromLeft(100).reduced(2));

    auto weightsArea = area.removeFromTop(30);

    int oneThird = weightsArea.getWidth() / 3;

    auto styleWeightArea = weightsArea.removeFromLeft(oneThird);
    textWeightLabel.setBounds(styleWeightArea.removeFromLeft(80).reduced(2));
    textWeightEditor.setBounds(styleWeightArea.reduced(2));

    auto preferenceWeightArea = weightsArea.removeFromLeft(oneThird);
    preferenceWeightLabel.setBounds(preferenceWeightArea.removeFromLeft(80).reduced(2));
    preferenceWeightEditor.setBounds(preferenceWeightArea.reduced(2));

    auto featureWeightArea = weightsArea.removeFromLeft(oneThird);
    audioWeightLabel.setBounds(featureWeightArea.removeFromLeft(80).reduced(2));
    audioWeightEditor.setBounds(featureWeightArea.reduced(2));
    

    auto audioArea = area.removeFromTop(40);
    audioFileButton.setBounds(audioArea.removeFromLeft(150).reduced(2));
    cancelAudioButton.setBounds(audioArea.removeFromLeft(120).reduced(2));
    audioFileLabel.setBounds(audioArea.reduced(2));
    
    rejectAudioButton.setBounds(audioArea.removeFromRight(80).reduced(2));
    acceptAudioButton.setBounds(audioArea.removeFromRight(80).reduced(2));

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
    juce::MessageManager::callAsync([this, response]() {
        responseEditor.setText(response, juce::dontSendNotification);
        juce::Logger::writeToLog("Response updated in UI: " + response);
        });
}

void ChatComponent::buttonClicked(juce::Button* button)
{
    if (button == &sendButton)
    {
        auto message = inputEditor.getText();
        if (message.isNotEmpty())
        {
            userMessageToSend = message;

            storeEnvWithType("text_Weight", "0.0", "double");
            storeEnvWithType("audio_Weight", "0.0", "double");
            storeEnvWithType("preference_Weight", "0.0", "double");
            if (memoryEnabled) {
                storeEnvWithType("text_Weight", textWeightEditor.getText(), "double");
                storeEnvWithType("audio_Weight", audioWeightEditor.getText(), "double");
                storeEnvWithType("preference_Weight", preferenceWeightEditor.getText(), "double");
            }

            inputEditor.clear();
            startThread();
        }
    }
    else if (button == &audioFileButton) {
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

                    cancelAudioButton.setEnabled(true);

                    if (result.getSize() == 0) {
                        juce::AlertWindow::showMessageBoxAsync(juce::AlertWindow::WarningIcon,
                            "Error",
                            "The selected file is empty!");
                        audioFilePath.clear();
                        audioFileLabel.setText("No file selected", juce::dontSendNotification);
                        cancelAudioButton.setEnabled(false);
                        acceptAudioButton.setEnabled(false);
                        rejectAudioButton.setEnabled(false);

                        audioWeightLabel.setVisible(false);
                        audioWeightEditor.setVisible(false);
                    }
                    else {
                        updateAudioWeightVisibility();
                        storeEnvWithType("text_Weight", textWeightEditor.getText(), "double");
                        storeEnvWithType("audio_Weight", audioWeightEditor.getText(), "double");
                        storeEnvWithType("preference_Weight", preferenceWeightEditor.getText(), "double");
                    }
                }
            });
    }
    else if (button == &cancelAudioButton) {
        audioFilePath.clear();
        storeEnvWithType("audio_File_Path", "", "string");
        storeEnvWithType("user_Message", "", "string");
        audioFileLabel.setText("No file selected", juce::dontSendNotification);
        cancelAudioButton.setEnabled(true);

        audioWeightLabel.setVisible(false);
        audioWeightEditor.setVisible(false);

        juce::Logger::writeToLog("Audio file selection cleared");
    }
    else if (button == &acceptAudioButton) {
        auto userMessage = userMessageToSend;
        juce::Logger::writeToLog("userMessage: " + juce::String(userMessage));
        if (userMessage.isNotEmpty()) {
            juce::Logger::writeToLog("accept ");
            juce::File pythonInterpreterFile;
            juce::File pythonScriptFile;
            const char* pythonInterpreterEnv = std::getenv("SUPERTONAL_PYTHON_INTERPRETER");
            const char* pythonScriptEnv = std::getenv("SUPERTONAL_PYTHON_SCRIPT3");
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

            juce::String command;
            command << pythonInterpreterPath.toStdString() << " " << pythonScriptPath.toStdString();

            command << " \"" << userMessage << "\"";

            std::string utf8Command = command.toStdString();
            STARTUPINFOA si = { sizeof(si) };
            PROCESS_INFORMATION pi = { 0 };
            
            if (!CreateProcessA(NULL, const_cast<LPSTR>(utf8Command.c_str()), NULL, NULL, FALSE, CREATE_NO_WINDOW, NULL, NULL, &si, &pi)) {
                DWORD error = GetLastError();
                std::cerr << "CreateProcess failed with error: " << error << std::endl;
                updateStatus("Failed to execute Python script");
                return;
            }
            
            WaitForSingleObject(pi.hProcess, INFINITE);
            
            DWORD exitCode;
            GetExitCodeProcess(pi.hProcess, &exitCode);
            int returnCode = static_cast<int>(exitCode);
            
            CloseHandle(pi.hProcess);
            CloseHandle(pi.hThread);
            juce::Logger::writeToLog("commandWithErrorCapture: " + juce::String(utf8Command) + ", return code: " + juce::String(returnCode));
            if (returnCode != 0) {
                std::cerr << "Python script execution failed, return code: " << returnCode << std::endl;
                std::cerr << "The executed command: " << command << std::endl;
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
        auto userMessage = userMessageToSend;
        if (userMessage.isNotEmpty()) {
            juce::Logger::writeToLog("reject");
            juce::File pythonInterpreterFile;
            juce::File pythonScriptFile;
            const char* pythonInterpreterEnv = std::getenv("SUPERTONAL_PYTHON_INTERPRETER");
            const char* pythonScriptEnv = std::getenv("SUPERTONAL_PYTHON_SCRIPT4");
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

            juce::String command;
            command << pythonInterpreterPath.toStdString() << " " << pythonScriptPath.toStdString();

            command << " \"" << userMessage << "\"";

            std::string utf8Command = command.toStdString();
            STARTUPINFOA si = { sizeof(si) };
            PROCESS_INFORMATION pi = { 0 };
            
            if (!CreateProcessA(NULL, const_cast<LPSTR>(utf8Command.c_str()), NULL, NULL, FALSE, CREATE_NO_WINDOW, NULL, NULL, &si, &pi)) {
                DWORD error = GetLastError();
                std::cerr << "CreateProcess failed with error: " << error << std::endl;
                updateStatus("Failed to execute Python script");
                return;
            }
            
            WaitForSingleObject(pi.hProcess, INFINITE);
            
            DWORD exitCode;
            GetExitCodeProcess(pi.hProcess, &exitCode);
            int returnCode = static_cast<int>(exitCode);
            
            CloseHandle(pi.hProcess);
            CloseHandle(pi.hThread);
            juce::Logger::writeToLog("commandWithErrorCapture: " + juce::String(utf8Command) + ", return code: " + juce::String(returnCode));
            if (returnCode != 0) {
                std::cerr << "Python script execution failed, return code: " << returnCode << std::endl;
                std::cerr << "The executed command: " << command << std::endl;
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
        memoryEnabled = memoryToggleButton.getToggleState();
        if (memoryEnabled) {
            memoryToggleButton.setButtonText("MemoryOn");

            textWeightLabel.setVisible(true);
            preferenceWeightLabel.setVisible(true);
            textWeightEditor.setVisible(true);
            preferenceWeightEditor.setVisible(true);

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
            textWeightLabel.setVisible(false);
            preferenceWeightLabel.setVisible(false);
            audioWeightLabel.setVisible(false);
            textWeightEditor.setVisible(false);
            preferenceWeightEditor.setVisible(false);
            audioWeightEditor.setVisible(false);
        }
    }
}

void ChatComponent::updateAudioWeightVisibility()
{
    bool shouldShowAudioWeight = memoryEnabled && !audioFilePath.isEmpty();

    audioWeightLabel.setVisible(shouldShowAudioWeight);
    audioWeightEditor.setVisible(shouldShowAudioWeight);

    if (shouldShowAudioWeight) {
        adjustWeightsForAudio(true);
    }
    else {
        adjustWeightsForAudio(false);
    }
}

void ChatComponent::adjustWeightsForAudio(bool includeAudio)
{
    if (!memoryEnabled) return;

    double textWeight = textWeightEditor.getText().getDoubleValue();
    double audioWeight = includeAudio ? audioWeightEditor.getText().getDoubleValue() : 0.0;
    double preferenceWeight = preferenceWeightEditor.getText().getDoubleValue();

    if (textWeight < 0.0) textWeight = 0.0;
    if (audioWeight < 0.0) audioWeight = 0.0;
    if (preferenceWeight < 0.0) preferenceWeight = 0.0;

    double totalWeight = textWeight + audioWeight + preferenceWeight;

    if (totalWeight < 0.001) {
        if (includeAudio) {
            textWeight = audioWeight = preferenceWeight = 1.0 / 3.0;
        }
        else {
            textWeight = preferenceWeight = 0.5;
            audioWeight = 0.0;
        }
    }
    else {
        textWeight /= totalWeight;
        preferenceWeight /= totalWeight;
        if (includeAudio) {
            audioWeight /= totalWeight;
        }
        else {
            audioWeight = 0.0;
        }
    }

    textWeightEditor.setText(juce::String(textWeight, 2), false);
    if (includeAudio) {
        audioWeightEditor.setText(juce::String(audioWeight, 2), false);
    }
    preferenceWeightEditor.setText(juce::String(preferenceWeight, 2), false);
}

void ChatComponent::textEditorTextChanged(juce::TextEditor& editor)
{
    if (!memoryEnabled) {
        return;
    }

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

void ChatComponent::run() {
    updateStatus("sending request");
    auto userMessage = userMessageToSend;
    if (userMessage.isNotEmpty()) {
        juce::Logger::writeToLog("send request: " + userMessage);
        juce::Logger::writeToLog("currentPresetName: " + currentPresetName);
    }

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
        double audioWeight = 0.0;
        double textWeight = textWeightEditor.getText().getDoubleValue();
        double preferenceWeight = preferenceWeightEditor.getText().getDoubleValue();
        if (!audioFilePath.isEmpty()) {
            audioWeight = audioWeightEditor.getText().getDoubleValue();
        }
        double totalWeight = textWeight + preferenceWeight + audioWeight;
        if (std::abs(totalWeight - 1.0) > 0.001) {
            updateStatus("The sum of weights must be one, Please enter again");
            return;
        }
    }
    else {
        juce::Logger::writeToLog("Memory feature is disabled");
    }
    
    juce::File pythonInterpreterFile;
    juce::File pythonScriptFile;
    const char* pythonInterpreterEnv = std::getenv("SUPERTONAL_PYTHON_INTERPRETER");
    const char* pythonScriptEnv = std::getenv("SUPERTONAL_PYTHON_SCRIPT1");

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
    

    juce::String command;
    command << pythonInterpreterPath.toStdString() << " " << pythonScriptPath.toStdString();

    command << " \"" << userMessage << "\"";

    command << " \"" << (memoryEnabled ? "true" : "false") << "\"";

    if (!audioFilePath.isEmpty()) {
        command << " \"" << audioFilePath << "\"";
    }
    if (memoryEnabled) {
        command << " \"" << text_Weight << "\"";
        command << " \"" << preference_Weight << "\"";
        command << " \"" << audio_Weight << "\"";

    }

    storeEnvWithType("user_Message", userMessage, "string");
    if (!audioFilePath.isEmpty()) {
        storeEnvWithType("audio_File_Path", audioFilePath, "string");
    }

    
    std::string utf8Command = command.toStdString();
    
    STARTUPINFOA si = { sizeof(si) };
    PROCESS_INFORMATION pi = { 0 };
    
    if (!CreateProcessA(NULL, const_cast<LPSTR>(utf8Command.c_str()), NULL, NULL, FALSE, CREATE_NEW_CONSOLE, NULL, NULL, &si, &pi)) {   //CREATE_NO_WINDOW
        DWORD error = GetLastError();
        std::cerr << "CreateProcess failed with error: " << error << std::endl;
        updateStatus("Failed to execute Python script");
        return;
    }
    
    WaitForSingleObject(pi.hProcess, INFINITE);
    
    DWORD exitCode;
    GetExitCodeProcess(pi.hProcess, &exitCode);
    int returnCode = static_cast<int>(exitCode);
    
    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);
    juce::Logger::writeToLog("commandWithErrorCapture: " + juce::String(utf8Command) + ", return code: " + juce::String(returnCode));
    if (returnCode != 0) {
        std::cerr << "Python script execution failed, return code: " << returnCode << std::endl;
        std::cerr << "The executed command: " << command << std::endl;
        updateStatus("Python script execution failed");
    }
    else {
        updateStatus("Python script executed successfully");

        std::ifstream file(R"(result.txt)", std::ios::binary);
        if (!file.is_open()) {
            std::cerr << "Failed to open result.txt" << std::endl;
            file.close();

            juce::String documentsPath = juce::SystemStats::getEnvironmentVariable("DOCUMENTS_DIR", "");

            if (documentsPath.isEmpty()) {
                std::cerr << "DOCUMENTS_DIR environment variable not set" << std::endl;
                updateStatus("Failed to open DOCUMENTS_DIR");
            }
            else {
                juce::File resultFile = juce::File(documentsPath).getChildFile("result.txt");
                file.open(resultFile.getFullPathName().toStdString(), std::ios::binary);
            }

            if (!file.is_open()) {
                std::cerr << "Failed to open file from alternative location" << std::endl;
                updateStatus("Failed to open result file from all locations");
                return;
            }
        }

        std::stringstream buffer;
        buffer << file.rdbuf();
        std::string resultBytes = buffer.str();
        file.close();

        std::ifstream file3(R"(result3.txt)", std::ios::binary);
        if (!file3.is_open()) {
            std::cerr << "Failed to open result3.txt" << std::endl;
            file3.close();

            juce::String documentsPath = juce::SystemStats::getEnvironmentVariable("DOCUMENTS_DIR", "");

            if (!documentsPath.isEmpty()) {
                juce::File result3File = juce::File(documentsPath).getChildFile("result3.txt");
                file3.open(result3File.getFullPathName().toStdString(), std::ios::binary);
            }

            if (!file3.is_open()) {
                std::cerr << "Failed to open result3.txt from alternative location" << std::endl;
            }
        }
        std::string result3Bytes;
        if (file3.is_open()) {
            std::stringstream buffer3;
            buffer3 << file3.rdbuf();
            result3Bytes = buffer3.str();
            file3.close();
        }
        else {
            result3Bytes = "No data";
        }
        juce::String resultStr = juce::String::fromUTF8(resultBytes.data(), resultBytes.size());
        EffectParameters params = extractParameters(resultStr);
        juce::String result3Str = juce::String::fromUTF8(result3Bytes.data(), result3Bytes.size());
        callAsync(juce::String(result3Str));
    }
}

void ChatComponent::updateStatus(const juce::String& text)
{
    juce::MessageManager::callAsync([this, text]() {
        statusLabel.setColour(juce::Label::textColourId, juce::Colours::black);
        statusLabel.setText(text, juce::dontSendNotification);
        });
}

MainWindow::MainWindow(PluginPresetManager& pm)
    : DocumentWindow("DeepSeek Chat",
        juce::Colours::lightgrey,
        DocumentWindow::allButtons),
    presetManager(pm)
{
    tabbedComponent = std::make_unique<juce::TabbedComponent>(juce::TabbedButtonBar::TabsAtTop);
    tabbedComponent->addTab("Chat", juce::Colours::lightblue, new ChatComponent(presetManager), true);

    setContentOwned(tabbedComponent.get(), true);
    centreWithSize(800, 600);
    setVisible(true);
}

void MainWindow::closeButtonPressed()
{
    juce::JUCEApplication::quit();
}