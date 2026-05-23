"""Tests for EPR sensitivity analysis (MA-1).

Validates:
  - Grid completeness: K x tau = 4 x 5 = 20 configurations
  - Output format: EPRGridResult dataclass fields
  - Reasonable value ranges
  - K=5, tau=0.05 is within expected range
  - Heatmap was generated
"""
from __future__ import annotations

import csv
import json
import sys
from dataclasses import dataclass, fields
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

OUTPUT_DIR = REPO_ROOT / "Experiments" / "E9_TMMMajorRevision" / "outputs" / "epr_sensitivity"
CSV_PATH = OUTPUT_DIR / "epr_sensitivity_summary.csv"
JSON_PATH = OUTPUT_DIR / "epr_sensitivity_summary.json"
HEATMAP_PATH = OUTPUT_DIR / "epr_sensitivity_heatmap.png"

EXPECTED_KS = [3, 5, 10, 20]
EXPECTED_TEMPS = [0.01, 0.05, 0.10, 0.20, 0.50]
EXPECTED_GRID_SIZE = len(EXPECTED_KS) * len(EXPECTED_TEMPS)  # 20
EXPECTED_N_QUERIES = 204

# Required fields per EPRGridResult interface contract
REQUIRED_FIELDS = [
    "k", "temperature", "norm_l2", "acc_at_0_1", "recall",
    "cosine", "switch_f1", "n_eff", "max_wi", "n_queries",
]


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def _load_json_results() -> list[dict]:
    return json.loads(JSON_PATH.read_text(encoding="utf-8"))


def _load_csv_results() -> list[dict]:
    with CSV_PATH.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _get_result_by_config(results: list[dict], k: int, temperature: float) -> dict | None:
    for r in results:
        if r["k"] == k and abs(r["temperature"] - temperature) < 1e-6:
            return r
    return None


# ------------------------------------------------------------------
# Fixture
# ------------------------------------------------------------------
@pytest.fixture(scope="module")
def json_results():
    return _load_json_results()


@pytest.fixture(scope="module")
def csv_results():
    return _load_csv_results()


# ------------------------------------------------------------------
# Grid completeness
# ------------------------------------------------------------------
class TestGridCompleteness:
    def test_output_files_exist(self):
        assert CSV_PATH.exists(), f"CSV not found at {CSV_PATH}"
        assert JSON_PATH.exists(), f"JSON not found at {JSON_PATH}"
        assert HEATMAP_PATH.exists(), f"Heatmap not found at {HEATMAP_PATH}"

    def test_grid_size(self, json_results):
        assert len(json_results) == EXPECTED_GRID_SIZE, (
            f"Expected {EXPECTED_GRID_SIZE} results, got {len(json_results)}"
        )

    def test_all_k_present(self, json_results):
        observed = sorted({r["k"] for r in json_results})
        assert observed == EXPECTED_KS, f"Expected Ks={EXPECTED_KS}, got {observed}"

    def test_all_temperatures_present(self, json_results):
        observed = sorted({r["temperature"] for r in json_results})
        # Float comparison
        for expected_t in EXPECTED_TEMPS:
            match = any(abs(o - expected_t) < 1e-6 for o in observed)
            assert match, f"Temperature {expected_t} not found in {observed}"

    def test_full_grid_coverage(self, json_results):
        """Every (K, tau) combination has exactly one result."""
        pairs = {(r["k"], round(r["temperature"], 4)) for r in json_results}
        expected = {(k, t) for k in EXPECTED_KS for t in EXPECTED_TEMPS}
        assert pairs == expected, f"Missing or extra pairs: diff={expected ^ pairs}"

    def test_n_queries_is_204(self, json_results):
        for r in json_results:
            assert r["n_queries"] == EXPECTED_N_QUERIES, (
                f"Expected n_queries={EXPECTED_N_QUERIES}, got {r['n_queries']} for "
                f"K={r['k']}, tau={r['temperature']}"
            )


# ------------------------------------------------------------------
# Output format (EPRGridResult contract)
# ------------------------------------------------------------------
class TestOutputFormat:
    def test_required_fields_present_json(self, json_results):
        for r in json_results:
            for field in REQUIRED_FIELDS:
                assert field in r, f"Field '{field}' missing from result: {r}"

    def test_required_fields_present_csv(self, csv_results):
        if not csv_results:
            pytest.skip("No CSV results")
        for field in REQUIRED_FIELDS:
            assert field in csv_results[0], (
                f"Field '{field}' missing from CSV header: {list(csv_results[0].keys())}"
            )

    def test_types(self, json_results):
        for r in json_results:
            assert isinstance(r["k"], int), f"k should be int, got {type(r['k'])}"
            assert isinstance(r["temperature"], float), f"temperature should be float"
            assert isinstance(r["norm_l2"], float), f"norm_l2 should be float"
            assert isinstance(r["acc_at_0_1"], float), f"acc_at_0_1 should be float"
            assert isinstance(r["recall"], float), f"recall should be float"
            assert isinstance(r["cosine"], float), f"cosine should be float"
            assert isinstance(r["switch_f1"], float), f"switch_f1 should be float"
            assert isinstance(r["n_eff"], float), f"n_eff should be float"
            assert isinstance(r["max_wi"], float), f"max_wi should be float"
            assert isinstance(r["n_queries"], int), f"n_queries should be int"

    def test_value_ranges_norm_l2(self, json_results):
        """norm_l2 should be in [0, 1] (normalized RMSE)."""
        for r in json_results:
            assert 0.0 <= r["norm_l2"] <= 1.0, (
                f"norm_l2={r['norm_l2']} out of [0, 1] for K={r['k']}, tau={r['temperature']}"
            )

    def test_value_ranges_acc_at_0_1(self, json_results):
        """acc@0.1 should be in [0, 1]."""
        for r in json_results:
            assert 0.0 <= r["acc_at_0_1"] <= 1.0, (
                f"acc_at_0_1={r['acc_at_0_1']} out of [0, 1]"
            )

    def test_value_ranges_recall(self, json_results):
        for r in json_results:
            assert 0.0 <= r["recall"] <= 1.0, f"recall out of [0, 1]"

    def test_value_ranges_cosine(self, json_results):
        for r in json_results:
            assert 0.0 <= r["cosine"] <= 1.0, f"cosine out of [0, 1]"

    def test_value_ranges_switch_f1(self, json_results):
        for r in json_results:
            assert 0.0 <= r["switch_f1"] <= 1.0, f"switch_f1 out of [0, 1]"

    def test_value_ranges_n_eff(self, json_results):
        """n_eff should be positive."""
        for r in json_results:
            assert r["n_eff"] > 0, f"n_eff={r['n_eff']} must be positive"

    def test_value_ranges_max_wi(self, json_results):
        """max_wi should be in (0, 1]."""
        for r in json_results:
            assert 0.0 < r["max_wi"] <= 1.0, f"max_wi out of (0, 1]"


# ------------------------------------------------------------------
# Behavioral sanity checks
# ------------------------------------------------------------------
class TestBehavioral:
    def test_k5_tau005_reasonable(self, json_results):
        """K=5, tau=0.05 should produce reasonable results."""
        r = _get_result_by_config(json_results, 5, 0.05)
        assert r is not None, "K=5, tau=0.05 result not found"
        # norm_l2: typical range ~0.10-0.15
        assert 0.05 < r["norm_l2"] < 0.50, f"norm_l2={r['norm_l2']} unreasonable"
        # switch_f1: typical range ~0.80-0.95
        assert 0.50 < r["switch_f1"] < 1.0, f"switch_f1={r['switch_f1']} unreasonable"
        # acc_at_0.1: typical range ~0.70-0.90
        assert 0.10 < r["acc_at_0_1"] < 1.0, f"acc_at_0_1={r['acc_at_0_1']} unreasonable"
        # n_eff: should be <= K=5
        assert 0 < r["n_eff"] <= 5.0, f"n_eff={r['n_eff']} should be <= K=5"
        # cosine should be high
        assert r["cosine"] > 0.80, f"cosine={r['cosine']} unexpectedly low"

    def test_higher_k_tends_better_cosine(self, json_results):
        """Cosine similarity generally increases with K."""
        k3_results = [r for r in json_results if r["k"] == 3]
        k20_results = [r for r in json_results if r["k"] == 20]
        avg_k3 = sum(r["cosine"] for r in k3_results) / len(k3_results)
        avg_k20 = sum(r["cosine"] for r in k20_results) / len(k20_results)
        # K=20 should be at least as good as K=3 on average
        assert avg_k20 >= avg_k3 - 0.05, (
            f"K=20 avg cosine {avg_k20:.4f} should not be much worse than "
            f"K=3 avg {avg_k3:.4f}"
        )

    def test_lower_temperature_sharper_weights(self, json_results):
        """Lower temperature -> higher max_wi (more concentrated weights)."""
        same_k = [r for r in json_results if r["k"] == 10]
        tau01 = next(r for r in same_k if abs(r["temperature"] - 0.01) < 1e-6)
        tau50 = next(r for r in same_k if abs(r["temperature"] - 0.50) < 1e-6)
        # Lower temp => more peaky => higher max_wi
        assert tau01["max_wi"] > tau50["max_wi"], (
            f"tau=0.01 max_wi={tau01['max_wi']} should > tau=0.50 max_wi={tau50['max_wi']}"
        )

    def test_lower_temperature_higher_n_eff_concentration(self, json_results):
        """Lower temperature concentrates weights -> lower n_eff."""
        same_k = [r for r in json_results if r["k"] == 10]
        tau01 = next(r for r in same_k if abs(r["temperature"] - 0.01) < 1e-6)
        tau50 = next(r for r in same_k if abs(r["temperature"] - 0.50) < 1e-6)
        # Lower temp => more concentrated => lower n_eff
        assert tau01["n_eff"] < tau50["n_eff"], (
            f"tau=0.01 n_eff={tau01['n_eff']} should < tau=0.50 n_eff={tau50['n_eff']}"
        )


# ------------------------------------------------------------------
# Heatmap
# ------------------------------------------------------------------
class TestHeatmap:
    def test_heatmap_file_exists(self):
        assert HEATMAP_PATH.exists(), f"Heatmap not generated at {HEATMAP_PATH}"

    def test_heatmap_file_not_empty(self):
        size = HEATMAP_PATH.stat().st_size
        assert size > 10000, f"Heatmap file too small: {size} bytes"


# ------------------------------------------------------------------
# Module-level integration: importability
# ------------------------------------------------------------------
class TestModuleImport:
    def test_import_epr_sensitivity(self):
        from Experiments.E9_TMMMajorRevision.epr_sensitivity import (
            EPRGridResult,
            epr_sensitivity_rows,
            find_optimal,
            generate_heatmap,
            write_outputs,
        )
        # Verify dataclass fields
        field_names = [f.name for f in fields(EPRGridResult)]
        for required in REQUIRED_FIELDS:
            assert required in field_names, f"EPRGridResult missing field '{required}'"
