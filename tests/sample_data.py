"""
Sample input data for testing bulk company enrichment — Mission 4.
"""

VALID_REQUEST = {
    "companies": [
        {
            "companyName": "Example Company",
            "websiteUrl": "https://www.example.com",
            "linkedinUrl": "https://www.linkedin.com/company/example",
        },
        {
            "companyName": "Another Company",
            "websiteUrl": "https://www.another.com",
            # linkedinUrl intentionally omitted — it's optional
        },
    ]
}

EMPTY_LIST_REQUEST = {"companies": []}

MISSING_COMPANY_NAME_REQUEST = {
    "companies": [
        {"websiteUrl": "https://www.example.com"}
    ]
}

MISSING_WEBSITE_URL_REQUEST = {
    "companies": [
        {"companyName": "Example Company"}
    ]
}

BLANK_COMPANY_NAME_REQUEST = {
    "companies": [
        {"companyName": "   ", "websiteUrl": "https://www.example.com"}
    ]
}

NOT_A_LIST_REQUEST = {"companies": "not-a-list"}

MISSING_COMPANIES_KEY_REQUEST = {}
