"""
Tests for the EYEjee export adapter — SCRUM-18 demo integration.

Built against a real platform export (scripts/eyejee_export_example.json),
which is where the bare-LinkedIn-URL problem surfaced.
"""

import json
from pathlib import Path

from src.services import import_service
from src.services.validation_service import is_valid_linkedin_url, is_valid_website_url

EXPORT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "eyejee_export_example.json"

EXPORT_ROW = {
    "data_companies": "LinkTrust",
    "website": "https://linktrust.com",
    "Keyword": "Marketing",
    "Loc": "united states",
    "Size": "11-50",
    "Linkedin_url": "linkedin.com/company/linktrust-systems-inc-",
}


def test_maps_export_field_names_to_our_contract():
    [company] = import_service.from_eyejee_export([EXPORT_ROW])

    assert company["companyName"] == "LinkTrust"
    assert company["websiteUrl"] == "https://linktrust.com"


def test_bare_linkedin_url_gets_a_scheme():
    # The export ships LinkedIn URLs without a scheme, which validation
    # rejects outright — every real row would be marked invalid without
    # this. Regression guard for the whole integration.
    [company] = import_service.from_eyejee_export([EXPORT_ROW])

    assert company["linkedinUrl"] == "https://linkedin.com/company/linktrust-systems-inc-"
    assert is_valid_linkedin_url(company["linkedinUrl"])


def test_bare_website_url_gets_a_scheme():
    [company] = import_service.from_eyejee_export(
        [dict(EXPORT_ROW, website="linktrust.com")]
    )

    assert company["websiteUrl"] == "https://linktrust.com"
    assert is_valid_website_url(company["websiteUrl"])


def test_existing_scheme_is_left_alone():
    [company] = import_service.from_eyejee_export(
        [dict(EXPORT_ROW, website="http://linktrust.com")]
    )

    assert company["websiteUrl"] == "http://linktrust.com"


def test_missing_linkedin_is_omitted_not_blank():
    [company] = import_service.from_eyejee_export([dict(EXPORT_ROW, Linkedin_url="")])

    assert "linkedinUrl" not in company


def test_rows_without_name_or_website_are_skipped():
    rows = [
        EXPORT_ROW,
        dict(EXPORT_ROW, data_companies=""),
        dict(EXPORT_ROW, website=None),
        "not-a-dict",
    ]

    assert len(import_service.from_eyejee_export(rows)) == 1


def test_empty_export_maps_to_nothing():
    assert import_service.from_eyejee_export([]) == []


def test_real_export_file_maps_to_valid_input():
    rows = json.loads(EXPORT_PATH.read_text())

    companies = import_service.from_eyejee_export(rows)

    assert len(companies) == len(rows) == 5
    assert [c["companyName"] for c in companies][:2] == ["LinkTrust", "Onimod Global"]
    # Every mapped company must survive the validation the batch applies.
    for company in companies:
        assert is_valid_website_url(company["websiteUrl"])
        assert is_valid_linkedin_url(company["linkedinUrl"])


def test_export_location_and_size_are_carried_through_as_known_facts():
    [company] = import_service.from_eyejee_export([EXPORT_ROW])

    assert company["location"] == "united states"
    assert company["companySize"] == "11-50"


def test_blank_export_location_and_size_are_omitted():
    [company] = import_service.from_eyejee_export([dict(EXPORT_ROW, Loc="", Size="   ")])

    assert "location" not in company
    assert "companySize" not in company
