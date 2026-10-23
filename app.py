"""Streamlit interface for source-linked organization reputation research."""

import pandas as pd
import plotly.express as px
import streamlit as st

from src.agents.research_graph import process_research_records
from src.analysis.platform_sentiment import build_platform_sentiment
from src.data_collection.web_search import (
    SearchConfigurationError,
    SearchError,
    is_search_configured,
    search_social_platforms,
)
from src.database.storage import load_reviews, save_reviews
from src.rag.retrieval import answer_from_evidence

st.set_page_config(page_title="TrustScope AI", page_icon="🔎", layout="wide")
st.title("🔎 TrustScope AI")
st.caption(
    "Evidence-first organization research. Search with Tavily, analyze locally, "
    "and inspect the source for every finding."
)

sample = pd.DataFrame([
    {"organization": "Example Academy", "platform": "Demo", "review": "The instructor explained concepts clearly.", "date": "2026-09-01", "source_url": "", "content_type": "fictional_demo"},
    {"organization": "Example Academy", "platform": "Demo", "review": "The support team did not respond to my complaint.", "date": "2026-09-03", "source_url": "", "content_type": "fictional_demo"},
    {"organization": "Example Academy", "platform": "Demo", "review": "The projects were useful for learning.", "date": "2026-09-05", "source_url": "", "content_type": "fictional_demo"},
    {"organization": "Example Academy", "platform": "Demo", "review": "The course was expensive for the value provided.", "date": "2026-09-08", "source_url": "", "content_type": "fictional_demo"},
    {"organization": "Example Academy", "platform": "Demo", "review": "The staff was helpful and friendly.", "date": "2026-09-10", "source_url": "", "content_type": "fictional_demo"},
    {"organization": "Example Academy", "platform": "Demo", "review": "My experience was average, with both good and bad points.", "date": "2026-09-12", "source_url": "", "content_type": "fictional_demo"},
])

with st.sidebar:
    st.header("Research settings")
    organization = st.text_input("Organization name", placeholder="e.g., Example Academy")
    search_mode = st.radio(
        "Data source", ["Demo reviews", "Upload CSV", "Social platform search", "Saved research"]
    )
    search_topic = st.selectbox(
        "Research topic",
        ["reviews and feedback", "employee reviews", "customer complaints",
         "student experiences", "placement outcomes", "work culture"],
    )
    identity_context = st.text_input(
        "Optional location or industry",
        placeholder="e.g., Austin, Texas; online education",
    )
    st.caption("Only Tavily is used for external search. Saved data stays in local SQLite.")

data: pd.DataFrame | None = None
is_fictional = search_mode == "Demo reviews"

if search_mode == "Demo reviews":
    data = sample.copy()
elif search_mode == "Upload CSV":
    upload = st.file_uploader("Upload a CSV", type=["csv"])
    if upload is not None:
        try:
            data = pd.read_csv(upload)
        except (pd.errors.ParserError, UnicodeDecodeError, ValueError, OSError) as exc:
            st.error(f"Could not read CSV: {exc}")
    st.caption("Required: `review`. Optional: `organization`, `platform`, `date`, `source_url`.")
elif search_mode == "Social platform search":
    st.info(
        "Searches Reddit, YouTube, X, Instagram, Facebook, TikTok, and LinkedIn "
        "separately. Official websites and non-social domains are excluded. "
        "Tavily may return no results for a platform, so coverage cannot be guaranteed."
    )
    result_limit = st.slider(
        "Maximum results per platform",
        min_value=1,
        max_value=20,
        value=5,
        help="Seven separate platform searches. At 20 each, up to 140 results may be returned.",
    )
    if not is_search_configured():
        st.warning("Add TAVILY_API_KEY to your local .env file to enable social search.")
    if st.button("Search selected social platforms", type="primary"):
        st.session_state.pop("social_search_records", None)
        if not organization.strip():
            st.error("Enter an organization name first.")
        else:
            try:
                with st.spinner("Searching each social platform separately with Tavily..."):
                    search_result = search_social_platforms(
                        organization,
                        search_topic,
                        context=identity_context,
                        max_results_per_platform=result_limit,
                    )
                st.session_state["social_search_records"] = {
                    "organization": organization.strip(),
                    "topic": search_topic,
                    "context": identity_context.strip(),
                    "records": search_result["records"],
                    "platforms": search_result["platforms"],
                }
            except (SearchConfigurationError, SearchError, ValueError, RuntimeError) as exc:
                st.error(f"Search failed: {exc}")
    cached = st.session_state.get("social_search_records")
    if (
        cached
        and cached["organization"].casefold() == organization.strip().casefold()
        and cached["topic"] == search_topic
        and cached["context"] == identity_context.strip()
    ):
        data = pd.DataFrame(cached["records"])
        st.subheader("Social platform search coverage")
        coverage_frame = pd.DataFrame(cached["platforms"])
        st.dataframe(
            coverage_frame[["platform", "domain", "status", "result_count", "details"]],
            width="stretch",
            hide_index=True,
            alt="Search result status for each requested social platform.",
        )
        failed_platforms = coverage_frame[coverage_frame["status"] == "Search failed"]
        if not failed_platforms.empty:
            st.warning("Some platform searches failed. Other platform results are still shown.")
            for failed in failed_platforms.to_dict(orient="records"):
                st.error(f"{failed['platform']}: {failed['details']}")
        if data.empty:
            st.warning("No matching social-platform results were returned.")
elif search_mode == "Saved research":
    data = load_reviews(organization=organization.strip() or None)
    if data.empty:
        st.info("No local research is saved yet. Search with Tavily or upload a CSV.")

if data is not None and not data.empty:
    raw_result_count = len(data)
    try:
        result = process_research_records(
            data,
            persist=(search_mode == "Social platform search"),
        )
        data = result.records
    except (ValueError, OSError, RuntimeError) as exc:
        st.error(f"Could not process these records: {exc}")
        st.stop()

    if data.empty:
        st.warning("No usable review text was found.")
        st.stop()

    if is_fictional:
        st.subheader("Analysis results — fictional demo data")
    elif search_mode == "Social platform search":
        st.subheader(f"Search results: {organization.strip()}")
        st.caption(f"Collected {raw_result_count} social-platform snippets before deduplication.")
        st.success(f"Saved or updated {result.stored_count} unique records in local research history.")
    elif search_mode == "Saved research":
        st.subheader("Saved research")
    else:
        st.subheader("CSV analysis")

    counts = data["sentiment"].value_counts()
    total = len(data)
    linked_sources = data["source_url"].replace("", pd.NA).nunique()
    metric1, metric2, metric3, metric4 = st.columns(4)
    metric1.metric("Unique records", total)
    metric2.metric("Positive", f"{counts.get('Positive', 0) / total:.1%}")
    metric3.metric("Neutral", f"{counts.get('Neutral', 0) / total:.1%}")
    metric4.metric("Linked sources", int(linked_sources))

    left, right = st.columns(2)
    sentiment_data = (
        counts.reindex(["Positive", "Neutral", "Negative"], fill_value=0)
        .rename_axis("Sentiment").reset_index(name="Count")
    )
    with left:
        st.plotly_chart(
            px.pie(sentiment_data, names="Sentiment", values="Count", hole=0.4,
                   title="Sentiment distribution"),
            width="stretch",
            alt="Distribution of estimated sentiment labels.",
        )
    with right:
        topic_counts = data["primary_topic"].value_counts().rename_axis("Topic").reset_index(name="Count")
        st.plotly_chart(
            px.bar(topic_counts, x="Topic", y="Count", title="Keyword-based topic tags"),
            width="stretch",
            alt="Number of records assigned to each keyword-based topic.",
        )

    if "date" in data.columns:
        dated = data.assign(_date=pd.to_datetime(data["date"], errors="coerce"))
        dated = dated.dropna(subset=["_date"])
        if not dated.empty:
            with st.expander("Date breakdown (only where a source supplied a date)"):
                trend = (
                    dated.assign(_month=dated["_date"].dt.to_period("M").astype(str))
                    .groupby(["_month", "sentiment"]).size().reset_index(name="Count")
                )
                st.plotly_chart(
                    px.bar(trend, x="_month", y="Count", color="sentiment",
                           barmode="group", title="Records by published month"),
                    width="stretch",
                    alt="Search records grouped by supplied publication month.",
                )

    if search_mode == "Upload CSV":
        if st.button("Save analyzed CSV to local history"):
            try:
                saved = save_reviews(data)
                st.success(f"Saved or updated {saved} unique records locally.")
            except (ValueError, OSError, RuntimeError) as exc:
                st.error(f"Could not save records: {exc}")

    with st.expander("Evidence-based report and limitations"):
        st.write(f"Analyzed unique records: **{result.report['record_count']}**")
        st.write(
            "Source coverage:",
            f"{result.report.get('linked_record_count', 0)} records with links · "
            f"{result.report.get('unlinked_record_count', 0)} without links · "
            f"{result.report.get('source_count', 0)} distinct source URLs",
        )
        st.write("Providers represented in collected results:", result.report.get("source_providers", {}) or "Not recorded")
        st.write("Sentiment percentages:", result.report["sentiment"])
        st.write("Keyword topic counts:", result.report["topics"] or "No matching topics.")
        if result.report.get("mixed_sentiment_topics"):
            st.write(
                "Topics with both positive and negative records:",
                result.report["mixed_sentiment_topics"],
                "(mixed mentions, not verified contradictions)",
            )
        st.write("Limitations:")
        for limitation in result.report.get("limitations", []):
            st.markdown(f"- {limitation}")

    if search_mode == "Social platform search":
        search_state = st.session_state.get("social_search_records", {})
        if search_state.get("organization", "").casefold() == organization.strip().casefold():
            platform_summary = build_platform_sentiment(
                search_state.get("records", []),
                search_state.get("platforms", []),
            )
            scored_platforms = platform_summary[platform_summary["Records"] > 0].sort_values(
                ["Negative %", "Negative", "Records"],
                ascending=[False, False, False],
            )
            unavailable_platforms = platform_summary[platform_summary["Records"] == 0]
            platform_summary = pd.concat(
                [scored_platforms, unavailable_platforms],
                ignore_index=True,
            )
            st.subheader("Sentiment by social platform")
            st.caption(
                "Platforms with the larger negative share appear first. A platform "
                "is labeled more negative only when negative records outnumber positive "
                "records. These are VADER estimates from search snippets, not verified reviews."
            )
            st.dataframe(
                platform_summary,
                width="stretch",
                hide_index=True,
                alt="Positive, neutral, negative counts and sentiment balance for each social platform.",
            )

    if result.report.get("sources"):
        st.subheader("Source pages and platforms")
        source_pages = pd.DataFrame(result.report["sources"])
        st.dataframe(
            source_pages,
            width="stretch",
            hide_index=True,
            column_config={
                "source_url": st.column_config.LinkColumn(
                    "Source link", display_text="Open source page"
                )
            },
            alt="Source websites and links for collected feedback snippets.",
        )

    st.subheader("Ask about the collected evidence")
    st.caption(
        "Answers are retrieved excerpts, not AI-generated conclusions. "
        "If no evidence matches, TrustScope says so."
    )
    question = st.text_input(
        "Question",
        placeholder="e.g., What do the sources say about customer support?",
        key="evidence_question",
    )
    if question.strip():
        response = answer_from_evidence(question, data)
        st.write(response["answer"])
        for item in response["evidence"]:
            citation = item.get("source_url", "")
            label = item.get("title") or item.get("review_id", "Collected record")
            st.markdown(f"> {item.get('review', '')}")
            st.caption(f"Source: {item.get('source_platform') or 'Unknown source'}")
            if citation:
                st.markdown(f"[{label}]({citation})")
            else:
                st.caption(f"Source URL unavailable · record {item.get('review_id', 'unknown')}")

    st.subheader("Evidence explorer")
    sentiment_filter = st.selectbox(
        "Filter by estimated sentiment", ["All", "Positive", "Neutral", "Negative"]
    )
    shown = data if sentiment_filter == "All" else data[data["sentiment"] == sentiment_filter]
    visible_columns = [
        column for column in (
            "review_id", "organization", "platform", "date", "review", "sentiment",
            "sentiment_score", "sentiment_model", "primary_topic", "topics",
            "source_platform", "source_url", "title", "content_type", "source_provider",
            "search_query", "collected_at", "duplicate_group", "duplicate_sources",
        ) if column in shown.columns
    ]
    link_config = {}
    if "source_url" in shown.columns:
        link_config["source_url"] = st.column_config.LinkColumn(
            "Source URL", display_text="Open source"
        )
    st.dataframe(
        shown[visible_columns],
        width="stretch",
        hide_index=True,
        column_config=link_config,
        alt="Evidence records, estimates, topics, provenance, and duplicate metadata.",
    )
    st.download_button(
        "Download analyzed CSV",
        data.to_csv(index=False).encode("utf-8"),
        "trustscope_analysis.csv",
        "text/csv",
    )
    st.info(
        "Sentiment and keyword topics are estimates, not verification of claims "
        "or a verdict about an organization."
    )
elif data is None:
    st.markdown("### Start a research session")
    st.write(
        "Choose fictional demo data, upload a CSV, search supported social platforms "
        "with Tavily, or inspect records saved locally."
    )
