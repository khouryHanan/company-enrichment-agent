# Agent 1 — Technical Documentation (SCRUM-17)

Everything a new developer needs to understand, run, and extend Agent 1.
Deeper material lives in the sibling docs and is linked where relevant:
[`technical-design.md`](technical-design.md) (original design),
[`api-examples.md`](api-examples.md) (full request/response examples),
[`test-results.md`](test-results.md) (test coverage and results).

---

## 1. Purpose

Agent 1 receives a bulk list of companies (name, website URL, optional
LinkedIn URL), validates and normalizes the input, enriches each company
profile using an AI model, triggers Agent 3 to scan the company website,
merges the AI output with website evidence, persists everything, and
exposes results through a REST API.

The core design guarantee: **one bad company never breaks the batch.**
Every per-company failure is caught, logged, and recorded while the rest
of the batch continues.

## 2. How a request flows

```
POST /api/agents/agent1/bulk-enrichment
  └─ validation_service      reject invalid records, flag duplicates
  └─ repository.create_batch assign batch_id, persist counts
  └─ for each valid company (sequential):
       ├─ normalization_service   clean URL, extract domain
       ├─ enrichment_service      AI call → structured profile
       ├─ agent3_integration      POST to Agent 3, get website evidence
       ├─ merge_service           AI profile + confirmed evidence
       └─ repository.save_company persist profile + source references
  └─ repository.finalize_batch   Completed / Completed with Errors
```

Stage failures degrade gracefully rather than propagate:
normalization/enrichment failure → company `Failed`, batch continues;
Agent 3 failure → company saved as `Partially Completed` with the AI
profile it already has; merge failure → same fallback.

Orchestration lives in `src/services/batch_service.py`; each stage is
its own module under `src/services/` (see the README for the layout).

## 3. Setup and running locally

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # then fill in your values
uvicorn src.main:app --reload
```

Confirm with `http://localhost:8000/health` → `{"status": "ok"}`.
Interactive API docs (Swagger) are auto-served at `/docs`.
Database tables are created automatically at application startup — no
migration step. Deleting `agent1.db` for a clean slate is always safe.

### Environment variables (`.env`)

| Variable | Meaning | Example |
|---|---|---|
| `DATABASE_URL` | SQLAlchemy connection string | `sqlite:///./agent1.db` |
| `AI_MODEL` | LangChain `provider:model` string — swapping providers is config-only, no code change | `google_genai:gemini-flash-latest` |
| `GEMINI_API_KEY` (or `ANTHROPIC_API_KEY`, `GROQ_API_KEY`) | API key matching the chosen provider | — |
| `AGENT3_BASE_URL` | Where Agent 3 listens | `http://localhost:8003` |
| `MAX_RETRIES` | Default retry budget for temporary errors | `3` |

The app refuses to start without `AI_MODEL` set. If your key returns
`429 RESOURCE_EXHAUSTED` with `limit: 0`, that model has no free-tier
quota — pick another (e.g. `gemini-flash-latest`).

## 4. Input and output formats

**Input** — `POST` body: `{"companies": [{"companyName", "websiteUrl",
"linkedinUrl"?}, ...]}`. The list must be non-empty; `companyName` and a
valid `websiteUrl` are required; `linkedinUrl` is optional but must be a
LinkedIn company-profile URL when present.

**Output** — a batch summary (`batchId`, `status`, counts) from the POST,
and per-company enrichment profiles (description, industry,
products/services, target audience, business model, `confidence`,
`missingFields`, `sourcesUsed`, `status`) from the company endpoint.

Full JSON examples for every endpoint and error case:
[`api-examples.md`](api-examples.md).

## 5. API endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/agents/agent1/bulk-enrichment` | Submit a batch; returns the batch summary |
| `GET` | `/api/agents/agent1/bulk-enrichment/{batchId}` | Batch status + counts |
| `GET` | `/api/companies/{companyId}` | One company's enriched profile |
| `GET` | `/health` | Liveness check |

## 6. Database schema

Five tables, defined in `src/db/models.py` (all access goes through
`src/db/repository.py`):

- **batches** — id, status, received/valid/invalid/duplicate counts, timestamps.
- **companies** — profile fields + `status` and `confidence`; FK to batch
  (cascade delete); unique constraint on `(batch_id, domain)` so the same
  domain can't be stored twice within one batch.
- **enrichment_results** — raw AI JSON per company (1:1), kept for
  auditability.
- **errors** — batch/company FK, `error_type`, message, `retry_count`.
- **sources** — `(company_id, field_name, source_url)` rows recording
  which URL confirmed which field (written by the merge step, so
  AI-generated vs. website-confirmed data stays distinguishable).

Field-level detail: [`technical-design.md` §7](technical-design.md).

## 7. Prompt design (enrichment)

`src/services/enrichment_service.py`. Design decisions, in order of
importance:

- **Structured output is enforced, not requested.** The output shape is a
  Pydantic model (`CompanyProfile`) passed to LangChain's
  `with_structured_output` — the provider's JSON/tool-calling mode
  guarantees types and required fields, so a malformed profile fails
  validation before reaching our code.
- **Hallucination control.** When the domain clearly identifies a company
  the model knows (github.com → GitHub), it may use its knowledge of that
  company to fill the profile. For companies it cannot confidently
  identify — a similar name alone is not identification — it must never
  guess: fields come back as `"unknown"` / `"not_available"` and are
  listed in `missingFields`, yielding a sparse, `confidence: "low"`
  profile by design.
- **Confidence is rubric-based and evidence-aware**: the prompt defines
  what `high` / `medium` / `low` mean so the value is comparable across
  companies, and the merge step promotes confidence one level when the
  website scan confirms evidence (recorded in `sourceReferences`) — the
  AI rated itself before any evidence existed.
- **Deterministic**: `temperature=0`.
- **Fail fast on bad output**: one retry on malformed output, then the
  company is marked `Failed` (a model that returns garbage once tends to
  repeat it — no point burning the full retry budget).
- **Provider-agnostic**: the model is chosen by the `AI_MODEL` config
  string; no code references a specific provider.

## 8. Error handling

Errors are classified as **permanent** (bad input, 4xx, malformed AI
output — never retried) or **temporary** (timeouts, connection errors,
5xx, DB save failures — retried with linear backoff via
`src/core/retry.py`, budget `MAX_RETRIES`). Exception types live in
`src/core/errors.py`; the full case-by-case table is in
[`technical-design.md` §9](technical-design.md).

Every stage logs structured events (`event key=value`) with batch and
company IDs via `src/core/logging.py`, which also **redacts secrets**
(Bearer tokens, provider key shapes, `api_key=` pairs) from every line —
provider exceptions can echo credentials, and error logs include raw
exception text.

## 9. Testing

```bash
pytest
```

94 tests: unit per service, integration for the full pipeline, API tests
per endpoint. External boundaries (AI provider, Agent 3, network) are
mocked; persistence runs against a real SQLAlchemy engine on in-memory
SQLite. Scenario-by-scenario coverage and latest results:
[`test-results.md`](test-results.md).

For a live end-to-end run you need an AI key with quota and something
answering the Agent 3 contract on `AGENT3_BASE_URL` (a ~30-line HTTP
stub returning `{"scanStatus": "Completed", "extractedData": {...}}`
suffices — see §8 of [`technical-design.md`](technical-design.md) for
the contract).

## 10. Known limitations

- **Synchronous batch processing.** The POST request blocks until the
  whole batch finishes — companies are processed sequentially, each with
  an AI call. Large batches mean long requests. A production version
  would enqueue the batch and return `202` immediately (the
  `GET /bulk-enrichment/{batchId}` endpoint already anticipates that).
- **No authentication** on any endpoint.
- **SQLite by default** — fine for the course scope; concurrent writers
  or multi-instance deployments need a real database via `DATABASE_URL`.
- **Duplicates are per-batch only.** The same company submitted in two
  different batches is enriched (and paid for) twice.
- **Enrichment uses no live web data of its own.** Agent 1 gives the
  model only the name/URLs; grounding comes from Agent 3's website scan.
  If Agent 3 is down, profiles rely purely on the model's prior knowledge
  minus the hallucination guardrails — i.e., often mostly `unknown`.
- **Agent 3 is an external contract, not part of this repo.** Nothing
  here implements the scanner; without one running, every company ends
  `Partially Completed`.
- **LinkedIn URLs are cleaned minimally** (whitespace/trailing slash);
  host variants like `linkedin.com` vs `www.linkedin.com` are not
  canonicalized. Nothing currently deduplicates on LinkedIn, so this has
  no functional impact today.
- **No schema migrations** — tables are `create_all`'d; schema changes
  on an existing database require manual handling.
