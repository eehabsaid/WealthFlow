# Fixed assets
- Model package `core/models/fixed_assets/` (`model.py`, mixins), type-specific models (`fixed_assets_realestate/`, `fixed_assets_vehicle.py`, `fixed_assets_gold.py`, `fixed_assets_other.py`) and history models in `fixed_assets_history/`.
- Services in `core/services/fixed_assets/`: purchase, sale, maintenance, rent receipts, valuation history, property valuation (Aqarmap scraper), gold valuation/sync, vehicle.
- Renovations, acquisition costs and furniture create mirrored `Expense` rows (`asset_expense_mirror_service.py`, signals in `fixed_assets_history`). Edit the source record, never the mirror.
- Gold prices come from the site's live feed; do not parse the stale HTML table.
- Photos are served from `media/`; asset documents use `core/services/shared/document_service`.
- Tests: `core/tests/fixed_assets/`; E2E: `tests/modules/fixed_assets.py`, `tests/modules/rent_receipts.py`.
