#pragma once
#include <JuceHeader.h>
#include <iostream>
#include "../PluginPresetManager.h"


static const juce::String COZE_API_KEY = "pat_qYqWeCHQq2kXBWHJukeL8mOYyyRI9gdDa8a4ENXQiQjXqb3DNOYs3RbgN54gD4vE"; 
static const juce::String RESULT_ENDPOINT = "https://api.coze.cn/v3/chat/result"; 


struct EffectParameters {
    int Compressor_on;
    int Driver_on;
    int Screamer_on;
    int Delay_on;
    int Reverb_on;
    int Chorus_on;
    int Flanger_on;
    int Phaser_on;
    int Equaliser_on;
    int NoiseGate_on;
    double co_mix;
    double co_threshold;
    int co_ratio;
    double co_attack;
    double co_release;
    double co_makeup;
    double dr_distortion;
    double dr_volume;
    double s_drive; 
    double s_tone;
    double s_level;
    double de_feedback;
    double de_delay;
    double de_mix;
    double r_size;
    double r_damping;
    double r_width; 
    double r_mix;
    double ch_delay;
    double ch_depth;
    double ch_frequency;
    double ch_width;
    double f_delay;
    double f_depth;
    double f_feedback;
    double f_frequency; 
    double f_width; 
    double p_depth; 
    double p_feedback;  
    double p_frequency;
    double p_width;
    double e_1;
    double e_2;
    double e_4;
    double e_8;
    double e_16;
    double e_32;
    double e_64;
    double e_level;
    double n_noisegatethreshold;
    
    juce::String toString() const {
        return juce::String("Compressor_on: ") + juce::String(Compressor_on) + "\n" +
            "Driver_on: " + juce::String(Driver_on) + "\n" +
            "Screamer_on: " + juce::String(Screamer_on) + "\n" +
            "Delay_on: " + juce::String(Delay_on) + "\n" +
            "Reverb_on: " + juce::String(Reverb_on) + "\n" +
            "Chorus_on: " + juce::String(Chorus_on) + "\n" +
            "Flanger_on: " + juce::String(Flanger_on) + "\n" +
            "Phaser_on: " + juce::String(Phaser_on) + "\n" +
            "Equaliser_on: " + juce::String(Equaliser_on) + "\n" +
            "NoiseGate_on: " + juce::String(NoiseGate_on) + "\n" +
            "co_threshold" + juce::String(co_threshold) + "\n" +
            "co_ratio: " + juce::String(co_ratio) + "\n" +
            "co_attack: " + juce::String(co_attack) + "\n" +
            "co_release: " + juce::String(co_release) + "\n" +
            "co_makeup: " + juce::String(co_makeup) + "\n" +
            "co_mix: " + juce::String(co_mix) + "\n" +
            "dr_distortion: " + juce::String(dr_distortion) + "\n" +
            "dr_volume: " + juce::String(dr_volume) + "\n" +
            "s_drive: " + juce::String(s_drive) + "\n" +
            "s_tone: " + juce::String(s_tone) + "\n" +
            "s_level: " + juce::String(s_level) + "\n" +
            "de_feedback: " + juce::String(de_feedback) + "\n" +
            "de_delay: " + juce::String(de_delay) + "\n" +
            "de_mix: " + juce::String(de_mix) + "\n" +
            "r_size: " + juce::String(r_size) + "\n" +
            "r_damping: " + juce::String(r_damping) + "\n" +
            "r_width: " + juce::String(r_width) + "\n" +
            "r_mix: " + juce::String(r_mix) + "\n" +
            "ch_delay: " + juce::String(ch_delay) + "\n" +
            "ch_depth: " + juce::String(ch_depth) + "\n" +
            "ch_frequency: " + juce::String(ch_frequency) + "\n" +
            "ch_width: " + juce::String(ch_width) + "\n" +
            "f_delay: " + juce::String(f_delay) + "\n" +
            "f_depth: " + juce::String(f_depth) + "\n" +
            "f_feedback: " + juce::String(f_feedback) + "\n" +
            "f_frequency: " + juce::String(f_frequency) + "\n" +
            "f_width: " + juce::String(f_width) + "\n" +
            "p_depth: " + juce::String(p_depth) + "\n" +
            "p_feedback: " + juce::String(p_feedback) + "\n" +
            "p_frequency: " + juce::String(p_frequency) + "\n" +
            "p_width: " + juce::String(p_width) + "\n" +
            "e_1: " + juce::String(e_1) + "\n" +
            "e_2: " + juce::String(e_2) + "\n" +
            "e_4: " + juce::String(e_4) + "\n" +
            "e_8: " + juce::String(e_8) + "\n" +
            "e_16: " + juce::String(e_16) + "\n" +
            "e_32: " + juce::String(e_32) + "\n" +
            "e_64: " + juce::String(e_64) + "\n" +
            "e_level: " + juce::String(e_level) + "\n" +
            "n_noisegatethreshold: " + juce::String(n_noisegatethreshold) + "\n";
    }
};


class ChatComponent : public juce::Component,
    public juce::Button::Listener,
    private juce::Thread,
    public juce::TextEditor::Listener  
{
public:
    ChatComponent(PluginPresetManager& pm);
    void resized() override;
    void buttonClicked(juce::Button* button) override;
    void textEditorTextChanged(juce::TextEditor& editor) override;
    //void textEditorFocusLost(juce::TextEditor& editor) override;
    
private:
    PluginPresetManager& presetManager;  
    juce::String currentPresetName;
    juce::TextEditor inputEditor;
    juce::TextButton sendButton;
    juce::TextEditor responseEditor;
    juce::Label statusLabel;
    juce::String userMessageToSend; 
    
    juce::TextButton audioFileButton{ "选择音频文件" };  
    juce::String audioFilePath;  
    juce::Label audioFileLabel;  
    
    juce::TextButton memoryToggleButton;  
    juce::Label textWeightLabel;
    juce::Label audioWeightLabel; 
    juce::Label preferenceWeightLabel;
    juce::TextEditor textWeightEditor;
    juce::TextEditor audioWeightEditor;
    juce::TextEditor preferenceWeightEditor;
    bool memoryEnabled = false;  
    juce::TextButton cancelAudioButton;
    juce::TextButton acceptAudioButton;   
    juce::TextButton rejectAudioButton;   

    void run() override;
    void updateStatus(const juce::String& text);
    void callAsync(const juce::String& response);
    void updateAudioWeightVisibility();
    void adjustWeightsForAudio(bool includeAudio);

    juce::ToggleButton autoImportButton{ "Auto-Import" };
};


class MainWindow : public juce::DocumentWindow
{
public:
    
    MainWindow(PluginPresetManager& pm);
    void closeButtonPressed() override;

private:
    std::unique_ptr<juce::TabbedComponent> tabbedComponent;
    PluginPresetManager& presetManager; 
};







