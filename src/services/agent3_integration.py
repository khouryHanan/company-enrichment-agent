"""
Agent 3 Integration Service — Mission 10.

Triggers Agent 3 to scan a company's website and receives the scan result.
Agent 3 failures must be handled safely and must not crash Agent 1.
"""


def trigger_scan(company_id: str, website_url: str) -> dict:
    """
    Sends {"companyId": ..., "websiteUrl": ...} to Agent 3.

    Returns:
      {"companyId": ..., "scanStatus": "Completed" | "Failed", "extractedData": {...}}

    On failure or timeout, return scanStatus="Failed" rather than raising,
    so the caller can mark the company Partially Completed and continue.
    """
    raise NotImplementedError
