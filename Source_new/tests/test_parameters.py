"""Tests for parameter processing module."""

from __future__ import annotations

import json

import pytest

from core.parameters import (
    EFFECTOR_CONFIG,
    EffectorDefaults,
    ParameterProcessor,
)


class TestEffectorConfig:
    def test_all_effectors_have_defaults(self):
        for cfg in EFFECTOR_CONFIG:
            assert cfg.defaults, f"{cfg.name} missing defaults"
            assert cfg.on_key.endswith("On")
            assert cfg.off_key.endswith("Off")

    def test_effectors_count(self):
        assert len(EFFECTOR_CONFIG) == 9

    def test_compressor_config(self):
        comp = EFFECTOR_CONFIG[0]
        assert comp.name == "compression"
        assert comp.on_key == "CompressorOn"
        assert comp.toggle_index == 0
        assert "Threshold" in comp.defaults

    def test_distortion_config(self):
        dist = EFFECTOR_CONFIG[2]
        assert dist.name == "distortion"
        assert dist.on_key == "DriverOn"


class TestParameterProcessor:
    def test_toggle_on(self):
        params = {"CompressorOff": {"Ratio": 1}}
        toggles = [1.0]
        result = ParameterProcessor.apply_toggles(params, toggles)
        assert "CompressorOn" in result
        assert "CompressorOff" not in result

    def test_toggle_off_injects_defaults(self):
        params = {"CompressorOn": {"Ratio": 4.0}}
        toggles = [0.0]
        result = ParameterProcessor.apply_toggles(params, toggles)
        assert "CompressorOff" in result
        assert result["CompressorOff"]["Ratio"] == 1  # default Off value

    def test_toggle_multiple_effectors(self):
        params = {
            "ScreamerOff": {"Drive": 0.0},
            "DriverOn": {"Distortion": 0.8},
        }
        toggles = [0.0, 1.0, 0.0]  # comp=off, screamer=on, driver=off
        result = ParameterProcessor.apply_toggles(params, toggles)
        assert "ScreamerOn" in result
        assert "DriverOff" in result

    def test_serialise(self):
        params = {"ReverbOn": {"Size": 0.75}}
        output = ParameterProcessor.serialise(params)
        assert isinstance(output, str)
        parsed = json.loads(output)
        assert parsed == params

    def test_to_preset_params(self):
        params = {
            "CompressorOn": {"Ratio": 4.0},
        }
        mapping = {
            "CompressorOn": (1, "tuple_switch"),
            "CompressorOn.Ratio": 2,
        }
        result = ParameterProcessor.to_preset_params(params, mapping)
        assert 2 in result
        assert result[2] == 4.0
