"""Bounded, deterministic workflow for processing collected evidence."""

from dataclasses import dataclass
from typing import Any

import pandas as pd

from src.analysis.sentiment import add_sentiment
from src.analysis.topics import add_topics
from src.database.storage import save_reviews
from src.preprocessing.cleaning import prepare_reviews
from src.reporting.report_generator import build_report


@dataclass
class ResearchResult:
    """Results from the single bounded search-and-analysis pass."""

    records: pd.DataFrame
    report: dict[str, Any]
    stored_count: int


def process_research_records(
    records: list[dict[str, Any]] | pd.DataFrame,
    database_path: str | None = None,
    persist: bool = True,
) -> ResearchResult:
    """Clean, deduplicate, analyze, summarize, then persist one bounded batch."""
    cleaned = prepare_reviews(
        records.copy() if isinstance(records, pd.DataFrame) else pd.DataFrame(records)
    )
    analyzed = add_topics(add_sentiment(cleaned))
    report = build_report(analyzed)
    stored_count = (
        save_reviews(analyzed, path=database_path)
        if persist and not analyzed.empty else 0
    )
    return ResearchResult(records=analyzed, report=report, stored_count=stored_count)
