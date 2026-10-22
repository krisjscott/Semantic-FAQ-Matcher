# Verification record

The real-model API verification ran on 2026-10-22 at 07:40 UTC, using CPU inference, `all-MiniLM-L6-v2`, Sentence Transformers 6.2.0, and PyTorch 2.14.1. The threshold was 0.45. Measurements came from `python3 scripts/verify.py --in-process`, which invokes the real FastAPI routes through HTTPX's ASGI transport.

| Supplied test set | Valid queries | Invalid labels excluded | Top-1 | Top-3 | Correct after threshold | Unrelated rejection |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Original | 19 | 1 | 73.68% | 89.47% | 73.68% | Not applicable |
| Additional | 106 | 0 | 81.13% | 96.23% | 78.30% | Not applicable |
| Unrelated | 20 | 0 | Not applicable | Not applicable | Not applicable | 100.00% |

The invalid original label is `ORD011` for “I want to stop my order”. The label remains unchanged. No exact duplicate query rows were found across these supplied files.

The verification also exercised all 98 FAQ self-queries and independently recomputed the returned candidate score formula and evaluation denominators. This verifies integration; FAQ self-queries are not a generalization test. Full per-query output and current dataset hashes are in `artifacts/evaluation.json` and `artifacts/evaluation.csv`, generated locally and excluded from version control.

All 13 tests in `tests/test_backend.py` passed. The source audit in `scripts/check_data.py` verified the imported file hashes. The tests use fixed vectors for scoring behavior; the API verification uses the actual cached model.

Frontend verification is incomplete. This workspace blocks registry DNS access and TCP connections, and Recharts is absent from the available npm cache. A partial TypeScript check against available local dependencies reported only the unresolved `recharts` import. A Vite build also stopped on that unresolved import. This does not establish a successful production build or browser test. No substitute chart implementation or fabricated chart results were used. Run `npm install` and `npm run build` in `frontend` on a network-enabled machine, then exercise the UI against the running backend.

These measurements describe the supplied test files. They do not establish an optimal threshold or performance on independent held-out queries.
