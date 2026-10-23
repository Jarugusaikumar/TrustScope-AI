import pandas as pd

from src.rag.retrieval import answer_from_evidence, retrieve_evidence


def test_retrieval_returns_matching_evidence_with_original_source():
    records = pd.DataFrame([{
        "review_id": "record-1",
        "review": "Customer support responded quickly and helpfully.",
        "source_url": "https://example.com/review",
        "content_type": "search_snippet",
    }])

    result = answer_from_evidence("What about customer support?", records)

    assert result["supported"] is True
    assert result["evidence"][0]["review_id"] == "record-1"
    assert result["evidence"][0]["source_url"] == "https://example.com/review"


def test_retrieval_abstains_when_no_records_match():
    result = answer_from_evidence(
        "Tell me about pricing",
        pd.DataFrame([{"review": "The staff was friendly."}]),
    )

    assert result["supported"] is False
    assert result["evidence"] == []
    assert "could not find matching evidence" in result["answer"]


def test_retrieval_rejects_unbounded_limit():
    try:
        retrieve_evidence("support", pd.DataFrame(), limit=21)
    except ValueError as error:
        assert "between 1 and 20" in str(error)
    else:
        raise AssertionError("An excessive retrieval limit should be rejected")
