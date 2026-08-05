# Final Demo Runbook — Agent 1 (SCRUM-18)

A scripted end-to-end demo, ~10 minutes. Every command and expected
output below was verified against `main`. Talking points cover the
SCRUM-18 acceptance criteria: architecture, Jira, GitHub PRs, database
records, and failure handling.

## Before the demo

- [ ] `.env` exists with a working AI key (`AI_MODEL=google_genai:gemini-flash-latest` — see `.env.example`)
- [ ] Fresh database for clean numbers: `rm -f agent1.db` — **do this before
      starting the servers** (tables are created once at startup, so deleting
      the file while the API is running leaves it with no tables and every
      request fails; if you delete it later, restart the API)
- [ ] Three terminals ready, venv activated in each (`source venv/bin/activate`)
- [ ] Browser tabs open: the Jira board (Epic SCRUM-1) and the GitHub repo's closed PRs

## Step 0 — Start the services (terminals 1 and 2)

```bash
python scripts/mock_agent3.py          # terminal 1 — stands in for Agent 3
```

```bash
python scripts/run_agent1.py           # terminal 2 — Agent 1's API
```

Both stop when you type `exit` + Enter (Ctrl+C works too).

## The client-facing way: the demo UI

Open **http://localhost:8000/demo** — a client-ready UI styled after the
EYEjee platform this agent extends. It comes pre-loaded with the demo
batch: click **Enrich companies** and the page shows live pipeline
stages, then the batch summary tiles (received / valid / invalid /
duplicates) and an enriched profile card per company — status badge,
confidence, products, audience, and which sources (including the
website scan) backed each profile.

The failure story works there too: stop the mock Agent 3, submit another
company from the UI, and its card comes back **Partially Completed**
with the Agent 3 Scanner dot in the header turning red.

Steps 2–5 below drive the same flow from the terminal — use whichever
fits the audience (the UI for clients, the terminal + logs + SQL for the
technical deep-dive), or the UI first and the terminal for the
"under the hood" encore.

Sanity check: `curl http://localhost:8000/health` → `{"status": "ok"}`.

> **Say:** "Agent 3 — the website scanner — is another team's service, so
> for the demo a small stub answers its contract on port 8003. Agent 1
> doesn't know the difference; the integration code is identical."

## Step 1 — Explain the architecture (30 seconds, before any request)

> **Say:** "The pipeline is eight services, top to bottom: API controller
> → input validation → URL normalization → batch orchestration → AI
> enrichment → Agent 3 integration → merge → database, with structured
> logging across all of them. Each service is one file under
> `src/services/`, each was built on its own feature branch and merged by
> PR, and each maps to a Jira ticket. The key design rule: one bad
> company never kills the batch."

## Step 2 — Submit the batch (terminal 3)

The demo payload has 4 companies engineered to exercise every path: two
valid (Anthropic, GitHub), one duplicate of Anthropic under a different
name and path, and one with a broken URL.

```bash
curl -s -X POST http://localhost:8000/api/agents/agent1/bulk-enrichment \
  -H 'Content-Type: application/json' -d @scripts/demo_batch.json | python3 -m json.tool
```

To demo on a **real EYEjee export** instead, use the platform's own
format — click **Import EYEjee export** in the UI and pick
`scripts/eyejee_export_example.json`, or from the terminal:

```bash
curl -s -X POST http://localhost:8000/api/agents/agent1/bulk-enrichment/import \
  -H 'Content-Type: application/json' -d @scripts/eyejee_export_example.json | python3 -m json.tool
```

> **Say:** "This is the platform's export, unchanged — its field names,
> its bare LinkedIn URLs. Agent 1 maps it at the boundary, so nobody has
> to reshape a file to use this."

Takes ~20–40 s (two live AI calls). Expected shape:

```json
{
  "batchId": "batch_xxxxxxxx",
  "status": "Completed",
  "totalReceived": 4,
  "validCompanies": 2,
  "invalidCompanies": 1,
  "duplicates": 1
}
```

> **Say:** "Four in — two valid, one rejected for an invalid URL, and one
> caught as a duplicate even though its name and URL path differ, because
> normalization reduces both to the same domain."

While it runs, point at **terminal 2's logs** scrolling by:
`validation_started` → `company_duplicate_skipped` →
`company_validation_failed` → `enrichment_started/completed` →
`agent3_scan_triggered` → `company_saved` — every line carries the batch
and company IDs, and the logger redacts any API keys that leak into
error text. Terminal 1 shows Agent 3 receiving the two scan requests.

## Step 3 — Retrieve results via the API

```bash
curl -s http://localhost:8000/api/agents/agent1/bulk-enrichment/<batchId> | python3 -m json.tool
```

Grab a `company_id` from the `company_saved` log lines, then:

```bash
curl -s http://localhost:8000/api/companies/<companyId> | python3 -m json.tool
```

> **Say (either profile):** "A full profile — description, industry,
> products, business model — at `confidence: high`. The domain clearly
> identified a company the model knows, so it filled the profile from
> solid knowledge; then the website scan confirmed evidence, which
> promotes confidence one level. `sourcesUsed` includes `website_scan`,
> and every confirmed field is linked to the URL that proved it."
>
> **Say (hallucination control):** "The flip side: a company the model
> can't confidently identify from its domain comes back mostly `unknown`
> at `confidence: low` — it's instructed that a similar name is not
> identification and an honest unknown beats confident fiction. Add a
> made-up company with a plausible URL if you want to show it live."

## Step 4 — Show the database records

```bash
sqlite3 -header -column agent1.db \
  "SELECT id, status, total_received, valid_companies, invalid_companies, duplicates FROM batches;"

sqlite3 -header -column agent1.db \
  "SELECT id, company_name, status, confidence FROM companies;"

sqlite3 -header -column agent1.db \
  "SELECT c.company_name, s.field_name, s.source_url
   FROM sources s JOIN companies c ON c.id = s.company_id LIMIT 6;"
```

> **Say:** "Batches, companies, and — the part I like — the `sources`
> table: every website-confirmed field is linked to the URL that proved
> it. AI-generated data and website evidence stay distinguishable."

## Step 5 — What happens when things fail

**Stop the mock Agent 3 (type `exit` in terminal 1), then:**

```bash
curl -s -X POST http://localhost:8000/api/agents/agent1/bulk-enrichment \
  -H 'Content-Type: application/json' \
  -d '{"companies": [{"companyName": "Vercel", "websiteUrl": "https://vercel.com"}]}' | python3 -m json.tool
```

Expected: batch `"Completed with Errors"`, and the company saved as
`Partially Completed` (visible in the companies query from Step 4).

> **Say:** "Agent 3 is down. Agent 1 retried the connection with backoff
> — you can see `agent3_scan_retry_attempt_failed` lines in the logs —
> then saved the company anyway with what AI enrichment produced, marked
> Partially Completed. Failures are classified permanent vs. temporary:
> temporary ones retry, permanent ones (like the broken URL in Step 2)
> fail fast into the `errors` table. Nothing crashes the batch."

## Step 6 — Jira and GitHub workflow

- **Jira board:** Epic SCRUM-1, tickets SCRUM-4 … SCRUM-18 — one per
  service/mission, moved across the board as work progressed.
- **GitHub → closed PRs:** one feature branch and PR per ticket
  (validation, DB model, enrichment, endpoints, Agent 3, merge, retry,
  logging, tests, normalization). Open PR #15 to show the review cycle:
  review comments → fix commit → merge.

> **Say:** "Every code change traces ticket → branch → PR → merge; the
> commit titles carry the SCRUM IDs."

## Q&A cheat sheet

- **How is confidence decided?** The model rates itself against a rubric
  (identified + solid knowledge = high; identified but incomplete =
  medium; unidentifiable = low), and the merge step promotes it one level
  when the website scan confirms evidence — every bump is traceable to a
  recorded source URL.
- **What if the AI returns malformed JSON?** Structured output is
  schema-enforced (Pydantic + LangChain); a bad response fails
  validation, retries once, then the company is marked Failed.
- **Can it use a different AI provider?** Yes — `AI_MODEL` in `.env` is a
  LangChain `provider:model` string; swapping providers is config-only.
- **Known limitations?** Synchronous processing, per-batch dedup only, no
  auth — the honest list is in
  [`agent1-documentation.md` §10](agent1-documentation.md).
