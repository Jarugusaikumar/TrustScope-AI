# TrustScope AI Architecture

## Implemented data flow

```text
Demo / CSV / seven separate Tavily social-domain searches
        |
        v
Clean + normalize + exact deduplication
        |
        v
VADER sentiment + keyword topics
        |
        +------> Dashboard, CSV export, descriptive report
        |
        +------> Local SQLite research history
        |
        +------> Lexical evidence retrieval -> excerpts with source URLs
```

## Modules

- `app.py`: Streamlit controls, charts, evidence explorer, and question interface.
- `src/data_collection/web_search.py`: bounded Tavily social-domain searches and per-platform coverage status.
- `src/data_collection/platforms.py`: shared canonical platform/domain list.
- `src/analysis/platform_sentiment.py`: per-platform positive/neutral/negative counts and overall balance.
- `src/preprocessing/cleaning.py`: text normalization, per-organization deduplication, stable record IDs, duplicate-source retention.
- `src/analysis/sentiment.py`: VADER labels and model/version fields.
- `src/analysis/platform_sentiment.py`: separate per-platform sentiment counts and negative-first ranking.
- `src/analysis/topics.py`: explainable keyword-based topic tags.
- `src/agents/research_graph.py`: bounded, deterministic clean/analyze/report/persist pipeline. It does not run autonomous model agents.
- `src/database/storage.py`: local SQLite schema, persistence, organization filtering, and source merging.
- `src/rag/retrieval.py`: lexical retrieval and source-linked extractive evidence responses; no generated claims.
- `src/reporting/report_generator.py`: measured counts, sentiment shares, source coverage, and mixed-topic indicators.
- `src/evaluation/sentiment_metrics.py`: sentiment metrics for manually labeled examples.
- `src/evaluation/evidence_metrics.py`: retrieval, citation validity, and manually judged claim-support metrics.

## Provenance and evidence

The social search runs separate domain-restricted Tavily queries for Reddit, YouTube, X, Instagram, Facebook, TikTok, and LinkedIn. Only results whose URLs match the requested social domain are retained; official websites and other domains are excluded. Each platform reports results found, no results, or a safely described search failure. The URL, platform, query, available publication date, and UTC collection time are retained. Results remain search snippets and are not necessarily independent user reviews.

Sentiment is counted separately within each platform before cross-platform deduplication, so the per-platform comparison is not lost when duplicate text appears on multiple platforms. Within a platform, normalized exact duplicates are counted once. The overall platform balance is called more negative only when negative records outnumber positive records; an absent result is never treated as negative or positive.

Question answering returns matching records as quoted excerpts. It does not ask a language model to invent a synthesis. If no terms match, it explicitly says that there is no matching evidence. A URL is displayed only when it was returned or supplied.

## Deliberately lightweight design

Tavily is the only external API. The current implementation does not include Transformer model downloads, sentence embeddings, ChromaDB, an LLM, or LangGraph. VADER, keyword tags, SQLite, lexical retrieval, and a normal Python workflow provide local alternatives with fewer dependencies and easier testing. The boundaries are explicit so that a later migration can substitute these components without changing the evidence schema.

## Coverage and limitations

Source-coverage counts describe returned records and URLs; they are not proof that every post was searched. Tavily may return no results for some platforms. The app makes one bounded search request per platform and cannot guarantee platform coverage. Platform-hosted results could include official organization accounts; this is not a verified independent-review-only collection. Snippets may omit context or represent a page summary rather than an original review. Sentiment and topic labels are estimates, not factual verification or a verdict on an organization.
