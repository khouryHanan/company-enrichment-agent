"""
API schemas — Mission 4 / SCRUM-4.

Defines the expected input structure for bulk company enrichment and
validates it structurally (list type, required fields, non-empty) before
anything reaches the business-logic validation in validation_service.py
(SCRUM-5, which handles URL format / duplicate checks).
"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator


class CompanyInput(BaseModel):
    companyName: str = Field(..., min_length=1, description="Required. Cannot be empty.")
    websiteUrl: str = Field(..., min_length=1, description="Required. Company website URL.")
    linkedinUrl: Optional[str] = Field(default=None, description="Optional. LinkedIn company profile URL.")

    @field_validator("companyName")
    @classmethod
    def company_name_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("companyName cannot be blank or whitespace-only")
        return value

    @field_validator("websiteUrl")
    @classmethod
    def website_url_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("websiteUrl cannot be blank or whitespace-only")
        return value


class BulkEnrichmentRequest(BaseModel):
    companies: list[CompanyInput]

    @field_validator("companies")
    @classmethod
    def companies_not_empty(cls, value: list) -> list:
        if not value:
            raise ValueError("companies list cannot be empty")
        return value


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
    # Optional with defaults so rows saved before these fields existed
    # still serialize cleanly.
    location: Optional[str] = None
    companySize: Optional[str] = None
    foundedYear: Optional[str] = None
    headquarters: Optional[str] = None
    keyCompetitors: list[str] = Field(default_factory=list)
    techStack: list[str] = Field(default_factory=list)
    keyContacts: list[str] = Field(default_factory=list)
    confidence: str
    missingFields: list[str]
    sourcesUsed: list[str]
    status: str
