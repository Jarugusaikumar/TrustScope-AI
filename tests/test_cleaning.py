import json

import pandas as pd
from src.preprocessing.cleaning import prepare_reviews


def test_prepare_reviews_removes_blank_and_duplicate_rows():
    data = pd.DataFrame({"review": [" Great support ", "Great support", "", None, "Poor support"]})
    result = prepare_reviews(data)
    assert len(result) == 2
    assert "source_url" in result.columns


def test_prepare_reviews_deduplicates_normalized_text_across_sources():
    data = pd.DataFrame({
        "organization": ["Example Co", "example co", "Example Co"],
        "platform": ["Web search", "Forum", "Web search"],
        "review": ["Great support!", " great   SUPPORT ", "Great support"],
        "source_url": ["https://one.example", "https://two.example", "https://three.example"],
    })

    result = prepare_reviews(data)

    assert len(result) == 1
    assert result.loc[0, "source_url"] == "https://one.example"
    assert result.loc[0, "platform"] == "Web search"
    duplicates = json.loads(result.loc[0, "duplicate_sources"])
    assert [source["source_url"] for source in duplicates] == [
        "https://two.example",
        "https://three.example",
    ]


def test_prepare_reviews_does_not_deduplicate_different_organizations():
    data = pd.DataFrame({
        "organization": ["Example Co", "Another Co"],
        "review": ["Great support", "Great support"],
    })

    assert len(prepare_reviews(data)) == 2


def test_prepare_reviews_keeps_columns_when_all_reviews_are_blank():
    result = prepare_reviews(pd.DataFrame({"review": ["", None]}))

    assert result.empty
    assert "source_url" in result.columns
    assert "duplicate_sources" in result.columns
