# Django architecture (WealthFlow)
- Stack: Django 6 backend, vanilla-JS single-page app (no framework), SQLite in the repo (`db.sqlite3` tracked on purpose, never edit it).
- Layers: `core/models/` (one file or folder per area) -> `core/services/<area>/` (business rules) -> `core/views/` (thin JSON views) -> `core/urls/*_urls.py` (all routes `api/...`).
- Views are class-based `View`s returning `JsonResponse`. Start each handler with `_api_auth_required(request)` (from `core.validators`); body via `parse_json_body(request)`.
- Business logic belongs in a service class, never in a view. Reuse the existing service the screen already uses (e.g. `ExpenseService`) instead of writing to models directly.
- Plan gating: wrap routes with `feature_required("allows_ai_workspace")` (`core/services/billing`). Sysadmin-only views use `SysadminRequiredMixin`.
- App settings live in `AppSettings` (`AppSettings.get(key, default, user=...)`); `user=None` = global. The AI app's own `ai_*`/`speech_*`/`image_gen_*` settings live in `ai.models.AISetting` (same get/set API). Prefer a UI setting over `.env`.
- `ai/` must not import `core`: WealthFlow-specific AI code lives in `core/ai_pack` and plugs in through `settings.AI_PACKS`; host answers (admin check, audit, currency) are `AI_*` hooks in `wealthflow/settings.py` (`ai/host.py`).
- Every code file must stay <= 200 lines: split into a package folder with an `__init__.py` that re-exports.
- Shared central services are additive-only: `CurrencyConversionService`, `base_currency.py`, `ExchangeRateHistoryService`, `market_profile.py`, settings access. List every caller before touching one.
