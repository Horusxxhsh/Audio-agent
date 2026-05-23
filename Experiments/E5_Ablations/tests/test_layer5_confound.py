"""
Tests for Layer-5 Gram vs mean-pool confound analysis (CR-1).

Validates:
  1. Output CSV structure and required columns
  2. Row count (6 configurations)
  3. Query count consistency (all 204)
  4. Bootstrap CI validity (lower < mean < upper)
  5. Wilcoxon paired test correctness for both comparison pairs
  6. Confound finding: Gram helps at layer-5 alone, not at multi-layer
"""

import csv
import math
from pathlib import Path

import pytest

# Resolve paths relative to this file
_BASE = Path(__file__).resolve().parent.parent
OUTPUT_DIR = _BASE / "outputs" / "layer5_confound"
CSV_PATH = OUTPUT_DIR / "layer5_confound_results.csv"

REQUIRED_COLUMNS = [
    "layer", "method", "project_dim", "norm_l2_mean",
    "norm_l2_ci_lower", "norm_l2_ci_upper",
    "improvement_vs_mean", "wilcoxon_p", "n_queries",
]

# Expected layer+method combinations
EXPECTED_ROWS = [
    ("5", "mean_pool"),
    ("5", "gram"),
    ("4+5+6", "mean_pool"),
    ("4+5+6", "gram"),
    ("4", "gram"),
    ("6", "gram"),
]


def _read_csv() -> list:
    """Read the output CSV into a list of dicts."""
    with open(CSV_PATH, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    return rows


# ---- Test 1: CSV structure ----

def test_csv_structure():
    """CSV exists, has required columns, and exactly 6 data rows."""
    assert CSV_PATH.exists(), f"Output CSV not found at {CSV_PATH}"
    rows = _read_csv()

    # Column check
    with open(CSV_PATH, newline="") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == REQUIRED_COLUMNS, (
            f"CSV columns {reader.fieldnames} != expected {REQUIRED_COLUMNS}"
        )

    # Row count: 6 configurations
    assert len(rows) == 6, f"Expected 6 rows, got {len(rows)}"

    # All 6 expected layer+method combos present
    actual_combos = [(r["layer"], r["method"]) for r in rows]
    for expected in EXPECTED_ROWS:
        assert expected in actual_combos, f"Missing row {expected}"


# ---- Test 2: Query count consistency ----

def test_query_count_consistency():
    """All rows must have exactly 204 queries."""
    rows = _read_csv()
    for i, row in enumerate(rows):
        n = int(row["n_queries"])
        assert n == 204, (
            f"Row {i} ({row['layer']}/{row['method']}): "
            f"n_queries={n}, expected 204"
        )


# ---- Test 3: Bootstrap CI validity ----

def test_bootstrap_ci_valid():
    """For every row: ci_lower < norm_l2_mean < ci_upper."""
    rows = _read_rows()
    for row in rows:
        mean = float(row["norm_l2_mean"])
        lo = float(row["norm_l2_ci_lower"])
        hi = float(row["norm_l2_ci_upper"])
        layer = row["layer"]
        method = row["method"]
        assert lo < mean < hi, (
            f"Row {layer}/{method}: CI [{lo:.6f}, {hi:.6f}] "
            f"does not contain mean {mean:.6f}"
        )


# ---- Test 4: Wilcoxon paired tests for both comparison pairs ----

def test_wilcoxon_paired_tests():
    """
    Verify Wilcoxon tests exist for both comparison pairs:
      - Layer 5: mean_pool vs gram (paired)
      - Layer 4+5+6: mean_pool vs gram (paired)
    And that Gram-only layers (4, 6) have NaN p-values.
    """
    rows = _read_rows()

    # Find Gram rows for paired comparisons
    gram_l5 = next(r for r in rows if r["layer"] == "5" and r["method"] == "gram")
    gram_multi = next(r for r in rows
                      if r["layer"] == "4+5+6" and r["method"] == "gram")

    # Paired layers must have finite p-values
    assert not math.isnan(float(gram_l5["wilcoxon_p"])), (
        "Layer 5 Gram row should have a finite Wilcoxon p-value"
    )
    assert not math.isnan(float(gram_multi["wilcoxon_p"])), (
        "Layer 4+5+6 Gram row should have a finite Wilcoxon p-value"
    )

    # p-values must be in [0, 1]
    p_l5 = float(gram_l5["wilcoxon_p"])
    p_multi = float(gram_multi["wilcoxon_p"])
    assert 0.0 <= p_l5 <= 1.0, f"Layer 5 p={p_l5} out of range"
    assert 0.0 <= p_multi <= 1.0, f"Layer 4+5+6 p={p_multi} out of range"

    # Gram-only rows must have NaN p-values
    gram_l4 = next(r for r in rows if r["layer"] == "4" and r["method"] == "gram")
    gram_l6 = next(r for r in rows if r["layer"] == "6" and r["method"] == "gram")
    assert math.isnan(float(gram_l4["wilcoxon_p"])), (
        "Layer 4 Gram-only row should have NaN Wilcoxon p-value"
    )
    assert math.isnan(float(gram_l6["wilcoxon_p"])), (
        "Layer 6 Gram-only row should have NaN Wilcoxon p-value"
    )


# ---- Test 5: Gram improvement values ----

def test_gram_improvement_values():
    """
    Verify improvement values:
      - Paired rows: positive delta (Gram improves over mean-pool)
      - Baseline mean_pool rows: delta = 0
      - Gram-only rows: NaN
    """
    rows = _read_rows()

    # Find rows by layer+method
    mp_l5 = next(r for r in rows if r["layer"] == "5" and r["method"] == "mean_pool")
    gr_l5 = next(r for r in rows if r["layer"] == "5" and r["method"] == "gram")
    mp_multi = next(r for r in rows
                    if r["layer"] == "4+5+6" and r["method"] == "mean_pool")
    gr_multi = next(r for r in rows
                    if r["layer"] == "4+5+6" and r["method"] == "gram")
    gr_l4 = next(r for r in rows if r["layer"] == "4" and r["method"] == "gram")
    gr_l6 = next(r for r in rows if r["layer"] == "6" and r["method"] == "gram")

    # Baseline rows: improvement = 0
    assert float(mp_l5["improvement_vs_mean"]) == 0.0, (
        "mean_pool layer 5 should have improvement = 0.0"
    )
    assert float(mp_multi["improvement_vs_mean"]) == 0.0, (
        "mean_pool layer 4+5+6 should have improvement = 0.0"
    )

    # Paired Gram rows: improvement > 0 (lower L2 = better)
    delta_l5 = float(gr_l5["improvement_vs_mean"])
    delta_multi = float(gr_multi["improvement_vs_mean"])
    assert delta_l5 > 0, (
        f"Layer 5 Gram should improve over mean-pool: delta={delta_l5}"
    )
    assert delta_multi > 0, (
        f"Layer 4+5+6 Gram should improve over mean-pool: delta={delta_multi}"
    )

    # Gram-only rows: NaN improvement
    assert math.isnan(float(gr_l4["improvement_vs_mean"])), (
        "Layer 4 Gram-only should have NaN improvement"
    )
    assert math.isnan(float(gr_l6["improvement_vs_mean"])), (
        "Layer 6 Gram-only should have NaN improvement"
    )


# ---- Test 6: Confound finding ----

def test_confound_finding():
    """
    Core finding: Gram improves more at layer-5 alone than at multi-layer.
    This is the key confound: the advantage is partly from layer selection,
    not just from the Gram matrix.

    Specifically: delta_layer5 >> delta_multilayer
    And the multi-layer delta is near-zero (not statistically significant).
    """
    rows = _read_rows()

    gr_l5 = next(r for r in rows if r["layer"] == "5" and r["method"] == "gram")
    gr_multi = next(r for r in rows
                    if r["layer"] == "4+5+6" and r["method"] == "gram")

    delta_l5 = float(gr_l5["improvement_vs_mean"])
    delta_multi = float(gr_multi["improvement_vs_mean"])

    # Gram helps at layer 5
    assert delta_l5 > 0.001, (
        f"Gram should provide measurable improvement at layer 5: delta={delta_l5}"
    )

    # Multi-layer Gram improvement is near-zero (confound)
    assert delta_multi < 0.005, (
        f"Gram at multi-layer should show near-zero improvement: delta={delta_multi}"
    )

    # Layer-5 improvement >> multi-layer improvement
    assert delta_l5 > delta_multi, (
        f"Layer-5 delta ({delta_l5:.6f}) should exceed "
        f"multi-layer delta ({delta_multi:.6f})"
    )

    # Multi-layer p-value should be non-significant (> 0.05)
    p_multi = float(gr_multi["wilcoxon_p"])
    assert p_multi > 0.05, (
        f"Multi-layer Gram vs mean-pool should not be significant: p={p_multi:.4f}"
    )


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _read_rows() -> list:
    """Read CSV into list of dicts (cached via module-level cache)."""
    if not hasattr(_read_rows, "_cache"):
        _read_rows._cache = _read_csv()
    return _read_rows._cache
