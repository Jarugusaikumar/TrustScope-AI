"""Generate descriptive, non-generative summaries from analyzed records."""

import json
from typing import Any

import pandas as pd


def build_report(data: pd.DataFrame) -> dict[str, Any]:
    """Summarize measured counts and source coverage without inventing claims."""
    if data.empty:
        return {"record_count": 0, "sentiment": {}, "topics": {}, "sources": []}

    sentiment = (
        data["sentiment"].value_counts(normalize=True).mul(100).round(1).to_dict()
        if "sentiment" in data.columns else {}
    )
    topic_counts: dict[str, int] = {}
    if "topics" in data.columns:
        for value in data["topics"].fillna("[]"):
            try:
                topics = json.loads(value) if isinstance(value, str) else value
            except json.JSONDecodeError:
                topics = []
            for topic in (topics if isinstance(topics, list) else []):
                topic_counts[str(topic)] = topic_counts.get(str(topic), 0) + 1
    topic_sentiment: dict[str, dict[str, int]] = {}
    if "topics" in data.columns and "sentiment" in data.columns:
        for row in data.to_dict(orient="records"):
            try:
                topics = json.loads(row.get("topics", "[]"))
            except (TypeError, json.JSONDecodeError):
                topics = []
            sentiment_label = str(row.get("sentiment", "Unknown"))
            for topic in topics if isinstance(topics, list) else []:
                counts = topic_sentiment.setdefault(str(topic), {})
                counts[sentiment_label] = counts.get(sentiment_label, 0) + 1

    sources = []
    if "source_url" in data.columns:
        for row in data.to_dict(orient="records"):
            source_base = {
                "review_id": str(row.get("review_id", "")),
                "content_type": str(row.get("content_type", "")),
            }
            if row.get("source_url"):
                sources.append({
                    **source_base,
                    "title": str(row.get("title", "")),
                    "source_url": str(row["source_url"]),
                    "source_platform": str(row.get("source_platform", "")),
                })
            try:
                duplicates = json.loads(row.get("duplicate_sources", "[]") or "[]")
            except (TypeError, json.JSONDecodeError):
                duplicates = []
            if isinstance(duplicates, list):
                for duplicate in duplicates:
                    if isinstance(duplicate, dict) and duplicate.get("source_url"):
                        sources.append({
                            **source_base,
                            "title": str(duplicate.get("title", "")),
                            "source_url": str(duplicate["source_url"]),
                            "source_platform": str(duplicate.get("source_platform", "")),
                            "content_type": str(duplicate.get("content_type", "")),
                        })
    source_providers = (
        data["source_provider"].replace("", pd.NA).value_counts().to_dict()
        if "source_provider" in data.columns else {}
    )
    linked_count = (
        int(data["source_url"].fillna("").astype(str).str.strip().ne("").sum())
        if "source_url" in data.columns else 0
    )
    mixed_topics = [
        topic for topic, labels in topic_sentiment.items()
        if labels.get("Positive", 0) and labels.get("Negative", 0)
    ]
    return {
        "record_count": len(data),
        "sentiment": sentiment,
        "topics": dict(sorted(topic_counts.items(), key=lambda item: (-item[1], item[0]))),
        "linked_record_count": linked_count,
        "unlinked_record_count": len(data) - linked_count,
        "source_count": len({source["source_url"] for source in sources}),
        "source_providers": source_providers,
        "topic_sentiment": topic_sentiment,
        "mixed_sentiment_topics": mixed_topics,
        "sources": sources,
        "limitations": [
            "Sentiment is a VADER estimate, not verification of a claim.",
            "Tavily results are accessible search snippets, not comprehensive review coverage.",
            "No social platform is considered searched unless its source appears in the results.",
        ],
    }
