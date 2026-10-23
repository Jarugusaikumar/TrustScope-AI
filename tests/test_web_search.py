import sys
from datetime import datetime
from types import ModuleType

import pytest
from tavily import errors as tavily_errors

from src.data_collection.web_search import (
    SearchConfigurationError,
    SearchError,
    _get_tavily_api_key,
    identify_source_platform,
    is_search_configured,
    search_organization,
    search_social_platforms,
)
from src.data_collection.platforms import SOCIAL_PLATFORMS


def install_fake_tavily(monkeypatch, client_class):
    fake_tavily = ModuleType("tavily")
    fake_tavily.__path__ = []
    fake_tavily.TavilyClient = client_class
    monkeypatch.setitem(sys.modules, "tavily", fake_tavily)
    monkeypatch.setitem(sys.modules, "tavily.errors", tavily_errors)


def test_tavily_key_can_be_read_from_streamlit_cloud_secrets():
    assert _get_tavily_api_key(
        environment={},
        cloud_secrets={"TAVILY_API_KEY": "cloud-test-key"},
    ) == "cloud-test-key"


def test_environment_key_takes_precedence_over_cloud_secret():
    assert _get_tavily_api_key(
        environment={"TAVILY_API_KEY": "local-test-key"},
        cloud_secrets={"TAVILY_API_KEY": "cloud-test-key"},
    ) == "local-test-key"


def test_tavily_placeholder_is_not_treated_as_configured():
    assert not _get_tavily_api_key(
        environment={},
        cloud_secrets={"TAVILY_API_KEY": "replace_with_your_key"},
    )


def test_search_organization_returns_source_metadata(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")

    class FakeTavilyClient:
        def __init__(self, api_key):
            assert api_key == "test-key"

        def search(self, query, max_results):
            assert query == '"Example Co" reviews'
            assert max_results == 8
            return {
                "results": [{
                    "content": "A search result snippet.",
                    "published_date": "2026-10-01",
                    "url": "https://example.com/review",
                    "title": "Review page",
                }]
            }

    install_fake_tavily(monkeypatch, FakeTavilyClient)

    records = search_organization(" Example Co ", "reviews")

    assert len(records) == 1
    assert records[0]["review"] == "A search result snippet."
    assert records[0]["content_type"] == "search_snippet"
    assert records[0]["source_provider"] == "Tavily"
    assert records[0]["source_url"] == "https://example.com/review"
    assert records[0]["source_platform"] == "Website (example.com)"
    assert records[0]["collected_at"]
    assert datetime.fromisoformat(records[0]["collected_at"]).utcoffset().total_seconds() == 0


def test_search_organization_supports_tavily_maximum_results(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")

    class FakeTavilyClient:
        def __init__(self, api_key):
            pass

        def search(self, query, max_results):
            assert max_results == 20
            return {"results": []}

    install_fake_tavily(monkeypatch, FakeTavilyClient)
    assert search_organization("Example Co", max_results=20) == []


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://www.reddit.com/r/example", "Reddit"),
        ("https://m.youtube.com/watch?v=123", "YouTube"),
        ("https://x.com/example/status/1", "X"),
        ("https://uk.trustpilot.com/review/example.com", "Trustpilot"),
        ("https://reviews.example.org/page", "Website (reviews.example.org)"),
        ("not a url", "Unknown source"),
    ],
)
def test_identify_source_platform_never_guesses_unknown_domain(url, expected):
    assert identify_source_platform(url) == expected


def test_search_organization_rejects_excessive_result_count(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    with pytest.raises(ValueError, match="between 1 and 20"):
        search_organization("Example Co", max_results=21)


def test_search_organization_requires_tavily_key(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)

    assert not is_search_configured()
    with pytest.raises(SearchConfigurationError, match="TAVILY_API_KEY"):
        search_organization("Example Co")


def test_search_organization_rejects_unexpected_response(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")

    class FakeTavilyClient:
        def __init__(self, api_key):
            pass

        def search(self, query, max_results):
            return {"results": None}

    install_fake_tavily(monkeypatch, FakeTavilyClient)

    with pytest.raises(SearchError, match="unexpected response"):
        search_organization("Example Co")


def test_search_organization_reports_provider_errors_safely(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")

    class FakeTavilyClient:
        def __init__(self, api_key):
            pass

        def search(self, query, max_results):
            raise tavily_errors.UsageLimitExceededError("private provider detail")

    install_fake_tavily(monkeypatch, FakeTavilyClient)

    with pytest.raises(SearchError, match="account usage limits") as error:
        search_organization("Example Co")

    assert "private provider detail" not in str(error.value)


def test_search_organization_reports_network_errors_safely(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")

    class FakeTavilyClient:
        def __init__(self, api_key):
            pass

        def search(self, query, max_results):
            raise OSError("private network detail")

    install_fake_tavily(monkeypatch, FakeTavilyClient)

    with pytest.raises(SearchError, match="network connection") as error:
        search_organization("Example Co")

    assert "private network detail" not in str(error.value)


def test_social_search_queries_all_seven_domains_and_rejects_off_platform_results(
    monkeypatch,
):
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    seen_queries = []

    def fake_search(organization, topic, context, max_results):
        assert max_results == 3
        assert "reviews and feedback" in topic
        seen_queries.append(topic)
        domain = topic.split()[0].removeprefix("site:")
        return [
            {
                "organization": organization,
                "review": f"Feedback from {domain}",
                "source_url": f"https://www.{domain}/feedback",
                "source_platform": domain,
                "content_type": "search_snippet",
            },
            {
                "organization": organization,
                "review": "An official website result must be excluded.",
                "source_url": "https://official.example.com/reviews",
                "source_platform": "Website (official.example.com)",
                "content_type": "search_snippet",
            },
        ]

    monkeypatch.setattr(
        "src.data_collection.web_search.search_organization",
        fake_search,
    )

    result = search_social_platforms("Example Co", max_results_per_platform=3)

    assert len(seen_queries) == 7
    assert {topic.split()[0] for topic in seen_queries} == {
        f"site:{domain}" for domain in SOCIAL_PLATFORMS.values()
    }
    assert len(result["records"]) == 7
    assert {row["source_platform"] for row in result["records"]} == set(SOCIAL_PLATFORMS)
    assert len(result["platforms"]) == 7
    assert all(row["status"] == "Results found" for row in result["platforms"])
    assert {row["platform"] for row in result["records"]} == set(SOCIAL_PLATFORMS)


def test_social_search_reports_no_result_and_continues_after_platform_failure(
    monkeypatch,
):
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    calls = []

    def fake_search(organization, topic, context, max_results):
        calls.append(topic)
        if "site:reddit.com" in topic:
            return []
        if "site:youtube.com" in topic:
            raise SearchError("Tavily search failed safely.")
        domain = topic.split()[0].removeprefix("site:")
        return [{
            "organization": organization,
            "review": f"Good experience on {domain}.",
            "source_url": f"https://www.{domain}/example",
            "source_platform": domain,
            "content_type": "search_snippet",
        }]

    monkeypatch.setattr(
        "src.data_collection.web_search.search_organization",
        fake_search,
    )

    result = search_social_platforms("Example Co")

    assert len(calls) == 7
    assert result["platforms"][0]["status"] == "No results"
    assert result["platforms"][1]["status"] == "Search failed"
    assert result["platforms"][1]["details"] == "Tavily search failed safely."
    assert result["records"][0]["source_platform"] == "X"
    assert len(result["records"]) == 5
