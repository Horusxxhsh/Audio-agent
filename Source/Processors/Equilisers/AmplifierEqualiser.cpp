/*
    This code is part of the Supertonal guitar effects multi-processor.
    Copyright (C) 2023-2024  Paul Jones

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.
 */

#include "AmplifierEqualiser.h"

AmplifierEqualiser::AmplifierEqualiser()
{
	*mFilters[0].state = *juce::dsp::IIR::Coefficients<float>::makeLowShelf(
		44100.0f,
		sFrequencies[0],
		sQualities[0],
		1.0f);
	*mFilters[1].state = *juce::dsp::IIR::Coefficients<float>::makePeakFilter(
		44100.0f,
		sFrequencies[1],
		sQualities[1],
		1.0f);
	*mFilters[2].state = *juce::dsp::IIR::Coefficients<float>::makePeakFilter(
		44100.0f,
		sFrequencies[2],
		sQualities[2],
		1.0f);
	*mFilters[3].state = *juce::dsp::IIR::Coefficients<float>::makePeakFilter(
		44100.0f,
		sFrequencies[3],
		sQualities[3],
		1.0f);
	*mFilters[4].state = *juce::dsp::IIR::Coefficients<float>::makeHighShelf(
		44100.0f,
		sFrequencies[4],
		sQualities[4],
		1.0f);
}

void AmplifierEqualiser::updateFilter(int index)
{
    if (mCurrentSampleRate <= 0) return;

    if (index == 0)
    {
        *mFilters[0].state = *juce::dsp::IIR::Coefficients<float>::makeLowShelf(
            mCurrentSampleRate, sFrequencies[0], sQualities[0], juce::Decibels::decibelsToGain(mGains[0]));
    }
    else if (index >= 1 && index <= 3)
    {
        *mFilters[index].state = *juce::dsp::IIR::Coefficients<float>::makePeakFilter(
            mCurrentSampleRate, sFrequencies[index], sQualities[index], juce::Decibels::decibelsToGain(mGains[index]));
    }
    else if (index == 4)
    {
        *mFilters[4].state = *juce::dsp::IIR::Coefficients<float>::makeHighShelf(
            mCurrentSampleRate, sFrequencies[4], sQualities[4], juce::Decibels::decibelsToGain(mGains[4]));
    }
}

void AmplifierEqualiser::updateAllFilters()
{
    for (int i = 0; i < 5; ++i)
        this->updateFilter(i);
}

void AmplifierEqualiser::prepare(juce::dsp::ProcessSpec& spec)
{
	mCurrentSampleRate = spec.sampleRate;

	for (auto& filter : mFilters)
	{
		filter.prepare(spec);
	}
    
    this->updateAllFilters();
}

void AmplifierEqualiser::processBlock(juce::AudioBuffer<float>& buffer)
{
	auto audioBlock = juce::dsp::AudioBlock<float>(buffer);
	auto processContext = juce::dsp::ProcessContextReplacing<float>(audioBlock);

	for (std::size_t filterIndex = 0; filterIndex < mFilters.size(); ++filterIndex)
	{
		mFilters[filterIndex].process(processContext);
	}
}

void AmplifierEqualiser::reset()
{
	for (auto& filter : mFilters)
	{
		filter.reset();
	}
}

void AmplifierEqualiser::setResonanceDecibels(float newValue)
{
    mGains[0] = newValue;
    this->updateFilter(0);
}

void AmplifierEqualiser::setBassDecibels(float newValue)
{
    mGains[1] = newValue;
    this->updateFilter(1);
}

void AmplifierEqualiser::setMiddleDecibels(float newValue)
{
    mGains[2] = newValue;
    this->updateFilter(2);
}

void AmplifierEqualiser::setTrebleDecibels(float newValue)
{
    mGains[3] = newValue;
    this->updateFilter(3);
}

void AmplifierEqualiser::setPresenceDecibels(float newValue)
{
    mGains[4] = newValue;
    this->updateFilter(4);
}
