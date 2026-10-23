import json

import pandas as pd

from src.reporting.report_generator import build_report


def test_report_includes_primary_and_duplicate_source_pages():
    report = build_report(pd.DataFrame([{
        "review_id": "record-1",
        "review": "Helpful support",
        "sentiment": "Positive",
        "topics": json.dumps(["Customer service"]),
        "source_url": "https://www.reddit.com/r/example",
        "source_platform": "Reddit",
        "title": "Reddit thread",
        "content_type": "search_snippet",
        "duplicate_sources": json.dumps([{
            "source_url": "https://example.org/feedback",
            "source_platform": "Website (example.org)",
            "title": "Feedback page",
            "content_type": "search_snippet",
        }]),
    }]))

    assert report["record_count"] == 1
    assert report["source_count"] == 2
    assert {source["source_platform"] for source in report["sources"]} == {
        "Reddit",
        "Website (example.org)",
    }
    assert {source["source_url"] for source in report["sources"]} == {
        "https://www.reddit.com/r/example",
        "https://example.org/feedback",
    }
