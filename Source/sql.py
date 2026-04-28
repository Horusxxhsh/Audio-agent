import sys
import json
import sqlite3
import math
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from openai import OpenAI
import pandas as pd
import xml.etree.ElementTree as ET
import os
import platform
import torch
import librosa
from transformers import Wav2Vec2Processor, Wav2Vec2Model
import numpy as np


def parameters_update(parameters):
    # When first_47[0] == 1.0, replace "CompressorOff" with "CompressorOn"
    if first_47[0] == 1.0 and 'CompressorOff' in parameters:
        compressor_settings = parameters.pop('CompressorOff')
        parameters['CompressorOn'] = compressor_settings
    if first_47[0] == 0.0 and 'CompressorOn' in parameters:
        compressor_settings = parameters.pop('CompressorOn')
        parameters['CompressorOff'] = compressor_settings
    if 'CompressorOff' in parameters:
        parameters['CompressorOff']['Threshold'] = -128.00
        parameters['CompressorOff']['Ratio'] = 1
        parameters['CompressorOff']['Attack'] = 0.00
        parameters['CompressorOff']['Release'] = 0.00
        parameters['CompressorOff']['Makeup'] = -12.00
        parameters['CompressorOff']['Mix'] = 0.00

    # When first_47[1] == 1.0, replace "ScreamerOff" with "ScreamerOn"
    if first_47[1] == 1.0 and 'ScreamerOff' in parameters:
        compressor_settings = parameters.pop('ScreamerOff')
        parameters['ScreamerOn'] = compressor_settings
    if first_47[1] == 0.0 and 'ScreamerOn' in parameters:
        compressor_settings = parameters.pop('ScreamerOn')
        parameters['ScreamerOff'] = compressor_settings
    if 'ScreamerOff' in parameters:
        parameters['ScreamerOff']['Drive'] = 0.00
        parameters['ScreamerOff']['Tone'] = 0.00
        parameters['ScreamerOff']['Level'] = -64.0000000

    # When first_47[2] == 1.0, replace "DriverOff" with "DriverOn"
    if first_47[2] == 1.0 and 'DriverOff' in parameters:
        compressor_settings = parameters.pop('DriverOff')
        parameters['DriverOn'] = compressor_settings
    if first_47[2] == 0.0 and 'DriverOn' in parameters:
        compressor_settings = parameters.pop('DriverOn')
        parameters['DriverOff'] = compressor_settings
    if 'DriverOff' in parameters:
        parameters['DriverOff']['Distortion'] = 0.00
        parameters['DriverOff']['Volume'] = -64.0

        # When first_47[3] == 1.0, replace "DelayOff" with "DelayOn"
    if first_47[3] == 1.0 and 'DelayOff' in parameters:
        compressor_settings = parameters.pop('DelayOff')
        parameters['DelayOn'] = compressor_settings
    if first_47[3] == 0.0 and 'DelayOn' in parameters:
        compressor_settings = parameters.pop('DelayOn')
        parameters['DelayOff'] = compressor_settings
    if 'DelayOff' in parameters:
        parameters['DelayOff']['Feedback'] = 0.00
        parameters['DelayOff']['Delay'] = 1.00
        parameters['DelayOff']['Mix'] = 0.00

        # When first_47[4] == 1.0, replace "ReverbOff" with "ReverbOn"
    if first_47[4] == 1.0 and 'ReverbOff' in parameters:
        compressor_settings = parameters.pop('ReverbOff')
        parameters['ReverbOn'] = compressor_settings
    if first_47[4] == 0.0 and 'ReverbOn' in parameters:
        compressor_settings = parameters.pop('ReverbOn')
        parameters['ReverbOff'] = compressor_settings
    if 'ReverbOff' in parameters:
        parameters['ReverbOff']['Size'] = 0.00
        parameters['ReverbOff']['Damping'] = 0.00
        parameters['ReverbOff']['Width'] = 0.00
        parameters['ReverbOff']['Mix'] = 0.00

        # When first_47[5] == 1.0, replace "ChorusOff" with "ChorusOn"
    if first_47[5] == 1.0 and 'ChorusOff' in parameters:
        compressor_settings = parameters.pop('ChorusOff')
        parameters['ChorusOn'] = compressor_settings
    if first_47[5] == 0.0 and 'ChorusOn' in parameters:
        compressor_settings = parameters.pop('ChorusOn')
        parameters['ChorusOff'] = compressor_settings
    if 'ChorusOff' in parameters:
        parameters['ChorusOff']['Delay'] = 0.010
        parameters['ChorusOff']['Depth'] = 0.00
        parameters['ChorusOff']['Frequency'] = 0.05
        parameters['ChorusOff']['Width'] = 0.010

        # When first_47[6] == 1.0, replace "FlangerOff" with "FlangerOn"
    if first_47[6] == 1.0 and 'FlangerOff' in parameters:
        compressor_settings = parameters.pop('FlangerOff')
        parameters['FlangerOn'] = compressor_settings
    if first_47[6] == 0.0 and 'FlangerOn' in parameters:
        compressor_settings = parameters.pop('FlangerOn')
        parameters['FlangerOff'] = compressor_settings
    if 'FlangerOff' in parameters:
        parameters['FlangerOff']['Delay'] = 0.00100
        parameters['FlangerOff']['Depth'] = 0.00
        parameters['FlangerOff']['Feedback'] = 0.00
        parameters['FlangerOff']['Frequency'] = 0.05
        parameters['FlangerOff']['Width'] = 0.001

    # When first_47[7] == 1.0, replace "PhaserOff" with "PhaserOn"
    if first_47[7] == 1.0 and 'PhaserOff' in parameters:
        compressor_settings = parameters.pop('PhaserOff')
        parameters['PhaserOn'] = compressor_settings
    if first_47[7] == 0.0 and 'PhaserOn' in parameters:
        compressor_settings = parameters.pop('PhaserOn')
        parameters['PhaserOff'] = compressor_settings
    if 'PhaserOff' in parameters:
        parameters['PhaserOff']['Depth'] = 0.00
        parameters['PhaserOff']['Feedback'] = 0.00
        parameters['PhaserOff']['Frequency'] = -64.0000000
        parameters['PhaserOff']['Width'] = -64.0000000

    # When first_47[8] == 1.0, replace "EqualiserOff" with "EqualiserOn"
    if first_47[8] == 1.0 and 'EqualiserOff' in parameters:
        compressor_settings = parameters.pop('EqualiserOff')
        parameters['EqualiserOn'] = compressor_settings
    if first_47[8] == 0.0 and 'EqualiserOn' in parameters:
        compressor_settings = parameters.pop('EqualiserOn')
        parameters['EqualiserOff'] = compressor_settings
    if 'EqualiserOff' in parameters:
        parameters['EqualiserOff']['100hz'] = 0.00
        parameters['EqualiserOff']['200hz'] = 0.00
        parameters['EqualiserOff']['400hz'] = 0.00
        parameters['EqualiserOff']['800hz'] = 0.00
        parameters['EqualiserOff']['1600hz'] = 0.00
        parameters['EqualiserOff']['3200hz'] = 0.00
        parameters['EqualiserOff']['6400hz'] = 0.00
        parameters['EqualiserOff']['Level'] = 0.00

        # Update parameter values in database
    if first_47[0] == 1.0:
        if 'CompressorOn' in parameters:

            # Convert first_47[9] to Threshold range value
            first_47[9] = float(first_47[9])
            threshold = -128 + (0 - (-128)) * first_47[9]
            parameters['CompressorOn']['Threshold'] = threshold

            # Get Ratio value
            first_47[11] = float(first_47[11])
            ratio = get_ratio(first_47[11])
            if ratio is not None:
                parameters['CompressorOn']['Ratio'] = ratio
            else:
                print(f"No corresponding Ratio value found for first_47[11] = {first_47[11]}")

            parameters['CompressorOn']['Attack'] = first_47[10]
            parameters['CompressorOn']['Release'] = first_47[12]

            # Convert first_47[13] to Makeup range value
            first_47[13] = float(first_47[13])
            makeup = -128 + (64 - (-128)) * first_47[13]
            parameters['CompressorOn']['Makeup'] = makeup

            parameters['CompressorOn']['Mix'] = first_47[14]

    if first_47[2] == 1.0:
        if 'DriverOn' in parameters:
            parameters['DriverOn']['Distortion'] = first_47[18]
            # Convert first_47[19] to Volume range value
            first_47[19] = float(first_47[19])
            volume = -64 + (0 - (-64)) * first_47[19]
            parameters['DriverOn']['Volume'] = volume

    if first_47[1] == 1.0:
        if 'ScreamerOn' in parameters:
            parameters['ScreamerOn']['Drive'] = first_47[15]
            parameters['ScreamerOn']['Tone'] = first_47[17]
            # Convert first_47[16] to Volume range value
            first_47[16] = float(first_47[16])
            volume = -64 + (0 - (-64)) * first_47[16]
            parameters['ScreamerOn']['Level'] = volume

    if first_47[3] == 1.0:
        if 'DelayOn' in parameters:
            parameters['DelayOn']['Feedback'] = first_47[20]

            parameters['DelayOn']['Delay'] = "450.00"

            parameters['DelayOn']['Mix'] = first_47[22]

    if first_47[4] == 1.0:
        if 'ReverbOn' in parameters:
            parameters['ReverbOn']['Size'] = first_47[23]
            parameters['ReverbOn']['Damping'] = first_47[24]
            parameters['ReverbOn']['Width'] = first_47[25]
            parameters['ReverbOn']['Mix'] = first_47[26]

    if first_47[8] == 1.0:
        if 'EqualiserOn' in parameters:
            if len(first_47) > 46:
                # Convert first_47[40] to Frequency range value
                first_47[40] = float(first_47[40])
                fz = -15.00 + (15.00 - (-15.00)) * first_47[40]
                parameters['EqualiserOn']['100hz'] = fz

                # Convert first_47[41] to Frequency range value
                first_47[41] = float(first_47[41])
                fz = -15.00 + (15.00 - (-15.00)) * first_47[41]
                parameters['EqualiserOn']['200hz'] = fz

                # Convert first_47[42] to Frequency range value
                first_47[42] = float(first_47[42])
                fz = -15.00 + (15.00 - (-15.00)) * first_47[42]
                parameters['EqualiserOn']['400hz'] = fz

                # Convert first_47[43] to Frequency range value
                first_47[43] = float(first_47[43])
                fz = -15.00 + (15.00 - (-15.00)) * first_47[43]
                parameters['EqualiserOn']['800hz'] = fz

                # Convert first_47[44] to Frequency range value
                first_47[44] = float(first_47[44])
                fz = -15.00 + (15.00 - (-15.00)) * first_47[44]
                parameters['EqualiserOn']['1600hz'] = fz

                # Convert first_47[45] to Frequency range value
                first_47[45] = float(first_47[45])
                fz = -15.00 + (15.00 - (-15.00)) * first_47[45]
                parameters['EqualiserOn']['3200hz'] = fz

                # Convert first_47[46] to Frequency range value
                first_47[46] = float(first_47[46])
                fz = -15.00 + (15.00 - (-15.00)) * first_47[46]
                parameters['EqualiserOn']['6400hz'] = fz
            if len(first_47) > 47:
                # Convert first_47[47] to Frequency range value
                first_47[47] = float(first_47[47])
                fz = -15.00 + (15.00 - (-15.00)) * first_47[47]
                parameters['EqualiserOn']['Level'] = fz

    if first_47[5] == 1.0:
        if 'ChorusOn' in parameters:
            # Convert first_47[27] to Depth range value
            first_47[27] = float(first_47[27])
            depth = 0.010 + (0.050 - 0.010) * first_47[27]
            parameters['ChorusOn']['Delay'] = depth

            parameters['ChorusOn']['Depth'] = first_47[28]

            # Convert first_47[29] to Frequency range value
            first_47[29] = float(first_47[29])
            frequency = 0.05 + (2.00 - 0.05) * first_47[29]
            parameters['ChorusOn']['Frequency'] = frequency

            # Convert first_47[30] to Width range value
            first_47[30] = float(first_47[30])
            width = 0.010 + (0.050 - 0.010) * first_47[30]
            parameters['ChorusOn']['Width'] = width

    if first_47[6] == 1.0:
        if 'FlangerOn' in parameters:
            # Convert first_47[31] to Delay range value
            first_47[31] = float(first_47[31])
            delay = 0.00100 + (0.02000 - 0.00100) * first_47[31]
            parameters['FlangerOn']['Delay'] = delay

            parameters['FlangerOn']['Depth'] = first_47[32]

            # Convert first_47[33] to Feedback range value
            first_47[33] = float(first_47[33])
            feedback = 0.00 + (0.50 - 0.00) * first_47[33]
            parameters['FlangerOn']['Feedback'] = feedback

            # Convert first_47[34] to Frequency range value
            first_47[34] = float(first_47[34])
            frequency = 0.05 + (2.00 - 0.05) * first_47[34]
            parameters['FlangerOn']['Frequency'] = frequency

            # Convert first_47[35] to Width range value
            first_47[35] = float(first_47[35])
            width = 0.001 + (0.020 - 0.001) * first_47[35]
            parameters['FlangerOn']['Width'] = width

    if first_47[7] == 1.0:
        if 'PhaserOn' in parameters:
            parameters['PhaserOn']['Depth'] = first_47[36]

            # Convert first_47[37] to Feedback range value
            first_47[37] = float(first_47[37])
            feedback = 0.00 + (0.09 - 0.00) * first_47[37]
            parameters['PhaserOn']['Feedback'] = feedback

            # Convert first_47[38] to Frequency range value
            first_47[38] = float(first_47[38])
            frequency = 0.00 + (2.00 - 0.00) * first_47[38]
            parameters['PhaserOn']['Frequency'] = frequency

            # Convert first_47[39] to Width range value
            first_47[39] = float(first_47[39])
            width = 50 + (3000 - 50) * first_47[39]
            parameters['PhaserOn']['Width'] = width

    return parameters



# 1. Define parameter mapping (reuse existing mapping)
param_mapping = {
    # Switch control mapping
    "CompressorOn": ("pre_compressor_on", 1),
    "CompressorOff": ("pre_compressor_on", 0),
    "ScreamerOn": ("tube_screamer_on", 1),
    "ScreamerOff": ("tube_screamer_on", 0),
    "DriverOn": ("mouse_drive_on", 1),
    "DriverOff": ("mouse_drive_on", 0),
    "DelayOn": ("delay_on", 1),
    "DelayOff": ("delay_on", 0),
    "ReverbOn": ("room_on", 1),
    "ReverbOff": ("room_on", 0),
    "ChorusOn": ("chorus_on", 1),
    "ChorusOff": ("chorus_on", 0),
    "FlangerOn": ("flanger_on", 1),
    "FlangerOff": ("flanger_on", 0),
    "PhaserOn": ("phaser_on", 1),
    "PhaserOff": ("phaser_on", 0),
    "EqualiserOn": ("pre_eq_on", 1),
    "EqualiserOff": ("pre_eq_on", 0),

    # Parameter value mapping
    "CompressorOn.Threshold": "pre_comp_thresh",
    "CompressorOn.Ratio": "pre_comp_ratio",
    "CompressorOn.Attack": "pre_comp_attack",
    "CompressorOn.Release": "pre_comp_release",
    "CompressorOn.Mix": "pre_comp_blend",
    "CompressorOn.Makeup": "pre_comp_gain",
    "CompressorOff.Threshold": "pre_comp_thresh",
    "CompressorOff.Ratio": "pre_comp_ratio",
    "CompressorOff.Attack": "pre_comp_attack",
    "CompressorOff.Release": "pre_comp_release",
    "CompressorOff.Mix": "pre_comp_blend",
    "CompressorOff.Makeup": "pre_comp_gain",
    "ScreamerOn.Drive": "tube_screamer_drive",
    "ScreamerOn.Tone": "tube_screamer_tone",
    "ScreamerOn.Level": "tube_screamer_level",
    "ScreamerOff.Drive": "tube_screamer_drive",
    "ScreamerOff.Tone": "tube_screamer_tone",
    "ScreamerOff.Level": "tube_screamer_level",
    "DriverOn.Distortion": "mouse_drive_distortion",
    "DriverOn.Volume": "mouse_drive_volume",
    "DriverOff.Distortion": "mouse_drive_distortion",
    "DriverOff.Volume": "mouse_drive_volume",
    "DelayOn.Feedback": "delay_feedback",
    "DelayOn.Delay": "delay_left_millisecond",
    "DelayOn.Mix": "delay_mix",
    "DelayOff.Feedback": "delay_feedback",
    "DelayOff.Delay": "delay_left_millisecond",
    "DelayOff.Mix": "delay_mix",
    "ReverbOn.Size": "room_size",
    "ReverbOn.Damping": "room_damping",
    "ReverbOn.Width": "room_width",
    "ReverbOn.Mix": "room_mix",
    "ReverbOff.Size": "room_size",
    "ReverbOff.Damping": "room_damping",
    "ReverbOff.Width": "room_width",
    "ReverbOff.Mix": "room_mix",
    "ChorusOn.Delay": "chorus_delay",
    "ChorusOn.Depth": "chorus_depth",
    "ChorusOn.Frequency": "chorus_frequency",
    "ChorusOn.Width": "chorus_width",
    "ChorusOff.Delay": "chorus_delay",
    "ChorusOff.Depth": "chorus_depth",
    "ChorusOff.Frequency": "chorus_frequency",
    "ChorusOff.Width": "chorus_width",
    "FlangerOn.Delay": "flanger_delay",
    "FlangerOn.Depth": "flanger_depth",
    "FlangerOn.Feedback": "flanger_feedback",
    "FlangerOn.Frequency": "flanger_frequency",
    "FlangerOn.Width": "flanger_width",
    "FlangerOff.Delay": "flanger_delay",
    "FlangerOff.Depth": "flanger_depth",
    "FlangerOff.Feedback": "flanger_feedback",
    "FlangerOff.Frequency": "flanger_frequency",
    "FlangerOff.Width": "flanger_width",
    "PhaserOn.Depth": "phaser_depth",
    "PhaserOn.Feedback": "phaser_feedback",
    "PhaserOn.Frequency": "phaser_frequency",
    "PhaserOn.Width": "phaser_width",
    "PhaserOff.Depth": "phaser_depth",
    "PhaserOff.Feedback": "phaser_feedback",
    "PhaserOff.Frequency": "phaser_frequency",
    "PhaserOff.Width": "phaser_width",
    "EqualiserOn.100hz": "pre_eq_100_gain",
    "EqualiserOn.200hz": "pre_eq_200_gain",
    "EqualiserOn.400hz": "pre_eq_400_gain",
    "EqualiserOn.800hz": "pre_eq_800_gain",
    "EqualiserOn.1600hz": "pre_eq_1600_gain",
    "EqualiserOn.3200hz": "pre_eq_3200_gain",
    "EqualiserOn.6400hz": "pre_eq_6400_gain",
    "EqualiserOn.Level": "pre_eq_level_gain",
    "EqualiserOff.100hz": "pre_eq_100_gain",
    "EqualiserOff.200hz": "pre_eq_200_gain",
    "EqualiserOff.400hz": "pre_eq_400_gain",
    "EqualiserOff.800hz": "pre_eq_800_gain",
    "EqualiserOff.1600hz": "pre_eq_1600_gain",
    "EqualiserOff.3200hz": "pre_eq_3200_gain",
    "EqualiserOff.6400hz": "pre_eq_6400_gain",
    "EqualiserOff.Level": "pre_eq_level_gain"
}

# Define MemoryNote class
class MemoryNote:
    def __init__(self, id, songName, style, feature, parameter, preference):
        self.id = id
        self.songName = songName
        self.style = style
        self.feature = feature
        self.parameter = parameter
        self.preference = preference

    def __str__(self):
        return f"ID: {self.id}, Song Name: {self.songName}, Style: {self.style}, Feature: {self.feature}, Parameter: {self.parameter}, Preference: {self.preference}"




# Define Jaccard similarity function
def jaccard_similarity(set1, set2):
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    return intersection / union if union != 0 else 0

# Enhanced tag similarity calculation function considering semantic similarity and weights
def enhanced_tag_similarity(target_tags, hist_tags):
    """Enhanced tag similarity calculation considering semantic similarity and weights"""
    if not target_tags or not hist_tags:
        return 0.0
    
    # Calculate base Jaccard similarity
    base_similarity = jaccard_similarity(set(target_tags), set(hist_tags))
    
    # Calculate exact match count
    exact_matches = len(set(target_tags).intersection(set(hist_tags)))
    
    # Calculate semantic similarity (based on prefix/suffix matching of tags)
    semantic_matches = 0
    for target_tag in target_tags:
        for hist_tag in hist_tags:
            # If tags have common prefix or suffix
            if target_tag == hist_tag:
                semantic_matches += 1  # Exact match already counted, no duplication here
            elif (target_tag.replace('_rock', '') == hist_tag.replace('_rock', '')) or \
                 (target_tag.replace('_metal', '') == hist_tag.replace('_metal', '')) or \
                 (target_tag.replace('_rhythm', '') == hist_tag.replace('_rhythm', '')) or \
                 (target_tag.replace('_riffing', '') == hist_tag.replace('_riffs', '')) or \
                 (target_tag.replace('_riffs', '') == hist_tag.replace('_riffing', '')) or \
                 (target_tag.replace('_solos', '') == hist_tag.replace('_solo', '')) or \
                 (target_tag.replace('_solo', '') == hist_tag.replace('_solos', '')) or \
                 (target_tag.replace('_influenced', '') == hist_tag.replace('_influenced_solos', '')) or \
                 (target_tag == hist_tag.replace('_solos', '')) or \
                 (hist_tag == target_tag.replace('_solos', '')):
                semantic_matches += 0.5  # Partial semantic similarity
    
    # Comprehensive calculation: base similarity accounts for 70%, semantic matching for 30%
    enhanced_sim = base_similarity * 0.7 + (semantic_matches / max(len(target_tags), len(hist_tags))) * 0.3
    
    return enhanced_sim


# Define text similarity function
def text_similarity(text1, text2):
    if not text1 or not text2:
        return 0.0
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform([text1, text2])
    return cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]

def parse_structured_features(feature_array):
    """Parse structured feature array to extract all keywords"""
    all_keywords = []
    if isinstance(feature_array, list):
        for feature in feature_array:
            if isinstance(feature, str):
                # Check if contains structured data (semicolon-separated parts)
                if ";" in feature:
                    # Split regular description and structured part
                    parts = feature.split(";", 1)
                    all_keywords.extend(parts[0].lower().split())
                    # Add keywords from structured part
                    if ":" in parts[1]:
                        tech_name, tech_details = parts[1].split(":", 1)
                        all_keywords.append(tech_name.strip())
                        all_keywords.extend([d.strip() for d in tech_details.split(",")])
                else:
                    all_keywords.extend(feature.lower().split())
    elif isinstance(feature_array, str):
        # Handle string format case
        if ";" in feature_array:
            parts = feature_array.split(";", 1)
            all_keywords.extend(parts[0].lower().split())
            if ":" in parts[1]:
                tech_name, tech_details = parts[1].split(":", 1)
                all_keywords.append(tech_name.strip())
                all_keywords.extend([d.strip() for d in tech_details.split(",")])
        else:
            all_keywords.extend(feature_array.lower().split())
    
    return list(set(all_keywords))  # Remove duplicates


# Update preset file
def update_preset_in_file(file_path, params_dict):
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()

        # Update parameters
        for param in root.findall('PARAM'):
            param_id = param.get('id')
            if param_id in params_dict:
                param.set('value', str(params_dict[param_id]))

        # Save updated content
        tree.write(file_path, encoding='utf-8', xml_declaration=True)
        print(f"Preset file {file_path} updated successfully")
        return True
    except Exception as e:
        print(f"Error updating preset file: {e}")
        return False


def safe_open_file(relative_path, absolute_dir=None):
    """Try to open file, if relative path fails try using environment variable specified path"""

    # If absolute path not provided, try to get from environment variable
    if absolute_dir is None:
        absolute_dir = os.environ.get('DOCUMENTS_DIR')
        # If environment variable also doesn't exist, use default value
        if not absolute_dir:
            print("Warning: Environment variable DOCUMENTS_DIR not set, using current directory")
            absolute_dir = os.getcwd()  # Use current working directory as alternative

    try:
        # First try relative path
        with open(relative_path, 'r', encoding='utf-8') as file:
            content = file.read()
            print(f"Successfully opened file from relative path: {relative_path}")
            return content
    except FileNotFoundError:
        try:
            # If relative path fails, try environment variable specified path
            absolute_path = os.path.join(absolute_dir, relative_path)
            with open(absolute_path, 'r', encoding='utf-8') as file:
                content = file.read()
                print(f"Successfully opened file from environment variable specified path: {absolute_path}")
                return content
        except FileNotFoundError:
            print(f"Cannot open file {relative_path}, both relative and environment variable paths failed")
            return ""

def get_ratio(value):
    mapping = {
        0.000000: 1,
        0.118416: 2,
        0.197404: 3,
        0.256761: 4,
        0.304328: 5,
        0.344022: 6,
        0.378081: 7,
        0.407910: 8,
        0.434443: 9,
        0.458337: 10,
    }
    return mapping.get(value)


def update_parameters_to_database(parameters):
    # Only execute this code when memory system is enabled
    if memoryEnabled == "true":
        # First query database for records matching current user_message
        cursor.execute("SELECT SongName, Style, Feature, Parameters, Preferences FROM music_responses WHERE SongName = ?", (user_message,))
        matched_row = cursor.fetchone()
        
        if matched_row:
            # If matching record found, use data from database
            song_name = matched_row[0]
            style_str = matched_row[1]
            feature_str = matched_row[2]
            parameter_str = matched_row[3]
            preferences_str = matched_row[4]
            
            print(f"Retrieved matching record from database: {song_name}")
            print(f"Database style_str: {style_str}")
            print(f"Database feature_str: {feature_str}")
        else:
            # If no matching record, fallback to result1.txt and result2.txt files
            song_name = user_message
            style_str = result1_str
            feature_str = result2_str
            parameter_str = result_str
            preferences_str = 'edit'
            
            print(f"No matching database record found, using result files: {song_name}")
            print(f"result1_str: {style_str}")
            print(f"result2_str: {feature_str}")
        
        # Get all song info from database and calculate similarity, getting similar_songs and memory_notes
        cursor.execute("SELECT SongName, Style, Feature, Parameters, Preferences FROM music_responses")
        rows = cursor.fetchall()
        similar_songs = []
        memory_notes = []  # List storing MemoryNote instances
        
        # Exclude current record from results
        db_rows = [row for row in rows if row[0] != user_message]

        for index, row in enumerate(db_rows, start=1):
            song_name = row[0]
            style_str = row[1]
            feature_str = row[2]
            parameter_str = row[3]
            preferences_str = row[4]  # Preference field, not used yet
            if song_name != user_message:
                try:
                    print(f"R song_name: {song_name}")
                    print(f"R style_str: {style_str}")
                    print(f"R feature_str: {feature_str}")
                    print(f"R parameter_str: {parameter_str}")
                    print(f"R preferences_str: {preferences_str}")
                    style = json.loads(style_str)
                    feature = json.loads(feature_str)

                    # Calculate tag similarity
                    tags = set(style)
                    tag_similarity = enhanced_tag_similarity(list(result1_set), list(tags))
                    
                    # Improved description similarity calculation: considering structured feature matching
                    # Use feature_str from database or file
                    target_features_str = feature_str
                    if target_features_str and feature:
                        # Parse target features (string from database/file may be JSON array or string)
                        try:
                            target_features = json.loads(target_features_str)
                        except json.JSONDecodeError:
                            target_features = target_features_str
                        
                        # Use new parsing function to extract all keywords
                        target_keywords = parse_structured_features(target_features)
                        desc_similarities = []
                        
                        # Calculate similarity for each historical feature
                        for hist_feature in feature:
                            if hist_feature.strip():
                                # Parse historical feature
                                hist_keywords = parse_structured_features(hist_feature)
                                
                                # Calculate keyword intersection similarity
                                common_keywords = set(target_keywords) & set(hist_keywords)
                                union_keywords = set(target_keywords) | set(hist_keywords)
                                
                                if union_keywords:
                                    keyword_similarity = len(common_keywords) / len(union_keywords)
                                    desc_similarities.append(keyword_similarity)
                        
                        # Take maximum similarity as description similarity
                        desc_similarity = max(desc_similarities) if desc_similarities else 0.0
                        
                        # Give extra reward if historical record has multiple description sentences
                        if len(feature) > 1:
                            desc_similarity = min(desc_similarity * 1.1, 1.0)  # Maximum not exceeding 1.0
                    else:
                        desc_similarity = 0.0
                    
                    # Weighted overall similarity: tag similarity weight 0.6, description similarity weight 0.4
                    similarity = tag_similarity * 0.6 + desc_similarity * 0.4
                    print(f"similarity:{similarity}")
                    if similarity > 0.11:
                        similar_songs.append((song_name, similarity, style_str, feature_str, parameter_str))
                        # Store retrieved song info
                        # Limit memory_notes maximum length to 3
                        if len(memory_notes) < 3:
                            note = MemoryNote(index, song_name, style, feature, parameter_str, preferences_str)
                            memory_notes.append(note)
                        else:
                            # Reached maximum length, can choose whether to break loop as needed
                            break  # If want to keep only first 3 qualifying, can add break

                except json.JSONDecodeError:
                    print(f"Error: Invalid JSON response: {style_str}")
        # Print MemoryNote instance information
        for note in memory_notes:
            print(f"note:{note}")

        # Memory update
        song_name = user_message
        sqlParameters = json.dumps(parameters, ensure_ascii=False, indent=2)
        print(f"sqlParameters:{sqlParameters}")
        # Format system_prompt3
        memory_notes_str = "\n".join([str(note) for note in memory_notes])
        system_prompt3 = f'''
                                        You are an AI memory evolution agent responsible for managing and evolving a knowledge base.
                                        Analyze the new memory note according to style, feature and parameter, also with their several nearest neighbors memory.
                                        Make decisions about its evolution.  

                                        The new memory name:
                                        {song_name}
                                        style: {result1_str}
                                        feature: {result2_str}
                                        parameter: {sqlParameters}

                                        The nearest neighbors memories:
                                        {memory_notes_str}

                                        Based on this information, determine:
                                        1. Should this memory be evolved? Consider its relationships with other memories.
                                        2. What specific actions should be taken (strengthen, update_neighbor)?
                                           2.1 If choose to strengthen the connection, which memory should it be connected to? Can you give the updated tags of this memory?
                                           2.2 If choose to update_neighbor, you must update the parameters of these memories based on the following rules:
                                                   - **CRITICAL MODULE STATE RULE - ABSOLUTE REQUIREMENT**: For ALL audio effectors (Compressor, Driver, Screamer, Delay, Reverb, Chorus, Flanger, Equaliser, Phaser):
                                                     * IF CURRENT MEMORY HAS "DriverOff" -> ALL NEIGHBORS MUST HAVE "DriverOff" (Distortion: 0.0, Volume: -64.0)
                                                     * IF CURRENT MEMORY HAS "ScreamerOff" -> ALL NEIGHBORS MUST HAVE "ScreamerOff" (Drive: 0.0, Tone: 0.0,Level: -64.0)
                                                     * IF CURRENT MEMORY HAS "ReverbOff" -> ALL NEIGHBORS MUST HAVE "ReverbOff" (Size: 0.0, Damping: 0.0, Mix: 0.0, Width: 0.0)
                                                     * IF CURRENT MEMORY HAS "PhaserOff" -> ALL NEIGHBORS MUST HAVE "PhaserOff" (Depth: 0.0, Feedback: 0.0, Frequency: -64.0, Width: -64.0)
                                                     * IF CURRENT MEMORY HAS "ChorusOff" -> ALL NEIGHBORS MUST HAVE "ChorusOff" (Depth: 0.0, Frequency: 0.05, Width: 0.01)
                                                     * IF CURRENT MEMORY HAS "FlangerOff" -> ALL NEIGHBORS MUST HAVE "FlangerOff" (Depth: 0.0, Feedback: 0.0, Frequency: 0.05, Width: 0.001)
                                                     * IF CURRENT MEMORY HAS "DelayOff" -> ALL NEIGHBORS MUST HAVE "DelayOff" (Feedback: 0.0, Delay: 1.0, Mix: 0.0)
                                                     * IF CURRENT MEMORY HAS "CompressorOff" -> ALL NEIGHBORS MUST HAVE "CompressorOff" (Threshold: -128.0, Ratio: 1, Attack: 0.0, Release: 0.0, Makeup: -128.0, Mix: 0.0)
                                                     * IF CURRENT MEMORY HAS "EqualiserOff" -> ALL NEIGHBORS MUST HAVE "EqualiserOff" (100hz: 0.0, 200hz: 0.0, 400hz: 0.0, 800hz: 0.0, 1600hz: 0.0, 3200hz: 0.0, 6400hz: 0.0, Level: 0.0)
                                                     * IF CURRENT MEMORY HAS "DriverOn" -> ALL NEIGHBORS MUST HAVE "DriverOn" (Distortion: DIFFERENT from current, Volume: DIFFERENT from current)
                                                     * IF CURRENT MEMORY HAS "PhaserOn" -> ALL NEIGHBORS MUST HAVE "PhaserOn" (Depth: DIFFERENT from current, Feedback: DIFFERENT from current, Frequency: DIFFERENT from current, Width: DIFFERENT from current)
                                                     * IF CURRENT MEMORY HAS "ChorusOn" -> ALL NEIGHBORS MUST HAVE "ChorusOn" (Delay: DIFFERENT from current, Depth: DIFFERENT from current, Frequency: DIFFERENT from current, Width: DIFFERENT from current)
                                                     * IF CURRENT MEMORY HAS "FlangerOn" -> ALL NEIGHBORS MUST HAVE "FlangerOn" (Delay: DIFFERENT from current,Depth: DIFFERENT from current, Feedback: DIFFERENT from current, Frequency: DIFFERENT from current, Width: DIFFERENT from current)
                                                     * IF CURRENT MEMORY HAS "DelayOn" -> ALL NEIGHBORS MUST HAVE "DelayOn" (Feedback: DIFFERENT from current, Delay: DIFFERENT from current, Mix: DIFFERENT from current)
                                                     * IF CURRENT MEMORY HAS "ReverbOn" -> ALL NEIGHBORS MUST HAVE "ReverbOn" (Size: DIFFERENT from current, Damping: DIFFERENT from current, Width: DIFFERENT from current, Mix: DIFFERENT from current)
                                                     * IF CURRENT MEMORY HAS "ScreamerOn" -> ALL NEIGHBORS MUST HAVE "ScreamerOn" (Drive: DIFFERENT from current, Tone: DIFFERENT from current, Level: DIFFERENT from current)
                                                     * IF CURRENT MEMORY HAS "CompressorOn" -> ALL NEIGHBORS MUST HAVE "CompressorOn" (Threshold: DIFFERENT from current, Ratio: DIFFERENT from current, Attack: DIFFERENT from current, Release: DIFFERENT from current, Makeup: DIFFERENT from current, Mix: DIFFERENT from current)
                                                     * IF CURRENT MEMORY HAS "EqualiserOn" -> ALL NEIGHBORS MUST HAVE "EqualiserOn" (100hz: DIFFERENT from current, 200hz: DIFFERENT from current, 400hz: DIFFERENT from current, 800hz: DIFFERENT from current, 1600hz: DIFFERENT from current, 3200hz: DIFFERENT from current, 6400hz: DIFFERENT from current, Level: DIFFERENT from current)
                                                     * THIS RULE OVERRIDES ALL OTHER PARAMETER ADJUSTMENT RULES
                                                     * DO NOT IGNORE "MODULEON" OR "MODULEOFF" STATES IN CURRENT MEMORY
                                                   - For audio effectors that are "On", create parameter values that are:
                                                   * DIFFERENT from current memory (e.g., if current has Drive: 0.72, neighbor should have 0.65 or 0.80, etc.)
                                                   * NOT identical between adjacent memories (each neighbor should have unique values)
                                                   * REALISTIC for the audio effect type (don't create extreme values that would sound bad)
                                                   - For other parameters (i.e., the parameter values of effectors), adjustments shall be made based on an understanding of the characteristics of these memory units. For instance, if the parameter value of a certain adjacent memory unit is smaller/larger than the corresponding parameter value of the new memory unit, it is necessary to increase/decrease that parameter value accordingly. This ensures that these parameters are more consistent with the features and style of the new memory unit.
                                                   - If no update is needed for certain parameters, keep them the same as the original.
                                                   Generate the new parameters in the sequential order of the input neighbors.
                                        3. Extract user preferences from the new memory parameters:
                                           - Identify which audio effects are consistently turned ON in the current memory
                                           - Determine preferred parameter values for each effect
                                           - Note any patterns in parameter combinations
                                           - Consider how these preferences align with the style and feature tags
                                        4. For each neighbor memory, analyze its parameters to extract user preferences following the same approach.

                                        Parameter should be determined by the content of these characteristic of these memories, which can be used to retrieve them later and categorize them.

                                        IMPORTANT: Return ONLY valid JSON format. Ensure all objects use curly braces {{}} and arrays use square brackets [].

                                        Return your decision in JSON format with the following structure:
                                        {{
                                            "should_evolve": true,
                                            "actions": ["strengthen", "update_neighbor"],
                                            "suggested_connections": ["neighbor_memory_ids"],
                                            "new_parameter_neighborhood": [
                                                {{"parameters_1": "corresponding to first song's parameters"}},
                                                {{"parameters_n": "corresponding to nth song's parameters"}}
                                            ]
                                        }}
                                        '''

        print(f"system_prompt3:{system_prompt3}")
        client = OpenAI(api_key=os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY", ""),
                        base_url="https://api.deepseek.com")
        user_prompt3 = f''
        response3 = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt3},
                {"role": "user", "content": user_prompt3},
            ],
            stream=False
        )

        # Get response3 response data and convert to JSON
        response_content3 = response3.choices[0].message.content
        # Remove code block markers and newlines from beginning and end
        cleaned_content3 = response_content3.replace("```json", "").replace("```", "").strip()
        try:
            result3 = json.loads(cleaned_content3)
            result3_str = json.dumps(result3, ensure_ascii=False)
            # Get whether to update memory
            should_evolve = result3.get("should_evolve", [])
            # Get actions
            actions = result3.get("actions", [])
            # Get connection suggestions
            suggested_connections = result3.get("suggested_connections", [])
            # Get neighbor's new parameters
            new_parameter_neighborhood = result3.get("new_parameter_neighborhood", [])

            # Print information
            print(f"Memory update model response: {result3_str}")
            print(f"user_message:{user_message}")

            # Add the following code after getting OpenAI response and parsing JSON
            if 'new_parameter_neighborhood' in result3:
                new_params_list = result3['new_parameter_neighborhood']
                total_updates = 0

                # Assume using first neighbor's parameters to update preset file
                if new_params_list:
                    for index, neighbor_params in enumerate(new_params_list):
                        print(f"new_params_list:{neighbor_params}")
                        # Convert parameter format to match Excel preset file
                        excel_params = {}

                        # Example: Update preset file parameters based on neighbor parameters
                        # Note: Need to adjust according to actual parameter mapping relationship
                        # (Reuse param_mapping here, consistent with new memory processing logic)

                        # 1. Priority processing top-level switch states (e.g., CompressorOff)
                        for key in neighbor_params:
                            if key in param_mapping:
                                # If switch state (mapping value is tuple), extract parameter name and value
                                if isinstance(param_mapping[key], tuple):
                                    param_id, param_value = param_mapping[key]
                                    excel_params[param_id] = param_value
                                    print(f"Processing switch state: {key} -> {param_id} = {param_value}")  # Log tracking

                        # 2. Process nested parameters (e.g., CompressorOn.Threshold etc.)
                        for key, value in neighbor_params.items():
                            if isinstance(value, dict):
                                # Process nested dictionary (e.g., DriverOn.Distortion)
                                for sub_key, sub_value in value.items():
                                    full_key = f"{key}.{sub_key}"
                                    if full_key in param_mapping:
                                        param_id = param_mapping[full_key]
                                        excel_params[param_id] = sub_value
                            else:
                                # Process non-nested parameter values (if any)
                                if key in param_mapping and not isinstance(param_mapping[key], tuple):
                                    param_id = param_mapping[key]
                                    excel_params[param_id] = value

                        # Print generated excel_params, verify pre_compressor_on is 0
                        print(f"Generated preset parameters: {excel_params.get('pre_compressor_on')}")
                        # Preset file path
                        if index < len(similar_songs):
                            song_name = similar_songs[index][0]
                            preset_file_path = fr"C:\Users\Public\Documents\Supertonal DSP\HCAP\{song_name}.preset"
                            try:
                                # Update preset file
                                if update_preset_in_file(preset_file_path, excel_params):
                                    print(f"Preset file {song_name}.preset updated successfully")
                                else:
                                    print(f"Preset file {song_name}.preset update failed, continue executing subsequent code")
                            except FileNotFoundError:
                                print(f"Preset file path {preset_file_path} does not exist, continue executing subsequent code")
                            except Exception as e:
                                print(f"Unknown error updating preset file: {e}, continue executing subsequent code")

                # Iterate through all similar songs
                for i, (song_name, similarity, _, _, _) in enumerate(similar_songs):
                    # Check if corresponding new parameters exist
                    if i < len(new_params_list):
                        new_params = new_params_list[i]
                        try:
                            # Convert parameters to JSON string
                            new_params_str = json.dumps(new_params, ensure_ascii=False)
                            cursor.execute(
                                "UPDATE music_responses SET Parameters =? WHERE SongName =?",
                                (new_params_str, song_name))
                            conn.commit()
                            print(f"Successfully updated '{song_name}' parameters (similarity: {similarity:.4f})")
                            total_updates += 1
                        except Exception as e:
                            print(f"Error updating '{song_name}' parameters: {e}")
                            conn.rollback()

                print(f"Total updated {total_updates} songs parameters")

                if total_updates < len(similar_songs):
                    print(f"Note: {len(similar_songs) - total_updates} songs have no corresponding new parameters")
            else:
                print("No new_parameter_neighborhood data found, cannot update parameters")
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON response: {cleaned_content3}")
            sys.exit(1)
    else:
        print(f"Memory system disabled")



# Read result1.txt file
result1_str = safe_open_file("result1.txt")
# Convert string to set
result1_set = set(result1_str.split(',')) if result1_str else set()

# Read result2.txt file
result2_str = safe_open_file("result2.txt")

# Read result.txt file
result_str = safe_open_file("result.txt")

# Connect to database
db_dir = os.environ.get('SUPERTONAL_DIR')
if not os.path.exists(db_dir):
    os.makedirs(db_dir)  # Create directory (if it doesn't exist)
db_path = os.path.join(db_dir, "music_info.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get index value
if len(sys.argv) > 0:
    if platform.system() == "Windows":
        chat_message = sys.argv[1]
        user_message = sys.argv[2].encode('cp936').decode('utf-8', errors='replace')
        currentPresetName = sys.argv[3].encode('cp936').decode('utf-8', errors='replace')
        memoryEnabled = sys.argv[4]
    else:
        chat_message = sys.argv[1]
        user_message = sys.argv[2]
        currentPresetName = sys.argv[3]
        memoryEnabled = sys.argv[4]
else:
    chat_message = sys.argv[1]
    user_message = sys.argv[2].encode('cp936').decode('utf-8', errors='replace')
    currentPresetName = sys.argv[3].encode('cp936').decode('utf-8', errors='replace')
    memoryEnabled = sys.argv[4]
 # Add judgment: if user_message is empty, use currentPresetName instead
if not user_message.strip():  # Handle empty string or whitespace-only case
    user_message = currentPresetName
print(f"chat_message: {chat_message}")  # Get first parameter passed from c++ program)
print(f"User message: {user_message}")  # Get second parameter passed from c++ program
print(f"currentPresetName: {currentPresetName}")
print(f"memoryEnabled: {memoryEnabled}")

parts = chat_message.split(',')
if len(parts) < 48:
    print("Command line parameter split list length less than 48, please check input.")
else:
    first_47 = parts[:48]
    # Convert first_47[0] to first_47[8] to float
    for i in range(9):
        first_47[i] = float(first_47[i])

    # Query matching records
    cursor.execute(
        "SELECT SongName, Parameters FROM music_responses WHERE SongName =?",
        (user_message,))
    row = cursor.fetchone()
    # If no matching record, add new data
    if row is None:
        parameters = json.loads(result_str)
        parameters = parameters_update(parameters)
        print(f"Update SongName: {user_message}")
        print(f"Update Parameters: {parameters}")
        print("-" * 50)
        cursor.execute("""
            INSERT INTO music_responses (SongName, Parameters, Preferences, Style, Feature)
            VALUES (?, ?, ?, ?, ?)
        """, (user_message, result_str, 'edit', result1_str, result2_str))
        conn.commit()
        update_parameters_to_database(parameters)
        #input("New record added, press Enter to close window...")
    # If there is matching record, update data
    else:
        song_name = row[0]
        parameters = json.loads(row[1])
        print(f"present parameters:{parameters}")

        parameters = parameters_update(parameters)

        # Convert updated parameters to string
        updated_parameters_str = json.dumps(parameters, ensure_ascii=False)

        # Update record in database
        cursor.execute("UPDATE music_responses SET Parameters =?, Preferences =? WHERE SongName =?",
                       (updated_parameters_str, "edit", song_name))
        conn.commit()
        # Print updated information
        print(f"Update SongName: {song_name}")
        print(f"Update Parameters: {parameters}")
        print("-" * 50)

        # ---------------------- Added: Update new memory (current song) preset file ----------------------

        # 2. Convert new memory parameters to preset file format
        new_memory_excel_params = {}
        # Process top-level switch states
        for key in parameters:
            if key in param_mapping and isinstance(param_mapping[key], tuple):
                param_id, param_value = param_mapping[key]
                new_memory_excel_params[param_id] = param_value
                print(f"New memory switch state processing: {key} -> {param_id} = {param_value}")

        # Process nested parameters
        for key, value in parameters.items():
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    full_key = f"{key}.{sub_key}"
                    if full_key in param_mapping:
                        param_id = param_mapping[full_key]
                        new_memory_excel_params[param_id] = sub_value
            else:
                if key in param_mapping and not isinstance(param_mapping[key], tuple):
                    param_id = param_mapping[key]
                    new_memory_excel_params[param_id] = value

        # 3. Define new memory preset file path
        new_memory_preset_path = fr"C:\Users\Public\Documents\Supertonal DSP\HCAP\{song_name}.preset"
        # 4. Update new memory preset file
        try:
            if update_preset_in_file(new_memory_preset_path, new_memory_excel_params):
                print(f"New memory '{song_name}' preset file updated successfully")
            else:
                print(f"New memory '{song_name}' preset file update failed")
        except FileNotFoundError:
            print(f"New memory preset file path does not exist: {new_memory_preset_path}")
        except Exception as e:
            print(f"Error updating new memory preset file: {e}")
        # ---------------------- Added end ----------------------

    update_parameters_to_database(parameters)

conn.close()

#input("Program execution completed, press Enter to close window...")