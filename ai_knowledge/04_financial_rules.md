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
