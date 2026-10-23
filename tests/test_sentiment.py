import pandas as pd
from src.analysis.sentiment import add_sentiment


def test_sentiment_returns_expected_columns():
    result = add_sentiment(pd.DataFrame({"review": ["This is wonderful!", "This is terrible."]}))
    assert "sentiment" in result.columns
    assert "sentiment_score" in result.columns
    assert len(result) == 2
