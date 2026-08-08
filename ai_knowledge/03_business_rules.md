# WealthFlow Business Concepts & Rules

## 1. Asset Classification & Liquidity
- **Liquid Cash**: Immediately accessible funds stored in bank accounts (`BankBalance`) or physical currency holdings.
- **Semi-Liquid Holdings**: High-yield bank certificates (`BankCertificate`). Funds are locked until maturity, but yield predictable recurring interest income (payout frequency: monthly, quarterly, annual, at maturity).
- **Illiquid Fixed Assets**: Real estate, vehicles, and specialized collectibles. Value is based on periodic market revaluation (`FixedAssetValuationHistory`).
- **Precious Metals (Gold)**: Valued continuously by multiplying total pure gold mass (converted to 24K equivalent grams) by current market gold spot price per gram.

## 2. Multi-Currency Operations
- Users operate with a designated **Primary/Home Currency** (stored in `UserProfile.preferred_currency`, defaulting to EGP).
- Accounts, certificates, salary payments, and expenses can exist in foreign currencies (USD, EUR, SAR).
- All overall net worth calculations must convert non-home currency figures into the active home currency using live exchange rates from `ExchangeRate`.

## 3. Net Worth Calculation Business Rule
Total Net Worth is defined as:
$$\text{Net Worth} = \text{Total Liquid Cash} + \text{Total Certificates Principal} + \text{Total Gold Market Value} + \text{Total Real Estate Market Value} + \text{Total Vehicle & Other Asset Market Value} - \text{Total Active Liabilities/Mortgages}$$

## 4. Expense Categorization & Budgeting
- Expenses are grouped under parent categories (e.g., Housing, Transportation, Food & Dining, Utilities, Healthcare, Discretionary).
- Monthly spending trends compare total monthly expenses against net salary income to derive monthly net cash flow and savings rate.
