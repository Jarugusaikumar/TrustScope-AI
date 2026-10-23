# Evaluation Plan

TrustScope does not claim model accuracy or citation-support rates until a representative, manually reviewed dataset exists.

## Sentiment

Create a held-out CSV with `review` and a manually assigned `expected_sentiment` column (`Positive`, `Negative`, or `Neutral`). Run the same VADER analysis used by the app and pass expected and predicted labels to `calculate_sentiment_metrics`. Record accuracy, per-class precision/recall/F1, macro F1, and the confusion matrix. Do not tune thresholds against the held-out set.

## Retrieval

For each test question, manually label relevant `review_id` values. Compare those IDs with the results from `retrieve_evidence` and use `calculate_retrieval_metrics` to measure Precision@K and Recall@K. Report the questions and K value alongside the scores.

## Citation validity and claim support

Check that every citation points to a record in the research set with `citation_validity`. Separately, have a reviewer label each factual report claim as supported, unsupported, or unclear based on its cited source. A citation that exists is not necessarily evidence that the cited source supports a claim.

## Data collection checks

Mocked Tavily tests cover result mapping and safe error handling. Live collection coverage depends on the configured Tavily account, the query, current web accessibility, and provider limits. Never report inaccessible social platforms as searched.

## Reporting

Keep the labeled examples and evaluation notes appropriately permissioned. Report dataset size and limitations with every evaluation. No target score should be presented as an achieved result without running the evaluation.
