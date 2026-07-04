# Agent 1 — Technical Design Document
### Bulk Company Enrichment Agent

**Status:** Draft — pending PM/instructor approval
**Owner:** Team Lead
**Related Jira Epic:** SCRUM-1

---

## 1. Purpose

Agent 1 receives a bulk list of companies (name, website URL, LinkedIn URL), validates and normalizes the data, enriches each company profile using AI, triggers Agent 3 to scan the company website, merges the results, persists everything to the database, and exposes the results through API endpoints.

This document defines the technical structure before implementation begins, per Mission 3.

---

## 2. High-Level Architecture

The pipeline flows top-down through eight components:

1. **API Controller** — receives the bulk request, returns batch ID
2. **Input Validation Service** — checks structure and required fields
3. **URL Normalization Service** — cleans and standardizes website/LinkedIn URLs
4. **Batch Processing Service** — orchestrates per-company processing, tracks status
5. **Company Enrichment Service** — calls the AI model, produces structured JSON
6. **Agent 3 Integration Service** — triggers website scanning, receives results
7. **Database Service** — persists companies, batches, results, errors
8. **Logging Service** — cross-cutting, called by every component above

*(See the architecture pipeline diagram above for the request-level flow.)*

---

## 3. Project / Folder Structure

```
agent1-enrichment/
├── src/
│   ├── api/
│   │   ├── routes.py               # API controller — route definitions
│   │   └── schemas.py              # request/response Pydantic models
│   ├── services/
│   │   ├── validation_service.py
│   │   ├── normalization_service.py
│   │   ├── batch_service.py
│   │   ├── enrichment_service.py    # AI prompt + parsing
│   │   ├── agent3_integration.py
│   │   └── merge_service.py
│   ├── db/
│   │   ├── models.py                # ORM models: Company, Batch, Result, Error
│   │   ├── repository.py            # DB read/write functions
│   │   └── migrations/
│   ├── core/
│   │   ├── logging.py
│   │   ├── errors.py                # custom exception classes
│   │   └── config.py
│   └── main.py                      # app entrypoint
├── tests/
│   ├── unit/
│   ├── integration/
│   └── api/
├── docs/
│   ├── technical-design.md          # this document
│   └── api-examples.md
├── requirements.txt
└── README.md
```

Each folder maps directly to a service in the architecture diagram, and to a GitHub feature branch (Mission 2): `feature/agent1-input-validation`, `feature/agent1-normalization`, `feature/agent1-database-model`, `feature/agent1-enrichment-service`, `feature/agent1-api-endpoints`, `feature/agent1-tests`.

---

## 4. Input Format

```json
{
  "companies": [
    {
      "companyName": "Example Company",
      "websiteUrl": "https://www.example.com",
      "linkedinUrl": "https://www.linkedin.com/company/example"
    }
  ]
}
```

- `companies` must be a non-empty list.
- `companyName` is required.
- `websiteUrl` is required, must be a valid URL/domain.
- `linkedinUrl` is optional, but if present must match a LinkedIn company profile pattern.

---

## 5. Output Format

**Batch start response:**
```json
{
  "batchId": "batch_9f8a3e",
  "status": "Running",
  "totalReceived": 20,
  "validCompanies": 15,
  "invalidCompanies": 3,
  "duplicates": 2
}
```

**Company enrichment result:**
```json
{
  "companyId": "company_123",
  "batchId": "batch_9f8a3e",
  "companyName": "Example Company",
  "description": "A short factual company summary based on available information.",
  "industry": "SaaS",
  "productsServices": ["CRM", "Workflow automation"],
  "targetAudience": ["Sales teams", "Small businesses"],
  "businessModel": "Subscription",
  "confidence": "medium",
  "missingFields": ["location", "companySize"],
  "sourcesUsed": ["company_name", "website_url", "linkedin_url", "website_scan"],
  "status": "Completed"
}
```

---

## 6. Core Services and Responsibilities

| Service | Responsibility | Input | Output |
|---|---|---|---|
| API Controller | Route handling, request/response shaping | HTTP request | HTTP response |
| Input Validation | Structural + field validation, duplicate detection | Raw company list | Valid/invalid split + summary |
| URL Normalization | Domain extraction, URL cleanup | Raw website/LinkedIn URL | Normalized URL + domain |
| Batch Processing | Assign batch ID, track per-company status, isolate failures | Valid companies | Batch + company statuses |
| Company Enrichment | AI prompt construction, JSON parsing, hallucination control | Company name/website/domain/LinkedIn | Structured enrichment JSON |
| Agent 3 Integration | Trigger scan, receive scan result, handle failure | companyId + websiteUrl | Scan status + extracted data |
| Merge Service | Combine AI + website evidence, track sources | AI result + scan result | Final company profile |
| Database Service | Persistence for all entities above | Any of the above | Confirmation / retrieval |
| Logging Service | Structured logs at each stage transition | Event + batchId/companyId | Log entry |

---

## 7. Database Schema (summary)

**companies**
| Field | Type |
|---|---|
| id (PK) | string |
| batch_id (FK) | string |
| company_name | string |
| website_url | string |
| domain | string |
| linkedin_url | string \| null |
| description | text |
| industry | string |
| products_services | json |
| target_audience | json |
| business_model | string |
| location | string \| null |
| company_size | string \| null |
| confidence | enum(low, medium, high) |
| status | enum(Pending, Validated, Enriching, Website Scanning, Completed, Failed, Partially Completed) |
| created_at / updated_at | timestamp |

**batches**
| Field | Type |
|---|---|
| id (PK) | string |
| status | enum(Pending, Running, Completed, Completed with Errors, Failed) |
| total_received / valid / invalid / duplicates | int |
| created_at / updated_at | timestamp |

**enrichment_results** — structured AI output per company, linked 1:1 to `companies`, keeps raw AI JSON for auditability.

**errors** — company_id/batch_id, error_type, message, retry_count, created_at.

**sources** — company_id, field_name, source_url, extracted_at (supports Mission 11's separation of confirmed vs. AI-generated data).

---

## 8. Agent 3 Integration Contract

**Request (Agent 1 → Agent 3):**
```json
{
  "companyId": "company_123",
  "websiteUrl": "https://www.example.com"
}
```

**Expected response (Agent 3 → Agent 1):**
```json
{
  "companyId": "company_123",
  "scanStatus": "Completed",
  "extractedData": {
    "productsServices": ["..."],
    "pricingFound": true,
    "sourceUrls": ["https://www.example.com/pricing"]
  }
}
```

If Agent 3 fails or times out, Agent 1 marks the company `Partially Completed` and continues the batch — it does not crash or block other companies.

---

## 9. Error Handling and Edge Cases

| Case | Handling |
|---|---|
| Empty company list | Rejected at API layer, 400 response |
| Missing required field | Company marked invalid, batch continues |
| Duplicate company (name+domain) | Flagged in validation summary, not processed twice |
| Unreachable website | Logged, enrichment continues with `unknown` fields |
| Invalid AI JSON | Retried once, then marked `Failed` with error logged |
| Agent 3 timeout/failure | Company marked `Partially Completed`, batch continues |
| Database save failure | Retried with backoff, logged if still failing |

Retry policy: temporary errors (timeouts, transient API errors) retry up to 3 times with backoff; permanent input errors (malformed data) are not retried.

---

## 10. Testing Support

The service-per-file structure allows each service to be unit tested in isolation (mocked DB/AI/Agent 3 calls), with integration tests covering the full pipeline and API tests covering the three endpoints end-to-end. See `tests/unit`, `tests/integration`, `tests/api`.

---

## 11. Approval

| Role | Name | Approved | Date |
|---|---|---|---|
| Project Manager / Instructor | | ☐ | |
| Team Lead | | ☐ | |
