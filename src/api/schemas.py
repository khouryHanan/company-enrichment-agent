"""
Pydantic request/response models for Agent 1's API.
See docs/technical-design.md sections 4 and 5 for the full input/output spec.
"""

from typing import Optional
from pydantic import BaseModel, Field


class CompanyInput(BaseModel):
    companyName: str = Field(..., min_length=1)
    websiteUrl: str
    linkedinUrl: Optional[str] = None


class BulkEnrichmentRequest(BaseModel):
    companies: list[CompanyInput]


class BulkEnrichmentResponse(BaseModel):
    batchId: str
    status: str
    totalReceived: int
    validCompanies: int
    invalidCompanies: int
    duplicates: int


class CompanyEnrichmentResult(BaseModel):
    companyId: str
    batchId: str
    companyName: str
    description: str
    industry: str
    productsServices: list[str]
    targetAudience: list[str]
    businessModel: str
    confidence: str
    missingFields: list[str]
    sourcesUsed: list[str]
    status: str
