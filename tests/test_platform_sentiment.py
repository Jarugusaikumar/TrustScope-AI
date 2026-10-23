import pandas as pd

from src.analysis.platform_sentiment import build_platform_sentiment
from src.data_collection.web_search import SOCIAL_PLATFORMS


def test_platform_sentiment_ranks_negative_when_negative_outnumbers_positive():
    rows = [
        {
            "organization": "Example",
            "source_platform": "Reddit",
            "review": "Terrible awful horrible experience. I hate this service.",
            "source_url": "https://reddit.com/r/example/1",
        },
        {
            "organization": "Example",
            "source_platform": "Reddit",
            "review": "Very bad and terrible. Completely disappointed.",
            "source_url": "https://reddit.com/r/example/2",
        },
        {
            "organization": "Example",
            "source_platform": "Reddit",
            "review": "Absolutely wonderful excellent great service. I love it.",
            "source_url": "https://reddit.com/r/example/3",
        },
        {
            "organization": "Example",
            "source_platform": "YouTube",
            "review": "Absolutely wonderful excellent great service. I love it.",
            "source_url": "https://youtube.com/watch?v=1",
        },
    ]
    coverage = [
        {
            "platform": platform,
            "status": "No results",
        }
        for platform in SOCIAL_PLATFORMS
    ]

    result = build_platform_sentiment(rows, coverage).set_index("Platform")

    assert result.loc["Reddit", "Negative"] == 2
    assert result.loc["Reddit", "Positive"] == 1
    assert result.loc["Reddit", "Overall balance"] == "More negative"
    assert result.loc["YouTube", "Overall balance"] == "More positive"
    assert result.loc["Instagram", "Overall balance"] == "No results"
    assert result.loc["Instagram", "Records"] == 0


def test_identical_feedback_on_different_platforms_is_counted_once_per_platform():
    rows = [
        {
            "organization": "Example",
            "source_platform": platform,
            "review": "Excellent and wonderful service!",
        }
        for platform in ("Reddit", "YouTube")
    ]
    coverage = [
        {"platform": platform, "status": "Results found"}
        for platform in SOCIAL_PLATFORMS
    ]

    result = build_platform_sentiment(pd.DataFrame(rows), coverage).set_index("Platform")

    assert result.loc["Reddit", "Records"] == 1
    assert result.loc["YouTube", "Records"] == 1
