"""Evaluation helpers for retrieved evidence and manually reviewed citations."""

from typing import Sequence


def calculate_retrieval_metrics(
    retrieved_ids: Sequence[str],
    relevant_ids: Sequence[str],
    k: int | None = None,
) -> dict[str, float]:
    """Calculate Precision@K and Recall@K against manually judged evidence IDs."""
    if k is not None and k < 1:
        raise ValueError("k must be at least 1.")
    relevant = set(relevant_ids)
    if not relevant:
        raise ValueError("At least one manually labeled relevant record is required.")
    results = list(retrieved_ids[:k] if k is not None else retrieved_ids)
    relevant_retrieved = sum(record_id in relevant for record_id in results)
    return {
        "precision_at_k": round(relevant_retrieved / len(results), 4) if results else 0.0,
        "recall_at_k": round(relevant_retrieved / len(relevant), 4),
    }


def citation_validity(citation_ids: Sequence[str], record_ids: Sequence[str]) -> float:
    """Return the fraction of citations that point to IDs in collected evidence."""
    if not citation_ids:
        raise ValueError("At least one citation is required.")
    available = set(record_ids)
    return round(sum(item in available for item in citation_ids) / len(citation_ids), 4)


def claim_support_rate(review_labels: Sequence[str]) -> float:
    """Return the manually judged supported-claim share; unclear is not supported."""
    allowed = {"supported", "unsupported", "unclear"}
    labels = [label.casefold().strip() for label in review_labels]
    if not labels:
        raise ValueError("At least one manually reviewed claim is required.")
    if any(label not in allowed for label in labels):
        raise ValueError("Claim labels must be supported, unsupported, or unclear.")
    return round(labels.count("supported") / len(labels), 4)
