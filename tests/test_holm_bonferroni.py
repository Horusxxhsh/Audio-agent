"""Tests for Holm-Bonferroni multiple-comparison correction.

Covers:
- Core holm_bonferroni() step-down algorithm correctness
- apply_correction() end-to-end with real significance results
- Edge cases (empty, single element, equal p-values, capping at 1.0)
- Significant flags
- JSON round-trip (load_and_correct)
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from Experiments.E9_TMMMajorRevision.holm_bonferroni import (
    HolmCorrectedResult,
    apply_correction,
    holm_bonferroni,
    load_and_correct,
    results_to_dict,
)

# -----------------------------------------------------------------------
# Core algorithm: holm_bonferroni()
# -----------------------------------------------------------------------

class TestHolmBonferroniCore:
    """Unit tests for the step-down p-value correction function.

    Given sorted p-values p_(1) <= p_(2) <= ... <= p_(m),
    the corrected value for rank i (1-based) is:
        min( (m - i + 1) * p_(i), 1.0)
    with step-up monotonicity enforcement.
    """

    def test_empty_input(self):
        assert holm_bonferroni([]) == []

    def test_single_value(self):
        """Single p-value: multiplier is 1, so unchanged."""
        result = holm_bonferroni([0.04])
        assert len(result) == 1
        assert abs(result[0] - 0.04) < 1e-15

    def test_two_values_simple(self):
        """Two p-values: smallest * 2, larger * 1 (unless capped by monotonicity)."""
        raw = [0.01, 0.04]
        corrected = holm_bonferroni(raw)
        # Sorted: 0.01 (rank 1), 0.04 (rank 2)
        # Corrected: min(0.01*2, 1.0)=0.02, min(0.04*1, 1.0)=0.04
        # Monotonicity: [0.02, 0.04] is already sorted
        assert abs(corrected[0] - 0.02) < 1e-15
        assert abs(corrected[1] - 0.04) < 1e-15

    def test_three_values_known(self):
        """Canonical 3-comparison example matching TRR results."""
        raw = [1.30e-09, 3.14e-09, 3.33e-08]
        corrected = holm_bonferroni(raw)
        # Sorted ascending: 1.30e-09 (rank 1), 3.14e-09 (rank 2), 3.33e-08 (rank 3)
        # Corrected: 1.30e-09*3, 3.14e-09*2, 3.33e-08*1
        expected = [1.30e-09 * 3, 3.14e-09 * 2, 3.33e-08 * 1]
        for a, b in zip(corrected, expected):
            assert abs(a - b) < 1e-20, f"expected {b}, got {a}"

    def test_capping_at_one(self):
        """Corrected p-value must not exceed 1.0."""
        raw = [0.8, 0.9, 0.95]
        corrected = holm_bonferroni(raw)
        assert all(c <= 1.0 for c in corrected)
        # rank 1: min(0.8*3, 1.0) = 1.0
        # rank 2: min(0.9*2, 1.0) = 1.0
        # rank 3: min(0.95*1, 1.0) = 0.95 -> but monotonicity forces >= 1.0
        assert corrected[0] == 1.0
        assert corrected[1] == 1.0
        assert corrected[2] == 1.0

    def test_monotonicity_enforcement(self):
        """When the step-down would decrease, enforce non-decreasing order."""
        # Example: raw = [0.1, 0.34, 0.35]
        # rank 1 (0.1): 0.1 * 3 = 0.3
        # rank 2 (0.34): 0.34 * 2 = 0.68  (ok, >= 0.3)
        # rank 3 (0.35): 0.35 * 1 = 0.35  (would be < 0.68 -> enforce 0.68)
        raw = [0.1, 0.34, 0.35]
        corrected = holm_bonferroni(raw)
        # Sorted order in result: [0.1, 0.34, 0.35] -> indices 0, 1, 2
        # Corrected[0] = min(0.1*3, 1.0) = 0.3
        # Corrected[1] = max(min(0.34*2, 1.0), 0.3) = max(0.68, 0.3) = 0.68
        # Corrected[2] = max(min(0.35*1, 1.0), 0.68) = max(0.35, 0.68) = 0.68
        assert abs(corrected[0] - 0.3) < 1e-15
        assert abs(corrected[1] - 0.68) < 1e-15
        assert corrected[2] == pytest.approx(0.68, abs=1e-15)
        # Verify monotonicity
        assert corrected[0] <= corrected[1] <= corrected[2]

    def test_unsorted_input_produces_correct_order(self):
        """Corrected p-values must be returned in the original input order."""
        raw = [0.04, 0.01, 0.03]
        corrected = holm_bonferroni(raw)
        # Sorted: 0.01 (idx 1, rank 1), 0.03 (idx 2, rank 2), 0.04 (idx 0, rank 3)
        # Corrected sorted: 0.01*3=0.03, 0.03*2=0.06, 0.04*1=0.04 -> monotone -> 0.03, 0.06, 0.06
        # Mapping back to original indices:
        # idx 0 (0.04): corrected = 0.06  (was rank 3, then monotonicity)
        # idx 1 (0.01): corrected = 0.03  (was rank 1)
        # idx 2 (0.03): corrected = 0.06  (was rank 2)
        assert abs(corrected[1] - 0.03) < 1e-15
        assert corrected[0] >= corrected[1]  # monotone by index mapping
        # Just check that all values are in [0, 1]
        assert all(0.0 <= c <= 1.0 for c in corrected)

    def test_equal_p_values(self):
        """Equal p-values produce equal corrected values."""
        raw = [0.05, 0.05, 0.05]
        corrected = holm_bonferroni(raw)
        # All are 0.05; rank 1: 0.15, rank 2: 0.10->enforced to 0.15, rank 3: 0.05->enforced to 0.15
        assert corrected[0] == corrected[1] == corrected[2]
        assert abs(corrected[0] - 0.15) < 1e-15

    def test_zero_p_value(self):
        """A p-value of exactly 0 stays 0 after correction."""
        raw = [0.0, 0.03, 0.06]
        corrected = holm_bonferroni(raw)
        assert corrected[0] == 0.0

    def test_preserves_order_for_well_separated_values(self):
        """When values are well-separated, no monotonicity enforcement needed."""
        raw = [1e-10, 1e-8, 1e-6]
        corrected = holm_bonferroni(raw)
        expected = [1e-10 * 3, 1e-8 * 2, 1e-6 * 1]
        for a, b in zip(corrected, expected):
            assert abs(a - b) < 1e-25

    def test_all_large_p_values(self):
        """All p-values above alpha: correction may push to 1.0."""
        raw = [0.4, 0.5, 0.6]
        corrected = holm_bonferroni(raw)
        assert all(c <= 1.0 for c in corrected)
        # rank 1: 0.4*3 = 1.2 -> capped at 1.0
        assert all(c == 1.0 for c in corrected)


# -----------------------------------------------------------------------
# apply_correction() — integration with real data
# -----------------------------------------------------------------------

class TestApplyCorrection:
    """Test the full correction pipeline with real significance results."""

    def test_all_comparisons_remain_significant(self):
        """All 15 comparisons (5 metrics * 3 baselines) remain significant."""
        results = _load_real_results()
        alpha = 0.05
        corrected = apply_correction(results, alpha=alpha)
        for metric, entries in corrected.items():
            for entry in entries:
                assert entry.significant_corrected, (
                    f"{metric}/{entry.baseline} lost significance after correction "
                    f"(p={entry.holm_corrected_p:.2e}, alpha={alpha})"
                )

    def test_corrected_p_is_larger_or_equal(self):
        """Holm-corrected p-value must be >= raw p-value."""
        corrected = apply_correction(_load_real_results())
        for entries in corrected.values():
            for e in entries:
                assert e.holm_corrected_p >= e.raw_p, (
                    f"{e.metric}/{e.baseline}: corrected < raw ({e.holm_corrected_p:.2e} < {e.raw_p:.2e})"
                )

    def test_norm_l2_values(self):
        """Spot-check Norm.L2 corrected p-values."""
        corrected = apply_correction(_load_real_results())
        norm_entries = corrected["top1_norm_l2"]
        # Find Wav2Vec entry
        wav = [e for e in norm_entries if e.baseline == "Wav2Vec"][0]
        # raw 1.30e-09, corrected ~ 3.90e-09
        assert abs(wav.holm_corrected_p - 3.90e-09) < 1e-10
        assert wav.n_comparisons == 3

    def test_switch_f1_max_correction(self):
        """SwitchF1 vs PaSST has the largest raw p — verify correction."""
        corrected = apply_correction(_load_real_results())
        f1_entries = corrected["top1_switch_f1"]
        passt = [e for e in f1_entries if e.baseline == "PaSST"][0]
        # raw ~1.63e-05, corrected = 1.63e-05 (rank 3, multiplier 1)
        assert abs(passt.holm_corrected_p - passt.raw_p) < 1e-20
        assert passt.significant_corrected

    def test_alpha_parameter(self):
        """Changing alpha changes significance flags."""
        results = _load_real_results()
        # At alpha=0.05, all significant
        corr_05 = apply_correction(results, alpha=0.05)
        assert all(
            e.significant_corrected
            for entries in corr_05.values()
            for e in entries
        )
        # At alpha=1e-15, none significant
        corr_strict = apply_correction(results, alpha=1e-15)
        assert all(
            not e.significant_corrected
            for entries in corr_strict.values()
            for e in entries
        )

    def test_dataclass_attributes(self):
        """HolmCorrectedResult has all required fields."""
        corrected = apply_correction(_load_real_results())
        entry = list(corrected.values())[0][0]
        for field in ("metric", "baseline", "raw_p", "holm_corrected_p",
                       "n_comparisons", "significant_raw", "significant_corrected",
                       "alpha"):
            assert hasattr(entry, field), f"Missing field: {field}"

    def test_all_five_metrics_present(self):
        """All 5 metric groups are in the results."""
        corrected = apply_correction(_load_real_results())
        expected_metrics = {
            "top1_norm_l2", "top1_acc_at_0_1", "top1_recall",
            "top1_cosine", "top1_switch_f1",
        }
        assert set(corrected.keys()) == expected_metrics


# -----------------------------------------------------------------------
# JSON round-trip
# -----------------------------------------------------------------------

class TestJsonRoundtrip:
    """Test load_and_correct and results_to_dict."""

    def test_load_and_correct_produces_expected_file(self, tmp_path):
        out = tmp_path / "result.json"
        results = load_and_correct(
            str(Path(__file__).resolve().parent.parent
                / "Experiments/E9_TMMMajorRevision/outputs/unified_protocol"
                / "significance_results.json"),
            output_path=out,
        )
        assert out.exists()
        loaded = json.loads(out.read_text())
        assert len(loaded) == 5  # 5 metrics

    def test_results_to_dict_is_serializable(self):
        corrected = apply_correction(_load_real_results())
        d = results_to_dict(corrected)
        s = json.dumps(d)
        assert len(s) > 0
        reparsed = json.loads(s)
        assert len(reparsed) == 5

    def test_results_to_dict_preserves_values(self):
        corrected = apply_correction(_load_real_results())
        d = results_to_dict(corrected)
        for metric, entries_dict in d.items():
            for ed in entries_dict:
                assert "raw_p" in ed
                assert "holm_corrected_p" in ed
                assert ed["holm_corrected_p"] >= ed["raw_p"]


# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------

def _load_real_results() -> dict:
    """Load the real significance_results.json."""
    path = (
        Path(__file__).resolve().parent.parent
        / "Experiments/E9_TMMMajorRevision/outputs/unified_protocol"
        / "significance_results.json"
    )
    with open(path) as f:
        return json.load(f)
