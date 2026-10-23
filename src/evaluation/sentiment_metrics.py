"""Dependency-light metrics for manually labeled sentiment predictions."""

from typing import Sequence


def calculate_sentiment_metrics(
    expected: Sequence[str], predicted: Sequence[str]
) -> dict[str, object]:
    """Return accuracy, per-class precision/recall/F1, macro F1, and confusion."""
    if len(expected) != len(predicted):
        raise ValueError("Expected labels and predictions must have equal lengths.")
    if not expected:
        raise ValueError("At least one labeled example is required.")
    labels = sorted(set(expected) | set(predicted))
    confusion = {
        actual: {guess: 0 for guess in labels}
        for actual in labels
    }
    for actual, guess in zip(expected, predicted):
        confusion[actual][guess] += 1

    per_class = {}
    f1_values = []
    for label in labels:
        true_positive = confusion[label][label]
        false_positive = sum(confusion[actual][label] for actual in labels if actual != label)
        false_negative = sum(confusion[label][guess] for guess in labels if guess != label)
        precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
        recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[label] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
        }
        f1_values.append(f1)

    return {
        "count": len(expected),
        "accuracy": round(sum(a == p for a, p in zip(expected, predicted)) / len(expected), 4),
        "macro_f1": round(sum(f1_values) / len(f1_values), 4),
        "per_class": per_class,
        "confusion_matrix": confusion,
    }
