"""The 16 categories, which table belongs to which category, and what the app supports (printed in the README and the model-test report).

Table -> category is the only fixed list here; every question, figure and label comes from the live app and its data."""

from __future__ import annotations

CATEGORIES = (
    ("overview", "1 Financial overview and net worth"), ("banking", "2 Banking and account management"),
    ("income", "3 Income and recurring income"), ("expenses", "4 Expenses, categories and subcategories"),
    ("fixed_assets", "5 Fixed assets, acquisition costs and renovations"), ("liabilities", "6 Liabilities, debts and installments"),
    ("cash_flow", "7 Historical and projected cash flow"), ("balance", "8 Balance management"),
    ("trends", "9 Trends, comparisons and ratios"), ("budgets", "10 Budgets, savings and goals"),
    ("what_if", "11 What-if scenarios"), ("cross", "12 Cross-module analysis"),
    ("explain", "13 Explaining calculations and records"), ("quality", "14 Data quality and anomalies"),
    ("language", "15 Arabic, French and German questions"), ("ambiguous", "16 Ambiguous questions needing clarification"),
)
TITLES = dict(CATEGORIES)

TABLE_CATEGORY = {
    "Bank": "banking", "BankInterest": "banking", "BankCertificate": "banking", "BankCertificateInterestHistory": "banking",
    "CardRenewalFee": "banking", "BalanceEntry": "balance", "BalanceTransfer": "balance", "CurrencyExchange": "balance",
    "SalaryEntry": "income", "PerDiem": "income", "Company": "income", "RentReceipt": "income", "AssetRental": "income",
    "Expense": "expenses", "ExpenseCategory": "expenses", "ExpenseSubcategory": "expenses",
    "FixedAsset": "fixed_assets", "AssetAcquisitionCost": "fixed_assets", "AssetRenovation": "fixed_assets", "AssetFurniture": "fixed_assets",
    "AssetMaintenance": "fixed_assets", "AssetInsurance": "fixed_assets", "AssetValuationHistory": "fixed_assets",
    "AssetPurchasePayment": "fixed_assets", "AssetSale": "fixed_assets", "GoldDetails": "fixed_assets", "VehicleDetails": "fixed_assets",
    "RealEstateDetails": "fixed_assets", "OtherAssetDetails": "fixed_assets",
    "AssetMortgage": "liabilities", "CreditCardPayment": "liabilities",
    "Budget": "budgets", "Goal": "budgets", "RecurringTransaction": "budgets",
    "Scenario": "what_if", "ScenarioEvent": "what_if",
}
REFERENCE = "reference"   # market prices, plans, reminders, settings tables: still asked (as before) but outside the 16 categories


def category_of(model_name: str) -> str:
    return TABLE_CATEGORY.get(model_name, REFERENCE)


# What the app can do for each category (the honest Step-1 answer, kept next to the code that depends on it).
SUPPORT = {
    "income": "salary, per diem and rent only: the app has no other income table",
    "liabilities": "mortgages and credit-card payments only: the app has no general debts / loans / installments module",
    "balance": "balance entries, transfers and exchanges: the app has no reconciliation function, so none is asked",
    "what_if": "numeric what-ifs only (code can prove the figure, not the reasoning)",
    "explain": "figures and the records behind them are proven; the quality of the explanation is not",
    "quality": "counts of real issues found by code (no category, duplicates, zero amounts); the app has no anomaly screen",
    "ambiguous": "only 'asked a question and gave no figures' is proven; whether the question was a good one is not",
    "language": "Arabic is told apart by its script; French/German/English by the app's own translation files (a word-evidence check)",
}
