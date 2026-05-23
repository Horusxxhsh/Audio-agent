"""Tests for formal near-duplicate filter (CR-5).

Validates:
  - NearDupFilterStats and FilteredResult dataclass contracts
  - Three thresholds (0.02, 0.05, 0.10) are all present
  - Filter stats JSON structure and values
  - Filtered results CSV structure and values
  - Script runs end-to-end via CLI
"""
from __future__ import annotations

import csv
import json
import sys
from dataclasses import dataclass, fields as dataclass_fields
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

# Output paths
OUTPUT_DIR = (
    REPO_ROOT
    / "Experiments"
    / "E5_Ablations"
    / "outputs"
    / "p0_formal_near_dup_filter"
)
STATS_JSON = OUTPUT_DIR / "filter_stats.json"
RESULTS_CSV = OUTPUT_DIR / "filtered_results.csv"
COMBINED_JSON = OUTPUT_DIR / "formal_near_dup_filter.json"

EXPECTED_THRESHOLDS = [0.02, 0.05, 0.10]
EXPECTED_ORIGINAL_QUERIES = 204
EXPECTED_ORIGINAL_KB = 1063
EXPECTED_METHODS = ["TRR", "Wav2Vec", "FeatureNN", "CLAP", "PaSST", "PANNs"]

# Required fields per NearDupFilterStats contract
STATS_REQUIRED_FIELDS = [
    "threshold",
    "original_queries",
    "retained_queries",
    "original_kb",
    "retained_kb",
    "filtered_pairs",
    "filter_rate",
]

# Required fields per FilteredResult contract
RESULT_REQUIRED_FIELDS = [
    "method",
    "threshold",
    "norm_l2",
    "coverage",
    "n_queries",
]


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def _load_stats() -> list[dict]:
    return json.loads(STATS_JSON.read_text(encoding="utf-8"))


def _load_results_csv() -> list[dict]:
    with RESULTS_CSV.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _load_combined() -> dict:
    return json.loads(COMBINED_JSON.read_text(encoding="utf-8"))


def _get_stat_by_threshold(stats: list[dict], threshold: float) -> dict | None:
    for s in stats:
        if abs(s["threshold"] - threshold) < 1e-6:
            return s
    return None


# ------------------------------------------------------------------
# Fixture
# ------------------------------------------------------------------
@pytest.fixture(scope="module")
def stats():
    return _load_stats()


@pytest.fixture(scope="module")
def results_csv():
    return _load_results_csv()


@pytest.fixture(scope="module")
def combined():
    return _load_combined()


# ------------------------------------------------------------------
# Behavior 1: Near-duplicate detection (module import + dataclass)
# ------------------------------------------------------------------
class TestDataclassContract:
    """Verify the interface contract dataclasses exist and have correct fields."""

    def test_near_dup_filter_stats_import(self):
        from Experiments.E5_Ablations.formal_near_dup_filter import (
            NearDupFilterStats,
        )
        field_names = [f.name for f in dataclass_fields(NearDupFilterStats)]
        for required in STATS_REQUIRED_FIELDS:
            assert required in field_names, (
                f"NearDupFilterStats missing field '{required}'"
            )

    def test_filtered_result_import(self):
        from Experiments.E5_Ablations.formal_near_dup_filter import (
            FilteredResult,
        )
        field_names = [f.name for f in dataclass_fields(FilteredResult)]
        for required in RESULT_REQUIRED_FIELDS:
            assert required in field_names, (
                f"FilteredResult missing field '{required}'"
            )

    def test_near_dup_filter_stats_has_defaults(self):
        from Experiments.E5_Ablations.formal_near_dup_filter import (
            NearDupFilterStats,
        )
        s = NearDupFilterStats(
            threshold=0.02,
            original_queries=204,
            retained_queries=204,
            original_kb=1063,
            retained_kb=84,
            filtered_pairs=979,
            filter_rate=0.92,
        )
        assert s.threshold == 0.02
        assert s.original_queries == 204
        assert s.original_kb == 1063

    def test_filtered_result_has_defaults(self):
        from Experiments.E5_Ablations.formal_near_dup_filter import (
            FilteredResult,
        )
        r = FilteredResult(
            method="TRR",
            threshold=0.02,
            norm_l2=0.21,
            coverage=1.0,
            n_queries=204,
        )
        assert r.method == "TRR"
        assert r.threshold == 0.02


# ------------------------------------------------------------------
# Behavior 2: Three thresholds
# ------------------------------------------------------------------
class TestThresholds:
    """Verify all three thresholds are present in outputs."""

    def test_output_files_exist(self):
        assert STATS_JSON.exists(), f"Stats JSON not found at {STATS_JSON}"
        assert RESULTS_CSV.exists(), f"Results CSV not found at {RESULTS_CSV}"
        assert COMBINED_JSON.exists(), f"Combined JSON not found at {COMBINED_JSON}"

    def test_three_thresholds_in_stats(self, stats):
        observed = sorted({s["threshold"] for s in stats})
        expected = sorted(EXPECTED_THRESHOLDS)
        assert observed == expected, (
            f"Expected thresholds={expected}, got {observed}"
        )

    def test_one_stat_per_threshold(self, stats):
        """Each threshold has exactly one stat entry."""
        thresholds = [s["threshold"] for s in stats]
        for t in EXPECTED_THRESHOLDS:
            count = sum(1 for x in thresholds if abs(x - t) < 1e-6)
            assert count == 1, f"Expected 1 stat for threshold={t}, got {count}"


# ------------------------------------------------------------------
# Behavior 3: Filter stats (re-evaluate all methods)
# ------------------------------------------------------------------
class TestFilterStats:
    """Verify filter statistics structure and values."""

    def test_required_fields_present(self, stats):
        for s in stats:
            for field in STATS_REQUIRED_FIELDS:
                assert field in s, f"Field '{field}' missing from stat: {s}"

    def test_original_queries_is_204(self, stats):
        for s in stats:
            assert (
                s["original_queries"] == EXPECTED_ORIGINAL_QUERIES
            ), f"original_queries={s['original_queries']}, expected {EXPECTED_ORIGINAL_QUERIES}"

    def test_original_kb_is_1063(self, stats):
        for s in stats:
            assert (
                s["original_kb"] == EXPECTED_ORIGINAL_KB
            ), f"original_kb={s['original_kb']}, expected {EXPECTED_ORIGINAL_KB}"

    def test_retained_kb_less_than_original(self, stats):
        for s in stats:
            assert (
                s["retained_kb"] < s["original_kb"]
            ), "Filtering must remove at least one KB item"

    def test_retained_queries_equals_original(self, stats):
        """Filtering only affects KB, not queries."""
        for s in stats:
            assert s["retained_queries"] == s["original_queries"]

    def test_filtered_pairs_positive(self, stats):
        for s in stats:
            assert s["filtered_pairs"] > 0, (
                f"Expected positive filtered_pairs at threshold={s['threshold']}"
            )

    def test_filter_rate_in_range(self, stats):
        for s in stats:
            assert 0.0 < s["filter_rate"] <= 1.0, (
                f"filter_rate={s['filter_rate']} out of (0, 1] for threshold={s['threshold']}"
            )

    def test_filter_rate_increases_with_threshold(self, stats):
        """Higher threshold => more filtering => higher filter_rate."""
        sorted_stats = sorted(stats, key=lambda x: x["threshold"])
        for i in range(len(sorted_stats) - 1):
            assert sorted_stats[i]["filter_rate"] <= sorted_stats[i + 1]["filter_rate"], (
                f"filter_rate should increase with threshold: "
                f"{sorted_stats[i]['filter_rate']} at {sorted_stats[i]['threshold']} "
                f"vs {sorted_stats[i + 1]['filter_rate']} at {sorted_stats[i + 1]['threshold']}"
            )


# ------------------------------------------------------------------
# Behavior 4: Output filter stats JSON
# ------------------------------------------------------------------
class TestStatsJson:
    """Verify the JSON output is well-formed and complete."""

    def test_stats_json_is_list(self):
        data = json.loads(STATS_JSON.read_text(encoding="utf-8"))
        assert isinstance(data, list), "Stats JSON must be a list"

    def test_stats_json_length(self):
        data = json.loads(STATS_JSON.read_text(encoding="utf-8"))
        assert len(data) == len(EXPECTED_THRESHOLDS)

    def test_stats_json_thresholds_match(self):
        data = json.loads(STATS_JSON.read_text(encoding="utf-8"))
        thresholds = sorted({s["threshold"] for s in data})
        assert thresholds == sorted(EXPECTED_THRESHOLDS)

    def test_types(self, stats):
        for s in stats:
            assert isinstance(s["threshold"], float)
            assert isinstance(s["original_queries"], int)
            assert isinstance(s["retained_queries"], int)
            assert isinstance(s["original_kb"], int)
            assert isinstance(s["retained_kb"], int)
            assert isinstance(s["filtered_pairs"], int)
            assert isinstance(s["filter_rate"], float)


# ------------------------------------------------------------------
# Behavior 5: Output filtered results CSV
# ------------------------------------------------------------------
class TestFilteredResultsCsv:
    """Verify filtered results CSV structure and values."""

    def test_csv_header_fields(self, results_csv):
        if not results_csv:
            pytest.skip("No CSV results")
        for field in RESULT_REQUIRED_FIELDS:
            assert field in results_csv[0], (
                f"Field '{field}' missing from CSV header: {list(results_csv[0].keys())}"
            )

    def test_all_methods_per_threshold(self, results_csv):
        """Each threshold has results for all expected methods."""
        for threshold in EXPECTED_THRESHOLDS:
            methods_at_t = [
                r["method"]
                for r in results_csv
                if abs(float(r["threshold"]) - threshold) < 1e-6
            ]
            for method in EXPECTED_METHODS:
                assert method in methods_at_t, (
                    f"Method '{method}' missing at threshold={threshold}: "
                    f"found {methods_at_t}"
                )

    def test_all_thresholds_in_csv(self, results_csv):
        observed = sorted({float(r["threshold"]) for r in results_csv})
        assert observed == sorted(EXPECTED_THRESHOLDS)

    def test_norm_l2_reasonable(self, results_csv):
        """norm_l2 for available methods should be in [0, 1]."""
        for r in results_csv:
            val = r["norm_l2"]
            if val == "nan":
                continue  # PaSST/PANNs may have no vectors
            n = float(val)
            assert 0.0 <= n <= 1.0, f"norm_l2={n} out of [0, 1]"

    def test_coverage_reasonable(self, results_csv):
        for r in results_csv:
            c = float(r["coverage"])
            assert 0.0 <= c <= 1.0, f"coverage={c} out of [0, 1]"

    def test_n_queries_positive_for_available(self, results_csv):
        """Methods with vectors should have n_queries > 0."""
        for r in results_csv:
            n = int(r["n_queries"])
            if n > 0:
                assert r["norm_l2"] != "nan", (
                    f"{r['method']} has n_queries={n} but norm_l2 is nan"
                )

    def test_csv_row_count(self, results_csv):
        """Expected rows = len(methods) * len(thresholds)."""
        expected = len(EXPECTED_METHODS) * len(EXPECTED_THRESHOLDS)
        assert len(results_csv) == expected, (
            f"Expected {expected} rows, got {len(results_csv)}"
        )


# ------------------------------------------------------------------
# Combined JSON
# ------------------------------------------------------------------
class TestCombinedJson:
    """Verify the combined JSON output."""

    def test_combined_has_stats_and_results(self, combined):
        assert "stats" in combined, "Combined JSON must have 'stats' key"
        assert "results" in combined, "Combined JSON must have 'results' key"

    def test_combined_stats_match(self, combined):
        assert len(combined["stats"]) == len(EXPECTED_THRESHOLDS)

    def test_combined_results_match(self, combined):
        expected = len(EXPECTED_METHODS) * len(EXPECTED_THRESHOLDS)
        assert len(combined["results"]) == expected


# ------------------------------------------------------------------
# Module-level integration: importability & function signatures
# ------------------------------------------------------------------
class TestModuleImport:
    def test_import_pipeline(self):
        from Experiments.E5_Ablations.formal_near_dup_filter import (
            NearDupFilterStats,
            FilteredResult,
            find_near_duplicate_indices,
            filter_by_indices,
            run_formal_filter,
            write_stats_json,
            write_results_csv,
            write_full_outputs,
        )
        # Verify callable
        assert callable(find_near_duplicate_indices)
        assert callable(filter_by_indices)
        assert callable(run_formal_filter)
        assert callable(write_stats_json)
        assert callable(write_results_csv)
        assert callable(write_full_outputs)

    def test_near_dup_filter_stats_dataclass(self):
        from Experiments.E5_Ablations.formal_near_dup_filter import (
            NearDupFilterStats,
        )
        from dataclasses import is_dataclass
        assert is_dataclass(NearDupFilterStats)

    def test_filtered_result_dataclass(self):
        from Experiments.E5_Ablations.formal_near_dup_filter import (
            FilteredResult,
        )
        from dataclasses import is_dataclass
        assert is_dataclass(FilteredResult)


# ------------------------------------------------------------------
# CLI integration test
# ------------------------------------------------------------------
class TestCLI:
    def test_cli_runs(self):
        """The CLI script can be invoked and produces outputs."""
        import subprocess

        result = subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "Experiments" / "E5_Ablations" / "formal_near_dup_filter.py"),
                "--dataset",
                str(
                    REPO_ROOT
                    / "Data"
                    / "External_1267_211"
                    / "dataset"
                    / "dataset_full_vectors_1267.json"
                ),
                "--split-file",
                str(
                    REPO_ROOT
                    / "Experiments"
                    / "tmm"
                    / "splits"
                    / "tmm_external1267_audio_grouped"
                    / "seed0"
                    / "test.txt"
                ),
                "--output-dir",
                str(OUTPUT_DIR),
                "--thresholds",
                "0.02",
                "0.05",
                "0.10",
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )
        assert result.returncode == 0, (
            f"CLI failed with exit code {result.returncode}.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
        # Verify outputs were created
        assert STATS_JSON.exists()
        assert RESULTS_CSV.exists()
        assert COMBINED_JSON.exists()
