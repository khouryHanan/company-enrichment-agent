# Agent 1 — Bulk Company Enrichment Agent

Receives a bulk list of companies, validates and normalizes the data,
enriches each profile using AI, triggers Agent 3 for website scanning,
merges the results, persists everything, and exposes it via API.

See [`docs/technical-design.md`](docs/technical-design.md) for the full
architecture, input/output formats, database schema, and error handling
design.

## Project structure

```
src/
├── api/          # API controller — routes + request/response schemas
├── services/     # validation, normalization, batch, enrichment, Agent 3, merge
├── db/           # models + repository (database service)
├── core/         # logging, custom errors, config
└── main.py       # app entrypoint

tests/
├── unit/         # per-service unit tests
├── integration/  # full pipeline tests
└── api/          # endpoint tests
```

## Setup

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Run locally

```bash
uvicorn src.main:app --reload
```

Visit `http://localhost:8000/health` to confirm it's running.

## Run tests

```bash
pytest
```

## Branches

Each folder above maps to a feature branch per Mission 2:
`feature/agent1-input-validation`, `feature/agent1-normalization`,
`feature/agent1-database-model`, `feature/agent1-enrichment-service`,
`feature/agent1-api-endpoints`, `feature/agent1-tests`.

## Status

Scaffold only — service functions raise `NotImplementedError` until
implemented by their owning branch. See the Jira board (Epic SCRUM-1)
for task assignments.
