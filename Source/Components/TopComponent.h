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

#include "../PluginPresetManager.h"
#include "../PluginAudioParameters.h"
#include "../PluginUtils.h"

class TopComponent : public juce::Component
{
public:
	TopComponent(
		PluginAudioProcessor& audioProcessor) :
		mAudioProcessorValueTreeState(audioProcessor.getAudioProcessorValueTreeState())
	{
		mViewportPtr = std::make_unique<juce::Viewport>();
		mContainerPtr = std::make_unique<juce::Component>();

		// 设置电平表颜色
		lnf.setColour(foleys::LevelMeter::lmMeterGradientLowColour, juce::Colours::green);
		lnf.setColour(foleys::LevelMeter::lmMeterGradientMidColour, juce::Colours::orange);
		lnf.setColour(foleys::LevelMeter::lmMeterGradientMaxColour, juce::Colours::red);
		lnf.setColour(foleys::LevelMeter::lmMeterBackgroundColour, juce::Colours::darkgrey);
		lnf.setColour(foleys::LevelMeter::lmBackgroundColour, juce::Colours::lightblue);      // 外层
		lnf.setColour(foleys::LevelMeter::lmTicksColour, juce::Colours::black);

		mInputLevelMeter.setLookAndFeel(&lnf);
		mInputLevelMeter.setMeterSource(&audioProcessor.getInputMeterSource());
		addAndMakeVisible(mInputLevelMeter);

		mOutputLevelMeter.setLookAndFeel(&lnf);
		mOutputLevelMeter.setMeterSource(&audioProcessor.getOutputMeterSource());
		addAndMakeVisible(mOutputLevelMeter);

		// 添加视口，不设置不存在的颜色ID
		addAndMakeVisible(mViewportPtr.get());
		mViewportPtr->setViewedComponent(mContainerPtr.get(), false);

		static const std::vector<std::vector<std::string>> apvtsIdRows = {
{
	apvts::inputGainId,
	apvts::noiseGateThresholdId,
	apvts::outputGainId,
	apvts::isLofiId,
	apvts::bypassId,
}
		};

		for (int row = 0; row < apvtsIdRows.size(); ++row)
		{
			const auto& colIds = apvtsIdRows[row];

			for (const auto& parameterId : colIds)
			{

				if (mComponentRows.size() < row + 1)
				{
					mComponentRows.add(new juce::OwnedArray<juce::Component>());
				}

				if (PluginUtils::isToggleId(parameterId))
				{
					auto* button = new juce::ToggleButton(PluginUtils::toTitleCase(parameterId));
					// 设置按钮文本颜色为黑色
					button->setColour(juce::ToggleButton::textColourId, juce::Colours::black);
					// 设置按钮勾选标记颜色为黑色
					button->setColour(juce::ToggleButton::tickColourId, juce::Colours::black);
					button->setColour(juce::ToggleButton::tickDisabledColourId, juce::Colours::black);

					mComponentRows[row]->add(button);
					mButtonAttachments.add(new juce::AudioProcessorValueTreeState::ButtonAttachment(
						mAudioProcessorValueTreeState,
						parameterId,
						*button
					));
					mContainerPtr->addAndMakeVisible(button);
				}
				else if (PluginUtils::isWaveshaperId(parameterId))
				{
					auto* comboBox = new juce::ComboBox(PluginUtils::toTitleCase(parameterId));
					// 设置下拉框文本颜色为黑色
					comboBox->setColour(juce::ComboBox::textColourId, juce::Colours::black);
					// 设置下拉框背景颜色
					comboBox->setColour(juce::ComboBox::backgroundColourId, juce::Colours::white);
					// 设置下拉框边框颜色
					comboBox->setColour(juce::ComboBox::outlineColourId, juce::Colours::black);
					// 设置下拉框箭头颜色
					comboBox->setColour(juce::ComboBox::arrowColourId, juce::Colours::black);

					for (int waveshaperIndex = 0; waveshaperIndex < apvts::waveShaperIds.size(); waveshaperIndex++) {
						comboBox->addItem(apvts::waveShaperIds.at(waveshaperIndex), waveshaperIndex + 1);
					}
					mComponentRows[row]->add(comboBox);
					mComboBoxAttachments.add(new juce::AudioProcessorValueTreeState::ComboBoxAttachment(
						mAudioProcessorValueTreeState,
						parameterId,
						*comboBox
					));
					mContainerPtr->addAndMakeVisible(comboBox);
				}
				else
				{
					auto* slider = new juce::Slider(juce::Slider::RotaryVerticalDrag, juce::Slider::TextBoxBelow);
					slider->setTitle(PluginUtils::toTitleCase(parameterId));
					slider->setScrollWheelEnabled(false);

					// 设置滑块文本颜色为黑色
					slider->setColour(juce::Slider::textBoxTextColourId, juce::Colours::black);
					// 设置滑块文本框背景颜色
					slider->setColour(juce::Slider::textBoxBackgroundColourId, juce::Colours::white);
					// 设置滑块文本框边框颜色
					slider->setColour(juce::Slider::textBoxOutlineColourId, juce::Colours::black);
					// 设置滑块旋钮颜色
					slider->setColour(juce::Slider::thumbColourId, juce::Colours::black);
					// 设置旋转滑块填充颜色
					slider->setColour(juce::Slider::rotarySliderFillColourId, juce::Colours::black);
					// 设置旋转滑块轮廓颜色
					slider->setColour(juce::Slider::rotarySliderOutlineColourId, juce::Colours::darkgrey);

					auto* label = new juce::Label(parameterId, PluginUtils::toTitleCase(parameterId));
					// 设置标签文本颜色为黑色
					label->setColour(juce::Label::textColourId, juce::Colours::black);
					// 设置标签背景颜色为透明
					label->setColour(juce::Label::backgroundColourId, juce::Colours::transparentBlack);
					label->attachToComponent(slider, false);

					mComponentRows[row]->add(slider);
					mSliderAttachments.add(new juce::AudioProcessorValueTreeState::SliderAttachment(
						mAudioProcessorValueTreeState,
						parameterId,
						*slider
					));
					mContainerPtr->addAndMakeVisible(slider);
				}
			}
		}
	};

	~TopComponent()
	{
		mSliderAttachments.clear();
		mButtonAttachments.clear();
		mComboBoxAttachments.clear();

		mComponentRows.clear();
		mViewportPtr.reset();
		mContainerPtr.reset();
	};

	void paint(juce::Graphics& g) override
	{
		// 创建一个从中心向外的径向渐变，从白色到浅蓝色
		juce::ColourGradient gradient(
			juce::Colours::white,                   // 中心色为白色
			getWidth() * 0.5f, getHeight() * 0.5f,  // 中心点
			juce::Colour::fromRGB(173, 216, 230),   // 边缘色为浅蓝色 (#ADD8E6)
			0.0f, 0.0f,                             // 任意边缘点
			true);                                  // 径向渐变


		g.setGradientFill(gradient);
		g.fillAll();
		g.setColour(juce::Colours::black);
		g.drawRect(getLocalBounds(), 1);
	};

	void resized() override
	{
		const auto localBounds = getLocalBounds();
		mViewportPtr->setBounds(localBounds);

		const int levelMeterWidth = 30; // Arbitrary width for the level meters

		// Place the input level meter on the very left, spanning the full height.
		mInputLevelMeter.setBounds(0, 0, levelMeterWidth, localBounds.getHeight());

		int numRows = mComponentRows.size();
		int numCols = 0;

		for (int i = 0; i < mComponentRows.size(); ++i) {
			int currentSize = mComponentRows[i]->size();

			if (currentSize > numCols) {
				numCols = currentSize;
			}
		}

		int buttonWidth = (localBounds.getWidth() - levelMeterWidth) / numCols;
		int buttonHeight = 125;

		int totalHeight = ((buttonHeight + 12.5) * numRows);
		mContainerPtr->setBounds(0, 0, mViewportPtr->getMaximumVisibleWidth() - 8, totalHeight);

		for (int row = 0; row < mComponentRows.size(); ++row)
		{
			for (int col = 0; col < mComponentRows[row]->size(); ++col)
			{
				(*mComponentRows[row])[col]->setBounds((col * buttonWidth) + levelMeterWidth, row * buttonHeight + 50, buttonWidth, buttonHeight - 50);
			}
		}

		mOutputLevelMeter.setBounds(localBounds.getWidth() - levelMeterWidth, 0, levelMeterWidth, localBounds.getHeight());
	};

private:
	juce::AudioProcessorValueTreeState& mAudioProcessorValueTreeState;

	std::unique_ptr<juce::Viewport> mViewportPtr;
	std::unique_ptr<juce::Component> mContainerPtr;

	juce::OwnedArray<juce::OwnedArray<juce::Component>> mComponentRows;

	juce::OwnedArray<juce::AudioProcessorValueTreeState::ButtonAttachment> mButtonAttachments;
	juce::OwnedArray<juce::AudioProcessorValueTreeState::SliderAttachment> mSliderAttachments;
	juce::OwnedArray<juce::AudioProcessorValueTreeState::ComboBoxAttachment> mComboBoxAttachments;

	foleys::LevelMeterLookAndFeel lnf;
	foleys::LevelMeter mInputLevelMeter{ foleys::LevelMeter::Minimal };
	foleys::LevelMeter mOutputLevelMeter{ foleys::LevelMeter::Minimal };

	JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(TopComponent)
};
