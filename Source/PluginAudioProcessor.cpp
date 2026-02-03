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

#include "PluginAudioProcessor.h"
#include "BinaryData.h"
#include "PluginAudioProcessorEditor.h"
#include "PluginAudioParameters.h"
#include <cassert>
#include "PluginUtils.h"


 //==============================================================================
PluginAudioProcessor::PluginAudioProcessor()
	: AudioProcessor(BusesProperties()
#if !JucePlugin_IsMidiEffect
#if !JucePlugin_IsSynth
		.withInput("Input", juce::AudioChannelSet::stereo(), true)
#endif
		.withOutput("Output", juce::AudioChannelSet::stereo(), true)
#endif
	),
	mUndoManager(std::make_unique<juce::UndoManager>()),
	mAudioProcessorValueTreeStatePtr(std::make_unique<juce::AudioProcessorValueTreeState>(
		*this,
		mUndoManager.get(),
		juce::Identifier(apvts::identifier),
		createParameterLayout())),
	mPresetManagerPtr(std::make_unique<PluginPresetManager>(*mAudioProcessorValueTreeStatePtr.get())),
	mAudioFormatManagerPtr(std::make_unique<juce::AudioFormatManager>()),
	mPitchMPM(std::make_unique<adamski::PitchMPM>(44100, 1024)),
	mAudioFifo(std::make_unique<AudioFifo>()),
	mAudioBuffer(std::make_unique<juce::AudioBuffer<float>>()),
	mInputLevelMeterSourcePtr(std::make_unique<foleys::LevelMeterSource>()),
	mOutputLevelMeterSourcePtr(std::make_unique<foleys::LevelMeterSource>()),

	mInputGainPtr(std::make_unique<juce::dsp::Gain<float>>()),

	mNoiseGate(std::make_unique<juce::dsp::NoiseGate<float>>()),
	mPreCompressorPtr(std::make_unique<juce::dsp::Compressor<float>>()),
	mPreCompressorGainPtr(std::make_unique<juce::dsp::Gain<float>>()),

	mPreCompressorDryWetMixerPtr(std::make_unique<juce::dsp::DryWetMixer<float>>()),

	mTubeScreamerPtr(std::make_unique<TubeScreamer>()),
	mMouseDrivePtr(std::make_unique<MouseDrive>()),
	mGraphicEqualiser(std::make_unique<GraphicEqualiser>()),

	mStage1Buffer(std::make_unique<juce::AudioBuffer<float>>()),
	mStage1InputGainPtr(std::make_unique<juce::dsp::Gain<float>>()),
	mStage1WaveShaperPtr(std::make_unique<juce::dsp::WaveShaper<float>>()),
	mStage1OutputGainPtr(std::make_unique<juce::dsp::Gain<float>>()),
	mStage1DryWetMixerPtr(std::make_unique<juce::dsp::DryWetMixer<float>>()),

	mStage2Buffer(std::make_unique<juce::AudioBuffer<float>>()),
	mStage2InputGainPtr(std::make_unique<juce::dsp::Gain<float>>()),
	mStage2WaveShaperPtr(std::make_unique<juce::dsp::WaveShaper<float>>()),
	mStage2OutputGainPtr(std::make_unique<juce::dsp::Gain<float>>()),
	mStage2DryWetMixerPtr(std::make_unique<juce::dsp::DryWetMixer<float>>()),

	mStage3Buffer(std::make_unique<juce::AudioBuffer<float>>()),
	mStage3InputGainPtr(std::make_unique<juce::dsp::Gain<float>>()),
	mStage3WaveShaperPtr(std::make_unique<juce::dsp::WaveShaper<float>>()),
	mStage3OutputGainPtr(std::make_unique<juce::dsp::Gain<float>>()),
	mStage3DryWetMixerPtr(std::make_unique<juce::dsp::DryWetMixer<float>>()),

	mStage4Buffer(std::make_unique<juce::AudioBuffer<float>>()),
	mStage4InputGainPtr(std::make_unique<juce::dsp::Gain<float>>()),
	mStage4WaveShaperPtr(std::make_unique<juce::dsp::WaveShaper<float>>()),
	mStage4OutputGainPtr(std::make_unique<juce::dsp::Gain<float>>()),
	mStage4DryWetMixerPtr(std::make_unique<juce::dsp::DryWetMixer<float>>()),

	mBiasPtr(std::make_unique<juce::dsp::Bias<float>>()),
	mAmplifierEqualiser(std::make_unique<AmplifierEqualiser>()),

	mDelayLineLeftPtr(std::make_unique<juce::dsp::DelayLine<float>>(apvts::delayTimeMsMaximumValue* (apvts::sampleRateAssumption / 1000))),
	mDelayLineRightPtr(std::make_unique<juce::dsp::DelayLine<float>>(apvts::delayTimeMsMaximumValue* (apvts::sampleRateAssumption / 1000))),
	mDelayLineDryWetMixerPtr(std::make_unique<juce::dsp::DryWetMixer<float>>()),
	mDelayHighPassFilterPtr(std::make_unique<juce::dsp::ProcessorDuplicator<juce::dsp::IIR::Filter<float>, juce::dsp::IIR::Coefficients<float>>>(
		juce::dsp::IIR::Coefficients<float>::makeHighPass(apvts::sampleRateAssumption, InstrumentEqualiser::sHighPassFrequencyNormalisableRange.start)
	)),
	mDelayLowPassFilterPtr(std::make_unique<juce::dsp::ProcessorDuplicator<juce::dsp::IIR::Filter<float>, juce::dsp::IIR::Coefficients<float>>>(
		juce::dsp::IIR::Coefficients<float>::makeLowPass(apvts::sampleRateAssumption, InstrumentEqualiser::sLowPassFrequencyNormalisableRange.start)
	)),

	mChorusPtr(std::make_unique<Chorus>()),
	mPhaserPtr(std::make_unique<Phaser>()),
	mFlangerPtr(std::make_unique<Flanger>()),
	mBitcrusherPtr(std::make_unique<Bitcrusher>()),

	mConvolutionMessageQueuePtr(std::make_unique<juce::dsp::ConvolutionMessageQueue>()),
	mCabinetImpulseResponseConvolutionPtr(std::make_unique<juce::dsp::Convolution>(juce::dsp::Convolution::NonUniform{ 128 }, * mConvolutionMessageQueuePtr.get())),
	mLofiImpulseResponseConvolutionPtr(std::make_unique<juce::dsp::Convolution>(juce::dsp::Convolution::NonUniform{ 128 }, * mConvolutionMessageQueuePtr.get())),

	mInstrumentCompressorPtr(std::make_unique<Compressor>()),
	mInstrumentEqualiserPtr(std::make_unique<InstrumentEqualiser>()),

	mReverbPtr(std::make_unique<juce::dsp::Reverb>()),

	mCabinetGainPtr(std::make_unique<juce::dsp::Gain<float>>()),
	mLimiterPtr(std::make_unique<juce::dsp::Limiter<float>>()),

	mOutputGainPtr(std::make_unique<juce::dsp::Gain<float>>())
{
	mAudioFormatManagerPtr->registerBasicFormats();
	mInputLevelMeterSourcePtr->resize(2, 44100 / 100 * 5);
	mOutputLevelMeterSourcePtr->resize(2, 44100 / 100 * 5);

	mAudioProcessorValueTreeStatePtr->state.addListener(this);
	for (const auto& parameterIdAndEnum : apvts::parameterIdToEnumMap) {
		mAudioProcessorValueTreeStatePtr->addParameterListener(parameterIdAndEnum.first, this);
	}

	// Initialize import file path for offline rendering
	importFile = juce::File::getSpecialLocation(juce::File::SpecialLocationType::commonDocumentsDirectory)
		.getChildFile("Supertonal")
		.getChildFile("Audio-agent")
		.getChildFile("import_params.json");

	// Start timer to check for file changes every 500ms
	startTimer(500);
}

juce::AudioProcessorValueTreeState::ParameterLayout PluginAudioProcessor::createParameterLayout()
{
	juce::AudioProcessorValueTreeState::ParameterLayout layout;

	juce::StringArray waveShaperIdsJuceStringArray;
	for (const auto& idToFunction : apvts::waveShaperIdToFunctionMap) {
		waveShaperIdsJuceStringArray.add(idToFunction.first);
	}

	for (const auto& parameterIdAndEnum : apvts::parameterIdToEnumMap)
	{
		auto& parameterId = parameterIdAndEnum.first;

		std::vector<std::string> parts;
		std::stringstream ss(parameterId);
		std::string item;

		while (std::getline(ss, item, '_')) {
			parts.push_back(item);
		}
		bool Compressor_on = readEnvWithType<bool>("Compressor_on");
		bool Driver_on = readEnvWithType<bool>("Driver_on");
		bool Screamer_on = readEnvWithType<bool>("Screamer_on");
		bool Delay_on = readEnvWithType<bool>("Delay_on");
		bool Reverb_on = readEnvWithType<bool>("Reverb_on");
		bool Chorus_on = readEnvWithType<bool>("Chorus_on");
		bool Flanger_on = readEnvWithType<bool>("Flanger_on");
		bool Phaser_on = readEnvWithType<bool>("Phaser_on");
		int co_Ratio = readEnvWithType<int>("co_Ratio");
		double co_Attack = readEnvWithType<double>("co_Attack");
		double co_Release = readEnvWithType<double>("co_Release");
		double dr_Distortion = readEnvWithType<double>("dr_Distortion");
		double dr_Volume = readEnvWithType<double>("dr_Volume");
		double s_Drive = readEnvWithType<double>("s_Drive");
		double s_Tone = readEnvWithType<double>("s_Tone");
		double s_Level = readEnvWithType<double>("s_Level");
		double r_Size = readEnvWithType<double>("r_Size");
		double r_Damping = readEnvWithType<double>("r_Damping");
		double r_Width = readEnvWithType<double>("r_Width");
		double r_Mix = readEnvWithType<double>("r_Mix");
		double ch_Delay = readEnvWithType<double>("ch_Delay");
		double ch_Depth = readEnvWithType<double>("ch_Depth");
		double ch_Frequency = readEnvWithType<double>("ch_Frequency");
		double ch_Width = readEnvWithType<double>("ch_Width");
		double f_Delay = readEnvWithType<double>("f_Delay");
		double f_Depth = readEnvWithType<double>("f_Depth");
		double f_Feedback = readEnvWithType<double>("f_Feedback");
		double f_Frequency = readEnvWithType<double>("f_Frequency");
		double f_Width = readEnvWithType<double>("f_Width");
		double p_Depth = readEnvWithType<double>("p_Depth");
		double p_Feedback = readEnvWithType<double>("p_Feedback");
		double p_Frequency = readEnvWithType<double>("p_Frequency");
		int p_Width = readEnvWithType<int>("p_Width");

		bool initialValue = true; // 提供默认值
		/*assert(parameterInitialValues.find("TUBE_SCREAMER_ON") == parameterInitialValues.end());
		std::cout << "Storing initial value: " << Screamer_on << std::endl;
		parameterInitialValues["TUBE_SCREAMER_ON"] = Screamer_on;*/

		switch (parameterIdAndEnum.second)
		{
		case apvts::ParameterEnum::INSTRUMENT_EQUALISER_LOW_PASS_ON:
			layout.add(std::make_unique<juce::AudioParameterBool>(
				juce::ParameterID{ parameterId, apvts::version },
				parameterId,
				false
			));
			break;
		case apvts::ParameterEnum::INSTRUMENT_EQUALISER_LOW_PEAK_ON:
			layout.add(std::make_unique<juce::AudioParameterBool>(
				juce::ParameterID{ parameterId, apvts::version },
				parameterId,
				false
			));
			break;
		case apvts::ParameterEnum::INSTRUMENT_EQUALISER_LOW_MID_PEAK_ON:
			layout.add(std::make_unique<juce::AudioParameterBool>(
				juce::ParameterID{ parameterId, apvts::version },
				parameterId,
				false
			));
			break;
		case apvts::ParameterEnum::INSTRUMENT_EQUALISER_HIGH_MID_PEAK_ON:
			layout.add(std::make_unique<juce::AudioParameterBool>(
				juce::ParameterID{ parameterId, apvts::version },
				parameterId,
				false
			));
			break;
		case apvts::ParameterEnum::INSTRUMENT_EQUALISER_HIGH_PEAK_ON:
			layout.add(std::make_unique<juce::AudioParameterBool>(
				juce::ParameterID{ parameterId, apvts::version },
				parameterId,
				false
			));
			break;
		case apvts::ParameterEnum::INSTRUMENT_EQUALISER_HIGH_PASS_ON:
			layout.add(std::make_unique<juce::AudioParameterBool>(
				juce::ParameterID{ parameterId, apvts::version },
				parameterId,
				false
			));
			break;
		case apvts::ParameterEnum::BYPASS_ON:
			layout.add(std::make_unique<juce::AudioParameterBool>(
				juce::ParameterID{ parameterId, apvts::version },
				parameterId,
				false
			));
			break;
		case apvts::ParameterEnum::TUBE_SCREAMER_ON://初始值（另）
			initialValue = Screamer_on; // 获取初始值
			// 打印 parameterId 到日志
			juce::Logger::writeToLog("TUBE_SCREAMER_ON parameterId: " + parameterId);
			//parameterInitialValues[parameterId] = initialValue; // 存储初始值
			//parameterInitialValues[TUBE_SCREAMER_ON] = Screamer_on; // 存储初始值
			layout.add(std::make_unique<juce::AudioParameterBool>(
				juce::ParameterID{ parameterId, apvts::version },
				parameterId,
				initialValue // 修改默认值为 true
			));
			break;
		case apvts::ParameterEnum::MOUSE_DRIVE_ON://初始值（另）
			layout.add(std::make_unique<juce::AudioParameterBool>(
				juce::ParameterID{ parameterId, apvts::version },
				parameterId,
				Driver_on // 修改默认值为 Driver_on
			));
			break;
		case apvts::ParameterEnum::STAGE2_ON:
			layout.add(std::make_unique<juce::AudioParameterBool>(
				juce::ParameterID{ parameterId, apvts::version },
				parameterId,
				false
			));
			break;
		case apvts::ParameterEnum::STAGE3_ON:
			layout.add(std::make_unique<juce::AudioParameterBool>(
				juce::ParameterID{ parameterId, apvts::version },
				parameterId,
				false
			));
			break;
		case apvts::ParameterEnum::STAGE4_ON:
			layout.add(std::make_unique<juce::AudioParameterBool>(
				juce::ParameterID{ parameterId, apvts::version },
				parameterId,
				false
			));
			break;
		case apvts::ParameterEnum::REVERB_ON://初始值（另）
			layout.add(std::make_unique<juce::AudioParameterBool>(
				juce::ParameterID{ parameterId, apvts::version },
				parameterId,
				Reverb_on // 修改默认值为 Reverb_on
			));
			break;
		case apvts::ParameterEnum::PRE_COMPRESSOR_IS_ON://初始值（另）
			layout.add(std::make_unique<juce::AudioParameterBool>(
				juce::ParameterID{ parameterId, apvts::version },
				parameterId,
				Compressor_on // 修改默认值为 true
			));
			break;
		case apvts::ParameterEnum::DELAY_ON://初始值（另）
			layout.add(std::make_unique<juce::AudioParameterBool>(
				juce::ParameterID{ parameterId, apvts::version },
				parameterId,
				Delay_on // 修改默认值为 true
			));
			break;
		case apvts::ParameterEnum::PHASER_IS_ON://初始值（另）
			layout.add(std::make_unique<juce::AudioParameterBool>(
				juce::ParameterID{ parameterId, apvts::version },
				parameterId,
				Phaser_on // 修改默认值为 true
			));
			break;
		case apvts::ParameterEnum::CHORUS_ON: //初始值（另）
			layout.add(std::make_unique<juce::AudioParameterBool>(
				juce::ParameterID{ parameterId, apvts::version },
				parameterId,
				Chorus_on // 修改默认值为 true
			));
			break;
		case apvts::ParameterEnum::PRE_EQUALISER_ON:
			layout.add(std::make_unique<juce::AudioParameterBool>(
				juce::ParameterID{ parameterId, apvts::version },
				parameterId,
				false
			));
			break;
		case apvts::ParameterEnum::DELAY_IS_SYNCED:
			layout.add(std::make_unique<juce::AudioParameterBool>(
				juce::ParameterID{ parameterId, apvts::version },
				parameterId,
				false
			));
			break;
		case apvts::ParameterEnum::PRE_COMPRESSOR_AUTO_MAKE_UP_ON:
			layout.add(std::make_unique<juce::AudioParameterBool>(
				juce::ParameterID{ parameterId, apvts::version },
				parameterId,
				false
			));
			break;
		case apvts::ParameterEnum::INSTRUMENT_COMPRESSOR_IS_PRE_EQ_ON:
			layout.add(std::make_unique<juce::AudioParameterBool>(
				juce::ParameterID{ parameterId, apvts::version },
				parameterId,
				false
			));
			break;
		case apvts::ParameterEnum::INSTRUMENT_COMPRESSOR_IS_ON:
			layout.add(std::make_unique<juce::AudioParameterBool>(
				juce::ParameterID{ parameterId, apvts::version },
				parameterId,
				false
			));
			break;
		case apvts::ParameterEnum::INSTRUMENT_COMPRESSOR_AUTO_GAIN_ON:
			layout.add(std::make_unique<juce::AudioParameterBool>(
				juce::ParameterID{ parameterId, apvts::version },
				parameterId,
				false
			));
			break;
		case apvts::ParameterEnum::INSTRUMENT_COMPRESSOR_AUTO_ATTACK_ON:
			layout.add(std::make_unique<juce::AudioParameterBool>(
				juce::ParameterID{ parameterId, apvts::version },
				parameterId,
				false
			));
			break;
		case apvts::ParameterEnum::INSTRUMENT_COMPRESSOR_AUTO_RELEASE_ON:
			layout.add(std::make_unique<juce::AudioParameterBool>(
				juce::ParameterID{ parameterId, apvts::version },
				parameterId,
				false
			));
			break;
		case apvts::ParameterEnum::INSTRUMENT_COMPRESSOR_LOOKAHEAD_ON:
			layout.add(std::make_unique<juce::AudioParameterBool>(
				juce::ParameterID{ parameterId, apvts::version },
				parameterId,
				false
			));
			break;
		case apvts::ParameterEnum::BIT_CRUSHER_ON:
			layout.add(std::make_unique<juce::AudioParameterBool>(
				juce::ParameterID{ parameterId, apvts::version },
				parameterId,
				false
			));
			break;
		case apvts::ParameterEnum::FLANGER_ON:                  //初始值（另）
			layout.add(std::make_unique<juce::AudioParameterBool>(
				juce::ParameterID{ parameterId, apvts::version },
				parameterId,
				Flanger_on // 修改默认值为 true
			));
			break;
		case apvts::ParameterEnum::IS_LOFI:
			layout.add(std::make_unique<juce::AudioParameterBool>(
				juce::ParameterID{ parameterId, apvts::version },
				parameterId,
				false
			));
			break;
		case apvts::ParameterEnum::TUNER_ON:
			layout.add(std::make_unique<juce::AudioParameterBool>(
				juce::ParameterID{ parameterId, apvts::version },
				parameterId,
				false
			));
			break;
		case apvts::ParameterEnum::DELAY_FEEDBACK:
		case apvts::ParameterEnum::REVERB_MIX:                   //初始值（另）
			//initialValue = r_Mix;
			//parameterInitialValues[parameterId] = initialValue; // 存储初始值
			layout.add(std::make_unique<juce::AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				apvts::zeroToOneLinearNormalisableRange,
				r_Mix
			));
			break;
		case apvts::ParameterEnum::REVERB_SIZE:                 //初始值
			layout.add(std::make_unique<juce::AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				apvts::zeroToOneLinearNormalisableRange,
				r_Size
			));
			break;
		case apvts::ParameterEnum::REVERB_DAMPING:              //初始值1
			layout.add(std::make_unique<juce::AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				apvts::zeroToOneLinearNormalisableRange,
				r_Damping
			));
			break;
		case apvts::ParameterEnum::PRE_EQUALISER_100_GAIN:
		case apvts::ParameterEnum::PRE_EQUALISER_200_GAIN:
		case apvts::ParameterEnum::PRE_EQUALISER_400_GAIN:
		case apvts::ParameterEnum::PRE_EQUALISER_800_GAIN:
		case apvts::ParameterEnum::PRE_EQUALISER_1600_GAIN:
		case apvts::ParameterEnum::PRE_EQUALISER_3200_GAIN:
		case apvts::ParameterEnum::PRE_EQUALISER_6400_GAIN:
		case apvts::ParameterEnum::PRE_EQUALISER_LEVEL_GAIN:
		{
			juce::NormalisableRange<float> normalisableRange = GraphicEqualiser::sDecibelGainNormalisableRange;
			normalisableRange.interval = apvts::defaultIntervalValue;
			layout.add(std::make_unique<juce::AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				normalisableRange,
				apvts::defaultValueOff
			));
		}
		break;
		case apvts::ParameterEnum::AMP_RESONANCE_DB:
		case apvts::ParameterEnum::AMP_BASS_DB:
		case apvts::ParameterEnum::AMP_MIDDLE_DB:
		case apvts::ParameterEnum::AMP_TREBLE_DB:
		case apvts::ParameterEnum::AMP_PRESENCE_DB:
		{
			juce::NormalisableRange<float> normalisableRange = AmplifierEqualiser::sDecibelsNormalisableRange;
			normalisableRange.interval = apvts::defaultIntervalValue;
			layout.add(std::make_unique<juce::AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				normalisableRange,
				apvts::defaultValueOff
			));
		}
		break;
		case apvts::ParameterEnum::STAGE1_INPUT_GAIN:
		case apvts::ParameterEnum::STAGE1_OUTPUT_GAIN:
		case apvts::ParameterEnum::STAGE2_INPUT_GAIN:
		case apvts::ParameterEnum::STAGE2_OUTPUT_GAIN:
		case apvts::ParameterEnum::STAGE3_INPUT_GAIN:
		case apvts::ParameterEnum::STAGE3_OUTPUT_GAIN:
		case apvts::ParameterEnum::STAGE4_INPUT_GAIN:
		case apvts::ParameterEnum::STAGE4_OUTPUT_GAIN:
		case apvts::ParameterEnum::INPUT_GAIN:
		case apvts::ParameterEnum::OUTPUT_GAIN:
		case apvts::ParameterEnum::PRE_COMPRESSOR_GAIN:
			layout.add(std::make_unique<juce::AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				apvts::gainDecibelsNormalisableRange,
				apvts::gainDeciblesDefaultValue
			));
			break;
		case apvts::ParameterEnum::CABINET_OUTPUT_GAIN:
			layout.add(std::make_unique<juce::AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				apvts::gainDecibelsNormalisableRange,
				10.0f
			));
			break;
		case apvts::ParameterEnum::PRE_COMPRESSOR_THRESHOLD:
			layout.add(std::make_unique<juce::AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				apvts::gainDecibelsNegativeNormalisableRange,
				apvts::gainDeciblesDefaultValue
			));
			break;
		case apvts::ParameterEnum::STAGE1_DRY_WET_MIX:
		case apvts::ParameterEnum::STAGE2_DRY_WET_MIX:
		case apvts::ParameterEnum::STAGE3_DRY_WET_MIX:
		case apvts::ParameterEnum::STAGE4_DRY_WET_MIX:
		case apvts::ParameterEnum::PRE_COMPRESSOR_DRY_WET_MIX:
		case apvts::ParameterEnum::REVERB_WIDTH:                      //初始值2
			layout.add(std::make_unique<juce::AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				apvts::zeroToOneLinearNormalisableRange,
				r_Width
			));
			break;
		case apvts::ParameterEnum::INSTRUMENT_EQUALISER_LOW_PEAK_GAIN:
		case apvts::ParameterEnum::INSTRUMENT_EQUALISER_LOW_MID_PEAK_GAIN:
		case apvts::ParameterEnum::INSTRUMENT_EQUALISER_HIGH_MID_PEAK_GAIN:
		case apvts::ParameterEnum::INSTRUMENT_EQUALISER_HIGH_PEAK_GAIN:
		{
			juce::NormalisableRange<float> normalisableRange = InstrumentEqualiser::sDecibelsNormalisableRange;
			normalisableRange.interval = apvts::defaultIntervalValue;
			layout.add(std::make_unique<juce::AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				normalisableRange,
				apvts::defaultValueOff
			));
		}
		break;
		case apvts::ParameterEnum::INSTRUMENT_EQUALISER_LOW_PEAK_QUALITY:
		case apvts::ParameterEnum::INSTRUMENT_EQUALISER_LOW_MID_PEAK_QUALITY:
		case apvts::ParameterEnum::INSTRUMENT_EQUALISER_HIGH_MID_PEAK_QUALITY:
		case apvts::ParameterEnum::INSTRUMENT_EQUALISER_HIGH_PEAK_QUALITY:
		{
			layout.add(std::make_unique<juce::AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				apvts::qualityNormalisableRange,
				apvts::qualityOnDefaultValue
			));
		}
		break;
		case apvts::ParameterEnum::INSTRUMENT_EQUALISER_HIGH_PASS_QUALITY:
		case apvts::ParameterEnum::INSTRUMENT_EQUALISER_LOW_PASS_QUALITY:
		{
			layout.add(std::make_unique<juce::AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				apvts::qualityNormalisableRange,
				apvts::qualityOnDefaultValue
			));
		}
		break;
		case apvts::ParameterEnum::INSTRUMENT_EQUALISER_LOW_PASS_FREQUENCY:
		case apvts::ParameterEnum::DELAY_LOW_PASS_FREQUENCY:
		{
			juce::NormalisableRange<float> normalisableRange = InstrumentEqualiser::sLowPassFrequencyNormalisableRange;
			normalisableRange.interval = apvts::defaultIntervalValue;
			layout.add(std::make_unique<juce::AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				normalisableRange,
				InstrumentEqualiser::sLowPassFrequencyDefaultValue
			));
		}
		break;
		case apvts::ParameterEnum::INSTRUMENT_EQUALISER_LOW_PEAK_FREQUENCY:
		{
			juce::NormalisableRange<float> normalisableRange = InstrumentEqualiser::sLowPeakFrequencyNormalisableRange;
			normalisableRange.interval = apvts::defaultIntervalValue;
			layout.add(std::make_unique<juce::AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				normalisableRange,
				InstrumentEqualiser::sLowPeakFrequencyDefaultValue
			));
		}
		break;
		case apvts::ParameterEnum::INSTRUMENT_EQUALISER_LOW_MID_PEAK_FREQUENCY:
		{
			juce::NormalisableRange<float> normalisableRange = InstrumentEqualiser::sLowMidPeakFrequencyNormalisableRange;
			normalisableRange.interval = apvts::defaultIntervalValue;
			layout.add(std::make_unique<juce::AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				normalisableRange,
				InstrumentEqualiser::sLowMidPeakFrequencyDefaultValue
			));
		}
		break;
		case apvts::ParameterEnum::INSTRUMENT_EQUALISER_HIGH_MID_PEAK_FREQUENCY:
		{
			juce::NormalisableRange<float> normalisableRange = InstrumentEqualiser::sHighMidPeakFrequencyNormalisableRange;
			normalisableRange.interval = apvts::defaultIntervalValue;
			layout.add(std::make_unique<juce::AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				normalisableRange,
				InstrumentEqualiser::sHighMidPeakFrequencyDefaultValue
			));
		}
		break;
		case apvts::ParameterEnum::INSTRUMENT_EQUALISER_HIGH_PEAK_FREQUENCY:
		{
			juce::NormalisableRange<float> normalisableRange = InstrumentEqualiser::sHighPeakFrequencyNormalisableRange;
			normalisableRange.interval = apvts::defaultIntervalValue;
			layout.add(std::make_unique<juce::AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				normalisableRange,
				InstrumentEqualiser::sHighPeakFrequencyDefaultValue
			));
		}
		break;
		case apvts::ParameterEnum::INSTRUMENT_EQUALISER_HIGH_PASS_FREQUENCY:
		case apvts::ParameterEnum::DELAY_HIGH_PASS_FREQUENCY:
		{
			juce::NormalisableRange<float> normalisableRange = InstrumentEqualiser::sHighPassFrequencyNormalisableRange;
			normalisableRange.interval = apvts::defaultIntervalValue;
			layout.add(std::make_unique<juce::AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				normalisableRange,
				InstrumentEqualiser::sHighPassFrequencyDefaultValue
			));
		}
		break;
		case apvts::ParameterEnum::STAGE1_ON:
		case apvts::ParameterEnum::LIMITER_ON:
		case apvts::ParameterEnum::CABINET_IMPULSE_RESPONSE_CONVOLUTION_ON:
		case apvts::ParameterEnum::DELAY_LINKED:
			layout.add(std::make_unique<juce::AudioParameterBool>(
				juce::ParameterID{ parameterId, apvts::version },
				parameterId,
				true));
			break;
		case apvts::ParameterEnum::DELAY_DRY_WET:
			layout.add(std::make_unique<juce::AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				apvts::zeroToOneLinearNormalisableRange,
				apvts::defaultValueHalf
			));
			break;
		case apvts::ParameterEnum::NOISE_GATE_THRESHOLD:
			layout.add(std::make_unique<juce::AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				apvts::gainDecibelsNegativeNormalisableRange,
				apvts::gainDecibelsMinimumValue
			));
			break;
		case apvts::ParameterEnum::LIMITER_THRESHOLD:
			layout.add(std::make_unique<juce::AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				apvts::gainDecibelsNegativeNormalisableRange,
				apvts::limiterThresholdDefaultValue
			));
			break;
		case apvts::ParameterEnum::STAGE1_WAVE_SHAPER:
		case apvts::ParameterEnum::STAGE2_WAVE_SHAPER:
		case apvts::ParameterEnum::STAGE3_WAVE_SHAPER:
		case apvts::ParameterEnum::STAGE4_WAVE_SHAPER:
			layout.add(std::make_unique<juce::AudioParameterChoice>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				waveShaperIdsJuceStringArray,
				1));
			break;
		case apvts::ParameterEnum::BIAS:
			layout.add(std::make_unique<juce::AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				apvts::negativeOneToOneLinearNormalisableRange,
				apvts::defaultValueOff
			));
			break;
		case apvts::ParameterEnum::PRE_COMPRESSOR_ATTACK:     //初始值（另）
			layout.add(std::make_unique<juce::AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				apvts::zeroToOneLinearNormalisableRange,
				co_Attack
			));
			break;
		case apvts::ParameterEnum::NOISE_GATE_ATTACK:
			layout.add(std::make_unique<juce::AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				apvts::attackNormalisableRange,
				apvts::attackMsDefaultValue
			));
			break;
		case apvts::ParameterEnum::PRE_COMPRESSOR_RELEASE:     //初始值（另）
			layout.add(std::make_unique<juce::AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				apvts::zeroToOneLinearNormalisableRange,
				co_Release
			));
			break;
		case apvts::ParameterEnum::NOISE_GATE_RELEASE:
			layout.add(std::make_unique<juce::AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				apvts::releaseMsNormalisableRange,
				apvts::releaseMsDefaultValue
			));
			break;
		case apvts::ParameterEnum::PRE_COMPRESSOR_RATIO:      //初始值3
			layout.add(std::make_unique<juce::AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				apvts::ratioNormalizableRange,
				co_Ratio
			));
			break;
		case apvts::ParameterEnum::NOISE_GATE_RATIO:
			layout.add(std::make_unique<juce::AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				apvts::ratioNormalizableRange,
				100.0f
			));
			break;

		case apvts::ParameterEnum::CHORUS_FREQUENCY:        //初始值4
			layout.add(std::make_unique<juce::AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				Chorus::lfoFrequencyNormalisableRange,
				ch_Frequency
			));
			break;
		case apvts::ParameterEnum::CHORUS_DEPTH:           //初始值5
			layout.add(std::make_unique<juce::AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				Chorus::depthNormalisableRange,
				ch_Depth
			));
			break;
		case apvts::ParameterEnum::CHORUS_WIDTH:             //初始值6
			layout.add(std::make_unique<juce::AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				Chorus::widthNormalisableRange,
				ch_Width
			));
			break;
		case apvts::ParameterEnum::CHORUS_DELAY:           //初始值7
			layout.add(std::make_unique<juce::AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				Chorus::delayNormalisableRange,
				ch_Delay
			));
			break;
		case apvts::ParameterEnum::LIMITER_RELEASE:
			layout.add(std::make_unique<juce::AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				apvts::releaseMsNormalisableRange,
				apvts::limiterReleaseDefaultValue
			));
			break;
		case apvts::ParameterEnum::PHASER_FREQUENCY:     //初始值8
			layout.add(std::make_unique<juce::AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				Phaser::frequencyNormalisableRange,
				p_Frequency
			));
			break;
		case apvts::ParameterEnum::PHASER_WIDTH:         //初始值9
			layout.add(std::make_unique<juce::AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				Phaser::widthNormalisableRange,
				p_Width
			));
			break;
		case apvts::ParameterEnum::PHASER_DEPTH:         //初始值10
			layout.add(std::make_unique<juce::AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				Phaser::depthNormalisableRange,
				p_Depth
			));
			break;
		case apvts::ParameterEnum::PHASER_FEEDBACK:       //初始值11
			layout.add(std::make_unique<juce::AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				Phaser::feedbackNormalisableRange,
				p_Feedback
			));
			break;
		case apvts::ParameterEnum::DELAY_RIGHT_MS:
		case apvts::ParameterEnum::DELAY_LEFT_MS:
			layout.add(std::make_unique<juce::AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				apvts::delayTimeMsNormalisableRange,
				apvts::delayTimeMsDefaultValue
			));
			break;
		case apvts::ParameterEnum::DELAY_LEFT_PER_BEAT:
		case apvts::ParameterEnum::DELAY_RIGHT_PER_BEAT:
			layout.add(std::make_unique<juce::AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				apvts::fractionalTimeNormalizableRange,
				2.0f
			));
			break;
		case apvts::ParameterEnum::TUBE_SCREAMER_LEVEL:    //初始值12
			layout.add(std::make_unique<juce::AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				TubeScreamer::levelNormalisableRange,
				s_Level
			));
			break;
		case apvts::ParameterEnum::TUBE_SCREAMER_TONE:      //初始值13
			layout.add(std::make_unique<juce::AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				TubeScreamer::toneNormalisableRange,
				s_Tone
			));
			break;
		case apvts::ParameterEnum::TUBE_SCREAMER_DRIVE:      //初始值14
			layout.add(std::make_unique<juce::AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				TubeScreamer::driveNormalisableRange,
				s_Drive
			));
			break;
		case apvts::ParameterEnum::TUBE_SCREAMER_DIODE_TYPE:
			layout.add(std::make_unique<juce::AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				TubeScreamer::diodeTypeNormalisableRange,
				TubeScreamer::diodeTypeDefaultValue
			));
			break;
		case apvts::ParameterEnum::TUBE_SCREAMER_DIODE_COUNT:
			layout.add(std::make_unique<juce::AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				TubeScreamer::diodeCountNormalisableRange,
				TubeScreamer::diodeCountDefaultValue
			));
			break;
		case apvts::ParameterEnum::INSTRUMENT_COMPRESSOR_INPUT_GAIN:
			layout.add(std::make_unique<AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				NormalisableRange<float>(
					apvts::Ctagdrc::inputStart,
					apvts::Ctagdrc::inputEnd,
					apvts::Ctagdrc::inputInterval), 0.0f,
				String(),
				AudioProcessorParameter::genericParameter,
				[](float value, float)
				{
					return String(value, 1) + " dB";
				}));
			break;
		case apvts::ParameterEnum::INSTRUMENT_COMPRESSOR_MAKEUP_GAIN:
			layout.add(std::make_unique<AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				NormalisableRange<float>(
					apvts::Ctagdrc::makeupStart,
					apvts::Ctagdrc::makeupEnd,
					apvts::Ctagdrc::makeupInterval),
				apvts::Ctagdrc::makeupDefault,
				String(),
				AudioProcessorParameter::genericParameter,
				[](float value, float)
				{
					return String(value, 1) + " dB ";
				}));
			break;
		case apvts::ParameterEnum::INSTRUMENT_COMPRESSOR_THRESHOLD:
			layout.add(std::make_unique<AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				NormalisableRange<float>(
					apvts::Ctagdrc::thresholdStart,
					apvts::Ctagdrc::thresholdEnd,
					apvts::Ctagdrc::thresholdInterval),
				apvts::Ctagdrc::thresholdDefault,
				String(), AudioProcessorParameter::genericParameter,
				[](float value, float maxStrLen)
				{
					return String(value, 1) + " dB";
				}));
			break;
		case apvts::ParameterEnum::INSTRUMENT_COMPRESSOR_RATIO:
			layout.add(std::make_unique<AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				NormalisableRange<float>(
					apvts::Ctagdrc::ratioStart,
					apvts::Ctagdrc::ratioEnd,
					apvts::Ctagdrc::ratioInterval,
					0.5f),
				apvts::Ctagdrc::ratioDefault,
				String(), AudioProcessorParameter::genericParameter,
				[](float value, float)
				{
					if (value > 23.9f)return String("Infinity") + ":1";
					return String(value, 1) + ":1";
				}));
			break;
		case apvts::ParameterEnum::INSTRUMENT_COMPRESSOR_KNEE:
			layout.add(std::make_unique<AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				NormalisableRange<float>(
					apvts::Ctagdrc::kneeStart,
					apvts::Ctagdrc::kneeEnd,
					apvts::Ctagdrc::kneeInterval),
				6.0f, String(), AudioProcessorParameter::genericParameter,
				[](float value, float)
				{
					return String(value, 1) + " dB";
				}));
			break;
		case apvts::ParameterEnum::INSTRUMENT_COMPRESSOR_ATTACK:
			layout.add(std::make_unique<AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				NormalisableRange<float>(
					apvts::Ctagdrc::attackStart,
					apvts::Ctagdrc::attackEnd,
					apvts::Ctagdrc::attackInterval, 0.5f),
				apvts::Ctagdrc::attackDefault,
				"ms",
				AudioProcessorParameter::genericParameter,
				[](float value, float)
				{
					if (value == 100.0f) return String(value, 0) + " ms";
					return String(value, 2) + " ms";
				}));
			break;
		case apvts::ParameterEnum::INSTRUMENT_COMPRESSOR_RELEASE:
			layout.add(std::make_unique<AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				NormalisableRange<float>(
					apvts::Ctagdrc::releaseStart,
					apvts::Ctagdrc::releaseEnd,
					apvts::Ctagdrc::releaseInterval, 0.35f),
				apvts::Ctagdrc::releaseDefault,
				String(),
				AudioProcessorParameter::genericParameter,
				[](float value, float)
				{
					if (value <= 100) return String(value, 2) + " ms";
					if (value >= 1000)
						return String(value * 0.001f, 2) + " s";
					return String(value, 1) + " ms";
				}));
			break;
		case apvts::ParameterEnum::INSTRUMENT_COMPRESSOR_MIX:
			layout.add(std::make_unique<AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				NormalisableRange<float>(
					apvts::Ctagdrc::mixStart,
					apvts::Ctagdrc::mixEnd,
					apvts::Ctagdrc::mixInterval),
				1.0f, "%", AudioProcessorParameter::genericParameter,
				[](float value, float)
				{
					return String(value * 100.0f, 1) + " %";
				}));
			break;
		case apvts::ParameterEnum::BIT_CRUSHER_SAMPLE_RATE:
			layout.add(std::make_unique<juce::AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				Bitcrusher::sampleRateNormalisableRange,
				Bitcrusher::sampleRateDefaultValue
			));
			break;
		case apvts::ParameterEnum::BIT_CRUSHER_BIT_DEPTH:
			layout.add(std::make_unique<juce::AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				Bitcrusher::bitDepthNormalisableRange,
				Bitcrusher::bitDepthDefaultValue
			));
			break;
		case apvts::ParameterEnum::MOUSE_DRIVE_DISTORTION:        //初始值15
			layout.add(std::make_unique<juce::AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				MouseDrive::distortionNormalisableRange,
				dr_Distortion
			));
			break;
		case apvts::ParameterEnum::MOUSE_DRIVE_VOLUME:           //初始值16
			layout.add(std::make_unique<juce::AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				MouseDrive::volumeNormalisableRange,
				dr_Volume
			));
			break;
		case apvts::ParameterEnum::MOUSE_DRIVE_FILTER:
			layout.add(std::make_unique<juce::AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				MouseDrive::filterNormalisableRange,
				MouseDrive::filterDefaultValue
			));
			break;
		case apvts::ParameterEnum::FLANGER_DELAY:              //初始值17
			layout.add(std::make_unique<juce::AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				Flanger::delayNormalisableRange,
				f_Delay
			));
			break;
		case apvts::ParameterEnum::FLANGER_WIDTH:                //初始值18
			layout.add(std::make_unique<juce::AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				Flanger::widthNormalisableRange,
				f_Width
			));
			break;
		case apvts::ParameterEnum::FLANGER_DEPTH:                 //初始值19
			layout.add(std::make_unique<juce::AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				Flanger::depthNormalisableRange,
				f_Depth
			));
			break;
		case apvts::ParameterEnum::FLANGER_FEEDBACK:            //初始值20
			layout.add(std::make_unique<juce::AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				Flanger::feedbackNormalisableRange,
				f_Feedback
			));
			break;
		case apvts::ParameterEnum::FLANGER_FREQUENCY:              //初始值21
			layout.add(std::make_unique<juce::AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				Flanger::frequencyNormalisableRange,
				f_Frequency
			));
			break;
		case apvts::ParameterEnum::CABINET_IMPULSE_RESPONSE_INDEX:
			layout.add(std::make_unique<juce::AudioParameterFloat>(
				juce::ParameterID{ parameterId, apvts::version },
				PluginUtils::toTitleCase(parameterId),
				juce::NormalisableRange<float>(0, 1, 1),
				0
			));
			break;
		default:
			assert(false);
			break;
		}
	}

	return layout;
}







void PluginAudioProcessor::prepareToPlay(double sampleRate, int samplesPerBlock)
{
	juce::dsp::ProcessSpec spec;

	const auto numChannels = getTotalNumOutputChannels();

	spec.sampleRate = sampleRate;
	spec.maximumBlockSize = samplesPerBlock;
	spec.numChannels = numChannels;

	mAudioFifo->setSize(numChannels, samplesPerBlock * 4.0f);
	mAudioBuffer->setSize(numChannels, samplesPerBlock * 2.0f);

	mPitchMPM->setBufferSize(1024);
	mPitchMPM->setSampleRate(sampleRate);

	mInputLevelMeterSourcePtr->resize(getTotalNumOutputChannels(), sampleRate * 0.1 / samplesPerBlock);
	mOutputLevelMeterSourcePtr->resize(getTotalNumOutputChannels(), sampleRate * 0.1 / samplesPerBlock);

	mInputGainPtr->prepare(spec);

	mNoiseGate->prepare(spec);
	mPreCompressorPtr->prepare(spec);
	mPreCompressorGainPtr->prepare(spec);
	mPreCompressorDryWetMixerPtr->prepare(spec);

	mGraphicEqualiser->prepare(spec);

	mTubeScreamerPtr->prepare(spec);
	mMouseDrivePtr->prepare(spec);

	mStage1Buffer->setSize(numChannels, samplesPerBlock);
	mStage1InputGainPtr->prepare(spec);
	mStage1WaveShaperPtr->prepare(spec);
	mStage1OutputGainPtr->prepare(spec);
	mStage1DryWetMixerPtr->prepare(spec);

	mStage2Buffer->setSize(numChannels, samplesPerBlock);
	mStage2InputGainPtr->prepare(spec);
	mStage2WaveShaperPtr->prepare(spec);
	mStage2OutputGainPtr->prepare(spec);
	mStage2DryWetMixerPtr->prepare(spec);

	mStage3Buffer->setSize(numChannels, samplesPerBlock);
	mStage3InputGainPtr->prepare(spec);
	mStage3WaveShaperPtr->prepare(spec);
	mStage3OutputGainPtr->prepare(spec);
	mStage3DryWetMixerPtr->prepare(spec);

	mStage4Buffer->setSize(numChannels, samplesPerBlock);
	mStage4InputGainPtr->prepare(spec);
	mStage4WaveShaperPtr->prepare(spec);
	mStage4OutputGainPtr->prepare(spec);
	mStage4DryWetMixerPtr->prepare(spec);

	mBiasPtr->prepare(spec);
	mAmplifierEqualiser->prepare(spec);

	const auto maximumDelayInSamples = apvts::delayTimeMsMaximumValue * (spec.sampleRate / 1000);
	mDelayLineLeftPtr->setMaximumDelayInSamples(maximumDelayInSamples);
	mDelayLineLeftPtr->prepare(spec);
	mDelayLineRightPtr->setMaximumDelayInSamples(maximumDelayInSamples);
	mDelayLineRightPtr->prepare(spec);
	mDelayLineDryWetMixerPtr->prepare(spec);

	mDelayLowPassFilterPtr->prepare(spec);
	mDelayHighPassFilterPtr->prepare(spec);

	mChorusPtr->prepare(spec);
	mPhaserPtr->prepare(spec);
	mFlangerPtr->prepare(spec);
	mBitcrusherPtr->prepare(spec);

	mCabinetImpulseResponseConvolutionPtr->prepare(spec);
	mLofiImpulseResponseConvolutionPtr->prepare(spec);
	loadImpulseResponseFromState();

	mInstrumentEqualiserPtr->prepare(spec);
	mInstrumentCompressorPtr->prepare(spec);

	if (*mAudioProcessorValueTreeStatePtr->getRawParameterValue(apvts::instrumentCompressorIsLookaheadOn) > 0.5f)
	{
		setLatencySamples(static_cast<int>(0.005 * sampleRate));
	}
	else
	{
		setLatencySamples(0);
	}

	mReverbPtr->prepare(spec);

	mCabinetGainPtr->prepare(spec);
	mLimiterPtr->prepare(spec);

	mOutputGainPtr->prepare(spec);

	for (const auto& patameterIdToEnum : apvts::parameterIdToEnumMap)
	{
		float newValue = *mAudioProcessorValueTreeStatePtr->getRawParameterValue(patameterIdToEnum.first);
		parameterChanged(patameterIdToEnum.first, newValue);
	}
}

void PluginAudioProcessor::resetParametersToDefault()
{
	bool Compressor_on = readEnvWithType<bool>("Compressor_on");
	bool Driver_on = readEnvWithType<bool>("Driver_on");
	bool Screamer_on = readEnvWithType<bool>("Screamer_on");
	bool Delay_on = readEnvWithType<bool>("Delay_on");
	bool Reverb_on = readEnvWithType<bool>("Reverb_on");
	bool Chorus_on = readEnvWithType<bool>("Chorus_on");
	bool Flanger_on = readEnvWithType<bool>("Flanger_on");
	bool Phaser_on = readEnvWithType<bool>("Phaser_on");
	bool Equaliser_on = readEnvWithType<bool>("Equaliser_on");
	bool NoiseGate_on = readEnvWithType<bool>("NoiseGate_on");
	double co_Threshold = readEnvWithType<double>("co_Threshold");
	int co_Ratio = readEnvWithType<int>("co_Ratio");
	double co_Attack = readEnvWithType<double>("co_Attack");
	double co_Release = readEnvWithType<double>("co_Release");
	double co_Makeup = readEnvWithType<double>("co_Makeup");
	double co_Mix = readEnvWithType<double>("co_Mix");
	double dr_Distortion = readEnvWithType<double>("dr_Distortion");
	double dr_Volume = readEnvWithType<double>("dr_Volume");
	double s_Drive = readEnvWithType<double>("s_Drive");
	double s_Tone = readEnvWithType<double>("s_Tone");
	double s_Level = readEnvWithType<double>("s_Level");
	double de_Feedback = readEnvWithType<double>("de_Feedback");
	double de_Delay = readEnvWithType<double>("de_Delay");
	double de_Mix = readEnvWithType<double>("de_Mix");
	double r_Size = readEnvWithType<double>("r_Size");
	double r_Damping = readEnvWithType<double>("r_Damping");
	double r_Width = readEnvWithType<double>("r_Width");
	double r_Mix = readEnvWithType<double>("r_Mix");
	double ch_Delay = readEnvWithType<double>("ch_Delay");
	double ch_Depth = readEnvWithType<double>("ch_Depth");
	double ch_Frequency = readEnvWithType<double>("ch_Frequency");
	double ch_Width = readEnvWithType<double>("ch_Width");
	double f_Delay = readEnvWithType<double>("f_Delay");
	double f_Depth = readEnvWithType<double>("f_Depth");
	double f_Feedback = readEnvWithType<double>("f_Feedback");
	double f_Frequency = readEnvWithType<double>("f_Frequency");
	double f_Width = readEnvWithType<double>("f_Width");
	double p_Depth = readEnvWithType<double>("p_Depth");
	double p_Feedback = readEnvWithType<double>("p_Feedback");
	double p_Frequency = readEnvWithType<double>("p_Frequency");
	int p_Width = readEnvWithType<int>("p_Width");
	double e_1 = readEnvWithType<double>("e_1");
	double e_2 = readEnvWithType<double>("e_2");
	double e_4 = readEnvWithType<double>("e_4");
	double e_8 = readEnvWithType<double>("e_8");
	double e_16 = readEnvWithType<double>("e_16");
	double e_32 = readEnvWithType<double>("e_32");
	double e_64 = readEnvWithType<double>("e_64");
	double e_Level = readEnvWithType<double>("e_Level");
	//double p_NoiseGateThreshold = readEnvWithType<double>("p_NoiseGateThreshold");
	for (const auto& parameter : mAudioProcessorValueTreeStatePtr->state)
	{
		auto parameterId = parameter.getProperty("id").toString().toStdString();

		if (auto* param = mAudioProcessorValueTreeStatePtr->getParameter(parameterId))
		{
			parameterInitialValues["pre_compressor_on"] = Compressor_on; // 存储初始值
			parameterInitialValues["mouse_drive_on"] = Driver_on; // 存储初始值
			parameterInitialValues["tube_screamer_on"] = Screamer_on; // 存储初始值
			parameterInitialValues["delay_on"] = Delay_on; // 存储初始值
			parameterInitialValues["room_on"] = Reverb_on; // 存储初始值
			parameterInitialValues["chorus_on"] = Chorus_on; // 存储初始值
			parameterInitialValues["flanger_on"] = Flanger_on; // 存储初始值
			parameterInitialValues["phaser_on"] = Phaser_on; // 存储初始值
			parameterInitialValues["pre_eq_on"] = Equaliser_on;
			//parameterInitialValues["phaser_on"] = NoiseGate_on;
			parameterInitialValues["pre_comp_thresh"] = co_Threshold; // 存储初始值
			parameterInitialValues["pre_comp_ratio"] = co_Ratio; // 存储初始值
			parameterInitialValues["pre_comp_attack"] = co_Attack; // 存储初始值
			parameterInitialValues["pre_comp_release"] = co_Release; // 存储初始值
			parameterInitialValues["pre_comp_gain"] = co_Makeup; // 存储初始值
			parameterInitialValues["pre_comp_blend"] = co_Mix; // 存储初始值
			parameterInitialValues["mouse_drive_distortion"] = dr_Distortion; // 存储初始值
			parameterInitialValues["mouse_drive_volume"] = dr_Volume; // 存储初始值
			parameterInitialValues["tube_screamer_drive"] = s_Drive; // 存储初始值
			parameterInitialValues["tube_screamer_tone"] = s_Tone; // 存储初始值
			parameterInitialValues["tube_screamer_level"] = s_Level; // 存储初始值
			parameterInitialValues["delay_feedback"] = de_Feedback; // 存储初始值
			parameterInitialValues["delay_left_millisecond"] = de_Delay; // 存储初始值
			parameterInitialValues["delay_mix"] = de_Mix; // 存储初始值
			parameterInitialValues["room_size"] = r_Size; // 存储初始值
			parameterInitialValues["room_damping"] = r_Damping; // 存储初始值
			parameterInitialValues["room_width"] = r_Width;// 存储初始值
			parameterInitialValues["room_mix"] = r_Mix; // 存储初始值
			parameterInitialValues["chorus_delay"] = ch_Delay; // 存储初始值
			parameterInitialValues["chorus_depth"] = ch_Depth; // 存储初始值
			parameterInitialValues["chorus_feedback"] = ch_Frequency; // 存储初始值
			parameterInitialValues["chorus_width"] = ch_Width; // 存储初始值
			parameterInitialValues["flanger_delay"] = f_Delay; // 存储初始值
			parameterInitialValues["flanger_depth"] = f_Depth; // 存储初始值
			parameterInitialValues["flanger_feedback"] = f_Feedback; // 存储初始值
			parameterInitialValues["flanger_frequency"] = f_Frequency; // 存储初始值
			parameterInitialValues["flanger_width"] = f_Width; // 存储初始值
			parameterInitialValues["phaser_depth"] = p_Depth; // 存储初始值
			parameterInitialValues["phaser_feedback"] = p_Feedback; // 存储初始值
			parameterInitialValues["phaser_frequency"] = p_Frequency; // 存储初始值
			parameterInitialValues["phaser_width"] = p_Width; // 存储初始值
			parameterInitialValues["pre_eq_100_gain"] = e_1;
			parameterInitialValues["pre_eq_200_gain"] = e_2;
			parameterInitialValues["pre_eq_400_gain"] = e_4;
			parameterInitialValues["pre_eq_800_gain"] = e_8;
			parameterInitialValues["pre_eq_1600_gain"] = e_16;
			parameterInitialValues["pre_eq_3200_gain"] = e_32;
			parameterInitialValues["pre_eq_6400_gain"] = e_64;
			parameterInitialValues["pre_eq_level_gain"] = e_Level;
			
			
			if (parameterInitialValues.find(parameterId) != parameterInitialValues.end())
			{
				float initialValue = parameterInitialValues[parameterId];
				param->setValueNotifyingHost(param->convertTo0to1(initialValue));
			}
		}
	}
}




void PluginAudioProcessor::reset()
{
	mInputGainPtr->reset();

	mNoiseGate->reset();
	mPreCompressorPtr->reset();
	mPreCompressorGainPtr->reset();

	mPreCompressorDryWetMixerPtr->reset();

	mTubeScreamerPtr->reset();
	mMouseDrivePtr->reset();

	mStage1InputGainPtr->reset();
	mStage1WaveShaperPtr->reset();
	mStage1OutputGainPtr->reset();
	mStage1DryWetMixerPtr->reset();

	mStage2InputGainPtr->reset();
	mStage2WaveShaperPtr->reset();
	mStage2OutputGainPtr->reset();
	mStage2DryWetMixerPtr->reset();

	mStage3InputGainPtr->reset();
	mStage3WaveShaperPtr->reset();
	mStage3OutputGainPtr->reset();
	mStage3DryWetMixerPtr->reset();

	mStage4InputGainPtr->reset();
	mStage4WaveShaperPtr->reset();
	mStage4OutputGainPtr->reset();
	mStage4DryWetMixerPtr->reset();

	mBiasPtr->reset();
	mAmplifierEqualiser->reset();

	mDelayLineLeftPtr->reset();
	mDelayLineRightPtr->reset();
	mDelayLineDryWetMixerPtr->reset();
	mDelayLowPassFilterPtr->reset();
	mDelayHighPassFilterPtr->reset();

	mChorusPtr->reset();
	mPhaserPtr->reset();
	mFlangerPtr->reset();
	mBitcrusherPtr->reset();

	mCabinetImpulseResponseConvolutionPtr->reset();
	mLofiImpulseResponseConvolutionPtr->reset();
	mInstrumentEqualiserPtr->reset();
	//mInstrumentCompressor->reset();

	mReverbPtr->reset();

	mCabinetGainPtr->reset();

	mLimiterPtr->reset();

	mOutputGainPtr->reset();
}

void PluginAudioProcessor::processBlock(juce::AudioBuffer<float>& buffer, juce::MidiBuffer& midiMessages)
{
	// Prevent reentrant calls during offline rendering
	if (mIsProcessingOffline)
	{
		buffer.clear();
		return;
	}

	processShared(buffer, midiMessages);
}

void PluginAudioProcessor::processShared(juce::AudioBuffer<float>& buffer, juce::MidiBuffer& midiMessages)
{
	juce::ScopedNoDenormals noDenormals;
	const auto totalNumInputChannels = getTotalNumInputChannels();
	const auto totalNumOutputChannels = getTotalNumOutputChannels();
	const auto numSamples = buffer.getNumSamples();
	const double rawBeatsPerMinute = getPlayHead()->getPosition()->getBpm().orFallback(120);
	mBpmSmoothedValue.setTargetValue(rawBeatsPerMinute);




	if (mIsBypassOn)
	{
		return;
	}

	mInputLevelMeterSourcePtr->measureBlock(buffer);


	for (auto i = totalNumInputChannels; i < totalNumOutputChannels; ++i)
	{
		buffer.clear(i, 0, numSamples);
	}

	auto audioBlock = juce::dsp::AudioBlock<float>(buffer);
	auto processContext = juce::dsp::ProcessContextReplacing<float>(audioBlock);

	if (mTunerOn)
	{
		mAudioFifo->write(buffer);
		mAudioFifo->read(*mAudioBuffer);
		mPitchAtom = mPitchMPM->getPitch(mAudioBuffer->getReadPointer(0));
	}

	mNoiseGate->process(processContext);
	mInputGainPtr->process(processContext);

	if (mIsPreCompressorOn)
	{
		mPreCompressorDryWetMixerPtr->pushDrySamples(audioBlock);
		float preCompressorInputRms = mIsPreCompressorAutoMakeup ? buffer.getRMSLevel(0, 0, numSamples) : 0;
		mPreCompressorPtr->process(processContext);

		if (mIsPreCompressorAutoMakeup)
		{
			float preCompressorOutputRms = buffer.getRMSLevel(0, 0, numSamples);
			mPreCompressorGainSmoothedValue.setTargetValue(std::min(preCompressorInputRms / preCompressorOutputRms, 12.0f));

			for (int sample = 0; sample < numSamples; ++sample)
			{
				float preCompressorGainSmoothedNextValue = mPreCompressorGainSmoothedValue.getNextValue();

				for (int channel = 0; channel < totalNumInputChannels; ++channel)
				{
					auto* channelData = buffer.getWritePointer(channel);
					channelData[sample] *= preCompressorGainSmoothedNextValue;
				}
			}
		}

		mPreCompressorGainPtr->process(processContext);
		mPreCompressorDryWetMixerPtr->mixWetSamples(audioBlock);
	}

	if (mIsGraphicEqualiserOn)
	{
		mGraphicEqualiser->processBlock(buffer);
	}

	if (mIsTubeScreamerOn)
	{
		mTubeScreamerPtr->processBlock(buffer);
	}

	if (mIsMouseDriveOn)
	{
		mMouseDrivePtr->processBlock(buffer);
	}

	if (mIsStage1On)
	{
		mStage1DryWetMixerPtr->pushDrySamples(audioBlock);
		mStage1InputGainPtr->process(processContext);
		mStage1WaveShaperPtr->process(processContext);
		mStage1OutputGainPtr->process(processContext);
		mStage1DryWetMixerPtr->mixWetSamples(audioBlock);
	}

	if (mIsStage2On)
	{
		mStage2DryWetMixerPtr->pushDrySamples(audioBlock);
		mStage2InputGainPtr->process(processContext);
		mStage2WaveShaperPtr->process(processContext);
		mStage2OutputGainPtr->process(processContext);
		mStage2DryWetMixerPtr->mixWetSamples(audioBlock);
	}

	if (mIsStage3On)
	{
		mStage3DryWetMixerPtr->pushDrySamples(audioBlock);
		mStage3InputGainPtr->process(processContext);
		mStage3WaveShaperPtr->process(processContext);
		mStage3OutputGainPtr->process(processContext);
		mStage3DryWetMixerPtr->mixWetSamples(audioBlock);
	}

	if (mIsStage4On)
	{
		mStage4DryWetMixerPtr->pushDrySamples(audioBlock);
		mStage4InputGainPtr->process(processContext);
		mStage4WaveShaperPtr->process(processContext);
		mStage4OutputGainPtr->process(processContext);
		mStage4DryWetMixerPtr->mixWetSamples(audioBlock);
	}

	mAmplifierEqualiser->processBlock(buffer);
	mBiasPtr->process(processContext);

	if (mDelayFeedback > 0.0f && mIsDelayOn)
	{
		mDelayLineDryWetMixerPtr->pushDrySamples(audioBlock);

		auto* leftChannelData = audioBlock.getChannelPointer(0);
		if (leftChannelData)
		{
			for (int sampleIndex = 0; sampleIndex < numSamples; ++sampleIndex)
			{
				const float delayedSample = mDelayLineLeftPtr->popSample(0, mDelayLineLeftPtr->getDelay());

				if (sampleIndex < audioBlock.getNumSamples())
				{
					mDelayLineLeftPtr->pushSample(0, leftChannelData[sampleIndex] + mDelayFeedback * delayedSample);
					leftChannelData[sampleIndex] += delayedSample;
				}
			}
		}

		auto* rightChannelData = audioBlock.getChannelPointer(1);
		if (rightChannelData)
		{
			for (int sampleIndex = 0; sampleIndex < numSamples; ++sampleIndex)
			{
				const float delayedSample = mDelayLineRightPtr->popSample(0, mDelayLineRightPtr->getDelay());

				if (sampleIndex < audioBlock.getNumSamples())
				{
					mDelayLineRightPtr->pushSample(0, rightChannelData[sampleIndex] + mDelayFeedback * delayedSample);
					rightChannelData[sampleIndex] += delayedSample;
				}
			}
		}

		juce::dsp::ProcessContextReplacing<float> wetContext(audioBlock);

		mDelayLowPassFilterPtr->process(wetContext);
		mDelayHighPassFilterPtr->process(wetContext);
		mDelayLineDryWetMixerPtr->mixWetSamples(audioBlock);
	}

	mChorusPtr->process(buffer);
	mPhaserPtr->process(buffer);
	mFlangerPtr->process(buffer);
	mBitcrusherPtr->process(buffer);

	if (mIsReverbOn)
	{
		mReverbPtr->process(processContext);
	}

	if (mIsCabImpulseResponseConvolutionOn)
	{
		mCabinetImpulseResponseConvolutionPtr->process(processContext);
		mCabinetGainPtr->process(processContext);
	}

	if (mIsInstrumentCompressorPreEqualiser)
	{
		mInstrumentCompressorPtr->process(buffer);
	}

	mInstrumentEqualiserPtr->processBlock(buffer);

	if (!mIsInstrumentCompressorPreEqualiser)
	{
		mInstrumentCompressorPtr->process(buffer);
	}

	if (mIsLimiterOn)
	{
		mLimiterPtr->process(processContext);
	}

	if (mIsLofi)
	{
		mLofiImpulseResponseConvolutionPtr->process(processContext);
	}

	mOutputGainPtr->process(processContext);

	mOutputLevelMeterSourcePtr->measureBlock(buffer);

#ifdef JUCE_DEBUG
	PluginUtils::checkForInvalidSamples(audioBlock);
#endif
}


void PluginAudioProcessor::parameterChanged(const juce::String& parameterIdJuceString, float newValue)
{
	auto sampleRate = getSampleRate();
	auto playhead = this->getPlayHead();
	double beatsPerMinute = 120; // Default fallback BPM

	if (playhead != nullptr) // Check if playhead is valid
	{
		juce::AudioPlayHead::CurrentPositionInfo positionInfo;

		if (playhead->getCurrentPosition(positionInfo)) // Check if position info is valid
		{
			beatsPerMinute = positionInfo.bpm; // Use actual BPM if available
		}
	}

	switch (apvts::parameterIdToEnumMap.at(parameterIdJuceString.toStdString()))
	{
	case apvts::ParameterEnum::INPUT_GAIN:
		mInputGainPtr->setGainDecibels(newValue);
		break;
	case apvts::ParameterEnum::REVERB_ON:
		mIsReverbOn = static_cast<bool>(newValue);
		break;
	case apvts::ParameterEnum::LIMITER_ON:
		mIsLimiterOn = static_cast<bool>(newValue);
		break;
	case apvts::ParameterEnum::BYPASS_ON:
		mIsBypassOn = static_cast<bool>(newValue);
		break;
	case apvts::ParameterEnum::STAGE1_ON:
		mIsStage1On = static_cast<bool>(newValue);
		break;
	case apvts::ParameterEnum::STAGE2_ON:
		mIsStage2On = static_cast<bool>(newValue);
		break;
	case apvts::ParameterEnum::STAGE3_ON:
		mIsStage3On = static_cast<bool>(newValue);
		break;
	case apvts::ParameterEnum::STAGE4_ON:
		mIsStage4On = static_cast<bool>(newValue);
		break;
	case apvts::ParameterEnum::PRE_EQUALISER_ON:
		mIsGraphicEqualiserOn = static_cast<bool>(newValue);
		break;
	case apvts::ParameterEnum::PRE_COMPRESSOR_AUTO_MAKE_UP_ON:
		mIsPreCompressorAutoMakeup = static_cast<bool>(newValue);
		break;
	case apvts::ParameterEnum::PRE_EQUALISER_100_GAIN:
		mGraphicEqualiser->setGainDecibelsAtIndex(newValue, 0);
		break;
	case apvts::ParameterEnum::PRE_EQUALISER_200_GAIN:
		mGraphicEqualiser->setGainDecibelsAtIndex(newValue, 1);
		break;
	case apvts::ParameterEnum::PRE_EQUALISER_400_GAIN:
		mGraphicEqualiser->setGainDecibelsAtIndex(newValue, 2);
		break;
	case apvts::ParameterEnum::PRE_EQUALISER_800_GAIN:
		mGraphicEqualiser->setGainDecibelsAtIndex(newValue, 3);
		break;
	case apvts::ParameterEnum::PRE_EQUALISER_1600_GAIN:
		mGraphicEqualiser->setGainDecibelsAtIndex(newValue, 4);
		break;
	case apvts::ParameterEnum::PRE_EQUALISER_3200_GAIN:
		mGraphicEqualiser->setGainDecibelsAtIndex(newValue, 5);
		break;
	case apvts::ParameterEnum::PRE_EQUALISER_6400_GAIN:
		mGraphicEqualiser->setGainDecibelsAtIndex(newValue, 6);
		break;
	case apvts::ParameterEnum::PRE_EQUALISER_LEVEL_GAIN:
		mGraphicEqualiser->setGainDecibelsAtIndex(newValue, 7);
		break;
	case apvts::ParameterEnum::AMP_RESONANCE_DB:
		mAmplifierEqualiser->setResonanceDecibels(newValue);
		break;
	case apvts::ParameterEnum::AMP_BASS_DB:
		mAmplifierEqualiser->setBassDecibels(newValue);
		break;
	case apvts::ParameterEnum::AMP_MIDDLE_DB:
		mAmplifierEqualiser->setMiddleDecibels(newValue);
		break;
	case apvts::ParameterEnum::AMP_TREBLE_DB:
		mAmplifierEqualiser->setTrebleDecibels(newValue);
		break;
	case apvts::ParameterEnum::AMP_PRESENCE_DB:
		mAmplifierEqualiser->setPresenceDecibels(newValue);
		break;
	case apvts::ParameterEnum::PRE_COMPRESSOR_IS_ON:
		mIsPreCompressorOn = static_cast<bool>(newValue);
		break;
	case apvts::ParameterEnum::STAGE1_INPUT_GAIN:
		mStage1InputGainPtr->setGainDecibels(newValue);
		break;
	case apvts::ParameterEnum::STAGE2_INPUT_GAIN:
		mStage2InputGainPtr->setGainDecibels(newValue);
		break;
	case apvts::ParameterEnum::STAGE3_INPUT_GAIN:
		mStage3InputGainPtr->setGainDecibels(newValue);
		break;
	case apvts::ParameterEnum::STAGE4_INPUT_GAIN:
		mStage4InputGainPtr->setGainDecibels(newValue);
		break;
	case apvts::ParameterEnum::STAGE1_WAVE_SHAPER:
		mStage1WaveShaperPtr->functionToUse = apvts::waveShaperIdToFunctionMap.at(apvts::waveShaperIds.at(newValue));
		break;
	case apvts::ParameterEnum::STAGE2_WAVE_SHAPER:
		mStage2WaveShaperPtr->functionToUse = apvts::waveShaperIdToFunctionMap.at(apvts::waveShaperIds.at(newValue));
		break;
	case apvts::ParameterEnum::STAGE3_WAVE_SHAPER:
		mStage3WaveShaperPtr->functionToUse = apvts::waveShaperIdToFunctionMap.at(apvts::waveShaperIds.at(newValue));
		break;
	case apvts::ParameterEnum::STAGE4_WAVE_SHAPER:
		mStage4WaveShaperPtr->functionToUse = apvts::waveShaperIdToFunctionMap.at(apvts::waveShaperIds.at(newValue));
		break;
	case apvts::ParameterEnum::STAGE1_OUTPUT_GAIN:
		mStage1OutputGainPtr->setGainDecibels(newValue);
		break;
	case apvts::ParameterEnum::STAGE2_OUTPUT_GAIN:
		mStage2OutputGainPtr->setGainDecibels(newValue);
		break;
	case apvts::ParameterEnum::STAGE3_OUTPUT_GAIN:
		mStage3OutputGainPtr->setGainDecibels(newValue);
		break;
	case apvts::ParameterEnum::STAGE4_OUTPUT_GAIN:
		mStage4OutputGainPtr->setGainDecibels(newValue);
		break;
	case apvts::ParameterEnum::STAGE1_DRY_WET_MIX:
		mStage1DryWetMixerPtr->setWetMixProportion(newValue);
		break;
	case apvts::ParameterEnum::STAGE2_DRY_WET_MIX:
		mStage2DryWetMixerPtr->setWetMixProportion(newValue);
		break;
	case apvts::ParameterEnum::STAGE3_DRY_WET_MIX:
		mStage3DryWetMixerPtr->setWetMixProportion(newValue);
		break;
	case apvts::ParameterEnum::STAGE4_DRY_WET_MIX:
		mStage4DryWetMixerPtr->setWetMixProportion(newValue);
		break;
	case apvts::ParameterEnum::BIAS:
		mBiasPtr->setBias(newValue);
		break;
	case apvts::ParameterEnum::PRE_COMPRESSOR_THRESHOLD:
		mPreCompressorPtr->setThreshold(newValue);
		break;
	case apvts::ParameterEnum::PRE_COMPRESSOR_ATTACK:
		mPreCompressorPtr->setAttack(newValue);
		break;
	case apvts::ParameterEnum::PRE_COMPRESSOR_RATIO:
		mPreCompressorPtr->setRatio(newValue);
		break;
	case apvts::ParameterEnum::PRE_COMPRESSOR_RELEASE:
		mPreCompressorPtr->setRelease(newValue);
		break;
	case apvts::ParameterEnum::PRE_COMPRESSOR_GAIN:
		mPreCompressorGainPtr->setGainDecibels(newValue);
		break;
	case apvts::ParameterEnum::PRE_COMPRESSOR_DRY_WET_MIX:
		mPreCompressorDryWetMixerPtr->setWetMixProportion(newValue);
		break;
	case apvts::ParameterEnum::CABINET_IMPULSE_RESPONSE_CONVOLUTION_ON:
		mIsCabImpulseResponseConvolutionOn = static_cast<bool>(newValue);
		break;
	case apvts::ParameterEnum::CABINET_OUTPUT_GAIN:
		mCabinetGainPtr->setGainDecibels(newValue);
		break;
	case apvts::ParameterEnum::LIMITER_RELEASE:
		mLimiterPtr->setRelease(newValue);
		break;
	case apvts::ParameterEnum::LIMITER_THRESHOLD:
		mLimiterPtr->setThreshold(newValue);
		break;
	case apvts::ParameterEnum::CHORUS_DEPTH:
		mChorusPtr->setDepth(newValue);
		break;
	case apvts::ParameterEnum::CHORUS_DELAY:
		mChorusPtr->setDelay(newValue);
		break;
	case apvts::ParameterEnum::CHORUS_WIDTH:
		mChorusPtr->setWidth(newValue);
		break;
	case apvts::ParameterEnum::CHORUS_FREQUENCY:
		mChorusPtr->setFrequency(newValue);
		break;
	case apvts::ParameterEnum::PHASER_DEPTH:
		mPhaserPtr->setDepth(newValue);
		break;
	case apvts::ParameterEnum::PHASER_FREQUENCY:
		mPhaserPtr->setFrequency(newValue);
		break;
	case apvts::ParameterEnum::PHASER_FEEDBACK:
		mPhaserPtr->setFeedback(newValue);
		break;
	case apvts::ParameterEnum::PHASER_WIDTH:
		mPhaserPtr->setWidth(newValue);
		break;
	case apvts::ParameterEnum::REVERB_SIZE:
	{
		const auto& parameters = mReverbPtr->getParameters();
		mReverbPtr->setParameters({ newValue, parameters.damping, parameters.wetLevel, parameters.dryLevel, parameters.width, 0.0f });
	}
	break;
	case apvts::ParameterEnum::REVERB_DAMPING:
	{
		const auto& parameters = mReverbPtr->getParameters();
		mReverbPtr->setParameters({ parameters.roomSize, newValue, parameters.wetLevel, parameters.dryLevel, parameters.width, 0.0f });
	}
	break;
	case apvts::ParameterEnum::REVERB_MIX:
	{
		const auto& parameters = mReverbPtr->getParameters();
		mReverbPtr->setParameters({ parameters.roomSize, parameters.damping, newValue, 1.0f - newValue, parameters.width, 0.0f });
	}
	break;
	case apvts::ParameterEnum::REVERB_WIDTH:
	{
		const auto& parameters = mReverbPtr->getParameters();
		mReverbPtr->setParameters({ parameters.roomSize, parameters.damping, parameters.wetLevel, parameters.dryLevel, newValue, 0.0f });
	}
	break;
	case apvts::ParameterEnum::DELAY_DRY_WET:
		mDelayLineDryWetMixerPtr->setWetMixProportion(newValue);
		break;
	case apvts::ParameterEnum::DELAY_FEEDBACK:
		mDelayFeedback = newValue;
		break;
	case apvts::ParameterEnum::DELAY_LOW_PASS_FREQUENCY:
		*mDelayLowPassFilterPtr->state = *juce::dsp::IIR::Coefficients<float>::makeLowPass(sampleRate, std::max(newValue, apvts::defaultEpsilon), 0.7);
		break;
	case apvts::ParameterEnum::DELAY_HIGH_PASS_FREQUENCY:
		*mDelayHighPassFilterPtr->state = *juce::dsp::IIR::Coefficients<float>::makeHighPass(sampleRate, std::max(newValue, apvts::defaultEpsilon), 0.7);
		break;
	case apvts::ParameterEnum::DELAY_LEFT_MS:
		mDelayLeftMilliseconds = newValue;
		mDelayLineLeftPtr->setDelay(PluginUtils::calculateSamplesForMilliseconds(sampleRate, newValue));
		break;
	case apvts::ParameterEnum::DELAY_RIGHT_MS:
		mDelayRightMilliseconds = newValue;
		mDelayLineRightPtr->setDelay(PluginUtils::calculateSamplesForMilliseconds(sampleRate, newValue));
		break;
	case apvts::ParameterEnum::DELAY_LEFT_PER_BEAT:
		mDelayLeftPerBeatDivision = newValue;
		mDelayLineLeftPtr->setDelay(PluginUtils::calculateSamplesForBpmFractionAndRate(beatsPerMinute, newValue, sampleRate));
		break;
	case apvts::ParameterEnum::DELAY_RIGHT_PER_BEAT:
		mDelayRightPerBeatDivision = newValue;
		mDelayLineRightPtr->setDelay(PluginUtils::calculateSamplesForBpmFractionAndRate(beatsPerMinute, newValue, sampleRate));
		break;
	case apvts::ParameterEnum::DELAY_IS_SYNCED:
		mDelayBpmSynced = newValue;
		if (mDelayBpmSynced)
		{
			mDelayLineLeftPtr->setDelay(PluginUtils::calculateSamplesForBpmFractionAndRate(beatsPerMinute, mDelayLeftPerBeatDivision, sampleRate));
			mDelayLineRightPtr->setDelay(PluginUtils::calculateSamplesForBpmFractionAndRate(beatsPerMinute, mDelayRightPerBeatDivision, sampleRate));
		}
		else
		{
			mDelayLineLeftPtr->setDelay(PluginUtils::calculateSamplesForMilliseconds(sampleRate, mDelayLeftMilliseconds));
			mDelayLineRightPtr->setDelay(PluginUtils::calculateSamplesForMilliseconds(sampleRate, mDelayRightMilliseconds));
		}
		break;
	case apvts::ParameterEnum::NOISE_GATE_THRESHOLD:
		mNoiseGate->setThreshold(newValue);
		break;
	case apvts::ParameterEnum::NOISE_GATE_ATTACK:
		mNoiseGate->setAttack(newValue);
		break;
	case apvts::ParameterEnum::NOISE_GATE_RATIO:
		mNoiseGate->setRatio(newValue);
		break;
	case apvts::ParameterEnum::NOISE_GATE_RELEASE:
		mNoiseGate->setRelease(newValue);
		break;
	case apvts::ParameterEnum::MOUSE_DRIVE_DISTORTION:
		mMouseDrivePtr->setDistortion(newValue);
		break;
	case apvts::ParameterEnum::MOUSE_DRIVE_FILTER:
		mMouseDrivePtr->setFilter(newValue);
		break;
	case apvts::ParameterEnum::MOUSE_DRIVE_VOLUME:
		mMouseDrivePtr->setVolume(newValue);
		break;
	case apvts::ParameterEnum::MOUSE_DRIVE_ON:
		mIsMouseDriveOn = static_cast<bool>(newValue);
		break;
	case apvts::ParameterEnum::TUBE_SCREAMER_ON:
		mIsTubeScreamerOn = static_cast<bool>(newValue);
		break;
	case apvts::ParameterEnum::TUBE_SCREAMER_DRIVE:
		mTubeScreamerPtr->setDrive(newValue);
		break;
	case apvts::ParameterEnum::TUBE_SCREAMER_LEVEL:
		mTubeScreamerPtr->setLevel(newValue);
		break;
	case apvts::ParameterEnum::TUBE_SCREAMER_TONE:
		mTubeScreamerPtr->setTone(newValue);
		break;
	case apvts::ParameterEnum::TUBE_SCREAMER_DIODE_TYPE:
		mTubeScreamerPtr->setDiodeType(newValue);
		break;
	case apvts::ParameterEnum::TUBE_SCREAMER_DIODE_COUNT:
		mTubeScreamerPtr->setDiodeCount(newValue);
		break;
	case apvts::ParameterEnum::OUTPUT_GAIN:
		mOutputGainPtr->setGainDecibels(newValue);
		break;
	case apvts::ParameterEnum::DELAY_ON:
		mIsDelayOn = static_cast<bool>(newValue);
		break;
	case apvts::ParameterEnum::PHASER_IS_ON:
		mPhaserPtr->setBypassed(!static_cast<bool>(newValue));
		break;
	case apvts::ParameterEnum::CHORUS_ON:
		mChorusPtr->setBypassed(!static_cast<bool>(newValue));
		break;
	case apvts::ParameterEnum::INSTRUMENT_EQUALISER_HIGH_PASS_ON:
		mInstrumentEqualiserPtr->setOnAtIndex(static_cast<bool>(newValue), 0);
		break;
	case apvts::ParameterEnum::INSTRUMENT_EQUALISER_HIGH_PASS_FREQUENCY:
		mInstrumentEqualiserPtr->setFrequencyAtIndex(newValue, 0);
		break;
	case apvts::ParameterEnum::INSTRUMENT_EQUALISER_HIGH_PASS_QUALITY:
		mInstrumentEqualiserPtr->setQualityAtIndex(newValue, 0);
		break;
	case apvts::ParameterEnum::INSTRUMENT_EQUALISER_LOW_PEAK_ON:
		mInstrumentEqualiserPtr->setOnAtIndex(static_cast<bool>(newValue), 1);
		break;
	case apvts::ParameterEnum::INSTRUMENT_EQUALISER_LOW_PEAK_FREQUENCY:
		mInstrumentEqualiserPtr->setFrequencyAtIndex(newValue, 1);
		break;
	case apvts::ParameterEnum::INSTRUMENT_EQUALISER_LOW_PEAK_GAIN:
		mInstrumentEqualiserPtr->setGainAtIndex(newValue, 1);
		break;
	case apvts::ParameterEnum::INSTRUMENT_EQUALISER_LOW_PEAK_QUALITY:
		mInstrumentEqualiserPtr->setQualityAtIndex(newValue, 1);
		break;
	case apvts::ParameterEnum::INSTRUMENT_EQUALISER_LOW_MID_PEAK_ON:
		mInstrumentEqualiserPtr->setOnAtIndex(static_cast<bool>(newValue), 2);
		break;
	case apvts::ParameterEnum::INSTRUMENT_EQUALISER_LOW_MID_PEAK_FREQUENCY:
		mInstrumentEqualiserPtr->setFrequencyAtIndex(newValue, 2);
		break;
	case apvts::ParameterEnum::INSTRUMENT_EQUALISER_LOW_MID_PEAK_GAIN:
		mInstrumentEqualiserPtr->setGainAtIndex(newValue, 2);
		break;
	case apvts::ParameterEnum::INSTRUMENT_EQUALISER_LOW_MID_PEAK_QUALITY:
		mInstrumentEqualiserPtr->setQualityAtIndex(newValue, 2);
		break;
	case apvts::ParameterEnum::INSTRUMENT_EQUALISER_HIGH_MID_PEAK_ON:
		mInstrumentEqualiserPtr->setOnAtIndex(static_cast<bool>(newValue), 3);
		break;
	case apvts::ParameterEnum::INSTRUMENT_EQUALISER_HIGH_MID_PEAK_FREQUENCY:
		mInstrumentEqualiserPtr->setFrequencyAtIndex(newValue, 3);
		break;
	case apvts::ParameterEnum::INSTRUMENT_EQUALISER_HIGH_MID_PEAK_GAIN:
		mInstrumentEqualiserPtr->setGainAtIndex(newValue, 3);
		break;
	case apvts::ParameterEnum::INSTRUMENT_EQUALISER_HIGH_MID_PEAK_QUALITY:
		mInstrumentEqualiserPtr->setQualityAtIndex(newValue, 3);
		break;
	case apvts::ParameterEnum::INSTRUMENT_EQUALISER_HIGH_PEAK_ON:
		mInstrumentEqualiserPtr->setOnAtIndex(static_cast<bool>(newValue), 4);
		break;
	case apvts::ParameterEnum::INSTRUMENT_EQUALISER_HIGH_PEAK_FREQUENCY:
		mInstrumentEqualiserPtr->setFrequencyAtIndex(newValue, 4);
		break;
	case apvts::ParameterEnum::INSTRUMENT_EQUALISER_HIGH_PEAK_GAIN:
		mInstrumentEqualiserPtr->setGainAtIndex(newValue, 4);
		break;
	case apvts::ParameterEnum::INSTRUMENT_EQUALISER_HIGH_PEAK_QUALITY:
		mInstrumentEqualiserPtr->setQualityAtIndex(newValue, 4);
		break;
	case apvts::ParameterEnum::INSTRUMENT_EQUALISER_LOW_PASS_ON:
		mInstrumentEqualiserPtr->setOnAtIndex(static_cast<bool>(newValue), 5);
		break;
	case apvts::ParameterEnum::INSTRUMENT_EQUALISER_LOW_PASS_FREQUENCY:
		mInstrumentEqualiserPtr->setFrequencyAtIndex(newValue, 5);
		break;
	case apvts::ParameterEnum::INSTRUMENT_EQUALISER_LOW_PASS_QUALITY:
		mInstrumentEqualiserPtr->setQualityAtIndex(newValue, 5);
		break;
	case apvts::ParameterEnum::INSTRUMENT_COMPRESSOR_IS_PRE_EQ_ON:
		mIsInstrumentCompressorPreEqualiser = static_cast<bool>(newValue);
		break;
	case apvts::ParameterEnum::INSTRUMENT_COMPRESSOR_IS_ON:
		mInstrumentCompressorPtr->setPower(!static_cast<bool>(newValue));
		break;
	case apvts::ParameterEnum::INSTRUMENT_COMPRESSOR_LOOKAHEAD_ON:
	{
		const bool newBool = static_cast<bool>(newValue);
		if (newBool)
		{
			setLatencySamples(static_cast<int>(0.005 * mInstrumentCompressorPtr->getSampleRate()));
		}
		else
		{
			setLatencySamples(0);
		}

		mInstrumentCompressorPtr->setLookahead(newBool);
	}
	break;
	case apvts::ParameterEnum::DELAY_LINKED:
		mDelayIsLinked = static_cast<bool>(newValue);

		if (mDelayIsLinked)
		{
			if (mDelayBpmSynced)
			{
				mDelayLineLeftPtr->setDelay(PluginUtils::calculateSamplesForBpmFractionAndRate(beatsPerMinute, mDelayLeftPerBeatDivision, sampleRate));
				mDelayLineRightPtr->setDelay(PluginUtils::calculateSamplesForBpmFractionAndRate(beatsPerMinute, mDelayLeftPerBeatDivision, sampleRate));
			}
			else
			{
				mDelayLineLeftPtr->setDelay(PluginUtils::calculateSamplesForMilliseconds(sampleRate, mDelayLeftMilliseconds));
				mDelayLineRightPtr->setDelay(PluginUtils::calculateSamplesForMilliseconds(sampleRate, mDelayLeftMilliseconds));
			}
		}
		else
		{
			if (mDelayBpmSynced)
			{
				mDelayLineLeftPtr->setDelay(PluginUtils::calculateSamplesForBpmFractionAndRate(beatsPerMinute, mDelayLeftPerBeatDivision, sampleRate));
				mDelayLineRightPtr->setDelay(PluginUtils::calculateSamplesForBpmFractionAndRate(beatsPerMinute, mDelayRightPerBeatDivision, sampleRate));
			}
			else
			{
				mDelayLineLeftPtr->setDelay(PluginUtils::calculateSamplesForMilliseconds(sampleRate, mDelayLeftMilliseconds));
				mDelayLineRightPtr->setDelay(PluginUtils::calculateSamplesForMilliseconds(sampleRate, mDelayRightMilliseconds));
			}
		}

		break;
	case apvts::ParameterEnum::INSTRUMENT_COMPRESSOR_AUTO_GAIN_ON:
		mInstrumentCompressorPtr->setAutoMakeup(static_cast<bool>(newValue));
		break;
	case apvts::ParameterEnum::INSTRUMENT_COMPRESSOR_AUTO_ATTACK_ON:
	{
		const bool newBool = static_cast<bool>(newValue);
		mInstrumentCompressorPtr->setAutoAttack(newBool);

		if (!newBool)
		{
			mInstrumentCompressorPtr->setAttack(*mAudioProcessorValueTreeStatePtr->getRawParameterValue(apvts::instrumentCompressorAttack));
		}
	}
	break;
	case apvts::ParameterEnum::INSTRUMENT_COMPRESSOR_AUTO_RELEASE_ON:
	{
		const bool newBool = static_cast<bool>(newValue);
		mInstrumentCompressorPtr->setAutoRelease(newBool);
		if (!newBool)
		{
			mInstrumentCompressorPtr->setRelease(*mAudioProcessorValueTreeStatePtr->getRawParameterValue(apvts::instrumentCompressorRelease));
		}
	}
	break;
	case apvts::ParameterEnum::INSTRUMENT_COMPRESSOR_INPUT_GAIN:
		mInstrumentCompressorPtr->setInput(newValue);
		break;
	case apvts::ParameterEnum::INSTRUMENT_COMPRESSOR_MAKEUP_GAIN:
		mInstrumentCompressorPtr->setMakeup(newValue);
		break;
	case apvts::ParameterEnum::INSTRUMENT_COMPRESSOR_THRESHOLD:
		mInstrumentCompressorPtr->setThreshold(newValue);
		break;
	case apvts::ParameterEnum::INSTRUMENT_COMPRESSOR_RATIO:
		mInstrumentCompressorPtr->setRatio(newValue);
		break;
	case apvts::ParameterEnum::INSTRUMENT_COMPRESSOR_KNEE:
		mInstrumentCompressorPtr->setKnee(newValue);
		break;
	case apvts::ParameterEnum::INSTRUMENT_COMPRESSOR_ATTACK:
		mInstrumentCompressorPtr->setAttack(newValue);
		break;
	case apvts::ParameterEnum::INSTRUMENT_COMPRESSOR_RELEASE:
		mInstrumentCompressorPtr->setRelease(newValue);
		break;
	case apvts::ParameterEnum::INSTRUMENT_COMPRESSOR_MIX:
		mInstrumentCompressorPtr->setMix(newValue);
		break;
	case apvts::ParameterEnum::BIT_CRUSHER_ON:
		mBitcrusherPtr->setIsBypassed(!newValue);
		break;
	case apvts::ParameterEnum::BIT_CRUSHER_SAMPLE_RATE:
		mBitcrusherPtr->setTargetSampleRate(newValue);
		break;
	case apvts::ParameterEnum::BIT_CRUSHER_BIT_DEPTH:
		mBitcrusherPtr->setBitDepth(newValue);
		break;
	case apvts::ParameterEnum::FLANGER_ON:
		mFlangerPtr->setBypassed(!static_cast<bool>(newValue));
		break;
	case apvts::ParameterEnum::FLANGER_DELAY:
		mFlangerPtr->setDelay(newValue);
		break;
	case apvts::ParameterEnum::FLANGER_WIDTH:
		mFlangerPtr->setWidth(newValue);
		break;
	case apvts::ParameterEnum::FLANGER_DEPTH:
		mFlangerPtr->setDepth(newValue);
		break;
	case apvts::ParameterEnum::FLANGER_FEEDBACK:
		mFlangerPtr->setFeedback(newValue);
		break;
	case apvts::ParameterEnum::FLANGER_FREQUENCY:
		mFlangerPtr->setFrequency(newValue);
		break;
	case apvts::ParameterEnum::IS_LOFI:
		mIsLofi = static_cast<bool>(newValue);
		break;
	case apvts::ParameterEnum::CABINET_IMPULSE_RESPONSE_INDEX:
		mCabinetImpulseResponseIndex = newValue;
		loadImpulseResponseFromState();
		break;
	case apvts::ParameterEnum::TUNER_ON:
		mTunerOn = static_cast<bool>(newValue);
		break;
	default:
		assert(false);
	}
}

void PluginAudioProcessor::valueTreePropertyChanged(juce::ValueTree& treeWhosePropertyHasChanged, const juce::Identifier& property)
{
	if (property == juce::Identifier(apvts::impulseResponseFileFullPathNameId))
	{
		loadImpulseResponseFromState();
	}
}

void PluginAudioProcessor::loadImpulseResponseFromState()
{
	const auto impulseResponseFullPathName = mAudioProcessorValueTreeStatePtr->state.getProperty(
		juce::String(apvts::impulseResponseFileFullPathNameId),
		juce::String()).toString();
	juce::File* impulseResponseFile = new juce::File(impulseResponseFullPathName);

	if (impulseResponseFullPathName.length() > 0)
	{
		mCabinetImpulseResponseConvolutionPtr->loadImpulseResponse(
			*impulseResponseFile,
			juce::dsp::Convolution::Stereo::yes,
			juce::dsp::Convolution::Trim::no, 0,
			juce::dsp::Convolution::Normalise::yes
		);
	}
	else
	{
		switch (mCabinetImpulseResponseIndex)
		{
		case 0:
			mCabinetImpulseResponseConvolutionPtr->loadImpulseResponse(
				BinaryData::default_cab_wav,
				BinaryData::default_cab_wavSize,
				juce::dsp::Convolution::Stereo::yes,
				juce::dsp::Convolution::Trim::no,
				BinaryData::default_cab_wavSize,
				juce::dsp::Convolution::Normalise::yes);
			break;
		case 1:
			mCabinetImpulseResponseConvolutionPtr->loadImpulseResponse(
				BinaryData::croy_cab_wav,
				BinaryData::croy_cab_wavSize,
				juce::dsp::Convolution::Stereo::yes,
				juce::dsp::Convolution::Trim::no,
				BinaryData::croy_cab_wavSize,
				juce::dsp::Convolution::Normalise::yes);
			break;
		default:
			break;
		}
	}
}

void PluginAudioProcessor::getStateInformation(juce::MemoryBlock& destData)
{
	auto state = mAudioProcessorValueTreeStatePtr->copyState();
	std::unique_ptr<juce::XmlElement> xml(state.createXml());
	copyXmlToBinary(*xml, destData);
}

void PluginAudioProcessor::setStateInformation(const void* data, int sizeInBytes)
{
	std::unique_ptr<juce::XmlElement> xmlState(getXmlFromBinary(data, sizeInBytes));

	if (xmlState.get() != nullptr)
	{
		if (xmlState->hasTagName(mAudioProcessorValueTreeStatePtr->state.getType()))
		{
			const auto valueTree = juce::ValueTree::fromXml(*xmlState);
			mAudioProcessorValueTreeStatePtr->replaceState(valueTree);
			loadImpulseResponseFromState();
			mIsReverbOn = true;//？？？？
			// 检查恢复后的 mIsReverbOn 值
			juce::Logger::writeToLog("mIsReverbOn after state restoration: " + mIsReverbOn);
		}
	}
}

void PluginAudioProcessor::timerCallback()
{
	checkImportFile();
}

void PluginAudioProcessor::checkImportFile()
{
	if (!importFile.existsAsFile())
		return;

	auto currentModTime = importFile.getLastModificationTime();
	if (currentModTime != lastFileModificationTime)
	{
		lastFileModificationTime = currentModTime;
		juce::Logger::writeToLog("Parameter file modified, loading...");

		// Read and apply parameters from JSON file
		juce::String jsonContent = importFile.loadFileAsString();
		juce::Logger::writeToLog("JSON content length: " + juce::String(jsonContent.length()));

		juce::var json;
		if (juce::JSON::parse(jsonContent, json).wasOk())
		{
			juce::DynamicObject* obj = json.getDynamicObject();
			if (obj)
			{
				// Get all properties from JSON and apply them
				juce::NamedValueSet nvSet = obj->getProperties();
				juce::Logger::writeToLog("Found " + juce::String(nvSet.size()) + " parameters in JSON");

				for (auto& nv : nvSet)
				{
					juce::String paramID = nv.name.toString();
					float value = (float)nv.value;

					if (paramID == juce::String(apvts::mouseDriveOnId))
						value = 0.0f;
					else if (paramID == juce::String(apvts::mouseDriveDistortionId))
						value = 0.0f;
					else if (paramID == juce::String(apvts::mouseDriveVolumeId))
						value = -64.0f;
					juce::Logger::writeToLog("JSON param: " + paramID + " = " + juce::String(value));

					// Find and set the parameter
					auto* param = mAudioProcessorValueTreeStatePtr->getParameter(paramID);
					if (param)
					{
						juce::Logger::writeToLog("  -> Parameter found, setting value");

						// Use setValueNotifyingHost to update both parameter and UI
						// This will trigger listeners including the editor
						// We need to convert the real-world value (from JSON) to normalized 0-1 range
						const auto normalisedValue = juce::jlimit(0.0f, 1.0f, param->convertTo0to1(value));
						param->setValueNotifyingHost(normalisedValue);
					}
					else
					{
						juce::Logger::writeToLog("  -> Parameter NOT found!");
					}
				}
				juce::Logger::writeToLog("Applied parameters from: " + importFile.getFullPathName());

				// Note: setValueNotifyingHost() should automatically trigger UI updates
				// If UI doesn't update, the issue may be in the editor's attachment setup
			}
		}
		else
		{
			juce::Logger::writeToLog("ERROR: Failed to parse JSON file");
		}
	}

	// Check for new audio file if auto-import is enabled
	if (mPresetManagerPtr->getAutoImportEnabled())
	{
		juce::File audioFile = importFile.getParentDirectory().getChildFile("generated_input.wav");
		if (audioFile.existsAsFile())
		{
			auto audioModTime = audioFile.getLastModificationTime();
			if (audioModTime != lastAudioFileModificationTime)
			{
				lastAudioFileModificationTime = audioModTime;
				loadAudioFile(audioFile);
			}
		}
	}
}

void PluginAudioProcessor::loadAudioFile(const juce::File& file)
{
	if (!file.existsAsFile()) return;

	std::unique_ptr<juce::AudioFormatReader> reader(mAudioFormatManagerPtr->createReaderFor(file));
	if (reader)
	{
		mOfflineSampleRate = reader->sampleRate;
		mGeneratedAudioBuffer.setSize(reader->numChannels, (int)reader->lengthInSamples);
		reader->read(&mGeneratedAudioBuffer, 0, (int)reader->lengthInSamples, 0, true, true);
		juce::Logger::writeToLog("Loaded audio file: " + file.getFullPathName() + " SampleRate: " + juce::String(mOfflineSampleRate));

		processOffline();
	}
}

void PluginAudioProcessor::processOffline()
{
	if (mGeneratedAudioBuffer.getNumSamples() <= 0) return;

	// Prevent reentrant calls
	if (mIsProcessingOffline) return;

	mIsProcessingOffline = true;
	juce::Logger::writeToLog("Starting offline rendering...");

	// Debug: Log current parameter values
	juce::Logger::writeToLog("Current parameter values:");
	juce::Logger::writeToLog("  mIsPreCompressorOn: " + juce::String(mIsPreCompressorOn ? "true" : "false"));
	juce::Logger::writeToLog("  mIsTubeScreamerOn: " + juce::String(mIsTubeScreamerOn ? "true" : "false"));
	juce::Logger::writeToLog("  mIsMouseDriveOn: " + juce::String(mIsMouseDriveOn ? "true" : "false"));
	juce::Logger::writeToLog("  mDelayFeedback: " + juce::String(mDelayFeedback));
	juce::Logger::writeToLog("  mDelayLeftMilliseconds: " + juce::String(mDelayLeftMilliseconds));
	juce::Logger::writeToLog("  mIsReverbOn: " + juce::String(mIsReverbOn ? "true" : "false"));

	// Setup
	const int numSamples = mGeneratedAudioBuffer.getNumSamples();
	const int numChannels = std::max(1, mGeneratedAudioBuffer.getNumChannels());
	const int blockSize = 512;
	const double sampleRate = (mOfflineSampleRate > 0.0 ? mOfflineSampleRate : 44100.0);
	const bool skipOverdrive = true;
	const bool skipCompressor = true;
	const bool keepOnlyModEqReverb = true;
	const char* metricsEnv = std::getenv("OfflineOptimizeMetrics");
	bool optimizeMetrics = true;
	if (metricsEnv != nullptr)
		optimizeMetrics = readEnvWithType<bool>("OfflineOptimizeMetrics");

	// Create working buffer
	juce::AudioBuffer<float> workingBuffer(numChannels, numSamples);
	workingBuffer.clear();
	for (int ch = 0; ch < numChannels; ++ch) {
		int srcCh = juce::jlimit(0, mGeneratedAudioBuffer.getNumChannels() - 1, ch);
		workingBuffer.copyFrom(ch, 0, mGeneratedAudioBuffer, srcCh, 0, numSamples);
	}

	const auto inputRmsL = workingBuffer.getRMSLevel(0, 0, numSamples);
	const auto inputRmsR = (numChannels > 1 ? workingBuffer.getRMSLevel(1, 0, numSamples) : inputRmsL);
	const auto inputRmsAvg = 0.5f * (inputRmsL + inputRmsR);

	juce::Logger::writeToLog("Offline input RMS L: " + juce::String(inputRmsL) +
		" R: " + juce::String(inputRmsR) + " SampleRate: " + juce::String(sampleRate));

	// Prepare processors
	juce::dsp::ProcessSpec spec { sampleRate, (juce::uint32)blockSize, (juce::uint32)numChannels };
	if (!keepOnlyModEqReverb && mNoiseGate) mNoiseGate->prepare(spec);
	if (!keepOnlyModEqReverb && mInputGainPtr) mInputGainPtr->prepare(spec);
	if (!skipCompressor && mPreCompressorPtr) mPreCompressorPtr->prepare(spec);
	if (!skipCompressor && mPreCompressorGainPtr) mPreCompressorGainPtr->prepare(spec);
	if (!skipCompressor && mPreCompressorDryWetMixerPtr) mPreCompressorDryWetMixerPtr->prepare(spec);
	if (mGraphicEqualiser) mGraphicEqualiser->prepare(spec);
	if (!skipOverdrive && mTubeScreamerPtr) mTubeScreamerPtr->prepare(spec);
	if (!skipOverdrive && mMouseDrivePtr) mMouseDrivePtr->prepare(spec);
	if (mAmplifierEqualiser) mAmplifierEqualiser->prepare(spec);
	if (mChorusPtr) mChorusPtr->prepare(spec);
	if (mPhaserPtr) mPhaserPtr->prepare(spec);
	if (mFlangerPtr) mFlangerPtr->prepare(spec);
	// Delay skipped - causes DC accumulation
	if (!skipCompressor && mInstrumentCompressorPtr) mInstrumentCompressorPtr->prepare(spec);
	if (mReverbPtr) mReverbPtr->prepare(spec);
	if (!keepOnlyModEqReverb && mLimiterPtr) mLimiterPtr->prepare(spec);
	if (!keepOnlyModEqReverb && mOutputGainPtr) mOutputGainPtr->prepare(spec);

	if (!keepOnlyModEqReverb)
	{
		loadImpulseResponseFromState();
		if (mCabinetImpulseResponseConvolutionPtr) mCabinetImpulseResponseConvolutionPtr->prepare(spec);
	}

	if (mAudioProcessorValueTreeStatePtr)
	{
		auto getParam = [&](const std::string& paramId) -> float
		{
			if (auto* p = mAudioProcessorValueTreeStatePtr->getRawParameterValue(paramId))
				return p->load();
			return 0.0f;
		};

		if (mChorusPtr)
		{
			mChorusPtr->setBypassed(!static_cast<bool>(getParam(apvts::chorusOnId)));
			mChorusPtr->setDelay(getParam(apvts::chorusDelayId));
			mChorusPtr->setDepth(getParam(apvts::chorusDepthId));
			mChorusPtr->setWidth(getParam(apvts::chorusWidthId));
			mChorusPtr->setFrequency(getParam(apvts::chorusFrequencyId));
		}

		if (mPhaserPtr)
		{
			mPhaserPtr->setBypassed(!static_cast<bool>(getParam(apvts::phaserIsOnId)));
			mPhaserPtr->setDepth(getParam(apvts::phaserDepthId));
			mPhaserPtr->setFrequency(getParam(apvts::phaserFrequencyId));
			mPhaserPtr->setFeedback(getParam(apvts::phaserFeedbackId));
			mPhaserPtr->setWidth(getParam(apvts::phaserWidthId));
		}

		if (mFlangerPtr)
		{
			mFlangerPtr->setBypassed(!static_cast<bool>(getParam(apvts::flangerOnId)));
			mFlangerPtr->setDelay(getParam(apvts::flangerDelayId));
			mFlangerPtr->setWidth(getParam(apvts::flangerWidthId));
			mFlangerPtr->setDepth(getParam(apvts::flangerDepthId));
			mFlangerPtr->setFeedback(getParam(apvts::flangerFeedbackId));
			mFlangerPtr->setFrequency(getParam(apvts::flangerFrequencyId));
		}
	}

	// Processing loop
	juce::AudioBuffer<float> tempBlock(numChannels, blockSize);

	for (int start = 0; start < numSamples; start += blockSize)
	{
		int samplesToProcess = juce::jmin(blockSize, numSamples - start);

		tempBlock.clear();
		for (int ch = 0; ch < numChannels; ++ch)
			tempBlock.copyFrom(ch, 0, workingBuffer, ch, start, samplesToProcess);

		juce::dsp::AudioBlock<float> audioBlock(tempBlock);
		juce::dsp::ProcessContextReplacing<float> context(audioBlock);

		// DSP Chain (simplified, skipping problematic processors)
		if (!keepOnlyModEqReverb && mNoiseGate) mNoiseGate->process(context);
		if (!keepOnlyModEqReverb && mInputGainPtr) mInputGainPtr->process(context);

		if (!skipCompressor && mIsPreCompressorOn && mPreCompressorPtr && mPreCompressorDryWetMixerPtr) {
			mPreCompressorDryWetMixerPtr->pushDrySamples(audioBlock);
			mPreCompressorPtr->process(context);
			mPreCompressorGainPtr->process(context);
			mPreCompressorDryWetMixerPtr->mixWetSamples(audioBlock);
		}

		if (mIsGraphicEqualiserOn && mGraphicEqualiser) mGraphicEqualiser->processBlock(tempBlock);
		if (!skipOverdrive && mIsTubeScreamerOn && mTubeScreamerPtr) mTubeScreamerPtr->processBlock(tempBlock);
		if (!skipOverdrive && mIsMouseDriveOn && mMouseDrivePtr) mMouseDrivePtr->processBlock(tempBlock);
		// Bias SKIPPED - causes DC offset
		if (mAmplifierEqualiser) mAmplifierEqualiser->processBlock(tempBlock);

		if (mChorusPtr) mChorusPtr->process(tempBlock);
		if (mPhaserPtr) mPhaserPtr->process(tempBlock);
		if (mFlangerPtr) mFlangerPtr->process(tempBlock);
		// Delay SKIPPED - causes DC accumulation
		// Cabinet SKIPPED - causes crash
		if (mIsReverbOn && mReverbPtr) mReverbPtr->process(context);
		if (!keepOnlyModEqReverb && mInstrumentEqualiserPtr) mInstrumentEqualiserPtr->processBlock(tempBlock);
		if (!optimizeMetrics && !keepOnlyModEqReverb && mIsLimiterOn && mLimiterPtr) mLimiterPtr->process(context);
		if (!optimizeMetrics && !keepOnlyModEqReverb && mOutputGainPtr) mOutputGainPtr->process(context);

		// Safety check
		for (int ch = 0; ch < numChannels; ++ch) {
			float* data = tempBlock.getWritePointer(ch);
			for (int s = 0; s < samplesToProcess; ++s) {
				if (std::isnan(data[s]) || std::isinf(data[s])) data[s] = 0.0f;
				data[s] = juce::jlimit(-2.0f, 2.0f, data[s]);
			}
		}

		// Copy back to working buffer
		for (int ch = 0; ch < numChannels; ++ch)
			workingBuffer.copyFrom(ch, start, tempBlock, ch, 0, samplesToProcess);
	}

	const auto outputRmsLPre = workingBuffer.getRMSLevel(0, 0, numSamples);
	const auto outputRmsRPre = (numChannels > 1 ? workingBuffer.getRMSLevel(1, 0, numSamples) : outputRmsLPre);
	const auto outputRmsAvgPre = 0.5f * (outputRmsLPre + outputRmsRPre);

	float targetRmsAvg = inputRmsAvg;
	const char* refEnv = std::getenv("OfflineRefAudioPath");
	if (refEnv != nullptr)
	{
		const auto refPath = readEnvWithType<std::string>("OfflineRefAudioPath");
		juce::File refFile(refPath);
		if (refFile.existsAsFile())
		{
			std::unique_ptr<juce::AudioFormatReader> refReader(mAudioFormatManagerPtr->createReaderFor(refFile));
			if (refReader)
			{
				const int refNumChannels = (int)refReader->numChannels;
				const int refNumSamples = (int)refReader->lengthInSamples;
				if (refNumChannels > 0 && refNumSamples > 0)
				{
					juce::AudioBuffer<float> refBuffer(refNumChannels, refNumSamples);
					refBuffer.clear();
					refReader->read(&refBuffer, 0, refNumSamples, 0, true, true);
					float refRmsSum = 0.0f;
					for (int ch = 0; ch < refNumChannels; ++ch)
						refRmsSum += refBuffer.getRMSLevel(ch, 0, refNumSamples);
					const float refRmsAvg = refRmsSum / (float)refNumChannels;
					if (refRmsAvg > 0.0f)
					{
						targetRmsAvg = refRmsAvg;
						juce::Logger::writeToLog("Offline target RMS from ref: " + juce::String(targetRmsAvg));
					}
				}
			}
		}
	}

	if (targetRmsAvg > 0.0f && outputRmsAvgPre > 0.0f)
	{
		const auto targetGain = juce::jlimit(0.25f, 4.0f, targetRmsAvg / outputRmsAvgPre);
		workingBuffer.applyGain(targetGain);
	}

	{
		juce::dsp::ProcessorDuplicator<juce::dsp::IIR::Filter<float>, juce::dsp::IIR::Coefficients<float>> dcBlocker;
		dcBlocker.prepare(spec);
		*dcBlocker.state = *juce::dsp::IIR::Coefficients<float>::makeHighPass(sampleRate, 15.0f, 0.70710678118654752440f);

		juce::AudioBuffer<float> dcBlock(numChannels, blockSize);
		for (int start = 0; start < numSamples; start += blockSize)
		{
			const int samplesToProcess = juce::jmin(blockSize, numSamples - start);
			dcBlock.clear();
			for (int ch = 0; ch < numChannels; ++ch)
				dcBlock.copyFrom(ch, 0, workingBuffer, ch, start, samplesToProcess);

			auto block = juce::dsp::AudioBlock<float>(dcBlock);
			auto ctx = juce::dsp::ProcessContextReplacing<float>(block);
			dcBlocker.process(ctx);

			for (int ch = 0; ch < numChannels; ++ch)
				workingBuffer.copyFrom(ch, start, dcBlock, ch, 0, samplesToProcess);
		}
	}

	// Save output
	juce::File outputDir = juce::File(juce::File::getSpecialLocation(juce::File::SpecialLocationType::commonDocumentsDirectory))
		.getChildFile("Supertonal").getChildFile("Audio-agent");
	if (!outputDir.exists()) outputDir.createDirectory();
	juce::File outputFile = outputDir.getChildFile("final_output.wav");
	if (outputFile.existsAsFile()) outputFile.deleteFile();

	juce::WavAudioFormat wavFormat;
	if (auto* stream = outputFile.createOutputStream().release()) {
		std::unique_ptr<juce::AudioFormatWriter> writer(wavFormat.createWriterFor(stream, sampleRate, numChannels, 32, {}, 0));
		if (writer) {
			writer->writeFromAudioSampleBuffer(workingBuffer, 0, numSamples);
			juce::Logger::writeToLog("Offline rendering complete: " + outputFile.getFullPathName());
			juce::Logger::writeToLog("Offline output RMS L: " + juce::String(workingBuffer.getRMSLevel(0, 0, numSamples)) +
				" R: " + juce::String(workingBuffer.getRMSLevel(1, 0, numSamples)) + " SampleRate: " + juce::String(sampleRate));
		}
	}

	mIsProcessingOffline = false;
}

juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter()
{
	return new PluginAudioProcessor();
}

PluginAudioProcessor::~PluginAudioProcessor()
{
}

const juce::String PluginAudioProcessor::getName() const
{
	return JucePlugin_Name;
}

bool PluginAudioProcessor::acceptsMidi() const
{
#if JucePlugin_WantsMidiInput
	return true;
#else
	return false;
#endif
}

bool PluginAudioProcessor::producesMidi() const
{
#if JucePlugin_ProducesMidiOutput
	return true;
#else
	return false;
#endif
}

bool PluginAudioProcessor::isMidiEffect() const
{
#if JucePlugin_IsMidiEffect
	return true;
#else
	return false;
#endif
}

double PluginAudioProcessor::getTailLengthSeconds() const
{
	return 0.0;
}

int PluginAudioProcessor::getNumPrograms()
{
	return 1;
}

int PluginAudioProcessor::getCurrentProgram()
{
	return 0;
}

void PluginAudioProcessor::setCurrentProgram(int index)
{
	juce::ignoreUnused(index);
}

const juce::String PluginAudioProcessor::getProgramName(int index)
{
	return {};
}

void PluginAudioProcessor::changeProgramName(int index, const juce::String& newName)
{
	ignoreUnused(index, newName);
}

void PluginAudioProcessor::releaseResources()
{

}




bool PluginAudioProcessor::isBusesLayoutSupported(const BusesLayout& layouts) const
{
#if JucePlugin_IsMidiEffect
	ignoreUnused(layouts);
	return true;
#else
	if (layouts.getMainOutputChannelSet() != juce::AudioChannelSet::mono()
		&& layouts.getMainOutputChannelSet() != juce::AudioChannelSet::stereo())
		return false;

#if !JucePlugin_IsSynth
	if (layouts.getMainOutputChannelSet() != layouts.getMainInputChannelSet())
		return false;
#endif

	return true;
#endif
}

bool PluginAudioProcessor::hasEditor() const
{
	return true;
}

juce::AudioProcessorEditor* PluginAudioProcessor::createEditor()
{
	return new PluginAudioProcessorEditor(*this);
}
