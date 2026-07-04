# API Examples

## POST /api/agents/agent1/bulk-enrichment

Request:
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

Response:
```json
{
  "batchId": "batch_9f8a3e",
  "status": "Running",
  "totalReceived": 1,
  "validCompanies": 1,
  "invalidCompanies": 0,
  "duplicates": 0
}
```

## GET /api/agents/agent1/bulk-enrichment/{batchId}

Returns the batch record including current status and per-company summary.

## GET /api/companies/{companyId}

Returns a single `CompanyEnrichmentResult` (see src/api/schemas.py).
