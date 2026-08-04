# API Documentation — Agent 1

Base path assumed: `http://localhost:8000` (local dev, per `uvicorn src.main:app --reload`)

---

## 1. Start Bulk Enrichment

**`POST /api/agents/agent1/bulk-enrichment`**

Accepts a list of companies, kicks off validation → normalization → AI
enrichment → Agent 3 scan → merge → persistence, and returns a batch
summary once processing completes.

### Request body

```json
{
  "companies": [
    {
      "companyName": "Example Company",
      "websiteUrl": "https://www.example.com",
      "linkedinUrl": "https://www.linkedin.com/company/example"
    },
    {
      "companyName": "Another Company",
      "websiteUrl": "https://www.another.com"
    }
  ]
}
```

`linkedinUrl` is optional; all other fields are required.

### Success response — `200 OK`

```json
{
  "batchId": "batch_9f8a3e12",
  "status": "Completed",
  "totalReceived": 2,
  "validCompanies": 2,
  "invalidCompanies": 0,
  "duplicates": 0
}
```

### Error response — empty list — `400 Bad Request`

```json
{
  "detail": "Invalid request",
  "errors": [
    {"field": "companies", "message": "Value error, companies list cannot be empty"}
  ]
}
```

### Error response — missing required field — `400 Bad Request`

```json
{
  "detail": "Invalid request",
  "errors": [
    {"field": "companies.0.companyName", "message": "Field required"}
  ]
}
```

---

## 2. Get Batch Status

**`GET /api/agents/agent1/bulk-enrichment/{batchId}`**

Retrieves the current status and summary counts for a previously
submitted batch.

### Success response — `200 OK`

```json
{
  "batchId": "batch_9f8a3e12",
  "status": "Completed",
  "totalReceived": 2,
  "validCompanies": 2,
  "invalidCompanies": 0,
  "duplicates": 0
}
```

Possible `status` values: `Pending`, `Running`, `Completed`,
`Completed with Errors`, `Failed`.

### Error response — batch not found — `404 Not Found`

```json
{
  "detail": "batch not found"
}
```

---

## 3. Get Company Enrichment Result

**`GET /api/companies/{companyId}`**

Retrieves the enriched profile for a single company.

### Success response — `200 OK`

```json
{
  "companyId": "company_1a2b3c4d",
  "batchId": "batch_9f8a3e12",
  "companyName": "Example Company",
  "description": "A short factual company summary based on available information.",
  "industry": "SaaS",
  "productsServices": ["CRM", "Workflow automation"],
  "targetAudience": ["Sales teams", "Small businesses"],
  "businessModel": "Subscription",
  "location": "United States",
  "companySize": "1000-5000",
  "foundedYear": "2008",
  "headquarters": "San Francisco, California, United States",
  "keyCompetitors": ["GitLab", "Bitbucket"],
  "techStack": ["Git", "Ruby on Rails", "Go"],
  "keyContacts": ["Thomas Dohmke — CEO"],
  "confidence": "medium",
  "missingFields": ["location", "companySize"],
  "sourcesUsed": ["company_name", "website_url", "website_scan"],
  "status": "Completed"
}
```

Possible `status` values: `Pending`, `Validated`, `Enriching`,
`Website Scanning`, `Completed`, `Failed`, `Partially Completed`.

Possible `confidence` values: `low`, `medium`, `high`.

### Error response — company not found — `404 Not Found`

```json
{
  "detail": "company not found"
}
```

---

## Trying it locally with curl

```bash
# Start a batch
curl -X POST http://localhost:8000/api/agents/agent1/bulk-enrichment \
  -H "Content-Type: application/json" \
  -d '{"companies": [{"companyName": "Example Company", "websiteUrl": "https://www.example.com"}]}'

# Check batch status (replace with the real batchId returned above)
curl http://localhost:8000/api/agents/agent1/bulk-enrichment/batch_9f8a3e12

# Get a company's result (replace with a real companyId)
curl http://localhost:8000/api/companies/company_1a2b3c4d
```