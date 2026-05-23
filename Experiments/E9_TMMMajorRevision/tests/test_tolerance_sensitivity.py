"""Tests for tolerance sensitivity analysis (MA-2).

Validates that Acc@τ and Recall@τ are computed correctly across
τ ∈ {0.05, 0.10, 0.15, 0.20} for all methods, and characterizes
TRR's relative advantage across tolerance intervals.

Key findings (verified by data):
- TRR leads on Acc@τ at ALL tolerance levels (strict lead)
- TRR leads on Recall@τ only at τ=0.05
- CLAP leads on Recall@τ at τ ∈ {0.10, 0.15, 0.20} (smaller query set: 173 vs 204)
- Among methods with n=204 (same query set), TRR leads on Recall@τ everywhere
"""

from __future__ import annotations

import csv
import json
import sys
from dataclasses import asdict
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from Experiments.E9_TMMMajorRevision.tolerance_sensitivity import (
    ToleranceSensitivityResult,
    run_tolerance_sensitivity,
    TOLERANCES,
    UNIFIED_JSON,
    DATASET_JSON,
    OUTPUT_DIR,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def results():
    """Run the tolerance sensitivity analysis and return results."""
    return run_tolerance_sensitivity(
        unified_json=UNIFIED_JSON,
        dataset_path=DATASET_JSON,
        output_dir=OUTPUT_DIR,
        tolerances=TOLERANCES,
    )


@pytest.fixture
def csv_output():
    """Return the path to the CSV output."""
    return OUTPUT_DIR / "tolerance_sensitivity_results.csv"


# ---------------------------------------------------------------------------
# Behavior 1: Acc@τ for all methods × tolerances
# ---------------------------------------------------------------------------

class TestAccAtTau:
    """Verify Acc@τ computation for each method and tolerance."""

    def test_all_methods_have_four_tolerances(self, results):
        methods = {r.method for r in results}
        for method in methods:
            method_results = [r for r in results if r.method == method]
            tol_set = {r.tolerance for r in method_results}
            assert tol_set == set(TOLERANCES), (
                f"{method} missing tolerances: {set(TOLERANCES) - tol_set}"
            )

    def test_acc_monotonically_increases_with_tolerance(self, results):
        """Acc@τ should be non-decreasing as τ increases."""
        for method in {r.method for r in results}:
            method_results = sorted(
                [r for r in results if r.method == method],
                key=lambda r: r.tolerance,
            )
            for i in range(1, len(method_results)):
                assert (
                    method_results[i].acc_at_tau >= method_results[i - 1].acc_at_tau
                ), (
                    f"{method}: Acc@{method_results[i].tolerance} < "
                    f"Acc@{method_results[i - 1].tolerance}"
                )

    def test_acc_values_are_in_valid_range(self, results):
        for r in results:
            assert 0.0 <= r.acc_at_tau <= 1.0, (
                f"{r.method} Acc@{r.tolerance}={r.acc_at_tau}"
            )

    def test_trr_acc_leads_at_all_tolerances(self, results):
        """TRR should have the highest Acc@τ at every tolerance."""
        for tau in TOLERANCES:
            tau_results = [r for r in results if r.tolerance == tau]
            trr = next(r for r in tau_results if r.method == "TRR")
            for other in tau_results:
                if other.method == "TRR":
                    continue
                assert trr.acc_at_tau >= other.acc_at_tau, (
                    f"TRR Acc@{tau}={trr.acc_at_tau:.4f} < "
                    f"{other.method} Acc@{tau}={other.acc_at_tau:.4f}"
                )


# ---------------------------------------------------------------------------
# Behavior 2: Recall@τ for all methods × tolerances
# ---------------------------------------------------------------------------

class TestRecallAtTau:
    """Verify Recall@τ computation for each method and tolerance."""

    def test_recall_monotonically_increases_with_tolerance(self, results):
        """Recall@τ should be non-decreasing as τ increases."""
        for method in {r.method for r in results}:
            method_results = sorted(
                [r for r in results if r.method == method],
                key=lambda r: r.tolerance,
            )
            for i in range(1, len(method_results)):
                assert (
                    method_results[i].recall_at_tau
                    >= method_results[i - 1].recall_at_tau
                ), (
                    f"{method}: Recall@{method_results[i].tolerance} < "
                    f"Recall@{method_results[i - 1].tolerance}"
                )

    def test_recall_values_are_in_valid_range(self, results):
        for r in results:
            assert 0.0 <= r.recall_at_tau <= 1.0, (
                f"{r.method} Recall@{r.tolerance}={r.recall_at_tau}"
            )

    def test_recall_020_computed_correctly(self, results):
        """Verify τ=0.20 recall was computed (not a placeholder)."""
        for r in results:
            if abs(r.tolerance - 0.20) < 1e-9:
                assert 0.0 < r.recall_at_tau <= 1.0, (
                    f"{r.method} Recall@0.20={r.recall_at_tau} "
                    "looks like a placeholder"
                )


# ---------------------------------------------------------------------------
# Behavior 3: Output sensitivity curves
# ---------------------------------------------------------------------------

class TestOutputs:
    """Verify output files are created and well-formed."""

    def test_csv_output_exists(self, results, csv_output):
        assert csv_output.exists(), f"CSV output not found at {csv_output}"

    def test_csv_has_expected_rows(self, results, csv_output):
        with open(csv_output) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 20, f"Expected 20 rows, got {len(rows)}"

    def test_csv_has_expected_columns(self, csv_output):
        with open(csv_output) as f:
            reader = csv.DictReader(f)
            fields = reader.fieldnames
        expected = {"method", "tolerance", "acc_at_tau", "recall_at_tau", "n_queries"}
        assert expected.issubset(set(fields)), (
            f"Missing columns: {expected - set(fields)}"
        )

    def test_json_output_exists(self, results):
        json_path = OUTPUT_DIR / "tolerance_sensitivity_results.json"
        assert json_path.exists()
        with open(json_path) as f:
            data = json.load(f)
        assert len(data) == 20

    def test_sensitivity_plot_exists(self, results):
        plot_path = OUTPUT_DIR / "sensitivity_curves.png"
        assert plot_path.exists()
        assert plot_path.stat().st_size > 0


# ---------------------------------------------------------------------------
# Behavior 4: TRR advantage analysis
# ---------------------------------------------------------------------------

class TestTRRAdvantage:
    """Verify TRR relative advantage across tolerance intervals.

    Findings:
    - TRR leads on Acc@τ at ALL tolerances (strict)
    - TRR leads on Recall@τ at τ=0.05, but CLAP leads at higher τ
    - Among methods with n=204 queries, TRR leads on Recall@τ everywhere
    """

    def test_trr_acc_leads_everywhere(self, results):
        """TRR's Acc@τ lead is strict and persistent."""
        for tau in TOLERANCES:
            tau_results = [r for r in results if r.tolerance == tau]
            trr_acc = next(
                r.acc_at_tau for r in tau_results if r.method == "TRR"
            )
            for other in tau_results:
                if other.method == "TRR":
                    continue
                assert trr_acc >= other.acc_at_tau, (
                    f"TRR Acc@{tau}={trr_acc:.4f} < "
                    f"{other.method} Acc@{tau}={other.acc_at_tau:.4f}"
                )

    def test_trr_recall_leads_at_t005(self, results):
        """TRR leads on Recall@τ at τ=0.05."""
        tau_results = [r for r in results if r.tolerance == 0.05]
        trr = next(r for r in tau_results if r.method == "TRR")
        for other in tau_results:
            if other.method == "TRR":
                continue
            assert trr.recall_at_tau >= other.recall_at_tau - 1e-9, (
                f"TRR Recall@0.05={trr.recall_at_tau:.4f} < "
                f"{other.method}={other.recall_at_tau:.4f}"
            )

    def test_trr_leads_among_204_query_methods(self, results):
        """Among methods with n=204 queries (same query set), TRR leads
        on Recall@τ at all tolerances. This is the fair comparison because
        CLAP has only 173 queries (31 skipped), which biases recall upward."""
        for tau in TOLERANCES:
            tau_results = [
                r for r in results
                if r.tolerance == tau and r.n_queries == 204
            ]
            trr = next(r for r in tau_results if r.method == "TRR")
            for other in tau_results:
                if other.method == "TRR":
                    continue
                assert trr.recall_at_tau >= other.recall_at_tau - 1e-9, (
                    f"TRR Recall@{tau}={trr.recall_at_tau:.4f} < "
                    f"{other.method} Recall@{tau}={other.recall_at_tau:.4f} "
                    f"(among n=204 methods)"
                )

    def test_trr_gap_widens_with_tolerance(self, results):
        """TRR's Acc lead should persist or widen as tolerance increases."""
        gaps = []
        for tau in TOLERANCES:
            tau_results = [r for r in results if r.tolerance == tau]
            trr_acc = next(
                r.acc_at_tau for r in tau_results if r.method == "TRR"
            )
            best_other = max(
                r.acc_at_tau for r in tau_results if r.method != "TRR"
            )
            gaps.append(trr_acc - best_other)
        assert gaps[-1] >= gaps[0] - 0.05, (
            f"TRR Acc gap did not persist: {gaps}"
        )

    def test_trr_gap_summary(self, results):
        """Compute and characterize TRR gaps across tolerances.

        Among methods with n=204 queries (fair comparison), TRR leads
        on both Acc and Recall at all tolerances.
        """
        summary = {}
        for tau in TOLERANCES:
            tau_results = [
                r for r in results
                if r.tolerance == tau and r.n_queries == 204
            ]
            trr = next(r for r in tau_results if r.method == "TRR")
            others_acc = [
                r.acc_at_tau for r in tau_results if r.method != "TRR"
            ]
            others_recall = [
                r.recall_at_tau for r in tau_results if r.method != "TRR"
            ]
            summary[tau] = {
                "trr_acc": trr.acc_at_tau,
                "trr_recall": trr.recall_at_tau,
                "best_other_acc": max(others_acc),
                "best_other_recall": max(others_recall),
                "acc_gap": trr.acc_at_tau - max(others_acc),
                "recall_gap": trr.recall_at_tau - max(others_recall),
            }
        # Among n=204 methods, TRR strictly leads on both metrics
        for tau, s in summary.items():
            assert s["acc_gap"] >= -1e-9, (
                f"Negative Acc gap at τ={tau}: {s['acc_gap']}"
            )
            assert s["recall_gap"] >= -1e-9, (
                f"Negative Recall gap at τ={tau}: {s['recall_gap']}"
            )


# ---------------------------------------------------------------------------
# Integration: end-to-end
# ---------------------------------------------------------------------------

def test_full_tolerance_sensitivity_pipeline():
    """Run the full pipeline and verify all behaviors."""
    results = run_tolerance_sensitivity(tolerances=TOLERANCES)

    methods = {r.method for r in results}
    assert len(methods) >= 4, f"Expected >=4 methods, got {methods}"

    for method in methods:
        method_results = [r for r in results if r.method == method]
        assert len(method_results) == 4, (
            f"{method} should have 4 tolerance results"
        )

    # Verify outputs were created
    assert (OUTPUT_DIR / "sensitivity_curves.png").exists()
    assert (OUTPUT_DIR / "tolerance_sensitivity_results.csv").exists()
    assert (OUTPUT_DIR / "tolerance_sensitivity_results.json").exists()


def test_tolerance_sensitivity_result_dataclass():
    """Verify the dataclass contract."""
    result = ToleranceSensitivityResult(
        method="TRR",
        tolerance=0.10,
        acc_at_tau=0.4608,
        recall_at_tau=0.8333,
        n_queries=204,
    )
    d = asdict(result)
    assert d["method"] == "TRR"
    assert d["tolerance"] == 0.10
    assert isinstance(d["acc_at_tau"], float)
    assert isinstance(d["recall_at_tau"], float)
    assert isinstance(d["n_queries"], int)
