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

class AmplifierEqualiser
{
public:
    inline static const juce::NormalisableRange<float> sDecibelsNormalisableRange = {
            -6.0f,
            6.0f
    };

    explicit AmplifierEqualiser();

    void prepare(juce::dsp::ProcessSpec& spec);
    void processBlock(juce::AudioBuffer<float>& buffer);
    void reset();
    
    void setResonanceDecibels(float newValue);
    void setBassDecibels(float newValue);
    void setMiddleDecibels(float newValue);
    void setTrebleDecibels(float newValue);
    void setPresenceDecibels(float newValue);

    void updateAllFilters();
    void updateFilter(int index);

private:
    inline static const std::array<float, 5> sFrequencies = { 100.0f, 200.0f, 1000.0f, 5000.0f, 10000.0f };
    inline static const std::array<float, 5> sQualities =   { 1.5f,   1.5f,   1.5f,    1.5f,    1.5f };

    float mCurrentSampleRate = 44100.0f;
    std::array<float, 5> mGains = { 0.0f, 0.0f, 0.0f, 0.0f, 0.0f };

    std::array<juce::dsp::ProcessorDuplicator<juce::dsp::IIR::Filter<float>, juce::dsp::IIR::Coefficients<float>>, 5> mFilters;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(AmplifierEqualiser)
};
