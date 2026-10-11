"""Evaluation metrics, written out in plain Python so every formula is readable.

Inputs are lists aligned by index. `None` in predictions means inference failed.
"""

from __future__ import annotations

from collections.abc import Sequence


def accuracy(y_true: Sequence[str], y_pred: Sequence[str | None]) -> float:
    pairs = list(zip(y_true, y_pred, strict=True))
    return sum(t == p for t, p in pairs) / len(pairs) if pairs else 0.0


def confusion_matrix(
    y_true: Sequence[str], y_pred: Sequence[str | None], labels: Sequence[str]
) -> dict[str, dict[str, int]]:
    """matrix[true_label][predicted_label]; failed predictions are counted under 'none'."""
    columns = [*labels, "none"]
    matrix = {t: dict.fromkeys(columns, 0) for t in labels}
    for t, p in zip(y_true, y_pred, strict=True):
        matrix[t][p if p is not None else "none"] += 1
    return matrix


def per_class_report(
    y_true: Sequence[str], y_pred: Sequence[str | None], labels: Sequence[str]
) -> dict[str, dict[str, float]]:
    report: dict[str, dict[str, float]] = {}
    for label in labels:
        tp = sum(t == label and p == label for t, p in zip(y_true, y_pred, strict=True))
        fp = sum(t != label and p == label for t, p in zip(y_true, y_pred, strict=True))
        fn = sum(t == label and p != label for t, p in zip(y_true, y_pred, strict=True))
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        report[label] = {"precision": precision, "recall": recall, "f1": f1, "support": tp + fn}
    report["macro_avg"] = {
        key: sum(report[label][key] for label in labels) / len(labels)
        for key in ("precision", "recall", "f1")
    }
    return report


def expected_calibration_error(
    confidences: Sequence[float], correct: Sequence[bool], n_bins: int = 5
) -> tuple[float, list[dict]]:
    """ECE: average |accuracy - mean confidence| across confidence bins, weighted by bin size.

    `confidences` should be the probability of the predicted class (p_max): that is the
    quantity that SHOULD equal accuracy if the model is calibrated. (TypeSafe's `confidence`
    field is a rescaled statistic, 0 at an even split, so it is not directly comparable.)
    With small datasets, bins are tiny and ECE is noisy - report n alongside it.
    """
    bins = []
    total = len(confidences)
    ece = 0.0
    for b in range(n_bins):
        lo, hi = b / n_bins, (b + 1) / n_bins
        idx = [
            i for i, c in enumerate(confidences) if lo <= c < hi or (b == n_bins - 1 and c == 1.0)
        ]
        if not idx:
            continue
        avg_conf = sum(confidences[i] for i in idx) / len(idx)
        acc = sum(correct[i] for i in idx) / len(idx)
        ece += len(idx) / total * abs(acc - avg_conf)
        bins.append(
            {
                "range": f"[{lo:.1f},{hi:.1f})",
                "n": len(idx),
                "mean_confidence": avg_conf,
                "accuracy": acc,
            }
        )
    return ece, bins


def multiclass_brier(
    probabilities: Sequence[dict[str, float]], y_true: Sequence[str], labels: Sequence[str]
) -> float:
    """Mean squared error between the predicted distribution and the one-hot truth.
    0 is perfect; lower is better. Rewards being confident only when right."""
    total = 0.0
    for dist, truth in zip(probabilities, y_true, strict=True):
        total += sum((dist.get(lab, 0.0) - (1.0 if lab == truth else 0.0)) ** 2 for lab in labels)
    return total / len(y_true) if y_true else 0.0


def percentile(values: Sequence[float], pct: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round(pct / 100 * (len(ordered) - 1)))]
