"""Parameter processing and effector configuration.

Centralises the effector definitions, default values, and
On/Off toggle logic that was previously duplicated across the codebase.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
#  Effector metadata ------------------------------------------------ #
# ------------------------------------------------------------------ #

@dataclass
class EffectorDefaults:
    """Default parameter values for the *Off* state of an effector."""

    name: str               # e.g. "compression"
    on_key: str             # e.g. "CompressorOn"
    off_key: str            # e.g. "CompressorOff"
    defaults: dict[str, float | int]  # Off-state param → value

    toggle_index: int = -1  # Index in first_47 array (-1 = n/a)


EFFECTOR_CONFIG: list[EffectorDefaults] = [
    EffectorDefaults(
        name="compression",
        on_key="CompressorOn",
        off_key="CompressorOff",
        toggle_index=0,
        defaults={
            "Threshold": -128.0,
            "Ratio": 1,
            "Attack": 0.0,
            "Release": 0.0,
            "Makeup": -12.0,
            "Mix": 0.0,
        },
    ),
    EffectorDefaults(
        name="overload",
        on_key="ScreamerOn",
        off_key="ScreamerOff",
        toggle_index=1,
        defaults={
            "Drive": 0.0,
            "Tone": 0.0,
            "Level": -64.0,
        },
    ),
    EffectorDefaults(
        name="distortion",
        on_key="DriverOn",
        off_key="DriverOff",
        toggle_index=2,
        defaults={
            "Distortion": 0.0,
            "Volume": -64.0,
        },
    ),
    EffectorDefaults(
        name="delay",
        on_key="DelayOn",
        off_key="DelayOff",
        toggle_index=3,
        defaults={
            "Feedback": 0.0,
            "Delay": 1.0,
            "Mix": 0.0,
        },
    ),
    EffectorDefaults(
        name="reverb",
        on_key="ReverbOn",
        off_key="ReverbOff",
        toggle_index=4,
        defaults={
            "Size": 0.0,
            "Damping": 0.0,
            "Width": 0.0,
            "Mix": 0.0,
        },
    ),
    EffectorDefaults(
        name="chorus",
        on_key="ChorusOn",
        off_key="ChorusOff",
        toggle_index=5,
        defaults={
            "Delay": 0.010,
            "Depth": 0.0,
            "Frequency": 0.05,
            "Width": 0.010,
        },
    ),
    EffectorDefaults(
        name="flanger",
        on_key="FlangerOn",
        off_key="FlangerOff",
        toggle_index=6,
        defaults={
            "Delay": 0.001,
            "Depth": 0.0,
            "Feedback": 0.0,
            "Frequency": 0.05,
            "Width": 0.001,
        },
    ),
    EffectorDefaults(
        name="phase",
        on_key="PhaserOn",
        off_key="PhaserOff",
        toggle_index=7,
        defaults={
            "Depth": 0.0,
            "Feedback": 0.0,
            "Frequency": 0.05,
            "Width": 50,
        },
    ),
    EffectorDefaults(
        name="equalization",
        on_key="EqualiserOn",
        off_key="EqualiserOff",
        toggle_index=8,
        defaults={
            "100hz": 0.0,
            "200hz": 0.0,
            "400hz": 0.0,
            "800hz": 0.0,
            "1600hz": 0.0,
            "3200hz": 0.0,
            "6400hz": 0.0,
            "Level": 0.0,
        },
    ),
]


# ------------------------------------------------------------------ #
#  ParameterProcessor ------------------------------------------------ #
# ------------------------------------------------------------------ #

class ParameterProcessor:
    """Applies On/Off toggles and default-value injection."""

    @staticmethod
    def apply_toggles(
        parameters: dict[str, Any],
        toggles: list[float],
    ) -> dict[str, Any]:
        """Update *parameters* according to binary *toggles*.

        Each ``toggles[i]`` is ``1.0`` (enable → ``*On``) or
        ``0.0`` (disable → ``*Off``).  Disabled effectors receive
        their default ``Off`` parameter values.

        Args:
            parameters: Raw parameter dict from LLM or DB.
            toggles: Float list (length ≥ len(EFFECTOR_CONFIG)).

        Returns:
            Normalised parameter dict.
        """
        for cfg in EFFECTOR_CONFIG:
            if cfg.toggle_index < 0 or cfg.toggle_index >= len(toggles):
                continue
            state = toggles[cfg.toggle_index]

            if state == 1.0 and cfg.off_key in parameters:
                # Flip Off → On
                params = parameters.pop(cfg.off_key)
                parameters[cfg.on_key] = params
            elif state == 0.0 and cfg.on_key in parameters:
                # Flip On → Off
                params = parameters.pop(cfg.on_key)
                parameters[cfg.off_key] = params

            # Always inject Off defaults when present
            if cfg.off_key in parameters:
                for k, v in cfg.defaults.items():
                    if isinstance(parameters[cfg.off_key], dict):
                        parameters[cfg.off_key][k] = v
                    else:
                        parameters[cfg.off_key] = cfg.defaults.copy()

        return parameters

    @staticmethod
    def to_preset_params(
        parameters: dict[str, Any],
        param_mapping: dict[str, int | tuple[int, Any]],
    ) -> dict[int, Any]:
        """Convert nested parameter dict to flat preset-id → value mapping.

        Args:
            parameters: Nested dict (e.g. ``{"CompressorOn": {"Ratio": 4.0}}``).
            param_mapping: Mapping from full key to preset ID (or tuple).

        Returns:
            Flat dict ``{preset_id: value, ...}``.
        """
        result: dict[int, Any] = {}

        # Top-level switches
        for key in parameters:
            if key in param_mapping and isinstance(param_mapping[key], tuple):
                param_id, param_value = param_mapping[key]
                result[param_id] = param_value

        # Nested parameters
        for key, value in parameters.items():
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    full_key = f"{key}.{sub_key}"
                    if full_key in param_mapping:
                        result[param_mapping[full_key]] = sub_value  # type: ignore[arg-type]
            else:
                if key in param_mapping and not isinstance(
                    param_mapping[key], tuple
                ):
                    result[param_mapping[key]] = value  # type: ignore[arg-type]

        return result

    @staticmethod
    def serialise(parameters: dict[str, Any]) -> str:
        """Return compact JSON string of *parameters*."""
        return json.dumps(parameters, ensure_ascii=False)
