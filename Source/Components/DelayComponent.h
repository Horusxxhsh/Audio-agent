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

 // 从环境变量读取时去除引号并处理转义字符
template<typename T>
T readEnvWithType(const std::string& key) {
    const char* envValue = std::getenv(key.c_str());
    if (envValue == nullptr) {
        return T(); // 返回默认值
    }

    std::string valueStr = envValue;
    size_t colonPos = valueStr.find(':');
    if (colonPos == std::string::npos) {
        return T(); // 返回默认值
    }

    std::string type = valueStr.substr(0, colonPos);
    std::string value = valueStr.substr(colonPos + 1);

    // 去除可能存在的引号
    if (value.size() >= 2 && value.front() == '"' && value.back() == '"') {
        value = value.substr(1, value.size() - 2);
        // 处理转义的引号
        size_t pos = 0;
        while ((pos = value.find("\\\"", pos)) != std::string::npos) {
            value.erase(pos, 1); // 移除反斜杠
            pos += 1;
        }
    }

    if constexpr (std::is_same_v<T, std::string>) {
        return value;
    }
    else {
        T result;
        std::istringstream iss(value);
        iss >> result;
        return result;
    }
}

class DelayComponent : public juce::Component, public juce::AudioProcessorValueTreeState::Listener
{
public:

    explicit DelayComponent(
        juce::AudioProcessorValueTreeState& apvts,
        const std::string& title,
        const std::string& delayLeftPerBeatParameterId,
        const std::string& delayRightPerBeatParameterId,
        const std::string& delayLeftMillisecondParameterId,
        const std::string& delayRightMillisecondParameterId,
        const std::string& delayHighPassFrequencyParameterId,
        const std::string& delayLowPassFrequencyParameterId,
        const std::string& delayFeedbackParameterId,
        const std::string& delayDryWetParameterId,
        const std::string& delayIsSyncedParameterId,
        const std::string& delayIsLinkedParameterId,
        const std::string& toggleParameterId) noexcept :
        mApvts(apvts)
    {
        // Start delayLeftPerBeatParameterId
        mLeftPerBeatSliderPtr = std::make_unique<juce::Slider>(juce::Slider::RotaryVerticalDrag, juce::Slider::TextBoxBelow);
        mLeftPerBeatSliderPtr->setTextValueSuffix(" division");
        mLeftPerBeatSliderPtr->setScrollWheelEnabled(false);
        // 设置滑块文本为黑色
        mLeftPerBeatSliderPtr->setColour(juce::Slider::textBoxTextColourId, juce::Colours::black);
        mLeftPerBeatSliderPtr->setColour(juce::Slider::thumbColourId, juce::Colours::black);
        mLeftPerBeatSliderPtr->setColour(juce::Slider::rotarySliderFillColourId, juce::Colours::black);
        mLeftPerBeatSliderPtr->setColour(juce::Slider::rotarySliderOutlineColourId, juce::Colours::black);

        mLeftPerBeatAttachmentPtr = std::make_unique<juce::AudioProcessorValueTreeState::SliderAttachment>(
            apvts, delayLeftPerBeatParameterId, *mLeftPerBeatSliderPtr);

        mLeftPerBeatLabelPtr = std::make_unique<juce::Label>();
        mLeftPerBeatLabelPtr->setText("Left delay", juce::dontSendNotification);
        mLeftPerBeatLabelPtr->attachToComponent(mLeftPerBeatSliderPtr.get(), false);
        // 设置标签文本为黑色
        mLeftPerBeatLabelPtr->setColour(juce::Label::textColourId, juce::Colours::black);

        addAndMakeVisible(mLeftPerBeatSliderPtr.get());
        addAndMakeVisible(mLeftPerBeatLabelPtr.get());
        // End delayLeftPerBeatParameterId

        // Start delayRightPerBeatParameterId
        mRightPerBeatSliderPtr = std::make_unique<juce::Slider>(juce::Slider::RotaryVerticalDrag, juce::Slider::TextBoxBelow);
        mRightPerBeatSliderPtr->setTextValueSuffix(" division");
        mRightPerBeatSliderPtr->setScrollWheelEnabled(false);
        // 设置滑块文本为黑色
        mRightPerBeatSliderPtr->setColour(juce::Slider::textBoxTextColourId, juce::Colours::black);
        mRightPerBeatSliderPtr->setColour(juce::Slider::thumbColourId, juce::Colours::black);
        mRightPerBeatSliderPtr->setColour(juce::Slider::rotarySliderFillColourId, juce::Colours::black);
        mRightPerBeatSliderPtr->setColour(juce::Slider::rotarySliderOutlineColourId, juce::Colours::black);

        mRightPerBeatAttachmentPtr = std::make_unique<juce::AudioProcessorValueTreeState::SliderAttachment>(
            apvts, delayRightPerBeatParameterId, *mRightPerBeatSliderPtr);

        mRightPerBeatLabelPtr = std::make_unique<juce::Label>();
        mRightPerBeatLabelPtr->setText("Right delay", juce::dontSendNotification);
        mRightPerBeatLabelPtr->attachToComponent(mRightPerBeatSliderPtr.get(), false);
        // 设置标签文本为黑色
        mRightPerBeatLabelPtr->setColour(juce::Label::textColourId, juce::Colours::black);

        addAndMakeVisible(mRightPerBeatSliderPtr.get());
        addAndMakeVisible(mRightPerBeatLabelPtr.get());
        // End delayRightPerBeatParameterId

        // Start delayLeftMillisecondParameterId
        mLeftMillisecondSliderPtr = std::make_unique<juce::Slider>(juce::Slider::RotaryVerticalDrag, juce::Slider::TextBoxBelow);
        mLeftMillisecondSliderPtr->setTextValueSuffix(" ms");
        mLeftMillisecondSliderPtr->setScrollWheelEnabled(false);
        // 设置滑块文本为黑色
        mLeftMillisecondSliderPtr->setColour(juce::Slider::textBoxTextColourId, juce::Colours::black);
        mLeftMillisecondSliderPtr->setColour(juce::Slider::thumbColourId, juce::Colours::black);
        mLeftMillisecondSliderPtr->setColour(juce::Slider::rotarySliderFillColourId, juce::Colours::black);
        mLeftMillisecondSliderPtr->setColour(juce::Slider::rotarySliderOutlineColourId, juce::Colours::black);

        mLeftMillisecondAttachmentPtr = std::make_unique<juce::AudioProcessorValueTreeState::SliderAttachment>(
            apvts, delayLeftMillisecondParameterId, *mLeftMillisecondSliderPtr);

        mLeftMillisecondLabelPtr = std::make_unique<juce::Label>();
        mLeftMillisecondLabelPtr->setText("Left delay", juce::dontSendNotification);
        mLeftMillisecondLabelPtr->attachToComponent(mLeftMillisecondSliderPtr.get(), false);
        // 设置标签文本为黑色
        mLeftMillisecondLabelPtr->setColour(juce::Label::textColourId, juce::Colours::black);

        addAndMakeVisible(mLeftMillisecondSliderPtr.get());
        addAndMakeVisible(mLeftMillisecondLabelPtr.get());
        // End delayLeftMillisecondParameterId

        // Start delayRightMillisecondParameterId
        mRightMillisecondSliderPtr = std::make_unique<juce::Slider>(juce::Slider::RotaryVerticalDrag, juce::Slider::TextBoxBelow);
        mRightMillisecondSliderPtr->setTextValueSuffix(" ms");
        mRightMillisecondSliderPtr->setScrollWheelEnabled(false);
        // 设置滑块文本为黑色
        mRightMillisecondSliderPtr->setColour(juce::Slider::textBoxTextColourId, juce::Colours::black);
        mRightMillisecondSliderPtr->setColour(juce::Slider::thumbColourId, juce::Colours::black);
        mRightMillisecondSliderPtr->setColour(juce::Slider::rotarySliderFillColourId, juce::Colours::black);
        mRightMillisecondSliderPtr->setColour(juce::Slider::rotarySliderOutlineColourId, juce::Colours::black);

        mRightMillisecondAttachmentPtr = std::make_unique<juce::AudioProcessorValueTreeState::SliderAttachment>(
            apvts, delayRightMillisecondParameterId, *mRightMillisecondSliderPtr);

        mRightMillisecondLabelPtr = std::make_unique<juce::Label>();
        mRightMillisecondLabelPtr->setText("Right delay", juce::dontSendNotification);
        // mRightMillisecondSliderPtr->setValue(100.0f);
        mRightMillisecondLabelPtr->attachToComponent(mRightMillisecondSliderPtr.get(), false);
        // 设置标签文本为黑色
        mRightMillisecondLabelPtr->setColour(juce::Label::textColourId, juce::Colours::black);

        addAndMakeVisible(mRightMillisecondSliderPtr.get());
        addAndMakeVisible(mRightMillisecondLabelPtr.get());
        // End delayRightMillisecondParameterId

        // Start delayHighPassFrequencyParameterId
        mHighPassFrequencySliderPtr = std::make_unique<juce::Slider>(juce::Slider::RotaryVerticalDrag, juce::Slider::TextBoxBelow);
        mHighPassFrequencySliderPtr->setTextValueSuffix(" Hz");
        mHighPassFrequencySliderPtr->setScrollWheelEnabled(false);
        // 设置滑块文本为黑色
        mHighPassFrequencySliderPtr->setColour(juce::Slider::textBoxTextColourId, juce::Colours::black);
        mHighPassFrequencySliderPtr->setColour(juce::Slider::thumbColourId, juce::Colours::black);
        mHighPassFrequencySliderPtr->setColour(juce::Slider::rotarySliderFillColourId, juce::Colours::black);
        mHighPassFrequencySliderPtr->setColour(juce::Slider::rotarySliderOutlineColourId, juce::Colours::black);

        mHighPassFrequencyAttachmentPtr = std::make_unique<juce::AudioProcessorValueTreeState::SliderAttachment>(
            apvts, delayHighPassFrequencyParameterId, *mHighPassFrequencySliderPtr);

        mHighPassFrequencyLabelPtr = std::make_unique<juce::Label>();
        mHighPassFrequencyLabelPtr->setText("HPF", juce::dontSendNotification);
        mHighPassFrequencyLabelPtr->attachToComponent(mHighPassFrequencySliderPtr.get(), false);
        // 设置标签文本为黑色
        mHighPassFrequencyLabelPtr->setColour(juce::Label::textColourId, juce::Colours::black);

        addAndMakeVisible(mHighPassFrequencySliderPtr.get());
        addAndMakeVisible(mHighPassFrequencyLabelPtr.get());
        // End delayHighPassFrequencyParameterId

        // Start delayLowPassFrequencyParameterId
        mLowPassFrequencySliderPtr = std::make_unique<juce::Slider>(juce::Slider::RotaryVerticalDrag, juce::Slider::TextBoxBelow);
        mLowPassFrequencySliderPtr->setTextValueSuffix(" Hz");
        mLowPassFrequencySliderPtr->setScrollWheelEnabled(false);
        // 设置滑块文本为黑色
        mLowPassFrequencySliderPtr->setColour(juce::Slider::textBoxTextColourId, juce::Colours::black);
        mLowPassFrequencySliderPtr->setColour(juce::Slider::thumbColourId, juce::Colours::black);
        mLowPassFrequencySliderPtr->setColour(juce::Slider::rotarySliderFillColourId, juce::Colours::black);
        mLowPassFrequencySliderPtr->setColour(juce::Slider::rotarySliderOutlineColourId, juce::Colours::black);

        mLowPassFrequencyAttachmentPtr = std::make_unique<juce::AudioProcessorValueTreeState::SliderAttachment>(
            apvts, delayLowPassFrequencyParameterId, *mLowPassFrequencySliderPtr);

        mLowPassFrequencyLabelPtr = std::make_unique<juce::Label>();
        mLowPassFrequencyLabelPtr->setText("LPF", juce::dontSendNotification);
        mLowPassFrequencyLabelPtr->attachToComponent(mLowPassFrequencySliderPtr.get(), false);
        // 设置标签文本为黑色
        mLowPassFrequencyLabelPtr->setColour(juce::Label::textColourId, juce::Colours::black);

        addAndMakeVisible(mLowPassFrequencySliderPtr.get());
        addAndMakeVisible(mLowPassFrequencyLabelPtr.get());
        // End delayLowPassFrequencyParameterId

        // Start delayFeedbackParameterId
        mFeedbackSliderPtr = std::make_unique<juce::Slider>(juce::Slider::RotaryVerticalDrag, juce::Slider::TextBoxBelow);
        //mFeedbackSliderPtr->setTextValueSuffix(" %");
        mFeedbackSliderPtr->setScrollWheelEnabled(false);
        // 设置滑块文本为黑色
        mFeedbackSliderPtr->setColour(juce::Slider::textBoxTextColourId, juce::Colours::black);
        mFeedbackSliderPtr->setColour(juce::Slider::thumbColourId, juce::Colours::black);
        mFeedbackSliderPtr->setColour(juce::Slider::rotarySliderFillColourId, juce::Colours::black);
        mFeedbackSliderPtr->setColour(juce::Slider::rotarySliderOutlineColourId, juce::Colours::black);

        mFeedbackAttachmentPtr = std::make_unique<juce::AudioProcessorValueTreeState::SliderAttachment>(
            apvts, delayFeedbackParameterId, *mFeedbackSliderPtr);

        mFeedbackLabelPtr = std::make_unique<juce::Label>();
        mFeedbackLabelPtr->setText("Feedback", juce::dontSendNotification);// 设置初始值
        double hsh1 = readEnvWithType<double>("de_Feedback");
        mFeedbackSliderPtr->setValue(hsh1);
        mFeedbackLabelPtr->attachToComponent(mFeedbackSliderPtr.get(), false);
        // 设置标签文本为黑色
        mFeedbackLabelPtr->setColour(juce::Label::textColourId, juce::Colours::black);

        addAndMakeVisible(mFeedbackSliderPtr.get());
        addAndMakeVisible(mFeedbackLabelPtr.get());
        // End delayFeedbackParameterId

        // Start delayDryWetParameterId
        mDryWetSliderPtr = std::make_unique<juce::Slider>(juce::Slider::RotaryVerticalDrag, juce::Slider::TextBoxBelow);
        //mDryWetSliderPtr->setTextValueSuffix(" %");
        mDryWetSliderPtr->setScrollWheelEnabled(false);
        // 设置滑块文本为黑色
        mDryWetSliderPtr->setColour(juce::Slider::textBoxTextColourId, juce::Colours::black);
        mDryWetSliderPtr->setColour(juce::Slider::thumbColourId, juce::Colours::black);
        mDryWetSliderPtr->setColour(juce::Slider::rotarySliderFillColourId, juce::Colours::black);
        mDryWetSliderPtr->setColour(juce::Slider::rotarySliderOutlineColourId, juce::Colours::black);

        mDryWetAttachmentPtr = std::make_unique<juce::AudioProcessorValueTreeState::SliderAttachment>(
            apvts, delayDryWetParameterId, *mDryWetSliderPtr);

        mDryWetLabelPtr = std::make_unique<juce::Label>();
        mDryWetLabelPtr->setText("Mix", juce::dontSendNotification);// 设置初始值
        double hsh2 = readEnvWithType<double>("de_Mix");
        mDryWetSliderPtr->setValue(hsh2);
        mDryWetLabelPtr->attachToComponent(mDryWetSliderPtr.get(), false);
        // 设置标签文本为黑色
        mDryWetLabelPtr->setColour(juce::Label::textColourId, juce::Colours::black);

        addAndMakeVisible(mDryWetSliderPtr.get());
        addAndMakeVisible(mDryWetLabelPtr.get());
        // End delayDryWetParameterId

        mGroupComponentPtr.reset(new juce::GroupComponent(title, title));
        addAndMakeVisible(mGroupComponentPtr.get());

        // 设置组件边框和文本颜色为黑色
        mGroupComponentPtr->setColour(juce::GroupComponent::outlineColourId, juce::Colours::black);
        mGroupComponentPtr->setColour(juce::GroupComponent::textColourId, juce::Colours::black);

        // Sync Button
        mDelayIsSyncedParameterId = delayIsSyncedParameterId;
        mSyncButtonPtr = std::make_unique<juce::ToggleButton>("BPM Sync");
        mSyncButtonAttachmentPtr = std::make_unique<juce::AudioProcessorValueTreeState::ButtonAttachment>(
            apvts, delayIsSyncedParameterId, *mSyncButtonPtr);
        // 设置按钮文本为黑色
        mSyncButtonPtr->setColour(juce::ToggleButton::textColourId, juce::Colours::black);
        // 设置按钮勾选标记为黑色
        mSyncButtonPtr->setColour(juce::ToggleButton::tickColourId, juce::Colours::black);
        mSyncButtonPtr->setColour(juce::ToggleButton::tickDisabledColourId, juce::Colours::black);
        addAndMakeVisible(mSyncButtonPtr.get());

        apvts.addParameterListener(mDelayIsSyncedParameterId, this);
        parameterChanged(mDelayIsSyncedParameterId, *apvts.getRawParameterValue(mDelayIsSyncedParameterId));

        mDelayIsLinkedParameterId = delayIsLinkedParameterId;
        mLinkedButtonPtr = std::make_unique<juce::ToggleButton>("Linked");
        mLinkedButtonAttachmentPtr = std::make_unique<juce::AudioProcessorValueTreeState::ButtonAttachment>(
            apvts, delayIsLinkedParameterId, *mLinkedButtonPtr);
        // 设置按钮文本为黑色
        mLinkedButtonPtr->setColour(juce::ToggleButton::textColourId, juce::Colours::black);
        // 设置按钮勾选标记为黑色
        mLinkedButtonPtr->setColour(juce::ToggleButton::tickColourId, juce::Colours::black);
        mLinkedButtonPtr->setColour(juce::ToggleButton::tickDisabledColourId, juce::Colours::black);
        addAndMakeVisible(mLinkedButtonPtr.get());

        apvts.addParameterListener(mDelayIsLinkedParameterId, this);
        parameterChanged(mDelayIsLinkedParameterId, *apvts.getRawParameterValue(mDelayIsLinkedParameterId));

        // Toggle Button
        mToggleButtonPtr = std::make_unique<juce::ToggleButton>();
        // 设置按钮默认状态为开启
        /*mToggleButtonPtr->setToggleState(true, juce::NotificationType::dontSendNotification);*/
        mToggleButtonAttachmentPtr = std::make_unique<juce::AudioProcessorValueTreeState::ButtonAttachment>(
            apvts, toggleParameterId, *mToggleButtonPtr);
        // 设置按钮文本和勾选标记为黑色
        mToggleButtonPtr->setColour(juce::ToggleButton::textColourId, juce::Colours::black);
        mToggleButtonPtr->setColour(juce::ToggleButton::tickColourId, juce::Colours::black);
        mToggleButtonPtr->setColour(juce::ToggleButton::tickDisabledColourId, juce::Colours::black);
        addAndMakeVisible(mToggleButtonPtr.get());
        // 设置按钮默认状态为开启
        // mToggleButtonPtr->setToggleState(true, juce::NotificationType::dontSendNotification);
    }



    void parameterChanged(const juce::String& parameterID, float newValue) override
    {
        if (parameterID.toStdString() == mDelayIsSyncedParameterId)
        {
            mDelayIsSynced = newValue;
        }
        else if (parameterID.toStdString() == mDelayIsLinkedParameterId)
        {
            mDelayIsLinked = newValue;
        }

        if (mDelayIsLinked)
        {
            mLeftPerBeatLabelPtr->setText("Delay", juce::dontSendNotification);
            mLeftMillisecondLabelPtr->setText("Delay", juce::dontSendNotification);// 设置初始值
            double hsh3 = readEnvWithType<double>("de_Delay");
            mLeftMillisecondSliderPtr->setValue(hsh3);
        }
        else
        {
            mLeftPerBeatLabelPtr->setText("Left delay", juce::dontSendNotification);
            mLeftMillisecondLabelPtr->setText("Left delay", juce::dontSendNotification);
        }

        resized();
    }

    ~DelayComponent()
    {
        // Reset sliders
        mLeftPerBeatSliderPtr.reset();
        mRightPerBeatSliderPtr.reset();
        mLeftMillisecondSliderPtr.reset();
        mRightMillisecondSliderPtr.reset();
        mHighPassFrequencySliderPtr.reset();
        mLowPassFrequencySliderPtr.reset();
        mFeedbackSliderPtr.reset();
        mDryWetSliderPtr.reset();

        // Reset labels
        mLeftPerBeatLabelPtr.reset();
        mRightPerBeatLabelPtr.reset();
        mLeftMillisecondLabelPtr.reset();
        mRightMillisecondLabelPtr.reset();
        mHighPassFrequencyLabelPtr.reset();
        mLowPassFrequencyLabelPtr.reset();
        mFeedbackLabelPtr.reset();
        mDryWetLabelPtr.reset();

        // Reset attachments
        mLeftPerBeatAttachmentPtr.reset();
        mRightPerBeatAttachmentPtr.reset();
        mLeftMillisecondAttachmentPtr.reset();
        mRightMillisecondAttachmentPtr.reset();
        mHighPassFrequencyAttachmentPtr.reset();
        mLowPassFrequencyAttachmentPtr.reset();
        mFeedbackAttachmentPtr.reset();
        mDryWetAttachmentPtr.reset();
        mSyncButtonAttachmentPtr.reset();
        mLinkedButtonAttachmentPtr.reset();

        // Reset any additional controls not previously mentioned
        mToggleButtonPtr.reset();
        mToggleButtonAttachmentPtr.reset();
        mGroupComponentPtr.reset();

        mSyncButtonPtr.reset();
        mLinkedButtonPtr.reset();
    }

    void resized() override
    {
        auto bounds = getLocalBounds().reduced(10);
        mGroupComponentPtr->setBounds(bounds);

        juce::FlexBox mainFlexBox;
        mainFlexBox.flexDirection = juce::FlexBox::Direction::column;
        mainFlexBox.justifyContent = juce::FlexBox::JustifyContent::center;
        mainFlexBox.alignItems = juce::FlexBox::AlignItems::stretch;
        mainFlexBox.alignContent = juce::FlexBox::AlignContent::stretch;

        mainFlexBox.items.add(juce::FlexItem().withFlex(0.1));

        juce::FlexBox row1FlexBox;
        row1FlexBox.flexDirection = juce::FlexBox::Direction::row;
        row1FlexBox.justifyContent = juce::FlexBox::JustifyContent::center;
        row1FlexBox.alignItems = juce::FlexBox::AlignItems::stretch;
        row1FlexBox.alignContent = juce::FlexBox::AlignContent::stretch;
        row1FlexBox.flexWrap = juce::FlexBox::Wrap::wrap;

        row1FlexBox.items.add(juce::FlexItem(*mSyncButtonPtr).withFlex(0.5).withMaxHeight(44));
        row1FlexBox.items.add(juce::FlexItem(*mLinkedButtonPtr).withFlex(0.5).withMaxHeight(44));
        mainFlexBox.items.add(juce::FlexItem(row1FlexBox).withFlex(0.5));

        juce::FlexBox row2FlexBox;
        row2FlexBox.flexDirection = juce::FlexBox::Direction::row;
        row2FlexBox.justifyContent = juce::FlexBox::JustifyContent::center;
        row2FlexBox.alignItems = juce::FlexBox::AlignItems::stretch;
        row2FlexBox.alignContent = juce::FlexBox::AlignContent::stretch;
        row2FlexBox.flexWrap = juce::FlexBox::Wrap::wrap;

        row2FlexBox.items.add(juce::FlexItem(*mFeedbackSliderPtr).withFlex(1).withMaxHeight(128));

        mLeftPerBeatSliderPtr->setVisible(mDelayIsSynced);
        mRightPerBeatSliderPtr->setVisible(mDelayIsSynced && !mDelayIsLinked);

        mLeftMillisecondSliderPtr->setVisible(!mDelayIsSynced);
        mRightMillisecondSliderPtr->setVisible(!mDelayIsSynced && !mDelayIsLinked);

        if (mDelayIsSynced)
        {
            row2FlexBox.items.add(juce::FlexItem(*mLeftPerBeatSliderPtr).withFlex(1).withMaxHeight(128));

            if (!mDelayIsLinked)
            {
                row2FlexBox.items.add(juce::FlexItem(*mRightPerBeatSliderPtr).withFlex(1).withMaxHeight(128));
            }
        }
        else
        {
            row2FlexBox.items.add(juce::FlexItem(*mLeftMillisecondSliderPtr).withFlex(1).withMaxHeight(128));
            if (!mDelayIsLinked)
            {
                row2FlexBox.items.add(juce::FlexItem(*mRightMillisecondSliderPtr).withFlex(1).withMaxHeight(128));
            }
        }

        mainFlexBox.items.add(juce::FlexItem(row2FlexBox).withFlex(1));
        mainFlexBox.items.add(juce::FlexItem().withFlex(0.1));

        juce::FlexBox row3FlexBox;
        row3FlexBox.flexDirection = juce::FlexBox::Direction::row;
        row3FlexBox.justifyContent = juce::FlexBox::JustifyContent::center;
        row3FlexBox.alignItems = juce::FlexBox::AlignItems::stretch;
        row3FlexBox.alignContent = juce::FlexBox::AlignContent::stretch;
        row3FlexBox.flexWrap = juce::FlexBox::Wrap::wrap;

        row3FlexBox.items.add(juce::FlexItem(*mDryWetSliderPtr).withFlex(1).withMaxHeight(128));
        row3FlexBox.items.add(juce::FlexItem(*mHighPassFrequencySliderPtr).withFlex(1).withMaxHeight(128));
        row3FlexBox.items.add(juce::FlexItem(*mLowPassFrequencySliderPtr).withFlex(1).withMaxHeight(128));

        mainFlexBox.items.add(juce::FlexItem(row3FlexBox).withFlex(1)); // 2/3 of space

        // FlexBox for the bottom 1/3 where toggle button will be
        juce::FlexBox row4FlexBox;
        row4FlexBox.flexDirection = juce::FlexBox::Direction::row;
        row4FlexBox.justifyContent = juce::FlexBox::JustifyContent::center;
        row4FlexBox.alignItems = juce::FlexBox::AlignItems::center;
        row4FlexBox.alignContent = juce::FlexBox::AlignContent::center;

        auto toggleButtonSize = juce::jmin(bounds.getWidth(), bounds.getHeight() / 3) / 4;
        juce::FlexItem toggleFlexItem(toggleButtonSize, toggleButtonSize, *mToggleButtonPtr);
        row4FlexBox.items.add(toggleFlexItem);

        mainFlexBox.items.add(juce::FlexItem(row4FlexBox).withFlex(1)); // 1/3 of space

        // Perform layout for the main FlexBox
        mainFlexBox.performLayout(bounds);
    }

private:
    juce::AudioProcessorValueTreeState& mApvts;

    std::string mDelayIsSyncedParameterId;
    std::string mDelayIsLinkedParameterId;

    bool mDelayIsSynced = false;
    bool mDelayIsLinked = true;

    std::unique_ptr<juce::GroupComponent> mGroupComponentPtr;

    std::unique_ptr<juce::Slider> mLeftPerBeatSliderPtr;
    std::unique_ptr<juce::Label> mLeftPerBeatLabelPtr;
    std::unique_ptr<juce::AudioProcessorValueTreeState::SliderAttachment> mLeftPerBeatAttachmentPtr;

    std::unique_ptr<juce::Slider> mRightPerBeatSliderPtr;
    std::unique_ptr<juce::Label> mRightPerBeatLabelPtr;
    std::unique_ptr<juce::AudioProcessorValueTreeState::SliderAttachment> mRightPerBeatAttachmentPtr;

    std::unique_ptr<juce::Slider> mLeftMillisecondSliderPtr;
    std::unique_ptr<juce::Label> mLeftMillisecondLabelPtr;
    std::unique_ptr<juce::AudioProcessorValueTreeState::SliderAttachment> mLeftMillisecondAttachmentPtr;

    std::unique_ptr<juce::Slider> mRightMillisecondSliderPtr;
    std::unique_ptr<juce::Label> mRightMillisecondLabelPtr;
    std::unique_ptr<juce::AudioProcessorValueTreeState::SliderAttachment> mRightMillisecondAttachmentPtr;

    std::unique_ptr<juce::Slider> mHighPassFrequencySliderPtr;
    std::unique_ptr<juce::Label> mHighPassFrequencyLabelPtr;
    std::unique_ptr<juce::AudioProcessorValueTreeState::SliderAttachment> mHighPassFrequencyAttachmentPtr;

    std::unique_ptr<juce::Slider> mLowPassFrequencySliderPtr;
    std::unique_ptr<juce::Label> mLowPassFrequencyLabelPtr;
    std::unique_ptr<juce::AudioProcessorValueTreeState::SliderAttachment> mLowPassFrequencyAttachmentPtr;

    std::unique_ptr<juce::Slider> mFeedbackSliderPtr;
    std::unique_ptr<juce::Label> mFeedbackLabelPtr;
    std::unique_ptr<juce::AudioProcessorValueTreeState::SliderAttachment> mFeedbackAttachmentPtr;

    std::unique_ptr<juce::Slider> mDryWetSliderPtr;
    std::unique_ptr<juce::Label> mDryWetLabelPtr;
    std::unique_ptr<juce::AudioProcessorValueTreeState::SliderAttachment> mDryWetAttachmentPtr;

    std::unique_ptr<juce::ToggleButton> mSyncButtonPtr;
    std::unique_ptr<juce::AudioProcessorValueTreeState::ButtonAttachment> mSyncButtonAttachmentPtr;

    std::unique_ptr<juce::ToggleButton> mLinkedButtonPtr;
    std::unique_ptr<juce::AudioProcessorValueTreeState::ButtonAttachment> mLinkedButtonAttachmentPtr;

    std::unique_ptr<juce::ToggleButton> mToggleButtonPtr;
    std::unique_ptr<juce::AudioProcessorValueTreeState::ButtonAttachment> mToggleButtonAttachmentPtr;
};



