"""Rule-based aspect tags for common organization feedback themes."""

import json

import pandas as pd

TOPIC_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Customer service": ("support", "service", "staff", "helpful", "response", "respond"),
    "Product or course quality": ("quality", "product", "course", "content", "instructor", "teaching"),
    "Pricing": ("price", "pricing", "cost", "expensive", "cheap", "value", "refund"),
    "Placement support": ("placement", "job", "career", "salary", "hiring", "employment"),
    "Work culture": ("work culture", "workplace", "employee", "workload", "team", "culture"),
    "Management": ("management", "manager", "leadership", "policy", "communication"),
    "Delivery and reliability": ("delivery", "late", "delay", "reliable", "reliability", "broken"),
}


def add_topics(data: pd.DataFrame) -> pd.DataFrame:
    """Add transparent keyword-derived topics; do not claim learned aspects."""
    if "review" not in data.columns:
        raise ValueError("The input must contain a column named 'review'.")

    result = data.copy()

    def topics_for(text: object) -> list[str]:
        normalized = str(text).casefold()
        return [
            topic
            for topic, keywords in TOPIC_KEYWORDS.items()
            if any(keyword in normalized for keyword in keywords)
        ]

    result["topics"] = result["review"].apply(
        lambda text: json.dumps(topics_for(text), ensure_ascii=False)
    )
    result["primary_topic"] = result["topics"].apply(
        lambda value: (json.loads(value) or ["Other"])[0]
    )
    return result
