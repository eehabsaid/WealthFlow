#!/usr/bin/env python3
"""
WealthFlow User Guide Generator
===============================
Builds a single shared content model (list of section dicts) and renders it
into BOTH:
  - docs/user_guide.html  (self-contained, offline, responsive, dark-mode)
  - docs/user_guide.docx  (Word document via python-docx)

The TOC / Contents page in BOTH formats is generated from the same section
list — there is no separate hand-typed TOC.

Usage:
    python scripts/generate_user_guide.py
"""

import html
import os
import re
from datetime import date

# ─────────────────────────────────────────────────────────────────────────────
# SHARED CONTENT MODEL  (single source of truth)
# ─────────────────────────────────────────────────────────────────────────────
# Each section:
#   number        – hierarchical number string, e.g. "1", "1.1"
#   title         – heading text
#   level         – 1, 2, or 3  (1 = top-level, 2 = sub, 3 = sub-sub)
#   purpose       – one-paragraph description
#   steps         – optional list of action steps
#   notes         – optional list of notes / tips
#   sysadmin_only – bool; True → "⚠️ Sysadmin only" badge in both formats
# ─────────────────────────────────────────────────────────────────────────────

def _sec(number, title, level, purpose, steps=None, notes=None, sysadmin_only=False):
    return {
        "number": number,
        "title": title,
        "level": level,
        "purpose": purpose,
        "steps": steps or [],
        "notes": notes or [],
        "sysadmin_only": sysadmin_only,
    }


SECTIONS = [
    # ── FRONT MATTER ──────────────────────────────────────────────────────────
    _sec(
        "1", "Introduction", 1,
        "WealthFlow is a single-tenant personal-finance platform built with Django and vanilla JavaScript. "
        "It tracks multi-currency liquid cash, bank balances, high-yield bank certificates, physical gold, "
        "real estate, vehicles, salary income, and expenses. The UI uses Bootstrap 5 with dark/light themes "
        "and supports Arabic, English, French, and German via JSON-based i18n. This guide walks through every "
        "page, feature, and setting in the order you will encounter them.",
        steps=[
            "Read this guide top-to-bottom for a first pass, or jump to a section via the Table of Contents.",
            "Keep the Roles & Permissions Reference (section 40) handy to understand what your role can access.",
            "Use the Glossary (section 41) whenever a term is unfamiliar.",
        ],
        notes=[
            "All data is stored locally in a SQLite database; no data leaves your machine unless you configure an external AI provider.",
            "The application is fully offline-capable once loaded (PWA service worker).",
        ],
    ),
    _sec(
        "2", "Getting Started", 1,
        "Covers account creation, email verification, first login, the default Member role, and initial "
        "configuration of base currency and language.",
        steps=[
            "Open the application URL in your browser and click the Sign Up button.",
            "Enter your name, email address, and a password (minimum 8 characters, at least one digit).",
            "Check your email inbox for a verification link and click it to activate your account.",
            "Log in with your verified email and password.",
            "On first login you are assigned the Member role, which grants access to all main-app pages and a curated set of Settings tabs.",
            "Go to Settings → Languages to choose your preferred display language (Arabic, English, French, or German).",
            "Go to Settings → Currency to set your base currency (the currency all amounts are normalised to for reporting).",
        ],
        notes=[
            "The Member role is the default for all self-registered users. A sysadmin can later promote you to a custom role with additional permissions.",
            "Your base currency affects how multi-currency balances are aggregated in reports and the dashboard.",
            "Email verification is mandatory; unverified accounts cannot log in.",
        ],
    ),
    _sec(
        "3", "Navigation & Interface", 1,
        "Explains the persistent UI chrome: the left sidebar, the top bar, mobile navigation, the date picker, "
        "modals, toast notifications, and right-to-left (RTL) / Arabic layout support.",
        steps=[
            "Use the left sidebar to navigate between main-app pages (Dashboard, WealthFlow AI, Financial Advisor, etc.).",
            "The top bar shows the current page title, a language switcher, a theme toggle (light/dark), and your user avatar with an account menu.",
            "On screens narrower than 768 px the sidebar collapses into a hamburger menu; tap the icon to open it.",
            "Click any date input to open the custom date picker; it supports month/year navigation and locale-aware labels.",
            "Modals (dialog boxes) appear over the page for add/edit forms; press Escape or click the backdrop to close.",
            "Toast notifications slide in from the top-right to confirm actions (saved, deleted, error).",
            "When Arabic is selected the entire layout mirrors to right-to-left automatically.",
        ],
        notes=[
            "The theme preference is stored per-user and persists across sessions.",
            "All UI strings are translated via data-i18n attributes; the active language is applied on every render.",
            "Keyboard navigation: Tab moves focus through interactive elements; Enter activates buttons and links.",
        ],
    ),

    # ── MAIN APP PAGES ────────────────────────────────────────────────────────
    _sec(
        "4", "Dashboard", 1,
        "The landing page after login. Shows a high-level snapshot of your financial position: net worth, "
        "recent transactions, upcoming reminders, certificate maturities, and salary status. "
        "Which widgets appear is controlled by Settings → Dashboard.",
        steps=[
            "Log in; the Dashboard loads automatically.",
            "Review the net-worth card (total assets minus liabilities, in your base currency).",
            "Check the reminders banner for any upcoming certificate maturities, insurance expiries, or salary-day alerts.",
            "Click any card to drill into the corresponding page (Balance, Bank Certificates, Employment, etc.).",
        ],
        notes=[
            "Toggle which widgets are visible in Settings → Dashboard (show certificates, show reminders, show salary).",
            "The dashboard refreshes data on every page load; there is no auto-polling.",
        ],
    ),
    _sec(
        "5", "WealthFlow AI", 1,
        "An AI-powered chat assistant that answers questions about your financial data using a read-only "
        "pipeline. It can query balances, salary, certificates, gold, expenses, and fixed assets. "
        "Supports streaming responses, a context panel, a prompt library, a knowledge base, and conversation history.",
        steps=[
            "Click WealthFlow AI in the sidebar.",
            "Type a question in the chat input (e.g. 'What is my total net worth?') and press Enter.",
            "Watch the streaming progress indicator while the AI orchestrator runs its investigation loop (up to 5 tool-calling steps).",
            "Open the right-hand context panel to view the knowledge base, prompt library, and capability cards.",
            "Browse or create prompts in the Prompt Library modal for reusable question templates.",
            "View past conversations in the history list; click one to resume it.",
        ],
        notes=[
            "The AI is strictly read-only: it never modifies your data.",
            "Supported providers: Ollama (local), OpenAI, Claude, Gemini, Azure OpenAI. The active provider is set in Settings → AI Advisor (sysadmin) or My AI Settings (per-user).",
            "Instant Data Answers (direct answers) bypass the LLM for simple data lookups, saving tokens.",
            "Multi-agent orchestration lets specialised agents collaborate on complex questions.",
        ],
    ),
    _sec(
        "6", "Financial Advisor", 1,
        "A rule-based (non-AI) analytics engine that provides portfolio overview, cash-flow forecasting, "
        "goal planning, risk analysis, spending intelligence, opportunity detection, scenario planning, "
        "and wealth-growth projections. All calculations run server-side in Python.",
        steps=[
            "Click Financial Advisor in the sidebar.",
            "Use the tab bar to switch between: Overview, Cash Flow, Goal Planning, Risk Analysis, Spending Intelligence, Opportunities, Scenario Planner, and Projections.",
            "In Goal Planning, set a target amount and time horizon; the service calculates the required monthly savings.",
            "In the Scenario Planner, add hypothetical events (e.g. a bonus, a purchase) and compare the projected outcome against your baseline.",
            "Review the Projections tab for long-term wealth-growth forecasts based on your current income, expenses, and asset growth rates.",
        ],
        notes=[
            "All advisor services are deterministic and do not require an AI provider.",
            "Cash-flow forecasts use your salary and recurring expense data.",
            "Opportunity detection surfaces under-utilised certificates, low-yield balances, and tax-advantaged moves.",
        ],
    ),
    _sec(
        "7", "Employment / Salary", 1,
        "Manage your employers, record monthly salary entries, track per-diem (daily allowance) payments, "
        "and view payroll history. Year pills let you jump between calendar years.",
        steps=[
            "Click Employment in the sidebar.",
            "Select or create a company (employer) from the dropdown.",
            "Add a salary entry: month, base amount, bonuses, deductions, and net pay.",
            "Record per-diem payments: date, amount, and reason.",
            "Use the year pills at the top of the page to switch between years.",
            "View the payroll summary table for the selected year.",
        ],
        notes=[
            "Salary data feeds the Financial Advisor's cash-flow and goal-planning services.",
            "Per-diem entries are treated as supplementary income in reports.",
            "You can have multiple employers; each has its own salary history.",
        ],
    ),
    _sec(
        "8", "Balance", 1,
        "Track liquid cash and bank-account balances across multiple currencies. Supports account management, "
        "inter-account transfers, currency exchange, credit-card payments, bank interest accrual, and card renewal fees.",
        steps=[
            "Click Balance in the sidebar.",
            "Use the tab bar: Overview, Accounts, Transfers, Currency Exchange, Bank Interest, Credit Card Payment, Card Renewal Fee, Allocation, Forecasts, Recommendations.",
            "In Accounts, add a new bank or cash account with a name, bank, currency, and opening balance.",
            "In Transfers, move money between your own accounts (source, destination, amount, date).",
            "In Currency Exchange, record a conversion between two of your currencies at a given rate.",
            "In Bank Interest, log interest credited to a certificate or savings account.",
            "In Credit Card Payment, record a payment toward a credit-card balance.",
            "In Card Renewal Fee, log annual card-fee charges.",
        ],
        notes=[
            "All amounts are stored in their original currency and normalised to your base currency for aggregation.",
            "Transfers do not change total net worth; they move value between accounts.",
            "Currency-exchange entries affect the per-currency balances but not total net worth (at the recorded rate).",
        ],
    ),
    _sec(
        "9", "Bank Certificates", 1,
        "Track high-yield bank certificates (fixed deposits): issue date, expiry date, principal amount, "
        "interest rate, interest value, and payout frequency (monthly, quarterly, semi-annually, annually, or at maturity).",
        steps=[
            "Click Bank Certificates in the sidebar.",
            "Click Add Certificate to open the modal.",
            "Fill in: status, bank, currency, issue date, expiry date, amount, interest rate (%), interest value, and frequency.",
            "Save; the certificate appears in the list with a countdown to maturity.",
            "Click a certificate to edit or view its interest history.",
        ],
        notes=[
            "Certificate maturity reminders are generated automatically based on the expiry date and your reminder rules (Settings → Reminders).",
            "Interest can be accrued monthly or paid at maturity, depending on the frequency you select.",
            "Certificates are included in net-worth calculations at their face value plus accrued interest.",
        ],
    ),
    _sec(
        "10", "Fixed Assets", 1,
        "Track non-liquid assets: real estate, vehicles, gold holdings, and other assets. Supports photos, "
        "valuation history, acquisition costs, insurance, maintenance, renovations, furniture, rental income, "
        "and sale records.",
        steps=[
            "Click Fixed Assets in the sidebar.",
            "Select an asset type: Real Estate, Vehicles, Gold, or Other Assets.",
            "Click Add Asset and fill in the type-specific fields (address / VIN / weight / description).",
            "Upload photos to document the asset's condition.",
            "Record the acquisition cost, including optional cost categories (lawyer fees, registration, notary, etc.).",
            "Add valuation entries over time to track appreciation or depreciation.",
            "For real estate: add renovation records, furniture inventory, insurance policies, and rental receipts.",
            "For vehicles: add maintenance logs and insurance details.",
            "For gold: the system auto-syncs the current market value using the Gold Price page rates.",
        ],
        notes=[
            "Gold asset values are recalculated automatically when gold prices are refreshed.",
            "Property valuations can be sourced from a configured market-rate provider or an external API (Settings → Property Valuation).",
            "Sold assets are marked with status 'Sold' and excluded from current net worth but retained in history.",
        ],
    ),
    _sec(
        "11", "Exchange Rates", 1,
        "View and refresh foreign-exchange rates. Rates are fetched from open.er-api.com (free, no API key) "
        "and stored in the local database. A Central Bank of Egypt (CBE) scrape can also run locally.",
        steps=[
            "Click Exchange Rates in the sidebar.",
            "Review the featured currency cards (top currencies by priority).",
            "Scroll to the full rate table for all configured currencies.",
            "Click Refresh from Internet to fetch the latest rates from the external API.",
        ],
        notes=[
            "Rates are used by the Balance page for currency-exchange calculations and by reports for multi-currency aggregation.",
            "The refresh button requires an internet connection; the app remains fully functional offline using the last stored rates.",
        ],
    ),
    _sec(
        "12", "Gold Price", 1,
        "Display current gold prices by purity (24K, 22K, 21K, 18K) and by unit (gram, kilogram, ounce, tola). "
        "Prices are fetched from an external API and cached locally.",
        steps=[
            "Click Gold Price in the sidebar.",
            "View the carat cards showing the price per gram for each purity.",
            "Switch units using the unit selector (g, kg, oz, tola).",
            "Click Refresh to fetch the latest prices from the external API.",
        ],
        notes=[
            "Gold asset values in Fixed Assets are auto-updated when prices are refreshed.",
            "Purity percentages: 24K = 99.9 %, 22K = 91.7 %, 21K = 87.5 %, 18K = 75.0 %.",
            "Unit conversions: 1 kg = 1000 g, 1 oz = 31.103 g, 1 tola = 11.664 g.",
        ],
    ),
    _sec(
        "13", "Expenses", 1,
        "Record and categorise daily expenses. Each expense has a date, amount, currency, category, "
        "payment method, and optional description. Expenses feed budgets, reports, and the AI assistant.",
        steps=[
            "Click Expenses in the sidebar.",
            "Click Add Expense and fill in: date, amount, currency, category, payment method, and description.",
            "Filter the list by date range, category, or currency.",
            "Edit or delete existing expenses by clicking the row actions.",
        ],
        notes=[
            "Expenses are the primary input for budget tracking and the Financial Advisor's spending intelligence.",
            "Payment methods: Cash, Card, Bank, Bank Transfer.",
            "Expenses can be imported in bulk via the Import Data page.",
        ],
    ),
    _sec(
        "14", "Expense Categories", 1,
        "Define the categories used to classify expenses. Each category has a name, an icon (emoji), "
        "and is scoped to your user account.",
        steps=[
            "Click Expense Categories in the sidebar.",
            "Click Add Category and enter a name and choose an icon.",
            "Edit or delete categories as needed.",
            "Categories are available as dropdown options in the Expense and Budget forms.",
        ],
        notes=[
            "Default categories are seeded on first login (Food, Transport, Utilities, Rent, Entertainment, Health, Shopping, Other).",
            "Deleting a category does not delete existing expenses; they retain a reference to the deleted category name.",
        ],
    ),
    _sec(
        "15", "Budgets", 1,
        "Set monthly or yearly spending limits per category. Budgets show a progress bar (spent vs limit), "
        "an alert threshold, and support recurring transactions with auto-posting and due-date alerts.",
        steps=[
            "Click Budgets in the sidebar.",
            "Click Add Budget: choose a category, period (monthly / yearly), amount, and alert threshold (%).",
            "The progress bar turns green → yellow (at threshold) → red (exceeded).",
            "In the Recurring section, add recurring transactions (e.g. monthly rent) with a frequency and next-run date.",
            "Pause or resume a recurring transaction with the toggle button.",
            "Enable auto-posting on login (Settings → Budgets) to automatically record due recurring transactions.",
        ],
        notes=[
            "Budget alerts appear in the dashboard banner and the Budgets page alert list.",
            "Alert types: budget_exceeded, budget_threshold, recurring_due_soon, recurring_overdue.",
            "Recurring auto-posting is off by default; enable it in your per-user settings.",
        ],
    ),
    _sec(
        "16", "Import Data", 1,
        "Bulk-import expenses from a CSV or Excel file. The import wizard lets you map columns "
        "(date, amount, description, category), choose a default currency and category, and preview "
        "sample rows before committing.",
        steps=[
            "Click Import Data in the sidebar.",
            "Upload a CSV or Excel file.",
            "Map the file's columns to WealthFlow fields: Date, Amount, Description, Category (optional).",
            "Select the default currency and category for rows that lack explicit values.",
            "Review the preview table (first 10 rows).",
            "Click Import to commit all rows.",
        ],
        notes=[
            "Duplicate detection flags rows that match an existing expense (same date + amount + description).",
            "The import is atomic: either all rows are inserted or none are, on validation failure.",
        ],
    ),
    _sec(
        "17", "Reports", 1,
        "Generate income-vs-expenses analysis reports for a month, a year, or a custom date range. "
        "Reports include charts, category breakdowns, and a PDF export.",
        steps=[
            "Click Reports in the sidebar.",
            "Choose a tab: Monthly, Yearly, or Custom Range.",
            "Select the year (and month, for the Monthly tab) or enter a start/end date (Custom Range).",
            "Review the income vs expenses chart and the category breakdown table.",
            "Click Export PDF to download a formatted report.",
        ],
        notes=[
            "Reports aggregate all expenses and salary income in your base currency.",
            "The PDF export includes the WealthFlow logo, date range, and a summary table.",
        ],
    ),
    _sec(
        "18", "Advanced Reports", 1,
        "Deep-dive analytics across four domains: Salary, Company, Balance, and Certificates. "
        "Each tab provides charts, KPIs, and trend analysis specific to that domain.",
        steps=[
            "Click Advanced Reports in the sidebar.",
            "Select a tab: Salary, Company, Balance, or Certificates.",
            "Review the KPI cards (totals, averages, growth rates).",
            "Interact with the charts (hover for crosshair values, zoom where supported).",
        ],
        notes=[
            "Advanced Reports are read-only; they do not modify any data.",
            "Charts are rendered client-side with a lightweight canvas library (no external CDN required).",
        ],
    ),

    # ── SETTINGS ──────────────────────────────────────────────────────────────
    _sec(
        "19", "Settings Overview", 1,
        "The Settings area contains 20 tabs, each managing a distinct domain. Access to each tab is "
        "controlled by your role's permission keys. Five tabs are sysadmin-only and cannot be granted "
        "to any role: Users, Roles, Billing Plans, AI Advisor, and Legal Text.",
        steps=[
            "Click Settings in the sidebar.",
            "The tab bar shows all tabs your role has access to.",
            "Click a tab to load its content into the main panel.",
            "Tabs you do not have permission for are hidden from the tab bar.",
        ],
        notes=[
            "Sysadmin-only tabs (Users, Roles, Billing Plans, AI Advisor, Legal Text) are visible only to users with the is_sysadmin flag.",
            "The Member role includes: Companies, Banks, Currency, Reminders, Certificate Status, Gold Settings, and My AI Settings.",
            "Per-user settings (e.g. dashboard widget visibility, reminder thresholds) are stored per-user and do not affect other users.",
        ],
    ),
    _sec(
        "20", "Languages", 1,
        "Manage the list of languages available in the application and set the default language for new users. "
        "Supported languages: Arabic (ar), English (en), French (fr), German (de).",
        steps=[
            "Go to Settings → Languages.",
            "Toggle languages on or off in the available-languages list.",
            "Set the default language for newly registered users.",
            "Save; the change takes effect on the next page load.",
        ],
        notes=[
            "Translation files are JSON-based and loaded per-language at runtime.",
            "Disabling a language removes it from the language switcher for all users.",
        ],
    ),
    _sec(
        "21", "Companies", 1,
        "Manage the list of companies (employers) available in the Employment page and the Financial Advisor. "
        "Each company has a name and an optional industry tag.",
        steps=[
            "Go to Settings → Companies.",
            "Click Add Company and enter a name.",
            "Edit or delete companies as needed.",
            "Companies appear in the Employment page employer dropdown.",
        ],
        notes=[
            "Deleting a company does not delete existing salary entries; they retain the company name.",
        ],
    ),
    _sec(
        "22", "Banks", 1,
        "Manage the list of banks available in the Balance, Bank Certificates, and Employment pages. "
        "Each bank has a name and an optional short code.",
        steps=[
            "Go to Settings → Banks.",
            "Click Add Bank and enter a name and optional code.",
            "Edit or delete banks as needed.",
            "Banks appear in the Balance account form and the Bank Certificate modal.",
        ],
        notes=[
            "Deleting a bank does not delete existing accounts or certificates; they retain the bank name.",
        ],
    ),
    _sec(
        "23", "Currency", 1,
        "Manage the list of currencies available throughout the application and set the base (home) currency. "
        "Each currency has a code, name, flag emoji, and an optional exchange rate against the base currency.",
        steps=[
            "Go to Settings → Currency.",
            "Click Add Currency and enter: code (e.g. USD), name, flag emoji, and exchange rate.",
            "Set the base (home) currency — all amounts are normalised to this for reporting.",
            "Enable or disable multi-currency mode.",
            "Save; the change propagates to all forms and reports.",
        ],
        notes=[
            "The base currency is used for net-worth aggregation, budget limits, and report totals.",
            "Exchange rates can be refreshed from the internet via the Exchange Rates page.",
        ],
    ),
    _sec(
        "24", "Users", 1,
        "Sysadmin-only. Create, edit, suspend, and delete user accounts. Assign roles, toggle the "
        "is_sysadmin flag, and manage account status.",
        steps=[
            "Go to Settings → Users (visible only to sysadmins).",
            "Click Add User and enter: name, email, password, and role.",
            "Edit a user to change their role, toggle sysadmin, or suspend the account.",
            "Delete a user (soft-delete with a 30-day grace period for restoration).",
        ],
        notes=[
            "⚠️ Sysadmin only — this tab cannot be granted to any role.",
            "Suspended users cannot log in but their data is retained.",
            "The is_sysadmin flag grants access to all five sysadmin-only tabs.",
        ],
        sysadmin_only=True,
    ),
    _sec(
        "25", "Roles", 1,
        "Sysadmin-only. Create and manage custom roles. Each role is a named collection of permission keys "
        "(main-app pages + settings tabs). Assign roles to users to control their access.",
        steps=[
            "Go to Settings → Roles (visible only to sysadmins).",
            "Click Add Role and enter a name and description.",
            "Check the permission keys to grant (main-app pages and settings tabs).",
            "Save; the role is now available in the Users tab for assignment.",
            "Edit a role to add or remove permissions; changes apply immediately to all users with that role.",
        ],
        notes=[
            "⚠️ Sysadmin only — this tab cannot be granted to any role.",
            "The Member role is the default for self-registered users and cannot be deleted.",
            "Permission keys are additive: a user's effective access is the union of their role's keys and any per-user overrides.",
        ],
        sysadmin_only=True,
    ),
    _sec(
        "26", "Billing Plans", 1,
        "Sysadmin-only. Manage subscription plans, prices (per currency), the payment gateway "
        "(Paymob or Stripe), gateway test, customer list, trial settings, invoices, and upgrade requests.",
        steps=[
            "Go to Settings → Billing Plans (visible only to sysadmins).",
            "Manage plans: add, edit, activate/deactivate, and delete subscription plans.",
            "Set prices per plan per currency (prices use the currencies configured in Settings → Currency).",
            "Configure the payment gateway: select Paymob or Stripe and enter the API keys.",
            "Run a gateway test to verify the connection.",
            "View the customer list with subscription status (trialing, active, past_due, canceled, expired, suspended).",
            "Configure trial settings (default 14 days).",
            "Review invoices (pending, paid, failed, refunded, void).",
            "Process upgrade requests submitted by customers.",
        ],
        notes=[
            "⚠️ Sysadmin only — this tab cannot be granted to any role.",
            "API keys are encrypted at rest and never returned by the API (only an 'is_set' flag).",
            "Subscription access is granted for statuses: trialing, active, past_due.",
        ],
        sysadmin_only=True,
    ),
    _sec(
        "27", "Email Templates", 1,
        "Configure SMTP settings and manage the email templates used for account verification, "
        "password reset, and notification emails.",
        steps=[
            "Go to Settings → Email Templates.",
            "Enter SMTP host, port, username, password, and sender email.",
            "Enable or disable the console fallback (log emails to server console instead of sending).",
            "Edit the body and subject of each email template (verification, reset, notification).",
            "Save and send a test email to verify the configuration.",
        ],
        notes=[
            "SMTP credentials are encrypted at rest and never returned by the API.",
            "The console fallback is useful during development when no SMTP server is available.",
        ],
    ),
    _sec(
        "28", "Translations", 1,
        "Manage the translation strings for each supported language. Edit, add, or remove key-value pairs "
        "in the JSON translation files.",
        steps=[
            "Go to Settings → Translations.",
            "Select a language from the dropdown.",
            "Edit the translation value for any key.",
            "Add new keys for UI strings that are not yet translated.",
            "Save; the changes are applied on the next page load.",
        ],
        notes=[
            "Translation files are JSON: { \"key\": \"translated value\" }.",
            "Untranslated keys fall back to the English (default) value.",
        ],
    ),
    _sec(
        "29", "Translation Coverage", 1,
        "View a report of translation coverage per language: total keys, translated keys, missing keys, "
        "and coverage percentage. Helps identify gaps before releasing a new language.",
        steps=[
            "Go to Settings → Translation Coverage.",
            "Review the coverage table: language, total keys, translated, missing, percentage.",
            "Click a language to see the list of missing keys.",
            "Add the missing translations in the Translations tab.",
        ],
        notes=[
            "Coverage is calculated as (translated keys / total keys) × 100 %.",
            "A key is considered translated if its value is non-empty and differs from the English fallback.",
        ],
    ),
    _sec(
        "30", "Reminders", 1,
        "Configure reminder rules for certificate maturity, insurance expiry, vehicle license expiry, "
        "property tax, salary day, salary unpaid, and custom reminders. Each rule has a name, type, "
        "days-before threshold, and an optional custom message.",
        steps=[
            "Go to Settings → Reminders.",
            "Click Add Rule and select a type: Certificate Maturity, Insurance Expiry, Vehicle License Expiry, Property Tax, Salary Day, Salary Unpaid, or Custom.",
            "Set the days-before threshold (e.g. remind 30 days before certificate maturity).",
            "For salary rules, set the trigger (day of month, days before end of month, days after start of month) and the salary day.",
            "Enable or disable the rule.",
            "Active reminders appear in the dashboard banner and the Reminders page.",
        ],
        notes=[
            "Reminder checking is enabled by default; disable it in your per-user settings if needed.",
            "Certificate expiry warning days are configurable per-user (default 30).",
            "Reminders are evaluated on every page load; there is no background scheduler.",
        ],
    ),
    _sec(
        "31", "Certificate Status", 1,
        "Manage the status options available for bank certificates (e.g. Active, Matured, Redeemed, Cancelled). "
        "These statuses appear in the Bank Certificate modal dropdown.",
        steps=[
            "Go to Settings → Certificate Status.",
            "Add, edit, or delete status options.",
            "Reorder statuses to control their display order in the dropdown.",
            "Save; the changes appear in the Bank Certificate form.",
        ],
        notes=[
            "Deleting a status does not delete existing certificates; they retain the status value.",
        ],
    ),
    _sec(
        "32", "Gold Settings", 1,
        "Manage the gold types and purities available in the Gold Price page and the Fixed Assets gold "
        "valuation. Configure which carats are displayed and their purity percentages.",
        steps=[
            "Go to Settings → Gold Settings.",
            "Manage gold types (e.g. jewelry, bars, coins).",
            "Manage purities: 24K (99.9 %), 22K (91.7 %), 21K (87.5 %), 18K (75.0 %).",
            "Enable or disable specific purities in the Gold Price page.",
            "Save; the changes propagate to the Gold Price page and Fixed Assets gold valuation.",
        ],
        notes=[
            "Purity percentages are used to calculate the pure-gold value of an alloy.",
            "The Gold Price page displays only the enabled purities.",
        ],
    ),
    _sec(
        "33", "Property Valuation", 1,
        "Configure the property-valuation data source for real-estate assets. Supports a local rate map "
        "(scraped from AqarMap), an external API provider, and a configured market-rate provider. "
        "Also manages map tile URL and attribution for the asset map view.",
        steps=[
            "Go to Settings → Property Valuation.",
            "Configure the provider order: local rate map, external API, or configured market rate.",
            "Enable or disable the external API provider and enter the URL, result path, timeout, and headers.",
            "Set the map tile URL and attribution for the asset map view.",
            "Save; the changes apply to the Fixed Assets property valuation.",
        ],
        notes=[
            "The local rate map is scraped from AqarMap (aqarmap.com) via a Python management command.",
            "Map tile settings are per-user (stored in USER_SCOPED_SETTING_KEYS).",
            "Valuation history is retained for each asset to track appreciation over time.",
        ],
    ),
    _sec(
        "34", "Dashboard (Settings)", 1,
        "Control which widgets are displayed on the main Dashboard page. Toggles are per-user and "
        "persist across sessions.",
        steps=[
            "Go to Settings → Dashboard.",
            "Toggle: Show Certificates, Show Reminders, Show Salary.",
            "Save; the dashboard updates on the next page load.",
        ],
        notes=[
            "These settings are per-user (stored in USER_SCOPED_SETTING_KEYS).",
            "All three widgets are enabled by default.",
        ],
    ),
    _sec(
        "35", "Backup & Restore", 1,
        "Create, download, upload, and restore database backups. Supports client-side download (Save dialog), "
        "client-side upload (Open dialog), and server-side backup management (list, restore, delete).",
        steps=[
            "Go to Settings → Backup & Restore.",
            "Click Create & Download Backup to generate a portable archive of your database.",
            "Upload a previously saved backup file to restore it.",
            "View the server-side backup list (filename, size, date).",
            "Click Restore to restore a server-side backup (overwrites current data).",
            "Click Delete to remove a server-side backup.",
        ],
        notes=[
            "Backups include all data: accounts, transactions, assets, settings, and Arabic notes.",
            "Restoring a backup is destructive: all current data is replaced.",
            "The backup file is a JSON archive with a manifest for integrity verification.",
        ],
    ),
    _sec(
        "36", "Documentation", 1,
        "Generate and manage the WealthFlow documentation set: user guide, admin guide, and technical guide. "
        "The documentation engine captures screenshots, renders HTML/PDF/DOCX/Markdown, and validates "
        "inventory coverage.",
        steps=[
            "Go to Settings → Documentation.",
            "Select the guide type: User, Admin, or Technical.",
            "Select the language and theme (light/dark).",
            "Click Generate to run the documentation engine.",
            "Download the generated file (HTML, PDF, DOCX, or Markdown).",
            "View the generation history and validation results.",
        ],
        notes=[
            "The documentation engine uses Playwright for screenshot capture and rendering.",
            "Inventory coverage validation ensures every page and modal is documented.",
            "Generated files are stored on the server and can be re-downloaded from the history.",
        ],
    ),
    _sec(
        "37", "AI Advisor", 1,
        "Sysadmin-only. Configure the app-wide AI provider, model, and pipeline settings. Supports "
        "Ollama (local), OpenAI, Claude, Gemini, and Azure OpenAI. Manages models, datasets, benchmarks, "
        "autonomous learning, permission tiers, and answer validation.",
        steps=[
            "Go to Settings → AI Advisor (visible only to sysadmins).",
            "Select the AI provider: Ollama, OpenAI, Claude, Gemini, or Azure OpenAI.",
            "Enter the provider-specific settings: model name, API key, base URL, context size, timeout.",
            "Configure sampling parameters: temperature, top-p, top-k, repeat penalty, seed, max tokens.",
            "Set the permission tier: Read Only, Read + Execute, or Read + Execute + Modify.",
            "Enable or disable: Instant Data Answers, Multi-Agent Orchestration, Code Access (admin only).",
            "Set the answer validation mode (flag, warn, block).",
            "Configure the AI investigator mode (auto, manual, disabled).",
            "Run a connection test to verify the provider is reachable.",
            "Manage datasets, benchmarks, and autonomous learning settings.",
        ],
        notes=[
            "⚠️ Sysadmin only — this tab cannot be granted to any role.",
            "API keys are encrypted at rest and never returned by the API.",
            "The AI is strictly read-only by default; the permission tier controls tool-calling capabilities.",
            "Autonomous learning scans the app structure and updates the knowledge base (triggered manually).",
        ],
        sysadmin_only=True,
    ),
    _sec(
        "38", "Legal Text", 1,
        "Sysadmin-only. Edit the Privacy Policy and Terms of Service text shown to users during signup "
        "and in the legal pages. Manage the legal version and consent tracking.",
        steps=[
            "Go to Settings → Legal Text (visible only to sysadmins).",
            "Edit the Privacy Policy text (HTML supported).",
            "Edit the Terms of Service text (HTML supported).",
            "Publish a new version; existing users must re-consent on their next login.",
            "View the consent history per user.",
        ],
        notes=[
            "⚠️ Sysadmin only — this tab cannot be granted to any role.",
            "Users must accept the latest legal version before they can use the app.",
            "Consent is tracked per user with a timestamp and the legal version ID.",
        ],
        sysadmin_only=True,
    ),
    _sec(
        "39", "My AI Settings", 1,
        "Per-user AI settings. Choose whether to use the general (sysadmin-configured) AI settings or "
        "your own. Configure provider, model, sampling parameters, and view your monthly token usage.",
        steps=[
            "Go to Settings → My AI Settings.",
            "Toggle: Use General AI Settings (on = use sysadmin config, off = use your own).",
            "If using your own: select provider (Ollama, OpenAI, Claude, Gemini), enter model and API key.",
            "Configure sampling: temperature, max tokens, context size, timeout, top-p, top-k, repeat penalty, history window, context token budget.",
            "View your monthly token usage and limit (if set by the sysadmin).",
            "Save; the changes apply to your AI chat sessions immediately.",
        ],
        notes=[
            "Only whitelisted keys are editable per-user (see AI_USER_SETTING_KEYS).",
            "Sysadmin-only settings (permission tier, code access, pipeline switches) are never shown here.",
            "Monthly token limits are set by the sysadmin in the AI Advisor tab.",
        ],
    ),

    # ── BACK MATTER ───────────────────────────────────────────────────────────
    _sec(
        "40", "Roles & Permissions Reference", 1,
        "Complete matrix of all permission keys, the roles that include them, and the pages/tabs they unlock. "
        "Use this reference to understand exactly what each role can access.",
        steps=[
            "Review the main-app page permissions (16 pages): Dashboard, WealthFlow AI, Financial Advisor, Employment, Balance, Bank Certificates, Fixed Assets, Exchange Rates, Gold Price, Expenses, Expense Categories, Budgets, Import Data, Reports, Advanced Reports, Settings.",
            "Review the settings-tab permissions (20 tabs): Languages, Companies, Banks, Currency, Users, Roles, Billing Plans, Email Templates, Translations, Translation Coverage, Reminders, Certificate Status, Gold Settings, Property Valuation, Dashboard, Backup & Restore, Documentation, AI Advisor, Legal Text, My AI Settings.",
            "Identify the five sysadmin-only tabs: Users, Roles, Billing Plans, AI Advisor, Legal Text.",
            "Check the Member role's default keys to understand what a new user can access.",
        ],
        notes=[
            "Permission keys are additive: a user's effective access is the union of their role's keys and any per-user overrides.",
            "The is_sysadmin flag is separate from roles and grants access to the five sysadmin-only tabs.",
            "The legacy 'user_management' page key is superseded by the 'settings_users' tab key.",
        ],
    ),
    _sec(
        "41", "Glossary", 1,
        "Definitions of key terms used throughout WealthFlow.",
        notes=[
            "Base Currency: The currency all amounts are normalised to for reporting and aggregation.",
            "Net Worth: Total assets (cash + bank + certificates + gold + fixed assets) minus liabilities.",
            "Per Diem: A daily allowance paid in addition to salary, recorded as supplementary income.",
            "Purity: The percentage of pure gold in an alloy (e.g. 21K = 87.5 %).",
            "Tola: A unit of mass used in South Asian gold markets (1 tola = 11.664 g).",
            "Recurring Transaction: A budget item that auto-posts on a schedule (monthly, weekly, etc.).",
            "Sysadmin: A user with the is_sysadmin flag, granting access to all five sysadmin-only tabs.",
            "Token: A unit of text used by LLMs; monthly token limits cap AI usage per user.",
            "Provider: The AI backend (Ollama, OpenAI, Claude, Gemini, Azure OpenAI).",
            "Permission Key: A string identifier (e.g. 'settings_billing') that grants access to a page or tab.",
        ],
    ),
    _sec(
        "42", "Troubleshooting & FAQ", 1,
        "Common issues and their resolutions.",
        notes=[
            "Q: I can't see a Settings tab. A: Your role does not include the permission key for that tab. Ask a sysadmin to assign a role that includes it.",
            "Q: The AI chat is slow. A: Check the provider connection in Settings → AI Advisor. Local Ollama models are slower than cloud providers but work offline.",
            "Q: Exchange rates are not updating. A: The refresh button requires an internet connection. Check your network and try again.",
            "Q: Gold prices are stale. A: Click Refresh on the Gold Price page to fetch the latest rates from the external API.",
            "Q: I forgot my password. A: Use the Forgot Password link on the login page. A reset email is sent to your registered address.",
            "Q: My account was suspended. A: Contact a sysadmin to review your account status.",
            "Q: The app is in the wrong language. A: Use the language switcher in the top bar, or set your preferred language in Settings → Languages.",
            "Q: Data was lost after a restore. A: Restoring a backup is destructive. Always create a new backup before restoring.",
        ],
    ),
    _sec(
        "43", "Appendix: Shortcuts & Tips", 1,
        "Keyboard shortcuts and productivity tips.",
        notes=[
            "Tab / Shift+Tab: Navigate between interactive elements.",
            "Enter: Activate the focused button or link.",
            "Escape: Close the active modal or dropdown.",
            "Ctrl+K (or the search icon): Quick-search across pages (if enabled).",
            "Tip: Use the Prompt Library in WealthFlow AI to save frequently asked questions as reusable prompts.",
            "Tip: Enable recurring auto-posting to automatically record monthly rent and subscriptions.",
            "Tip: Use the Scenario Planner in Financial Advisor to model the impact of a bonus or a large purchase before committing.",
            "Tip: Create a backup before any bulk import or restore operation.",
            "Tip: Set your base currency to the one you use most for day-to-day spending to make reports more intuitive.",
        ],
    ),
]


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def kebab_id(number: str, title: str) -> str:
    """Generate a unique kebab-case id from number + title."""
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return f"sec-{number.replace('.', '-')}-{slug}"


def esc(text: str) -> str:
    return html.escape(text, quote=True)


# ─────────────────────────────────────────────────────────────────────────────
# HTML RENDERER
# ─────────────────────────────────────────────────────────────────────────────

def render_html(sections: list, out_path: str) -> None:
    today = date.today().isoformat()

    # ── Build TOC (nested <ul>) ──────────────────────────────────────────────
    toc_items = []
    for s in sections:
        sid = kebab_id(s["number"], s["title"])
        badge = ' <span class="sysadmin-badge" aria-label="Sysadmin only">⚠️</span>' if s["sysadmin_only"] else ""
        toc_items.append(
            f'<li class="toc-l{s["level"]}">'
            f'<a href="#{sid}" data-target="{sid}">{esc(s["number"])} {esc(s["title"])}{badge}</a>'
            f"</li>"
        )
    toc_html = "\n".join(toc_items)

    # ── Build body sections ──────────────────────────────────────────────────
    body_parts = []
    for s in sections:
        sid = kebab_id(s["number"], s["title"])
        h_tag = f"h{s['level']}"
        badge_html = (
            '<p class="sysadmin-warning" role="note">⚠️ <strong>Sysadmin only</strong> — '
            "This section is restricted to system administrators.</p>"
            if s["sysadmin_only"]
            else ""
        )

        purpose_html = f'<p class="purpose">{esc(s["purpose"])}</p>' if s["purpose"] else ""

        steps_html = ""
        if s["steps"]:
            lis = "\n".join(f"  <li>{esc(step)}</li>" for step in s["steps"])
            steps_html = f'<ol class="steps">\n{lis}\n</ol>'

        notes_html = ""
        if s["notes"]:
            lis = "\n".join(f"  <li>{esc(note)}</li>" for note in s["notes"])
            notes_html = f'<ul class="notes">\n{lis}\n</ul>'

        body_parts.append(f"""
<section id="{sid}" class="guide-section" aria-labelledby="{sid}-heading">
  <{h_tag} id="{sid}-heading" class="section-heading">{esc(s["number"])} {esc(s["title"])}</{h_tag}>
  {badge_html}
  {purpose_html}
  {steps_html}
  {notes_html}
</section>""")

    body_html = "\n".join(body_parts)

    # ── Full HTML document ───────────────────────────────────────────────────
    html_doc = f"""<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>WealthFlow User Guide</title>
<meta name="description" content="Complete user guide for the WealthFlow personal-finance platform.">
<style>
/* ── Reset & tokens ─────────────────────────────────────────────────────── */
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
:root{{
  --bg:#f8f9fa;--bg-card:#fff;--text:#212529;--text-muted:#6c757d;
  --accent:#0d6efd;--accent-light:#cfe2ff;--border:#dee2e6;
  --sidebar-w:280px;--radius:8px;
  --sysadmin-bg:#fff3cd;--sysadmin-border:#ffc107;--sysadmin-text:#664d03;
}}
@media(prefers-color-scheme:dark){{
  :root{{
    --bg:#121212;--bg-card:#1e1e1e;--text:#e0e0e0;--text-muted:#9e9e9e;
    --accent:#4dabf7;--accent-light:#1a3a5c;--border:#333;
    --sysadmin-bg:#332b00;--sysadmin-border:#665200;--sysadmin-text:#ffc107;
  }}
}}
html{{scroll-behavior:smooth;scroll-padding-top:1rem}}
body{{font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  background:var(--bg);color:var(--text);line-height:1.6;font-size:15px}}

/* ── Skip link ──────────────────────────────────────────────────────────── */
.skip-link{{position:absolute;top:-100%;left:0;background:var(--accent);color:#fff;
  padding:.5rem 1rem;z-index:9999;border-radius:0 0 var(--radius) 0;
  text-decoration:none;font-weight:600}}
.skip-link:focus{{top:0}}

/* ── Layout ─────────────────────────────────────────────────────────────── */
.layout{{display:flex;min-height:100vh}}
.toc-rail{{
  position:sticky;top:0;width:var(--sidebar-w);height:100vh;overflow-y:auto;
  background:var(--bg-card);border-right:1px solid var(--border);
  padding:1rem .75rem;flex-shrink:0;
}}
.toc-rail h2{{font-size:.85rem;text-transform:uppercase;letter-spacing:.05em;
  color:var(--text-muted);margin-bottom:.75rem}}
.toc-rail ul{{list-style:none}}
.toc-rail li{{margin:.15rem 0}}
.toc-rail a{{
  display:block;padding:.3rem .5rem;border-radius:var(--radius);
  color:var(--text);text-decoration:none;font-size:.85rem;
  transition:background .15s,color .15s;
}}
.toc-rail a:hover,.toc-rail a:focus{{background:var(--accent-light);color:var(--accent);outline:none}}
.toc-rail a.active{{background:var(--accent);color:#fff;font-weight:600}}
.toc-l2 a{{padding-left:1.25rem;font-size:.82rem}}
.toc-l3 a{{padding-left:2rem;font-size:.8rem}}
.sysadmin-badge{{font-size:.75rem;margin-left:.25rem}}

main{{flex:1;padding:2rem 2.5rem;max-width:860px;min-width:0}}

/* ── Mobile TOC toggle ──────────────────────────────────────────────────── */
.toc-toggle{{
  display:none;position:fixed;top:.75rem;left:.75rem;z-index:1000;
  background:var(--accent);color:#fff;border:none;border-radius:var(--radius);
  padding:.5rem .75rem;font-size:1rem;cursor:pointer;
}}
@media(max-width:768px){{
  .toc-toggle{{display:block}}
  .toc-rail{{
    position:fixed;left:0;top:0;transform:translateX(-100%);
    transition:transform .25s ease;z-index:999;width:260px;
    box-shadow:2px 0 12px rgba(0,0,0,.15);
  }}
  .toc-rail.open{{transform:translateX(0)}}
  main{{padding:4rem 1rem 2rem}}
}}

/* ── Sections ───────────────────────────────────────────────────────────── */
.guide-section{{margin-bottom:2.5rem;padding-bottom:1.5rem;border-bottom:1px solid var(--border)}}
.guide-section:last-child{{border-bottom:none}}
.section-heading{{margin-bottom:.75rem;line-height:1.3}}
h1.section-heading{{font-size:1.6rem}}
h2.section-heading{{font-size:1.3rem}}
h3.section-heading{{font-size:1.1rem}}
.purpose{{color:var(--text);margin-bottom:.75rem}}
.steps{{padding-left:1.5rem;margin:.5rem 0}}
.steps li{{margin:.3rem 0}}
.notes{{padding-left:1.5rem;margin:.5rem 0;list-style:disc}}
.notes li{{margin:.3rem 0;color:var(--text-muted)}}
.sysadmin-warning{{
  background:var(--sysadmin-bg);border:1px solid var(--sysadmin-border);
  color:var(--sysadmin-text);padding:.5rem .75rem;border-radius:var(--radius);
  margin-bottom:.75rem;font-size:.9rem;
}}

/* ── Print ──────────────────────────────────────────────────────────────── */
@media print{{
  .toc-rail,.toc-toggle,.skip-link{{display:none!important}}
  main{{max-width:100%;padding:0}}
  .guide-section{{break-inside:avoid;page-break-inside:avoid}}
  body{{background:#fff;color:#000;font-size:12pt}}
}}
</style>
</head>
<body>
<a href="#main-content" class="skip-link">Skip to main content</a>
<button class="toc-toggle" id="tocToggle" aria-label="Toggle table of contents" aria-expanded="false">☰</button>
<div class="layout">
<nav class="toc-rail" id="tocRail" aria-label="Table of Contents">
  <h2>Contents</h2>
  <ul>
{toc_html}
  </ul>
</nav>
<main id="main-content" role="main">
<header>
  <h1>WealthFlow User Guide</h1>
  <p style="color:var(--text-muted);margin-bottom:1.5rem">Generated {today} · Single-tenant personal-finance platform</p>
</header>
{body_html}
</main>
</div>
<script>
// ── Mobile TOC toggle ──────────────────────────────────────────────────────
(function(){{
  var btn=document.getElementById("tocToggle"),rail=document.getElementById("tocRail");
  btn.addEventListener("click",function(){{
    var open=rail.classList.toggle("open");
    btn.setAttribute("aria-expanded",open?"true":"false");
  }});
  // Close on link click (mobile)
  rail.querySelectorAll("a").forEach(function(a){{
    a.addEventListener("click",function(){{
      if(window.innerWidth<=768){{rail.classList.remove("open");btn.setAttribute("aria-expanded","false");}}
    }});
  }});
}})();

// ── Active-section highlighting (IntersectionObserver) ─────────────────────
(function(){{
  var links=document.querySelectorAll(".toc-rail a[data-target]");
  var map={{}};
  links.forEach(function(a){{map[a.getAttribute("data-target")]=a;}});
  var sections=document.querySelectorAll(".guide-section");
  if(!("IntersectionObserver" in window))return;
  var visible=new Map();
  var obs=new IntersectionObserver(function(entries){{
    entries.forEach(function(e){{
      if(e.isIntersecting)visible.set(e.target.id,e.target);
      else visible.delete(e.target.id);
    }});
    // Pick the topmost visible section
    var top=null;
    visible.forEach(function(sec){{
      if(!top||sec.getBoundingClientRect().top<top.getBoundingClientRect().top)top=sec;
    }});
    links.forEach(function(a){{a.classList.remove("active");}});
    if(top&&map[top.id]){{
      map[top.id].classList.add("active");
      // Scroll TOC to keep active link in view
      map[top.id].scrollIntoView({{block:"nearest"}});
    }}
  }},{{rootMargin:"0px 0px -60% 0px",threshold:0}});
  sections.forEach(function(s){{obs.observe(s);}});
}})();
</script>
</body>
</html>"""

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_doc)
    print(f"  ✓ HTML  → {out_path}")


# ─────────────────────────────────────────────────────────────────────────────
# DOCX RENDERER
# ─────────────────────────────────────────────────────────────────────────────

def render_docx(sections: list, out_path: str) -> None:
    from docx import Document
    from docx.shared import Inches, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    doc = Document()

    # ── Header: title right-aligned ─────────────────────────────────────────
    section = doc.sections[0]
    header_p = section.header.paragraphs[0]
    header_p.text = "WealthFlow User Guide"
    header_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT

    # ── Footer: page number field, centred ──────────────────────────────────
    footer_p = section.footer.paragraphs[0]
    footer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = footer_p.add_run("Page ")

    def _add_page_number(r):
        fldChar1 = OxmlElement("w:fldChar")
        fldChar1.set(qn("w:fldCharType"), "begin")
        instrText = OxmlElement("w:instrText")
        instrText.set(qn("xml:space"), "preserve")
        instrText.text = "PAGE"
        fldChar2 = OxmlElement("w:fldChar")
        fldChar2.set(qn("w:fldCharType"), "separate")
        fldChar3 = OxmlElement("w:fldChar")
        fldChar3.set(qn("w:fldCharType"), "end")
        r._r.append(fldChar1)
        r._r.append(instrText)
        r._r.append(fldChar2)
        r._r.append(fldChar3)

    _add_page_number(run)

    # ── Title heading ────────────────────────────────────────────────────────
    doc.add_heading("WealthFlow User Guide", level=0)
    p = doc.add_paragraph()
    p.add_run(f"Generated: {date.today().isoformat()}")
    doc.add_page_break()

    # ── Contents page (generated from the same SECTIONS list) ───────────────
    doc.add_heading("Contents", level=1)
    for s in sections:
        indent_level = s["level"] - 1
        p_toc = doc.add_paragraph(f"{s['number']}  {s['title']}")
        p_toc.paragraph_format.left_indent = Inches(0.3 * indent_level)
        if s["sysadmin_only"]:
            run_badge = p_toc.add_run("  ⚠️ Sysadmin only")
            run_badge.font.color.rgb = RGBColor(0x99, 0x66, 0x00)
            run_badge.bold = True
    doc.add_page_break()

    # ── Body ─────────────────────────────────────────────────────────────────
    for s in sections:
        h_level = min(s["level"], 3)
        doc.add_heading(f"{s['number']} {s['title']}", level=h_level)

        if s["sysadmin_only"]:
            p_warn = doc.add_paragraph()
            run_warn = p_warn.add_run("⚠️ Sysadmin only — this section is restricted to system administrators.")
            run_warn.bold = True
            run_warn.font.color.rgb = RGBColor(0x99, 0x66, 0x00)

        if s["purpose"]:
            p = doc.add_paragraph()
            p.add_run("Purpose: ").bold = True
            p.add_run(s["purpose"])

        if s["steps"]:
            doc.add_paragraph("Steps:", style="Heading 3")
            for idx, step in enumerate(s["steps"], 1):
                doc.add_paragraph(f"{idx}. {step}", style="List Paragraph")

        if s["notes"]:
            doc.add_paragraph("Notes:", style="Heading 3")
            for note in s["notes"]:
                doc.add_paragraph(note, style="List Bullet")

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    doc.save(out_path)
    print(f"  ✓ DOCX  → {out_path}")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    base = os.path.join(os.path.dirname(__file__), "..")
    html_path = os.path.normpath(os.path.join(base, "docs", "user_guide.html"))
    docx_path = os.path.normpath(os.path.join(base, "docs", "user_guide.docx"))

    print("WealthFlow User Guide Generator")
    print(f"Sections: {len(SECTIONS)}")
    print(f"  Sysadmin-only: {sum(1 for s in SECTIONS if s['sysadmin_only'])}")
    print()

    render_html(SECTIONS, html_path)
    render_docx(SECTIONS, docx_path)

    print()
    print("Done. Both files generated from the same content model.")


if __name__ == "__main__":
    main()
