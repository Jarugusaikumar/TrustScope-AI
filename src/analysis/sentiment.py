"""Baseline sentiment classification using VADER."""

from importlib.metadata import PackageNotFoundError, version

import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

_ANALYZER = SentimentIntensityAnalyzer()
try:
    _VADER_VERSION = version("vaderSentiment")
except PackageNotFoundError:
    _VADER_VERSION = "unknown"


def add_sentiment(data: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with sentiment labels and VADER compound scores."""
    df = data.copy()

    def classify(text: str) -> pd.Series:
        score = _ANALYZER.polarity_scores(str(text))["compound"]
        if score >= 0.05:
            label = "Positive"
        elif score <= -0.05:
            label = "Negative"
        else:
            label = "Neutral"
        return pd.Series({"sentiment": label, "sentiment_score": score})

    result = df["review"].apply(classify)
    df[["sentiment", "sentiment_score"]] = result[["sentiment", "sentiment_score"]]
    df["sentiment_model"] = "VADER"
    df["sentiment_model_version"] = _VADER_VERSION
    return df
