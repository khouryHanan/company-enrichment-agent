"""
Database models — Mission 8.
See docs/technical-design.md section 7 for the full schema.
"""

from sqlalchemy import Column, String, Integer, JSON, DateTime, ForeignKey, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Batch(Base):
    __tablename__ = "batches"

    id = Column(String, primary_key=True)
    status = Column(String, nullable=False, default="Pending")
    total_received = Column(Integer, default=0)
    valid_companies = Column(Integer, default=0)
    invalid_companies = Column(Integer, default=0)
    duplicates = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Company(Base):
    __tablename__ = "companies"

    id = Column(String, primary_key=True)
    batch_id = Column(String, ForeignKey("batches.id"), nullable=False)
    company_name = Column(String, nullable=False)
    website_url = Column(String, nullable=False)
    domain = Column(String)
    linkedin_url = Column(String, nullable=True)
    description = Column(String)
    industry = Column(String)
    products_services = Column(JSON)
    target_audience = Column(JSON)
    business_model = Column(String)
    location = Column(String, nullable=True)
    company_size = Column(String, nullable=True)
    confidence = Column(String)
    status = Column(String, default="Pending")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class EnrichmentResult(Base):
    __tablename__ = "enrichment_results"

    id = Column(String, primary_key=True)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    raw_ai_output = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())


class ErrorLog(Base):
    __tablename__ = "errors"

    id = Column(String, primary_key=True)
    batch_id = Column(String, nullable=True)
    company_id = Column(String, nullable=True)
    error_type = Column(String)
    message = Column(String)
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())


class Source(Base):
    __tablename__ = "sources"

    id = Column(String, primary_key=True)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    field_name = Column(String)
    source_url = Column(String)
    extracted_at = Column(DateTime, server_default=func.now())
