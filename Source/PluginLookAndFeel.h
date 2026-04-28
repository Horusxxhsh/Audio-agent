/*
    This code is part of the Supertonal guitar effects multi-processor.
    Copyright (C) 2023-2024  Paul Jones

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>
*/
#pragma once

#include <JuceHeader.h>



class PluginLookAndFeel : public juce::LookAndFeel_V4
{
public:
    PluginLookAndFeel();
    ~PluginLookAndFeel() override;

 
    void drawRotarySlider(juce::Graphics&,
        int x, int y, int width, int height,
        float sliderPosProportional,
        const float rotaryStartAngle,
        const float rotaryEndAngle,
        juce::Slider&) override;


    void drawButtonBackground(juce::Graphics& g,
        juce::Button& button,
        const juce::Colour& backgroundColour,
        bool isMouseOverButton,
        bool isButtonDown) override;


    void drawButtonText(juce::Graphics& g,
        juce::TextButton& button,
        bool isMouseOverButton,
        bool isButtonDown) override;


    juce::Label* createSliderTextBox(juce::Slider& slider) override;

  
    void drawToggleButton(juce::Graphics& g,
        juce::ToggleButton& button,
        bool isMouseOverButton,
        bool isButtonDown) override;

  
    void drawPopupMenuSectionHeader(juce::Graphics& g,
        const juce::Rectangle<int>& area,
        const juce::String& sectionName) override;
   
    int getTabButtonBestWidth(juce::TabBarButton& button, int tabDepth) override;
    void positionComboBoxText(juce::ComboBox& box, juce::Label& label) override;
};
