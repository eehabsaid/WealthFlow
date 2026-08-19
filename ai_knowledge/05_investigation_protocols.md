# WealthFlow AI Investigation & Analytical Protocols

## 1. Portfolio Analysis
**Trigger**: "analyze my portfolio", "asset allocation", "rebalance", "diversification"
**Required data providers**: balance, certificates, gold, fixed_assets, exchange rates
**Steps**:
1. Aggregate total holdings per asset class in home currency.
2. Calculate % distribution: Liquid Cash, Certificates, Gold, Real Estate, Vehicles, Other.
3. Flag concentration risk (>70% in single asset class).
4. Evaluate liquidity ratio: (Liquid Cash + monthly certificate income) vs 6-month essential expenses.
**Output**: Asset breakdown table, concentration flags, rebalancing suggestions.

## 2. Net Worth Audit
**Trigger**: "net worth", "total wealth", "net worth audit"
**Required data providers**: balance, certificates, gold, fixed_assets, liabilities
**Steps**:
1. Sum all assets converted to home currency.
2. Subtract total active liabilities.
3. Check for missing/stale valuations.
**Output**: Net worth summary table, liquid vs illiquid breakdown.

## 3. Salary & Cash Flow
**Trigger**: "salary", "income", "cash flow", "savings rate"
**Required data providers**: salary, expenses
**Steps**:
1. Gross salary → subtract deductions → add per diems = net income.
2. Net income − monthly average expenses = net cash flow.
3. Savings rate = (net cash flow / net income) × 100%.
**Output**: Salary breakdown, top expense categories, savings efficiency.

## 4. Expense Audit
**Trigger**: "expenses", "spending", "budget", "category breakdown"
**Required data providers**: spending_intelligence, expenses
**Steps**:
1. Rank expense categories by total (using `amount_egp` field only).
2. Separate fixed vs discretionary.
3. Flag spikes vs prior period.
**Output**: Categorical breakdown table, savings opportunities, budget thresholds.

## 5. Certificate Analysis
**Trigger**: "certificates", "interest", "maturity", "yield"
**Required data providers**: certificates
**Steps**:
1. List active certificates with principal, rate, maturity date, payout frequency.
2. Calculate annual interest per certificate: `principal × annual_rate`.
3. Identify certificates maturing within 90 days.
**Output**: Certificate table, total annual yield, maturity calendar.

## 6. Missing Data Protocol
- If a required signal is absent: state "No data available for [module] in the current context."
- Never invent balances, rates, or certificate terms.
- If `amount_egp` is zero or missing on expenses, flag it rather than using `amount`.