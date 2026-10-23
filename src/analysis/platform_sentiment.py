"""Compare sentiment estimates independently for each social platform."""

import pandas as pd

from src.analysis.sentiment import add_sentiment
from src.data_collection.platforms import SOCIAL_PLATFORMS
from src.preprocessing.cleaning import prepare_reviews


def build_platform_sentiment(
    records: list[dict[str, str]] | pd.DataFrame,
    coverage: list[dict[str, str]],
) -> pd.DataFrame:
    """Report each platform's positive/negative balance or its unavailable status."""
    frame = records.copy() if isinstance(records, pd.DataFrame) else pd.DataFrame(records)
    rows = []
    for platform in SOCIAL_PLATFORMS:
        platform_coverage = next(
            (item for item in coverage if item.get("platform") == platform), {}
        )
        platform_records = (
            frame[frame["source_platform"] == platform]
            if not frame.empty and "source_platform" in frame.columns
            else pd.DataFrame()
        )
        if platform_records.empty:
            rows.append({
                "Platform": platform,
                "Records": 0,
                "Positive": 0,
                "Neutral": 0,
                "Negative": 0,
                "Positive %": None,
                "Neutral %": None,
                "Negative %": None,
                "Overall balance": platform_coverage.get("status", "No results"),
            })
            continue

        analyzed = add_sentiment(prepare_reviews(platform_records))
        counts = analyzed["sentiment"].value_counts()
        positive = int(counts.get("Positive", 0))
        neutral = int(counts.get("Neutral", 0))
        negative = int(counts.get("Negative", 0))
        total = len(analyzed)
        if negative > positive:
            balance = "More negative"
        elif positive > negative:
            balance = "More positive"
        elif positive == negative == 0:
            balance = "Neutral only"
        else:
            balance = "Equal positive and negative"
        rows.append({
            "Platform": platform,
            "Records": total,
            "Positive": positive,
            "Neutral": neutral,
            "Negative": negative,
            "Positive %": round(positive / total * 100, 1),
            "Neutral %": round(neutral / total * 100, 1),
            "Negative %": round(negative / total * 100, 1),
            "Overall balance": balance,
        })
    return pd.DataFrame(rows)
