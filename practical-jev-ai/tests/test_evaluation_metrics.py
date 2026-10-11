"""Metric formulas checked against values computed by hand."""

import pytest

from evaluation.metrics import (
    accuracy,
    confusion_matrix,
    expected_calibration_error,
    multiclass_brier,
    per_class_report,
    percentile,
)

LABELS = ["a", "b"]
Y_TRUE = ["a", "a", "a", "b", "b"]
Y_PRED = ["a", "a", "b", "b", None]  # one failed prediction


def test_accuracy_counts_failures_as_wrong():
    assert accuracy(Y_TRUE, Y_PRED) == pytest.approx(3 / 5)


def test_confusion_matrix_has_a_column_for_failures():
    assert confusion_matrix(Y_TRUE, Y_PRED, LABELS) == {
        "a": {"a": 2, "b": 1, "none": 0},
        "b": {"a": 0, "b": 1, "none": 1},
    }


def test_precision_recall_f1_by_hand():
    report = per_class_report(Y_TRUE, Y_PRED, LABELS)
    # a: tp=2 fp=0 fn=1 -> P=1, R=2/3, F1=0.8 ; b: tp=1 fp=1 fn=1 -> P=R=F1=0.5
    assert report["a"]["precision"] == 1.0
    assert report["a"]["recall"] == pytest.approx(2 / 3)
    assert report["a"]["f1"] == pytest.approx(0.8)
    assert report["b"]["f1"] == pytest.approx(0.5)
    assert report["macro_avg"]["f1"] == pytest.approx(0.65)


def test_perfectly_calibrated_bins_have_zero_ece():
    ece, bins = expected_calibration_error([0.9] * 10, [True] * 9 + [False], n_bins=5)
    assert ece == pytest.approx(0.0)
    assert bins[0]["n"] == 10


def test_overconfident_model_has_positive_ece():
    ece, _ = expected_calibration_error([0.95] * 4, [True, False, True, False])
    assert ece == pytest.approx(0.45)


def test_brier_score():
    assert multiclass_brier([{"a": 1.0, "b": 0.0}], ["a"], LABELS) == 0.0
    assert multiclass_brier([{"a": 0.5, "b": 0.5}], ["a"], LABELS) == pytest.approx(0.5)


def test_percentile():
    assert percentile([], 50) is None
    assert percentile([5, 1, 3], 50) == 3
