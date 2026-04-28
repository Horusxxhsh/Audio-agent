"""
E3: Audio Degradation for Realistic Noise Protocol-C

Implements realistic audio degradations:
1. AWGN (Additive White Gaussian Noise)
2. MP3 compression
3. Reverberation (using Room Impulse Response)
4. Truncation

Author: Claude
Date: 2026-03-05
"""

import logging
from dataclasses import dataclass
from typing import Optional, Tuple
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class DegradationConfig:
    """Configuration for audio degradation."""
    # AWGN
    snr_db: float = 20.0  # Signal-to-noise ratio in dB

    # MP3 compression
    mp3_bitrate: str = "64k"  # Options: "32k", "64k", "128k"

    # Reverberation
    rt60: float = 0.5  # Reverberation time in seconds
    room_scale: str = "small"  # Options: "small", "medium", "large"

    # Truncation
    truncation_ratio: float = 0.5  # Keep first X% of audio


class AudioDegrader:
    """
    Applies realistic degradations to audio signals.
    """

    def __init__(self, config: Optional[DegradationConfig] = None):
        self.config = config or DegradationConfig()

    def add_awgn_noise(
        self,
        audio: np.ndarray,
        snr_db: Optional[float] = None
    ) -> np.ndarray:
        """
        Add Additive White Gaussian Noise (AWGN) to audio.

        Args:
            audio: Input audio signal
            snr_db: Signal-to-noise ratio in dB (default: from config)

        Returns:
            Noisy audio signal
        """
        if snr_db is None:
            snr_db = self.config.snr_db

        # Calculate signal power
        signal_power = np.mean(audio ** 2)

        # Calculate noise power for target SNR
        snr_linear = 10 ** (snr_db / 10)
        noise_power = signal_power / snr_linear

        # Generate white noise
        noise = np.random.randn(len(audio)) * np.sqrt(noise_power)

        # Add noise to signal
        noisy_audio = audio + noise

        logger.debug(f"Added AWGN with SNR={snr_db}dB")
        return noisy_audio

    def apply_mp3_compression(
        self,
        audio: np.ndarray,
        sample_rate: int,
        bitrate: Optional[str] = None,
        temp_path: str = "/tmp/temp_audio.mp3"
    ) -> np.ndarray:
        """
        Apply MP3 compression degradation.

        Args:
            audio: Input audio signal
            sample_rate: Sample rate
            bitrate: MP3 bitrate (e.g., "64k", "32k")
            temp_path: Temporary file path for MP3

        Returns:
            Degraded audio after MP3 compression
        """
        try:
            import pydub
        except ImportError:
            logger.error("pydub not installed. Install with: pip install pydub")
            raise

        if bitrate is None:
            bitrate = self.config.mp3_bitrate

        # Save to temporary WAV
        temp_wav = temp_path.replace('.mp3', '.wav')
        sf.write(temp_wav, audio, sample_rate)

        # Convert to MP3
        from pydub import AudioSegment
        audio_segment = AudioSegment.from_wav(temp_wav)
        audio_segment.export(temp_path, format="mp3", bitrate=bitrate)

        # Load back
        degraded_segment = AudioSegment.from_mp3(temp_path)

        # Convert to numpy array
        degraded_audio = np.array(degraded_segment.get_array_of_samples(), dtype=np.float32)

        # Normalize
        if degraded_audio.max() > 1.0:
            degraded_audio = degraded_audio / 32768.0  # 16-bit normalization

        # Cleanup
        Path(temp_wav).unlink(missing_ok=True)
        Path(temp_path).unlink(missing_ok=True)

        logger.debug(f"Applied MP3 compression at {bitrate}")
        return degraded_audio

    def generate_synthetic_rir(
        self,
        rt60: Optional[float] = None,
        room_scale: Optional[str] = None,
        sample_rate: int = 16000
    ) -> np.ndarray:
        """
        Generate synthetic Room Impulse Response (RIR).

        When real RIR dataset is not available, use synthetic RIR.

        Args:
            rt60: Reverberation time in seconds
            room_scale: Room size ("small", "medium", "large")
            sample_rate: Sample rate

        Returns:
            Synthetic RIR
        """
        if rt60 is None:
            rt60 = self.config.rt60
        if room_scale is None:
            room_scale = self.config.room_scale

        # Room dimensions based on scale
        room_dims = {
            "small": (3, 4, 3),    # 3x4x3 meters (bedroom)
            "medium": (5, 7, 3),   # 5x7x3 meters (living room)
            "large": (10, 15, 5)   # 10x15x5 meters (hall)
        }

        Lx, Ly, Lz = room_dims.get(room_scale, room_dims["medium"])

        # Calculate room volume and surface area
        volume = Lx * Ly * Lz
        surface_area = 2 * (Lx*Ly + Lx*Lz + Ly*Lz)

        # Estimate absorption coefficient from RT60
        # Sabine's formula: RT60 = 0.161 * V / (A * alpha)
        # Approximate: alpha ≈ 0.161 * V / (A * RT60)
        alpha = 0.161 * volume / (surface_area * rt60)
        alpha = np.clip(alpha, 0.1, 0.9)  # Realistic range

        # Generate exponential decay
        duration = min(rt60 * 3, 2.0)  # 3x RT60 or max 2 seconds
        n_samples = int(duration * sample_rate)
        t = np.arange(n_samples) / sample_rate

        # Exponential decay envelope
        envelope = np.exp(-t * 6.907 / rt60)  # -60dB at RT60

        # Add reflections (spikes)
        rir = np.random.randn(n_samples) * envelope * 0.1

        # Add early reflections (discrete spikes)
        n_reflections = min(int(rt60 * 10), 50)
        for _ in range(n_reflections):
            delay = np.random.uniform(0.01, rt60 * 0.8)
            amp = np.random.uniform(0.05, 0.3) * np.exp(-delay / rt60)
            sample_idx = int(delay * sample_rate)
            if sample_idx < n_samples:
                rir[sample_idx] += amp * np.random.choice([-1, 1])

        # Normalize
        rir = rir / np.max(np.abs(rir))

        logger.debug(f"Generated synthetic RIR: RT60={rt60}s, scale={room_scale}")
        return rir

    def apply_reverberation(
        self,
        audio: np.ndarray,
        rir: Optional[np.ndarray] = None,
        rt60: Optional[float] = None,
        room_scale: Optional[str] = None,
        sample_rate: int = 16000
    ) -> np.ndarray:
        """
        Apply reverberation using convolution with RIR.

        Args:
            audio: Input audio signal
            rir: Room Impulse Response (if None, generate synthetic)
            rt60: Reverberation time (for synthetic RIR)
            room_scale: Room scale (for synthetic RIR)
            sample_rate: Sample rate

        Returns:
            Reverberant audio
        """
        if rir is None:
            rir = self.generate_synthetic_rir(rt60, room_scale, sample_rate)

        # Convolve audio with RIR
        reverberant = signal.convolve(audio, rir, mode='full')

        # Trim to original length
        reverberant = reverberant[:len(audio)]

        # Normalize
        reverberant = reverberant / np.max(np.abs(reverberant)) * np.max(np.abs(audio))

        logger.debug(f"Applied reverberation with RT60={rt60 or self.config.rt60}s")
        return reverberant

    def apply_truncation(
        self,
        audio: np.ndarray,
        truncation_ratio: Optional[float] = None
    ) -> np.ndarray:
        """
        Truncate audio to simulate early cut-off.

        Args:
            audio: Input audio signal
            truncation_ratio: Ratio of audio to keep (0-1)

        Returns:
            Truncated audio
        """
        if truncation_ratio is None:
            truncation_ratio = self.config.truncation_ratio

        n_samples = int(len(audio) * truncation_ratio)
        truncated = audio[:n_samples]

        logger.debug(f"Truncated audio to {truncation_ratio*100:.0f}%")
        return truncated

    def apply_degradation(
        self,
        audio: np.ndarray,
        sample_rate: int,
        degradation_type: str,
        **kwargs
    ) -> np.ndarray:
        """
        Apply specified degradation.

        Args:
            audio: Input audio signal
            sample_rate: Sample rate
            degradation_type: Type of degradation
                            ('awgn', 'mp3', 'reverb', 'truncate')
            **kwargs: Additional arguments for specific degradation

        Returns:
            Degraded audio
        """
        degradations = {
            'awgn': self.add_awgn_noise,
            'mp3': lambda a, sr: self.apply_mp3_compression(a, sr, **kwargs),
            'reverb': lambda a, sr: self.apply_reverberation(a, sample_rate=sr, **kwargs),
            'truncate': self.apply_truncation
        }

        if degradation_type not in degradations:
            raise ValueError(f"Unknown degradation type: {degradation_type}")

        return degradations[degradation_type](audio, sample_rate)

    def get_degradation_variants(self) -> dict:
        """
        Get all degradation variants for Protocol-C.

        Returns:
            Dictionary of degradation configurations
        """
        return {
            'clean': None,
            'awgn_snr20': {'type': 'awgn', 'snr_db': 20},
            'awgn_snr10': {'type': 'awgn', 'snr_db': 10},
            'awgn_snr5': {'type': 'awgn', 'snr_db': 5},
            'mp3_128k': {'type': 'mp3', 'bitrate': '128k'},
            'mp3_64k': {'type': 'mp3', 'bitrate': '64k'},
            'mp3_32k': {'type': 'mp3', 'bitrate': '32k'},
            'reverb_small': {'type': 'reverb', 'rt60': 0.3, 'room_scale': 'small'},
            'reverb_medium': {'type': 'reverb', 'rt60': 0.6, 'room_scale': 'medium'},
            'reverb_large': {'type': 'reverb', 'rt60': 1.0, 'room_scale': 'large'},
            'truncate_50': {'type': 'truncate', 'truncation_ratio': 0.5},
            'truncate_30': {'type': 'truncate', 'truncation_ratio': 0.3},
        }


# Example usage
if __name__ == "__main__":
    # Create test audio
    sample_rate = 16000
    duration = 3.0
    t = np.linspace(0, duration, int(sample_rate * duration))
    test_audio = np.sin(2 * np.pi * 440 * t)  # 440 Hz sine wave

    # Initialize degrader
    degrader = AudioDegrader()

    # Apply various degradations
    print("Applying degradations...")

    # AWGN
    noisy = degrader.add_awgn_noise(test_audio, snr_db=10)
    print(f"  AWGN: SNR=10dB, shape={noisy.shape}")

    # Reverberation
    reverberant = degrader.apply_reverberation(test_audio, sample_rate=sample_rate)
    print(f"  Reverb: RT60=0.5s, shape={reverberant.shape}")

    # Truncation
    truncated = degrader.apply_truncation(test_audio, truncation_ratio=0.5)
    print(f"  Truncation: 50%, shape={truncated.shape}")

    print("\nAll degradations applied successfully!")
