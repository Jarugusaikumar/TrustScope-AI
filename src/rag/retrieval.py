"""Small local lexical retriever with extractive, source-linked answers."""

import re
from typing import Any

import pandas as pd

_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "do", "for", "from",
    "how", "i", "in", "is", "it", "of", "on", "or", "the", "their", "this",
    "to", "was", "what", "when", "where", "which", "who", "why", "with",
}


def retrieve_evidence(
    question: str, records: pd.DataFrame, limit: int = 5
) -> list[dict[str, Any]]:
    """Rank existing records by query-term overlap; return evidence, not claims."""
    if limit < 1 or limit > 20:
        raise ValueError("limit must be between 1 and 20.")
    terms = {
        term for term in re.findall(r"[a-z0-9]+", question.casefold())
        if len(term) > 1 and term not in _STOP_WORDS
    }
    if not terms or records.empty or "review" not in records.columns:
        return []

    ranked = []
    for row in records.to_dict(orient="records"):
        text = " ".join(
            str(row.get(field, ""))
            for field in ("review", "title", "organization", "platform", "source_platform")
        ).casefold()
        matched = terms.intersection(re.findall(r"[a-z0-9]+", text))
        if matched:
            ranked.append((len(matched) / len(terms), row))
    ranked.sort(key=lambda item: (-item[0], str(item[1].get("review_id", ""))))
    return [
        {"score": round(score, 3), **record}
        for score, record in ranked[:limit]
    ]


def answer_from_evidence(question: str, records: pd.DataFrame) -> dict[str, Any]:
    """Return matched source excerpts and citations, or explicitly abstain."""
    evidence = retrieve_evidence(question, records)
    if not evidence:
        return {
            "answer": (
                "I could not find matching evidence in the records currently "
                "available. Try a more specific question or collect more sources."
            ),
            "evidence": [],
            "supported": False,
        }

    return {
        "answer": (
            "These are the collected excerpts that match your question. "
            "They are search snippets or supplied records, not independently verified facts."
        ),
        "evidence": evidence,
        "supported": True,
    }
