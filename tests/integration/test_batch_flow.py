"""
Integration tests for the full batch pipeline — Mission 15.
Mocks the AI call and Agent 3 call; uses a real (test) database.
"""


def test_batch_continues_after_one_company_fails():
    # TODO: seed one valid + one company that will raise inside
    # _process_company, assert the batch still completes and the
    # failing company is marked Failed / Partially Completed.
    pass


def test_batch_summary_matches_counts():
    # TODO: assert validCompanies + invalidCompanies + duplicates
    # reconcile against totalReceived.
    pass
