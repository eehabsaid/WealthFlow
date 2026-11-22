"""Shared cases for the query engine chat tests."""


from unittest.mock import patch


from ai.integrations.ai_provider import OllamaProvider




NO_LLM = patch.object(OllamaProvider, "generate", side_effect=AssertionError("LLM must not be called"))

# question -> substrings that must be in the answer. Every one runs with the LLM forbidden.
CASES = [
    ("what is the gold price today for 24k?", ["5,000.00 EGP", "4,950.00 EGP"]),
    ("gold 21k buy price", ["21K", "buy", "4,300.00 EGP"]),
    ("gold prices by karat", ["| 24K | 5,000.00 | 4,950.00 |", "| 18K |"]),
    ("سعر جرام الذهب عيار 21", ["عيار 21", "4,375.00 EGP"]),
    ("what is the USD exchange rate", ["1 USD = 50.2500 EGP", "buy 50.0000", "sell 50.5000"]),
    ("سعر الدولار اليوم", ["1 USD = 50.2500 EGP"]),
    ("total expenses for Sept 2026", ["1,000.00 EGP across 1 transactions"]),
    ("total expenses from Jun to Sept 2026", ["**Grand Total**", "1,170.50 EGP"]),
    ("expenses by category for Jun 2026", ["Food", "150.50 EGP", "100.0%"]),
    ("مصروفات شهر يونيو 2026", ["150.50 EGP"]),
    ("my last expense", ["Rent", "1,000.00 EGP"]),
    ("What was my paid salary for January 2026?", ["87,643.86 EGP"]),
    ("ما هو راتبي في يناير 2026", ["87,643.86 EGP", "الراتب المدفوع"]),
    ("last salary", ["Latest paid salary", "87,643.86"]),
    ("how much money do I have", ["Total balance: 1,000.00 EGP"]),
    ("كم رصيدي", ["إجمالي الرصيد: 1,000.00 EGP"]),
    ("balances per currency", ["| EGP |", "**Grand Total**"]),
    ("my certificates", ["1 active certificate(s)", "100,000.00 EGP"]),
    ("next certificate interest date", ["Next interest posting"]),
    ("what are my fixed assets", ["5,000,000.00 EGP", "1 asset(s)"]),
    ("assets by type", ["Real Estate", "100.0%"]),
]
