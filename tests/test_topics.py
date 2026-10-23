import json

import pandas as pd

from src.analysis.topics import add_topics


def test_topics_are_transparent_and_keep_other_records():
    result = add_topics(pd.DataFrame({
        "review": ["Support was helpful, but the price was expensive.", "A pleasant experience."]
    }))

    assert json.loads(result.loc[0, "topics"]) == ["Customer service", "Pricing"]
    assert result.loc[1, "primary_topic"] == "Other"


def test_topics_requires_review_column():
    try:
        add_topics(pd.DataFrame({"text": ["hello"]}))
    except ValueError as error:
        assert "review" in str(error)
    else:
        raise AssertionError("Missing review field should be rejected")
