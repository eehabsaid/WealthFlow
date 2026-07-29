"""
WealthFlow QA Data Generator — Realistic Unique Test Data Utility
Generates domain-realistic, strictly unique data entities for E2E human testing.
Never outputs generic placeholders like 'Test', 'AAA', or '123'.
"""

import time
import random

def _uid():
    return str(int(time.time() * 1000))[-6:]

def get_unique_company_data():
    uid = _uid()
    companies = [
        ("Apex Capital Group", "Financial Services"),
        ("Global Logistics Solutions", "Supply Chain"),
        ("Aegis Tech Systems", "Software & IT"),
        ("Vanguard Real Estate Co.", "Real Estate Development"),
        ("Horizon Healthcare Ltd", "Medical & Pharma"),
        ("Crestview Engineering", "Civil Construction"),
    ]
    name, group = random.choice(companies)
    return {
        "name": f"{name} {uid}",
        "display_name": f"{name} {uid}",
        "group_name": f"{group} {uid}",
        "tax_number": f"TX-{random.randint(100000, 999999)}",
        "notes": f"Verified corporate entity registration {uid}",
    }

def get_unique_bank_data():
    uid = _uid()
    banks = ["Commercial International Bank", "HSBC Middle East", "QNB Alahli", "Emirates NBD", "Banque Misr"]
    name = random.choice(banks)
    return {
        "name": f"{name} {uid}",
        "swift_code": f"CIBEG{random.randint(100, 999)}",
        "branch": "Main Financial District Branch",
        "notes": f"Primary corporate banking partnership {uid}",
    }

def get_unique_balance_account_data(bank_id=None):
    uid = _uid()
    account_titles = [
        "Executive Savings Account",
        "Corporate Operating Account",
        "Investment Reserve Fund",
        "Emergency Liquidity Vault",
        "Treasury Deposit Account",
    ]
    title = random.choice(account_titles)
    return {
        "title": f"{title} {uid}",
        "balance_type": random.choice(["bank", "cash", "gold", "other"]),
        "currency": "EGP",
        "current_balance": round(random.uniform(50000.0, 250000.0), 2),
        "account_number": f"EG{random.randint(10, 99)}40001000{random.randint(1000, 9999)}",
        "bank_id": bank_id,
        "notes": f"Active balance tracking account {uid}",
    }

def get_unique_salary_data(company_id):
    uid = _uid()
    year = random.randint(2025, 2026)
    month = random.randint(1, 12)
    return {
        "company_id": company_id,
        "year": year,
        "month": month,
        "basic_salary": round(random.uniform(35000.0, 65000.0), 2),
        "allowances": round(random.uniform(5000.0, 15000.0), 2),
        "deductions": round(random.uniform(1000.0, 3000.0), 2),
        "net_salary": round(random.uniform(39000.0, 77000.0), 2),
        "is_paid": True,
        "payment_date": f"{year}-{month:02d}-25",
        "notes": f"Monthly payroll distribution cycle {uid}",
    }

def get_unique_expense_category_data():
    uid = _uid()
    categories = [
        "Cloud Server Infrastructure",
        "Office Facilities & Utilities",
        "Corporate Travel & Hospitality",
        "Professional Legal & Audit Services",
        "Software Subscriptions & Tools",
    ]
    name = random.choice(categories)
    return {
        "name": f"{name} {uid}",
        "description": f"Operational expense category {uid}",
    }

def get_unique_expense_subcategory_data(category_id):
    uid = _uid()
    subcategories = ["Monthly Lease", "Maintenance Contract", "License Renewal", "Hardware Procurement", "Staff Catering"]
    name = random.choice(subcategories)
    return {
        "category_id": category_id,
        "name": f"{name} {uid}",
        "description": f"Detailed expense breakdown item {uid}",
    }

def get_unique_expense_data(category_id, subcategory_id=None):
    uid = _uid()
    amounts = [1250.0, 3400.5, 7800.0, 15200.0, 450.75]
    return {
        "category_id": category_id,
        "subcategory_id": subcategory_id,
        "amount": random.choice(amounts),
        "date": "2026-07-15",
        "payment_method": "bank_transfer",
        "notes": f"Corporate operating expense disbursement {uid}",
    }

def get_unique_certificate_data(bank_id=None):
    uid = _uid()
    titles = [
        "3-Year High Yield Certificate",
        "2-Year Fixed Return Certificate",
        "5-Year Growth Deposit",
        "Quarterly Payout Bond",
    ]
    title = random.choice(titles)
    return {
        "certificate_name": f"{title} {uid}",
        "certificate_number": f"CERT-{random.randint(100000, 999999)}",
        "bank_id": bank_id,
        "principal_amount": 100000.0,
        "interest_rate": 22.5,
        "payout_frequency": "monthly",
        "start_date": "2026-01-01",
        "duration_months": 36,
        "notes": f"Fixed income bank certificate investment {uid}",
    }

def get_unique_fixed_asset_data():
    uid = _uid()
    asset_types = [
        ("Real Estate Office Suite", "real_estate", 3500000.0),
        ("Corporate Executive SUV", "vehicle", 1800000.0),
        ("24K Gold Investment Bars 100g", "gold", 420000.0),
        ("Ergonomic Conference Room Furniture", "furniture", 250000.0),
    ]
    name, asset_type, purchase_price = random.choice(asset_types)
    return {
        "name": f"{name} {uid}",
        "asset_type": asset_type,
        "purchase_price": purchase_price,
        "current_market_value": purchase_price * 1.1,
        "purchase_date": "2025-06-15",
        "location": "New Cairo District 5",
        "notes": f"Capital asset investment portfolio record {uid}",
    }

def get_unique_reminder_rule_data():
    uid = _uid()
    titles = [
        "Quarterly Tax Return Filing Deadline",
        "Annual Vehicle Insurance Renewal",
        "Certificate Interest Maturity Check",
        "Office Lease Payment Notice",
    ]
    title = random.choice(titles)
    return {
        "title": f"{title} {uid}",
        "trigger_type": "monthly",
        "day_of_month": 15,
        "advance_days": 3,
        "is_active": True,
        "notes": f"Automated calendar reminder notification rule {uid}",
    }

def get_unique_goal_data():
    uid = _uid()
    goals = [
        ("Real Estate Expansion Fund", 5000000.0, 1200000.0),
        ("Emergency Liquidity Reserve", 1000000.0, 650000.0),
        ("Children Higher Education Fund", 2500000.0, 900000.0),
        ("Portfolio Diversification Reserve", 3000000.0, 1500000.0),
    ]
    title, target_amount, current_amount = random.choice(goals)
    return {
        "title": f"{title} {uid}",
        "target_amount": target_amount,
        "current_amount": current_amount,
        "target_date": "2028-12-31",
        "notes": f"Strategic long-term wealth goal {uid}",
    }
