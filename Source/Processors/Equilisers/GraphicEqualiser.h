/*
    This code is part of the Supertonal guitar effects multi-processor.
    Copyright (C) 2023-2024  Paul Jones

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.
 */

#pragma once

#include <JuceHeader.h>

class GraphicEqualiser
{
public:
    inline static const juce::NormalisableRange<float> sDecibelGainNormalisableRange = {
            -15.0f,
            15.0f
    };

    // https://www.youtube.com/watch?v=RKyx-qKb7to
    inline static const std::array<float, 7> sFrequencies = { 95.75,  204.65,  394.44,  791.28,  1552.39, 3309.70, 7163.56 };
    inline static const std::array<float, 7> sQualities =   { 2.83,   2.33,    2.45,    2.77,    2.09,    3.46,    1.41 };

    explicit GraphicEqualiser();

    void prepare(juce::dsp::ProcessSpec& spec);
    void processBlock(juce::AudioBuffer<float>& buffer);
    void reset();
    void setGainDecibelsAtIndex(float newGainDecibels, int index);

    void updateFilter(int index);
    void updateAllFilters();

private:
    std::array<juce::dsp::ProcessorDuplicator<juce::dsp::IIR::Filter<float>, juce::dsp::IIR::Coefficients<float>>, 7> mFilters;

    juce::dsp::Gain<float> mLevelGain;

    float mCurrentSampleRate = 44100.0f;
    std::array<float, 8> mGains = { 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f }; // 7 filters + level gain

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(GraphicEqualiser)
};
