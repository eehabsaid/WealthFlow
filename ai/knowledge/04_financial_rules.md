# WealthFlow Financial & Calculation Rules

## 1. Currency Conversion Formula
When converting an amount $A$ from currency $C_{\text{from}}$ to home currency $C_{\text{home}}$:
$$A_{\text{home}} = A \times R(C_{\text{from}} \rightarrow C_{\text{home}})$$
If no direct exchange rate is found, use the inverse rate or cross-rate via USD.

## 2. Bank Certificate Interest Calculations
- **Simple Annual Payout**:
$$\text{Annual Payout} = P \times r$$
$$\text{Monthly Payout} = \frac{P \times r}{12}$$
where $P$ is principal amount and $r$ is annual interest rate (e.g. 0.225 for 22.5%).

- **Total Expected Return at Maturity**:
$$\text{Total Interest} = P \times r \times T_{\text{years}}$$

## 3. Gold Valuation Formula
Gold asset market value is calculated as:
$$\text{Gold Value} = \sum_{\text{items}} \left( \text{Weight in Grams} \times \frac{\text{Karat}}{24} \right) \times \text{Spot Price per 24K Gram}$$

## 4. Net Cash Flow & Savings Rate Formulas
- **Monthly Net Cash Flow**:
$$\text{Net Cash Flow} = \text{Monthly Net Income} - \text{Total Monthly Expenses}$$
- **Savings Rate Percentage**:
$$\text{Savings Rate} = \left( \frac{\text{Net Cash Flow}}{\text{Monthly Net Income}} \right) \times 100\%$$

## 5. Forecasting & Compounding Assumptions
- Long-term growth projections apply compounding interest formulas to liquid holdings reinvested at the user's weighted average certificate/yield rate.
- Inflation stress tests compound baseline expenses at annual inflation rate $i$:
$$E_{t} = E_0 \times (1 + i)^t$$

## 6. Expense Amount Field Rule — CRITICAL
- Always use `amount_base` for all expense calculations, totals, and AI context payloads.
- `amount` stores the original currency value; `amount_base` stores the base-currency-converted value.
- Using `amount` instead of `amount_base` produces wrong totals for multi-currency expense data.

## 7. Net Worth Formula (Plain Text Reference)
Net Worth = Liquid Cash (all currencies → home) + Certificates Principal (→ home) + Gold Market Value + Real Estate Value + Vehicles & Other Assets − Active Liabilities
All non-home-currency values must be converted using live `ExchangeRate` records before summing.

## 8. Row-Cap Rule for AI Payloads
- All provider list payloads are capped at 20 most recent rows for token efficiency.
- Aggregates (totals, averages, counts) MUST be computed over the full queryset BEFORE slicing.
- Slicing first then aggregating produces incorrect totals — this is a known anti-pattern in this codebase.

## 9. Market Profiles: Egypt and the Gulf (SAR / AED)
- A user's market follows their base currency. Base SAR, AED, KWD, QAR, BHD or OMR is a Gulf-market user; everything else keeps the Egyptian behavior unchanged.
- A Gulf-market user has no EGP in their currency list or in their exchange-rate list. EGP is kept only when something still references it (balances, expenses, goals, assets); it is never deleted out from under existing data.
- Gold for a Gulf-market user is the international spot price converted to their own base currency (USD per gram of 24K × carat purity × the USD→base rate). There is no dealer buy/sell spread and no Egyptian making charge. Shop prices are higher than the spot price.
- Gold for every other user is the Egyptian dealer price in EGP with buy and sell prices, converted to the base currency when it is not EGP.
- To answer "what is the gold price" for a Gulf-market user, read the `/api/gold/` values (`market = "spot"`, `currency` = base code) and never quote EGP figures.
- Plan prices in EGP are not offered to a Gulf-market user who holds no EGP.
