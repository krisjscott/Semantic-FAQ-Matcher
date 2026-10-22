# Semantic FAQ Matcher · 

Clarity is a local full-stack FAQ search application built from `Semantic_FAQ_Matcher_Jury2.ipynb`. React provides semantic search, FAQ browsing, and an evaluation dashboard. FastAPI runs `all-MiniLM-L6-v2` through Sentence Transformers and PyTorch. Answers come directly from the existing CSV.

## Run locally

Use Python 3.12 and Node.js 22.12 or newer. Run these commands from this project directory, which is the application root.

Create a Python environment and install the backend dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

On Windows, use `py -3.12 -m venv .venv` and `.venv\Scripts\Activate.ps1` in PowerShell instead of the first two commands.

The first backend start downloads the model from Hugging Face. Later starts reuse its cache. CPU inference is the default; no GPU, paid service, API key, or database is required. Startup finishes after the FAQ embeddings are ready. Allow time for the first download.

For a smaller CPU-only PyTorch installation on Linux or Windows, install it before the other backend requirements:

```bash
python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
```

In a second terminal, start the frontend:

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**. Keep both terminals running. Vite proxies `/api` to the backend on port 8000. Interactive API documentation is at **http://127.0.0.1:8000/docs**.

Ask “I forgot my password” to exercise the matcher. Open Knowledge base to browse, filter, expand, and download FAQs. Open Evaluation lab and select **Run evaluation** to measure the supplied test queries. Adjust the threshold and rerun to compare results. The dashboard starts without assumed metrics.

To check a production frontend bundle locally:

```bash
cd frontend
npm run build
npm run preview
```

Open the preview URL printed by Vite. Its `/api` proxy also requires the backend. For deployment elsewhere, serve `frontend/dist` and route `/api` to FastAPI through your hosting proxy. The included setup targets local use.

## Project files

```text
Semantic_FAQ_matcher/
├── backend/
│   ├── main.py                    # FastAPI routes and model lifecycle
│   ├── matcher.py                 # FAQMatcher.find_answer and batch ranking
│   ├── evaluation.py              # Label-aware metrics and threshold sweep
│   ├── repository.py              # CSV validation and FAQRepository contract
│   ├── schemas.py                 # API request and response models
│   ├── requirements.txt
│   ├── semantic_faq_dataset.csv   # Original cleaned 98-record FAQ source
│   └── data/                      # Three supplied test CSVs and source hashes
├── frontend/
│   ├── package.json
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── components/
│       ├── pages/                 # Search, library, evaluation, model details
│       ├── services/              # API calls and runtime response validation
│       ├── types/
│       └── index.css
├── notebooks/Semantic_FAQ_Matcher_Jury2.ipynb
├── scripts/check_data.py
├── scripts/verify.py
└── tests/test_backend.py
```

## Verify the application

Activate the Python environment and run from the application root:

```bash
python -m unittest discover -s tests -v
python scripts/check_data.py
python scripts/verify.py
```

The unit tests cover the scoring formula, tokenization, threshold equality, rejection, invalid labels, CSV validation, and API request handling. They use fixed vectors to test scoring without downloading a model. `check_data.py` verifies the original source hashes and reports unknown labels.

See [the verification record](docs/validation.md) for the measured results and the current frontend verification limitation.

`verify.py` uses the running API and the real model. It checks all FAQ self-queries, recomputes each returned candidate score, evaluates every supplied test row, and independently checks metric denominators. It writes `artifacts/evaluation.json` and `artifacts/evaluation.csv`. Self-query checks verify integration; they do not measure generalization accuracy.

If TCP connections are unavailable in a restricted environment, run the same real-model API checks through FastAPI's ASGI transport:

```bash
FAQ_LOCAL_FILES_ONLY=1 python scripts/verify.py --in-process
```

`FAQ_LOCAL_FILES_ONLY=1` requires the model to be cached already. Omit that variable to allow the first download.

## API reference

| Method | Endpoint | Behavior |
| --- | --- | --- |
| GET | `/api/health` | Model readiness and FAQ count after startup |
| GET | `/api/metadata` | Model, weights, categories, threshold, source hash, test inventory |
| GET | `/api/faqs?search=order&category=Order%20Tracking` | Optional text and category filtering |
| GET | `/api/dataset/download` | Download the FAQ CSV |
| POST | `/api/match` | Return the best accepted FAQ and top three ranked candidates |
| POST | `/api/evaluate` | Evaluate all available supplied test sets |

Example matching request:

```bash
curl http://127.0.0.1:8000/api/match \
  -H 'Content-Type: application/json' \
  -d '{"query":"I forgot my password","threshold":0.45}'
```

Evaluation accepts `{"threshold":0.45}`. Match queries must contain non-whitespace text and at most 2,000 characters. Thresholds must be finite numbers from 0 to 1. Invalid requests return HTTP 422. `/docs` contains the live endpoint schemas.

## Matching method

The implementation preserves the notebook's model, tokenization, and weights:

```text
semantic_similarity = cosine(query_embedding, faq_question_embedding)
keyword_overlap = len(query_tokens & faq_tokens) / len(query_tokens)
combined_score = 0.85 * semantic_similarity + 0.15 * keyword_overlap
```

Tokens are distinct lowercase matches of `\b[a-z0-9]+\b`, including the notebook's stopwords and punctuation behavior. FAQ and query embeddings are normalized. Their dot product computes cosine similarity. The [Sentence Transformers encoding API](https://sbert.net/docs/package_reference/sentence_transformer/SentenceTransformer.html) documents this normalization option.

`FAQMatcher.find_answer()` retains the notebook function name and result fields. It adds the threshold, elapsed time, candidate answers, and score components. A best score greater than or equal to the threshold returns the FAQ answer. A lower score returns the original rephrase-or-contact-support fallback while still exposing the candidates. The API rejects empty questions before inference.

The initial threshold is **0.45**. It is not a proven optimum. Scores are similarity measures, not confidence probabilities. Full precision controls ranking and acceptance; the UI rounds scores only for display.

FAQ embeddings load once through [FastAPI lifespan](https://fastapi.tiangolo.com/advanced/events/). Blocking inference runs in FastAPI worker threads. A lock serializes access to the model. Test-query embeddings and scores are cached for the current process, so changing a threshold does not require another encoding pass. Each server worker loads its own model and data snapshot.

## Dataset and evaluation notes

The files were copied from the existing Downloads folder. The local FAQ CSV matched `semantic_faq_dataset.csv` in contents when inspected. No FAQ records or expected labels were invented. The alternative `semantic_faq_dataset (1).csv` has an extra empty spreadsheet column; the cleaned existing CSV has the four required columns.

| Source file | Application file | Records |
| --- | --- | ---: |
| `semantic_faq_dataset.csv` | `backend/semantic_faq_dataset.csv` | 98 |
| `semantic_faq_test_queries (1).csv` | `backend/data/semantic_faq_test_queries.csv` | 20 |
| `semantic_faq_additional_test_queries.csv` | `backend/data/semantic_faq_additional_test_queries.csv` | 106 |
| `semantic_faq_no_match_test_queries.csv` | `backend/data/semantic_faq_no_match_test_queries.csv` | 20 |

The original test row “I want to stop my order” expects `ORD011`, which does not exist in the supplied FAQ dataset. The evaluation keeps this row visible, marks its label invalid, and excludes it from accuracy denominators. It does not guess a replacement label.

Metrics follow these definitions:

- **Top-1 accuracy:** the highest-ranked FAQ has the expected ID, before thresholding, divided by valid labeled queries.
- **Top-3 accuracy:** the expected ID appears among the three ranked candidates, divided by valid labeled queries.
- **Correct after threshold:** the returned FAQ has the expected ID, divided by all valid labeled queries. Rejections remain in this denominator.
- **Unrelated-query rejection rate:** rejected queries divided by queries in the supplied no-match CSV. False accepts count unrelated questions that received an FAQ.

The original and additional sets remain separate. The dashboard reports repeated query rows, invalid labels, per-query outcomes, measurement time, and file hashes. Missing test files produce unavailable metrics rather than invented results. Malformed files produce a validation error.

The threshold chart explores 0.20 through 0.80 on these same queries. Its correct-match series pools valid labeled rows from both labeled files; its rejection series uses only the no-match file. These sets can overlap and should not be presented as independent held-out validation. A threshold selected from this chart needs fresh validation data. Exact-ID scoring can also mark a related answer incorrect when the original label names another FAQ.

## Change the datasets

Replace `backend/semantic_faq_dataset.csv` with a UTF-8 CSV containing `faq_id`, `category`, `question`, and `answer`, then restart the backend. IDs must be unique and every required field must contain text. The loader trims fields and normalizes IDs to uppercase. It fails startup for missing columns, duplicate IDs, empty records, or an empty dataset.

Keep labeled test files in `backend/data` with `user_query,expected_faq_id`. The unrelated-query file needs `user_query`. Restart after changing either FAQ or test data to rebuild the embeddings and cached test scores. `provenance.json` records the original imported files; `check_data.py` intentionally reports hash changes after a deliberate dataset update. Live metadata and evaluation reports include current hashes.

To add PostgreSQL later, implement `FAQRepository.load()` and pass it to `FAQMatcher`. Ranking and evaluation depend on the repository contract rather than CSV parsing.

## Configuration and troubleshooting

| Variable | Default | Purpose |
| --- | --- | --- |
| `FAQ_DATA_PATH` | `backend/semantic_faq_dataset.csv`, resolved beside the backend code | Alternative FAQ file |
| `FAQ_TEST_DATA_DIR` | `backend/data`, resolved beside the backend code | Alternative test directory |
| `FAQ_DEVICE` | `cpu` | PyTorch inference device, such as `cuda` |
| `FAQ_LOCAL_FILES_ONLY` | `0` | Set to `1` to require the cached model |
| `FAQ_CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated origins for direct API clients |

The UI keeps the chosen threshold and recent questions in memory. They reset on refresh; no user questions are written to disk. The evaluation export is a user-triggered JSON download. The CLI writes local JSON and CSV reports.

If the UI says the API is unavailable, wait for Uvicorn's `Application startup complete` message and check `/api/health`. If port 8000 changes, update both proxy targets in `frontend/vite.config.ts`. If npm cannot resolve packages or the model cannot download, check your network connection. An offline setup needs both the npm dependencies and Hugging Face model cached in advance.

The frontend uses React, Vite, strict TypeScript, Lucide React, Recharts, and [Tailwind's Vite integration](https://tailwindcss.com/docs/installation/using-vite). API response validation lives at the fetch boundary through Zod. Loading, empty, rejected, and error states use actual request outcomes.
