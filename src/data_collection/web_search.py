"""Tavily search connector. Search snippets are leads, not verified reviews."""

import os
from datetime import datetime, timezone
from collections.abc import Mapping
from urllib.parse import urlsplit

from dotenv import load_dotenv

from src.data_collection.platforms import SOCIAL_PLATFORMS

load_dotenv()


class SearchConfigurationError(ValueError):
    """Raised when Tavily web search has not been configured."""


class SearchError(RuntimeError):
    """Raised when Tavily cannot complete a search."""


_PLATFORM_DOMAINS = {
    "facebook.com": "Facebook",
    "glassdoor.com": "Glassdoor",
    "instagram.com": "Instagram",
    "linkedin.com": "LinkedIn",
    "reddit.com": "Reddit",
    "tiktok.com": "TikTok",
    "trustpilot.com": "Trustpilot",
    "x.com": "X",
    "twitter.com": "X (Twitter)",
    "youtube.com": "YouTube",
    "youtu.be": "YouTube",
    "indeed.com": "Indeed",
    "google.com": "Google",
}

def identify_source_platform(source_url: str) -> str:
    """Identify known platform URLs; otherwise report the returned website domain."""
    try:
        hostname = urlsplit(source_url.strip()).hostname
    except ValueError:
        hostname = None
    if not hostname:
        return "Unknown source"

    hostname = hostname.casefold().rstrip(".")
    for domain, platform in _PLATFORM_DOMAINS.items():
        if hostname == domain or hostname.endswith(f".{domain}"):
            return platform
    return f"Website ({hostname.removeprefix('www.')})"


def is_search_configured() -> bool:
    """Return whether a non-placeholder Tavily API key is available."""
    return bool(_get_tavily_api_key())


def _get_tavily_api_key(
    environment: Mapping[str, str] | None = None,
    cloud_secrets: Mapping[str, str] | None = None,
) -> str:
    """Read Tavily credentials from environment/.env or hosted Streamlit secrets."""
    environment = os.environ if environment is None else environment
    api_key = environment.get("TAVILY_API_KEY", "").strip()
    if api_key and "replace_with_your_key" not in api_key.casefold():
        return api_key

    if cloud_secrets is None:
        try:
            import streamlit as st
            from streamlit.errors import StreamlitSecretNotFoundError
        except ImportError:
            cloud_secrets = {}
        else:
            try:
                secret_key = st.secrets.get("TAVILY_API_KEY", "").strip()
            except StreamlitSecretNotFoundError as exc:
                if getattr(exc, "error_id", "") != "no-secrets-found":
                    raise
                secret_key = ""
    else:
        secret_key = cloud_secrets.get("TAVILY_API_KEY", "").strip()
    if "replace_with_your_key" in secret_key.casefold():
        return ""
    return secret_key


def search_organization(
    organization: str,
    topic: str = "reviews and feedback",
    context: str = "",
    max_results: int = 8,
) -> list[dict[str, str]]:
    """Search accessible web results and return records with source metadata."""
    organization = organization.strip()
    topic = topic.strip()
    context = context.strip()
    if not organization:
        raise ValueError("Enter an organization name before searching.")
    if max_results < 1 or max_results > 20:
        raise ValueError("max_results must be between 1 and 20.")

    api_key = _get_tavily_api_key()
    if not api_key:
        raise SearchConfigurationError(
            "TAVILY_API_KEY is not configured. Add your Tavily key to .env."
        )

    try:
        from tavily import TavilyClient
        from tavily.errors import (
            BadRequestError,
            ForbiddenError,
            InvalidAPIKeyError,
            TimeoutError as TavilyTimeoutError,
            UsageLimitExceededError,
        )
    except ImportError as exc:
        raise RuntimeError(
            "Install dependencies with: python -m pip install -r requirements.txt"
        ) from exc

    query = " ".join(part for part in (f'"{organization}"', context, topic) if part)
    try:
        client = TavilyClient(api_key=api_key)
        response = client.search(query=query, max_results=max_results)
    except (
        BadRequestError,
        ForbiddenError,
        InvalidAPIKeyError,
        UsageLimitExceededError,
        TavilyTimeoutError,
        OSError,
    ) as exc:
        raise SearchError(
            "Tavily search failed. Check the API key, account usage limits, "
            "and network connection."
        ) from exc

    if not isinstance(response, dict) or not isinstance(response.get("results", []), list):
        raise SearchError("Tavily returned an unexpected response.")

    collected_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    records = []
    for item in response.get("results", []):
        if not isinstance(item, dict):
            continue
        source_url = item.get("url", "") or ""
        records.append({
            "organization": organization,
            "platform": "Web search",
            "source_platform": identify_source_platform(source_url),
            "review": item.get("content", "") or "",
            "date": item.get("published_date", "") or "",
            "source_url": source_url,
            "title": item.get("title", "") or "",
            "content_type": "search_snippet",
            "source_provider": "Tavily",
            "search_query": query,
            "collected_at": collected_at,
        })
    return records


def search_social_platforms(
    organization: str,
    topic: str = "reviews and feedback",
    context: str = "",
    max_results_per_platform: int = 5,
) -> dict[str, list[dict[str, str]] | list[dict[str, str]]]:
    """Search the selected social domains separately and report per-platform coverage."""
    organization = organization.strip()
    if not organization:
        raise ValueError("Enter an organization name before searching.")
    if max_results_per_platform < 1 or max_results_per_platform > 20:
        raise ValueError("max_results_per_platform must be between 1 and 20.")
    if not is_search_configured():
        raise SearchConfigurationError(
            "TAVILY_API_KEY is not configured. Add your Tavily key to .env."
        )

    records: list[dict[str, str]] = []
    coverage: list[dict[str, str]] = []
    for platform, domain in SOCIAL_PLATFORMS.items():
        try:
            platform_records = search_organization(
                organization,
                topic=f"site:{domain} {topic}".strip(),
                context=context,
                max_results=max_results_per_platform,
            )
        except SearchError as exc:
            coverage.append({
                "platform": platform,
                "domain": domain,
                "status": "Search failed",
                "result_count": "0",
                "details": str(exc),
            })
            continue

        accepted = []
        for record in platform_records:
            source_platform = identify_source_platform(record.get("source_url", ""))
            is_platform_alias = (
                (platform == "X" and source_platform == "X (Twitter)")
                or (platform == "YouTube" and source_platform == "YouTube")
            )
            if source_platform != platform and not is_platform_alias:
                continue
            accepted.append({
                **record,
                "platform": platform,
                "source_platform": platform,
            })
        records.extend(accepted)
        coverage.append({
            "platform": platform,
            "domain": domain,
            "status": "Results found" if accepted else "No results",
            "result_count": str(len(accepted)),
            "details": "",
        })
    return {"records": records, "platforms": coverage}
