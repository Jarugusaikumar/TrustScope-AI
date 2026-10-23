"""Basic input validation, normalization, and deduplication."""

import hashlib
import json

import pandas as pd


def prepare_reviews(data: pd.DataFrame) -> pd.DataFrame:
    """Validate and normalize review data without discarding source fields."""
    if "review" not in data.columns:
        raise ValueError("The input must contain a column named 'review'.")

    df = data.copy()
    df["review"] = df["review"].fillna("").astype(str).str.replace(r"\s+", " ", regex=True).str.strip()
    df = df[df["review"] != ""].copy()

    defaults = {
        "organization": "Unknown organization",
        "platform": "Unknown source",
        "source_platform": "Unknown source",
        "date": "",
        "source_url": "",
        "title": "",
        "content_type": "review",
        "source_provider": "",
        "search_query": "",
        "collected_at": "",
    }
    for column, default in defaults.items():
        if column not in df.columns:
            df[column] = default
        df[column] = df[column].fillna(default).astype(str)

    if df.empty:
        df["duplicate_sources"] = pd.Series(dtype="object")
        return df.reset_index(drop=True)

    # Exact normalized review text is deduplicated per organization across sources.
    df["_organization_key"] = (
        df["organization"]
        .str.casefold()
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )
    df["_review_key"] = (
        df["review"].str.casefold().str.replace(r"[^\w]+", " ", regex=True).str.strip()
    )
    source_columns = [
        "platform",
        "source_platform",
        "date",
        "source_url",
        "title",
        "content_type",
        "source_provider",
        "search_query",
        "collected_at",
    ]
    records = []
    for _, group in df.groupby(
        ["_organization_key", "_review_key"], sort=False, dropna=False
    ):
        first = group.iloc[0].drop(labels=["_organization_key", "_review_key"]).copy()
        duplicate_sources = []
        for _, row in group.iterrows():
            try:
                prior_sources = json.loads(row.get("duplicate_sources", "[]") or "[]")
            except (TypeError, json.JSONDecodeError):
                prior_sources = []
            if isinstance(prior_sources, list):
                duplicate_sources.extend(
                    source for source in prior_sources if isinstance(source, dict)
                )
        duplicate_sources.extend(
            {column: row[column] for column in source_columns}
            for _, row in group.iloc[1:].iterrows()
        )
        seen_sources = set()
        unique_sources = []
        for source in duplicate_sources:
            identity = (
                str(source.get("source_url", "")),
                str(source.get("title", "")),
                str(source.get("collected_at", "")),
            )
            if any(identity) and identity not in seen_sources:
                seen_sources.add(identity)
                unique_sources.append(source)
        duplicate_sources = unique_sources
        first["duplicate_sources"] = json.dumps(duplicate_sources, ensure_ascii=False)
        identity = f"{group.iloc[0]['_organization_key']}\0{group.iloc[0]['_review_key']}"
        first["review_id"] = hashlib.sha256(identity.encode("utf-8")).hexdigest()
        first["duplicate_group"] = first["review_id"]
        records.append(first)

    return pd.DataFrame(records).reset_index(drop=True)
