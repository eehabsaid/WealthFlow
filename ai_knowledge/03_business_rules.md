# WealthFlow Business Concepts & Rules

## 1. Asset Classification & Liquidity
- **Liquid Cash** (`BankBalance`): Immediately accessible. Balances stored per account per currency.
- **Bank Certificates** (`BankCertificate`): Semi-liquid. Locked until maturity. Yield: monthly, quarterly, annual, or at-maturity payout. Key fields: `principal`, `annual_rate`, `start_date`, `maturity_date`, `payout_frequency`, `currency`.
- **Gold** (`GoldAsset`): Valued by weight × karat purity × live spot price. Weight in grams; karat stored as integer (e.g. 21).
- **Real Estate / Vehicles / Other Fixed Assets** (`FixedAsset`, `FixedAssetValuationHistory`): Illiquid. Value from most recent valuation record.
- **Salary** (`SalaryEntry`, `SalaryDeduction`, `PerDiem`): Multi-employer. Net = gross − deductions + per diems.
- **Expenses** (`Expense`, `ExpenseCategory`): Categorized under parent categories. Amount stored as `amount_egp` (always in EGP regardless of original currency).

## 2. Multi-Currency Operations
- Home currency stored in `UserProfile.preferred_currency` (default: EGP).
- Supported foreign currencies: USD, EUR, SAR.
- Live exchange rates from `ExchangeRate` model. Used for all net worth conversions.
- `amount_egp` on `Expense` is always the EGP-equivalent amount — use this field for expense calculations, NOT `amount`.

## 3. Net Worth Formula
Net Worth = Liquid Cash (all currencies → home) + Certificates Principal (→ home) + Gold Market Value + Real Estate Value + Vehicle & Other Asset Value − Active Liabilities


## 4. Expense Field Rule — CRITICAL
- Always use `amount_egp` for expense totals and AI context, not `amount`.
- `amount` stores the original currency amount; `amount_egp` stores the converted EGP value.

## 5. Row Cap Rules for AI Context
- All provider payloads cap list items to the 20 most recent rows to control token usage.
- Aggregates (totals, averages, counts) are computed over the FULL queryset before capping — never over the sliced list.

## 6. AppSettings Keys (Runtime Config)
- `ai_system_prompt` — base system prompt text
- `ai_context_token_budget` — token budget for context assembly (default: 2048)
- `home_currency` — fallback home currency if user profile not set
- `ai_provider` — active AI provider name (e.g. `ollama`, `openai`)