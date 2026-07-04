"""
Unit tests for the input validation service — Mission 15.
"""

import pytest

from src.services import validation_service


def test_rejects_empty_company_list():
    with pytest.raises(NotImplementedError):
        validation_service.validate_companies([])


def test_detects_missing_company_name():
    # TODO: once validate_companies is implemented, assert the record
    # with a blank companyName lands in invalid_companies.
    pass


def test_detects_duplicate_by_domain_and_name():
    # TODO: two records with the same domain + company name should
    # both be reported in duplicates.
    pass
