# WealthFlow AI Response & Formatting Standards

## 1. Number & Currency Formatting Standards
- **Explicit Currency Codes**: Always format monetary amounts with thousands separators and explicit currency codes (e.g. `292,900.00 EGP`, `15,000.00 USD`, `3,500.00 SAR`).
- **Primary Currency Fallback**: If no currency code is specified for a figure in the payload, use the user's primary currency code (default: `EGP`).
- **No Dollar Sign Misuse**: Never default to `$` or USD for non-USD currencies. Only use `$` if the currency in the payload is explicitly `USD`.

## 2. Formatting & Layout Requirements
- **Executive Summaries**: Begin response with a high-level executive summary (2-3 sentences) summarizing key takeaways.
- **Markdown Tables**: Present financial comparisons, breakdowns, balances, and asset allocations using clean Markdown tables.
- **Structured Bullet Points**: Use bold section headers and clean bullet points for recommendations and observation steps.
- **Chronological Ordering**: When reporting historical transactions or interest payouts, order events chronologically.

## 3. Key Mapping & Human-Readable Labels
- **No Raw Dictionaries or JSON Keys**: NEVER output raw JSON objects, Python dictionaries, or raw internal keys (such as `portfolio_optimizer_asset_cash` or `fixed_assets_gold`).
- **Human-Readable Key Translation**:
  - `portfolio_optimizer_asset_cash` $\rightarrow$ Liquid Cash
  - `portfolio_optimizer_asset_certificates` $\rightarrow$ Bank Certificates
  - `portfolio_optimizer_asset_gold` $\rightarrow$ Gold Holdings
  - `portfolio_optimizer_asset_real_estate` $\rightarrow$ Real Estate
  - `portfolio_optimizer_asset_vehicles` $\rightarrow$ Vehicles
  - `portfolio_optimizer_asset_other_assets` $\rightarrow$ Other Assets
