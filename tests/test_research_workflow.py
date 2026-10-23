import pandas as pd

from src.agents.research_graph import process_research_records
from src.database.storage import load_reviews


def test_workflow_cleans_analyzes_reports_and_persists_once(tmp_path):
    database = tmp_path / "workflow.sqlite3"
    raw = [
        {
            "organization": "Example",
            "review": "Helpful support and friendly staff.",
            "source_url": "https://example.com/a",
            "content_type": "search_snippet",
        },
        {
            "organization": "Example",
            "review": "Helpful support and friendly staff.",
            "source_url": "https://example.com/b",
            "content_type": "search_snippet",
        },
    ]

    result = process_research_records(raw, database_path=str(database))
    saved = load_reviews("Example", path=database)

    assert len(result.records) == 1
    assert result.records.loc[0, "primary_topic"] == "Customer service"
    assert result.report["record_count"] == 1
    assert result.stored_count == 1
    assert len(saved) == 1


def test_workflow_can_analyze_without_persisting():
    result = process_research_records(
        pd.DataFrame([{"organization": "Example", "review": "Good support."}]),
        persist=False,
    )

    assert len(result.records) == 1
    assert result.stored_count == 0
