# TrustScope AI

TrustScope AI is a local-first organization feedback research dashboard. It can analyze a fictional demo, a CSV you provide, accessible Tavily search snippets, or records saved from earlier research.

## What works today

- Streamlit dashboard with sentiment, topic, date, and source views.
- Tavily-only social-domain search for Reddit, YouTube, X, Instagram, Facebook, TikTok, and LinkedIn. Each platform is searched separately, and non-platform/official website domains are excluded from this mode.
- Up to 20 results per platform search (up to 140 total across seven platforms), with a clickable source URL. No results are fabricated when Tavily cannot find a platform result.
- Search defaults to 5 results per platform; raise the slider when you want a larger collection.
- Per-platform positive, neutral, and negative VADER estimates, with platforms ordered by negative share and a plain-language balance.
- Search result URLs, titles, available publication dates, provider, query, collection time, and content type are preserved.
- Exact normalized-text deduplication per organization, with duplicate source provenance retained.
- VADER sentiment with model name, package version, and compound score.
- Transparent keyword-based topic labels.
- Local SQLite history at `data/trustscope.sqlite3` (ignored by Git); CSV records are saved only when you choose to save them.
- Local lexical evidence retrieval. The question feature returns matching collected excerpts and their original URLs; it abstains when nothing matches.
- Descriptive reports, source-coverage counts, mixed-topic indicators, and manually labeled sentiment/retrieval/citation evaluation helpers.
- CSV download and fictional sample data.

## Important implementation limits

**Tavily is the only external API used.** No Gemini key or other model-provider key is needed. The app does not make generative-model calls.

To keep setup quick and local, this version uses:

- VADER rather than a downloaded Transformer model.
- Keyword rules rather than a trained aspect model.
- Lexical retrieval rather than embeddings/ChromaDB.
- Evidence excerpts rather than generated RAG answers.
- A bounded, deterministic Python workflow rather than LangGraph agents.

These choices avoid extra services, model downloads, and unpredictable API cost. They are straightforward to replace later if you choose to add those dependencies. The application does not claim that those advanced technologies are implemented.

Tavily returns accessible web search snippets, not necessarily original reviews. It does not guarantee that every platform returns a result or that every post on a platform is searched. Search results and sentiment are evidence leads, not proof that a statement is true or that an organization is trustworthy or untrustworthy. A platform's own official social-media account can appear because it is hosted on that platform; snippets are not guaranteed to be independent user feedback.

## Windows setup

Run these commands in PowerShell from the project folder:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
streamlit run app.py
```

If PowerShell blocks virtual-environment activation, run without activating:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Open the local URL printed by Streamlit (usually `http://localhost:8501`).

## Tavily setup (optional)

1. Copy the example environment file:

   ```powershell
   Copy-Item .env.example .env
   ```

2. Add your Tavily credential to `.env` as `TAVILY_API_KEY=...`.
3. Restart Streamlit and select **Social platform search**.

Do not paste API keys into chat, source files, screenshots, or commits. A key previously shared in a conversation should be revoked and replaced. Never share the contents of `.env`.

Social searches are bounded to at most 20 results per platform request. Search errors are displayed without exposing provider error details. Search records are saved to the local database; CSV rows are saved only after you click **Save analyzed CSV to local history**.

## Deploy on Streamlit Community Cloud

The repository entry point is `app.py`, and dependencies are listed in the root `requirements.txt`. To publish:

1. Push this repository to GitHub.
2. In Streamlit Community Cloud, choose **Create app**, select this repository and the `main` branch, and set the main file path to `app.py`.
3. In the app's **Settings → Secrets**, add your Tavily credential in TOML format:

   ```toml
   TAVILY_API_KEY = "paste-your-own-key-here"
   ```

   Do not put the real key in this README or commit it to GitHub. The application supports both local `.env` files and hosted Streamlit secrets.
4. Deploy the app. Demo and CSV analysis work without Tavily; social search requires the secret.

Streamlit Community Cloud's local filesystem is not durable storage. SQLite research history may be lost when the app restarts or redeploys. Use CSV download for a copy, or configure a separate persistent database before relying on long-term history.

## CSV format

Required column:

- `review`

Optional metadata columns include `organization`, `platform`, `date`, `source_url`, `title`, and `content_type`. Unknown dates are left blank rather than inferred.

## Run tests

From the project folder:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Tests use mocked Tavily results and local temporary databases; they do not spend Tavily API credits.

## Data and privacy

- SQLite history is local and excluded from Git.
- `.env` and private datasets must not be committed.
- Only analyze information you are authorized to process.
- Search content is untrusted data, not instructions.
- See [docs/architecture.md](docs/architecture.md) for the data flow and [docs/evaluation_plan.md](docs/evaluation_plan.md) for evaluation guidance.
