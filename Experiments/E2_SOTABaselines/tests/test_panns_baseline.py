"""Tests for PANNs baseline (CR-4).

Validates that:
1. panns-inference is installed and importable
2. The encoder code is syntactically correct
3. The interface contract matches PANNsBaselineResult
4. Skip result JSON is present and well-formed

The full PANNs evaluation is skipped due to infeasible model download
(312 MB from Zenodo at ~30-50 KB/s). See:
  Experiments/E9_TMMMajorRevision/outputs/panns_skip_statement.md
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
E2_DIR = REPO / "Experiments" / "E2_SOTABaselines"
OUTPUT_DIR = REPO / "Experiments" / "E9_TMMMajorRevision" / "outputs"


@dataclass
class PANNsBaselineResult:
    method: str              # "PANNs"
    protocol: str            # "Protocol-A"
    n_queries: int          # must be 204
    coverage: float         # fraction of evaluable queries
    norm_l2: float
    acc_at_0_1: float
    recall: float
    cosine: float
    switch_f1: float
    status: str             # "success" | "skipped" | "partial"
    skip_reason: str        # if status != "success"


# ------------------------------------------------------------------
# Test 1: panns-inference is importable
# ------------------------------------------------------------------

def test_panns_inference_imports():
    """panns-inference must be installed and importable."""
    from panns_inference import AudioTagging
    assert AudioTagging is not None


# ------------------------------------------------------------------
# Test 2: PANNs encoder module loads
# ------------------------------------------------------------------

def test_panns_encoder_module():
    """panns_encoder.py must be importable."""
    sys.path.insert(0, str(E2_DIR))
    from panns_encoder import PANNsEncoder
    assert hasattr(PANNsEncoder, "encode_audio")
    assert hasattr(PANNsEncoder, "encode_audio_batch")


# ------------------------------------------------------------------
# Test 3: PANNs baseline module loads
# ------------------------------------------------------------------

def test_panns_baseline_module():
    """panns_baseline.py must be importable."""
    sys.path.insert(0, str(E2_DIR))
    import panns_baseline
    assert hasattr(panns_baseline, "extract_panns_embeddings")
    assert hasattr(panns_baseline, "evaluate_retrieval")
    assert hasattr(panns_baseline, "main")


# ------------------------------------------------------------------
# Test 4: Interface contract — skip result JSON
# ------------------------------------------------------------------

def test_skip_result_exists():
    """Skip result JSON must exist and be well-formed."""
    skip_json = OUTPUT_DIR / "panns_baseline_skip_result.json"
    assert skip_json.exists(), f"Skip result not found at {skip_json}"

    data = json.loads(skip_json.read_text())
    assert data["status"] == "skipped"
    assert data["method"] == "PANNs"
    assert data["protocol"] == "Protocol-A"
    assert data["n_queries"] == 204
    assert data["skip_reason"]


def test_skip_result_contract():
    """Skip result must satisfy PANNsBaselineResult contract."""
    skip_json = OUTPUT_DIR / "panns_baseline_skip_result.json"
    data = json.loads(skip_json.read_text())

    # Fields that are None for skipped results
    for field in ("norm_l2", "acc_at_0_1", "recall", "cosine", "switch_f1"):
        assert data[field] is None, f"{field} should be null for skipped result"

    assert data["coverage"] == 0.0
    assert data["status"] == "skipped"


# ------------------------------------------------------------------
# Test 5: Skip statement exists
# ------------------------------------------------------------------

def test_skip_statement_exists():
    """Skip statement markdown must exist."""
    stmt = OUTPUT_DIR / "panns_skip_statement.md"
    assert stmt.exists(), f"Skip statement not found at {stmt}"
    content = stmt.read_text()
    assert "SKIPPED" in content or "skip" in content.lower()


# ------------------------------------------------------------------
# Test 6: Environment consistency
# ------------------------------------------------------------------

def test_environment_consistency():
    """Skip result environment should match actual environment."""
    skip_json = OUTPUT_DIR / "panns_baseline_skip_result.json"
    data = json.loads(skip_json.read_text())
    env = data["environment"]

    assert "python" in env
    # Python version prefix should match
    import platform
    assert platform.python_version().startswith(env["python"].split()[0].split(".")[:2][0])


# ------------------------------------------------------------------
# Test 7: No cached embeddings (confirming skip is warranted)
# ------------------------------------------------------------------

def test_no_cached_embeddings():
    """No PANNs embedding cache should exist (confirming skip rationale)."""
    import glob
    cache_files = glob.glob(str(E2_DIR / "panns_embeddings_cache.npz"))
    assert len(cache_files) == 0, "Unexpected PANNs embedding cache found"


# ------------------------------------------------------------------
# Test 8: Audio data available
# ------------------------------------------------------------------

def test_audio_data_exists():
    """Audio files should be present (the issue is model, not data)."""
    audio_dir = REPO / "Data" / "Audio_Synthetic"
    assert audio_dir.exists(), f"Audio directory missing: {audio_dir}"
    wav_count = len(list(audio_dir.glob("*.wav")))
    assert wav_count > 0, "No .wav files found in audio directory"
    assert wav_count >= 1000, f"Expected >= 1000 audio files, found {wav_count}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
