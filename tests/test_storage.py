import json

import pandas as pd

from src.database.storage import load_reviews, save_reviews
from src.preprocessing.cleaning import prepare_reviews


def test_storage_deduplicates_records_and_merges_source_provenance(tmp_path):
    database = tmp_path / "test.sqlite3"
    first = prepare_reviews(pd.DataFrame([{
        "organization": "Example",
        "review": "Helpful support",
        "source_url": "https://one.example/review",
        "title": "First source",
    }]))
    second = prepare_reviews(pd.DataFrame([{
        "organization": "Example",
        "review": "Helpful support",
        "source_url": "https://two.example/review",
        "title": "Second source",
    }]))

    assert save_reviews(first, database) == 1
    assert save_reviews(second, database) == 1
    saved = load_reviews("example", path=database)

    assert len(saved) == 1
    assert saved.loc[0, "source_url"] == "https://one.example/review"
    duplicates = json.loads(saved.loc[0, "duplicate_sources"])
    assert {source["source_url"] for source in duplicates} == {
        "https://two.example/review"
    }


def test_storage_returns_empty_for_database_that_does_not_exist(tmp_path):
    assert load_reviews(path=tmp_path / "missing.sqlite3").empty
