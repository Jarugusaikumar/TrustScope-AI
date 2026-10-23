"""SQLite storage for deduplicated research records and source provenance."""

import json
import os
import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd

DEFAULT_DATABASE_PATH = Path(__file__).resolve().parents[2] / "data" / "trustscope.sqlite3"


def _database_path(path: str | Path | None = None) -> Path:
    return Path(path or os.getenv("TRUSTSCOPE_DB_PATH", DEFAULT_DATABASE_PATH))


def initialize_database(path: str | Path | None = None) -> Path:
    """Create the local database and its schema if they do not exist."""
    database_path = _database_path(path)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS reviews (
                review_id TEXT PRIMARY KEY,
                organization TEXT NOT NULL,
                review TEXT NOT NULL,
                record_json TEXT NOT NULL,
                saved_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_reviews_organization "
            "ON reviews(organization COLLATE NOCASE)"
        )
    return database_path


def save_reviews(
    records: pd.DataFrame | list[dict[str, Any]],
    path: str | Path | None = None,
) -> int:
    """Save records and merge duplicate-source provenance without inflating counts."""
    frame = records.copy() if isinstance(records, pd.DataFrame) else pd.DataFrame(records)
    if frame.empty:
        return 0
    if "review" not in frame.columns:
        raise ValueError("The records must contain a 'review' column.")

    if "review_id" not in frame.columns:
        from src.preprocessing.cleaning import prepare_reviews

        frame = prepare_reviews(frame)
    if "organization" not in frame.columns:
        frame["organization"] = "Unknown organization"

    database_path = initialize_database(path)
    with sqlite3.connect(database_path) as connection:
        for record in frame.fillna("").to_dict(orient="records"):
            review_id = str(record["review_id"])
            existing = connection.execute(
                "SELECT record_json FROM reviews WHERE review_id = ?", (review_id,)
            ).fetchone()
            if existing:
                stored = json.loads(existing[0])
                old_sources = _source_list(stored.get("duplicate_sources", "[]"))
                new_sources = _source_list(record.get("duplicate_sources", "[]"))
                primary_source = {
                    key: record.get(key, "")
                    for key in (
                        "platform", "source_platform", "date", "source_url", "title", "content_type",
                        "source_provider", "search_query", "collected_at",
                    )
                }
                sources = _unique_sources(old_sources + [primary_source] + new_sources)
                primary_url = str(stored.get("source_url", ""))
                if primary_url:
                    sources = [source for source in sources if source.get("source_url") != primary_url]
                record["duplicate_sources"] = json.dumps(sources, ensure_ascii=False)
                for column in (
                    "platform", "source_platform", "date", "source_url", "title", "content_type",
                    "source_provider", "search_query", "collected_at",
                ):
                    if column in stored:
                        record[column] = stored[column]

            connection.execute(
                """
                INSERT INTO reviews (review_id, organization, review, record_json)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(review_id) DO UPDATE SET
                    record_json = excluded.record_json
                """,
                (
                    review_id,
                    str(record.get("organization", "Unknown organization")),
                    str(record["review"]),
                    json.dumps(record, ensure_ascii=False, default=str),
                ),
            )
    return len(frame)


def load_reviews(
    organization: str | None = None,
    limit: int = 1000,
    path: str | Path | None = None,
) -> pd.DataFrame:
    """Load saved records, optionally filtered by organization."""
    if limit < 1 or limit > 10000:
        raise ValueError("limit must be between 1 and 10000.")
    database_path = _database_path(path)
    if not database_path.exists():
        return pd.DataFrame()

    with sqlite3.connect(database_path) as connection:
        if organization:
            rows = connection.execute(
                """
                SELECT record_json FROM reviews
                WHERE organization = ? COLLATE NOCASE
                ORDER BY saved_at DESC LIMIT ?
                """,
                (organization.strip(), limit),
            ).fetchall()
        else:
            rows = connection.execute(
                "SELECT record_json FROM reviews ORDER BY saved_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
    return pd.DataFrame([json.loads(row[0]) for row in rows])


def _source_list(value: object) -> list[dict[str, Any]]:
    try:
        parsed = json.loads(value) if isinstance(value, str) else value
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def _unique_sources(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str]] = set()
    unique = []
    for source in sources:
        identity = (
            str(source.get("source_url", "")),
            str(source.get("title", "")),
            str(source.get("collected_at", "")),
        )
        if identity not in seen and any(identity):
            seen.add(identity)
            unique.append(source)
    return unique
