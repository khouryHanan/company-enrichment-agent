"""
Merge Service — Mission 11.

Combines the AI enrichment result with Agent 3's website scan result.
Keeps confirmed (website-sourced) data clearly separated from
AI-generated analysis, and records source URLs for each extracted insight.
"""


def merge_results(enrichment: dict, scan_result: dict) -> dict:
    """
    Returns the final company profile: AI fields overwritten by confirmed
    website evidence where available, with sourcesUsed extended to include
    the scan's source URLs. Missing information stays marked as missing —
    never silently filled in.
    """
    raise NotImplementedError
