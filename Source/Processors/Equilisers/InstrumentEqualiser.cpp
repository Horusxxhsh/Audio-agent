/*
    This code is part of the Supertonal guitar effects multi-processor.
    Copyright (C) 2023-2024  Paul Jones

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.
 */

#include "InstrumentEqualiser.h"

InstrumentEqualiser::InstrumentEqualiser()
{
    // Initialize the filters with default values
    *mFilters[0].state = *juce::dsp::IIR::Coefficients<float>::makeHighPass(44100.0f, sHighPassFrequencyNormalisableRange.start);
    for (int i = 1; i <= 4; ++i)
    {
        *mFilters[i].state = *juce::dsp::IIR::Coefficients<float>::makePeakFilter(44100.0f, getDefaultValueForIndex(i), sQualityNormalisableRange.start, 1.0f);
    }
    *mFilters[5].state = *juce::dsp::IIR::Coefficients<float>::makeLowPass(44100.0f, sLowPassFrequencyNormalisableRange.start);
}

void InstrumentEqualiser::updateFilter(int index)
{
    if (mCurrentSampleRate <= 0) return;
    
    auto& filter = mFilters[index];
    const auto frequency = mFrequencies[index];
    const auto quality = mQualities[index];
    const auto gain = mDecibelGains[index];

    if (index == 0)
    {
        *filter.state = *juce::dsp::IIR::Coefficients<float>::makeHighPass(mCurrentSampleRate, frequency, quality);
    }
    else if (index == 5)
    {
        *filter.state = *juce::dsp::IIR::Coefficients<float>::makeLowPass(mCurrentSampleRate, frequency, quality);
    }
    else 
    {
        *filter.state = *juce::dsp::IIR::Coefficients<float>::makePeakFilter(
            mCurrentSampleRate, 
            frequency, quality, juce::Decibels::decibelsToGain(gain));
    }
}

void InstrumentEqualiser::updateAllFilters()
{
    for (int i = 0; i < 6; ++i)
        this->updateFilter(i);
}

void InstrumentEqualiser::prepare(juce::dsp::ProcessSpec& spec)
{
    mCurrentSampleRate = spec.sampleRate;
    for (auto& filter : mFilters)
    {
        filter.prepare(spec);
    }
    this->updateAllFilters();
}

void InstrumentEqualiser::processBlock(juce::AudioBuffer<float>& buffer)
{
    auto audioBlock = juce::dsp::AudioBlock<float>(buffer);
    auto processContext = juce::dsp::ProcessContextReplacing<float>(audioBlock);

    for (std::size_t filterIndex = 0; filterIndex < mFilters.size(); ++filterIndex)
    {
        if (!mBypasses[filterIndex])
        {
            mFilters[filterIndex].process(processContext);
        }
    }
}

void InstrumentEqualiser::reset()
{
    for (auto& filter : mFilters)
    {
        filter.reset();
    }
}

void InstrumentEqualiser::setOnAtIndex(bool newValue, int index)
{
    if (index >= 0 && index < 6)
    {
        mBypasses[index] = !newValue;
    }
}

void InstrumentEqualiser::setFrequencyAtIndex(float newValue, int index)
{
    if (index >= 0 && index < 6)
    {
        mFrequencies[index] = newValue;
        this->updateFilter(index);
    }
}

void InstrumentEqualiser::setGainAtIndex(float newValue, int index)
{
    if (index >= 0 && index < 6)
    {
        mDecibelGains[index] = newValue;
        this->updateFilter(index);
    }
}

void InstrumentEqualiser::setQualityAtIndex(float newValue, int index)
{
    if (index >= 0 && index < 6)
    {
        mQualities[index] = newValue;
        this->updateFilter(index);
    }
}

float InstrumentEqualiser::getDefaultValueForIndex(int index)
{
    switch (index)
    {
    case 1: return InstrumentEqualiser::sLowPeakFrequencyDefaultValue;
    case 2: return InstrumentEqualiser::sLowMidPeakFrequencyDefaultValue;
    case 3: return InstrumentEqualiser::sHighMidPeakFrequencyDefaultValue;
    case 4: return InstrumentEqualiser::sHighPeakFrequencyDefaultValue;
    default: return 0.0f;
    }
}

const juce::NormalisableRange<float>& InstrumentEqualiser::getFrequencyNormalisableRangeForIndex(int index)
{
    switch (index)
    {
    case 0: return sHighPassFrequencyNormalisableRange;
    case 1: return sLowPeakFrequencyNormalisableRange;
    case 2: return sLowMidPeakFrequencyNormalisableRange;
    case 3: return sHighMidPeakFrequencyNormalisableRange;
    case 4: return sHighPeakFrequencyNormalisableRange;
    case 5: return sLowPassFrequencyNormalisableRange;
    default: return sHighPassFrequencyNormalisableRange;
    }
}