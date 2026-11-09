# How data flows (generated from code - do not edit by hand)

## Fixed assets
- Asset types (Fixed Assets page): Real Estate, Vehicles, Gold, Other Assets.
- Acquisition costs, renovations and furniture are kept only for type(s): Real Estate; for every other type they are discarded on save.
- 'Other Assets' details fields: category, manufacturer, model, serial_number, description, warranty_expiry, notes.
- Saving an asset with a purchase price records purchase payments; each payment deducts a cash/bank balance entry (same currency, same bank) and fails if that balance would go negative. Deleting the asset or editing the payments reverses it.
- The asset purchase price itself is NOT written as an Expense row; only acquisition costs, renovations and furniture of a Real Estate asset are mirrored into Expenses.
- Net worth counts each owned asset at its current market value (real estate, vehicles, other assets, gold).
- Asset purchase payment method 'Cash': needs a bank account: no
- Asset purchase payment method 'Card': needs a bank account: yes
- Asset purchase payment method 'Bank': needs a bank account: yes
- Asset purchase payment method 'Bank Transfer': needs a bank account: yes

## Expenses
- Saving an Expense deducts a balance entry when its payment method affects balance; editing or deleting reverses it.
- Expense payment method 'Cash': deducts a balance entry: yes; needs a bank account: no
- Expense payment method 'Card': deducts a balance entry: yes; needs a bank account: yes
- Expense payment method 'Bank Transfer': deducts a balance entry: yes; needs a bank account: yes
- Expense payment method 'Other': deducts a balance entry: no; needs a bank account: no
- Expenses reduce cash and appear in spending analytics; they do not create or change any asset.

## Mirroring (shared engine: core/services/shared/expense_mirror_engine.py)
- System-generated Expense rows (is_system_generated, read-only, source_type set) exist only for: Asset Renovation (asset_renovation), Asset Acquisition Cost (asset_acquisition_cost), Asset Furniture (asset_furniture), Credit Card Payment (credit_card_payment), Card Renewal Fee (card_renewal_fee).
- Fixed-asset mirrors land in expense category 'Fixed Assets', subcategories: Acquisition Costs, Renovation, Furniture.
- Credit card payments land in 'Credit Card' / 'Credit Card Payment'; card renewal fees in 'Card Fees' / 'Card Renewal Fee'.
- A mirror row is edited or deleted from its source record, never from the Expenses page.

## Double counting
- An Expense and an asset purchase payment each deduct a balance entry independently, so recording the same purchase in both deducts the money twice. Mirrored rows are the exception: they are created from the source record and do not deduct a second time.
