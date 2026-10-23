import pytest

from src.evaluation.evidence_metrics import (
    calculate_retrieval_metrics,
    citation_validity,
    claim_support_rate,
)
from src.evaluation.sentiment_metrics import calculate_sentiment_metrics


def test_metrics_include_macro_f1_accuracy_and_confusion_matrix():
    result = calculate_sentiment_metrics(
        ["Positive", "Negative", "Positive"],
        ["Positive", "Positive", "Positive"],
    )

    assert result["accuracy"] == pytest.approx(2 / 3, abs=0.0001)
    assert result["macro_f1"] < 1
    assert result["confusion_matrix"]["Negative"]["Positive"] == 1


def test_metrics_reject_different_label_counts():
    with pytest.raises(ValueError, match="equal lengths"):
        calculate_sentiment_metrics(["Positive"], [])


def test_metrics_reject_empty_labeled_dataset():
    with pytest.raises(ValueError, match="At least one"):
        calculate_sentiment_metrics([], [])


def test_retrieval_metrics_use_manually_labeled_relevant_ids():
    result = calculate_retrieval_metrics(
        ["a", "b", "c"], ["b", "c", "d"], k=2
    )

    assert result == {"precision_at_k": 0.5, "recall_at_k": 0.3333}


def test_citation_validity_flags_missing_record_ids():
    assert citation_validity(["known", "missing"], ["known"]) == 0.5


def test_claim_support_rate_treats_unclear_as_not_supported():
    assert claim_support_rate(
        ["supported", "unclear", "unsupported"]
    ) == pytest.approx(1 / 3, abs=0.0001)


def test_claim_support_rate_rejects_unknown_labels():
    with pytest.raises(ValueError, match="must be supported"):
        claim_support_rate(["probably"])
