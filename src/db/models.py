"""
Database models — Mission 8.
See docs/technical-design.md section 7 for the full schema.
"""

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Batch(Base):
    __tablename__ = "batches"

    id = Column(String, primary_key=True)
    status = Column(String, nullable=False, default="Pending")
    total_received = Column(Integer, nullable=False, default=0)
    valid_companies = Column(Integer, nullable=False, default=0)
    invalid_companies = Column(Integer, nullable=False, default=0)
    duplicates = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    companies = relationship(
        "Company",
        back_populates="batch",
        cascade="all, delete-orphan",
    )
    errors = relationship(
        "ErrorLog",
        back_populates="batch",
        cascade="all, delete-orphan",
    )


class Company(Base):
    __tablename__ = "companies"
    __table_args__ = (
        UniqueConstraint(
            "batch_id",
            "domain",
            name="uq_companies_batch_domain",
        ),
    )

    id = Column(String, primary_key=True)
    batch_id = Column(
        String,
        ForeignKey("batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    company_name = Column(String, nullable=False)
    website_url = Column(String, nullable=False)
    domain = Column(String, nullable=True)
    linkedin_url = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    industry = Column(String, nullable=True)
    products_services = Column(JSON, nullable=False, default=list)
    target_audience = Column(JSON, nullable=False, default=list)
    business_model = Column(String, nullable=True)
    location = Column(String, nullable=True)
    company_size = Column(String, nullable=True)
    confidence = Column(String, nullable=True)
    status = Column(String, nullable=False, default="Pending")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    batch = relationship("Batch", back_populates="companies")
    enrichment_result = relationship(
        "EnrichmentResult",
        back_populates="company",
        uselist=False,
        cascade="all, delete-orphan",
    )
    sources = relationship(
        "Source",
        back_populates="company",
        cascade="all, delete-orphan",
    )
    errors = relationship("ErrorLog", back_populates="company")


class EnrichmentResult(Base):
    __tablename__ = "enrichment_results"

    id = Column(String, primary_key=True)
    company_id = Column(
        String,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    raw_ai_output = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    company = relationship("Company", back_populates="enrichment_result")


class ErrorLog(Base):
    __tablename__ = "errors"

    id = Column(String, primary_key=True)
    batch_id = Column(
        String,
        ForeignKey("batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    company_id = Column(
        String,
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    error_type = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    retry_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    batch = relationship("Batch", back_populates="errors")
    company = relationship("Company", back_populates="errors")


class Source(Base):
    __tablename__ = "sources"

    id = Column(String, primary_key=True)
    company_id = Column(
        String,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    field_name = Column(String, nullable=False)
    source_url = Column(String, nullable=False)
    extracted_at = Column(DateTime, nullable=False, server_default=func.now())

    company = relationship("Company", back_populates="sources")
