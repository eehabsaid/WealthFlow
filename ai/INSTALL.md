# Installing the AI app (`ai/`) in another Django project

Needs Python 3.10+, Django 4.2+, `requests`, `cryptography` (see `ai/requirements.txt`; ranges only, nothing is pinned).

## Steps
1. **Copy** the `ai/` folder next to your `manage.py` (no node_modules, no `__pycache__`).
2. **settings.py**
   ```python
   INSTALLED_APPS += ["ai"]                    # label "ai"; user model = AUTH_USER_MODEL
   ```
   Everything below is optional (defaults in `ai/host.py` and `ai/conf.py`):
   ```python
   AI_PACKS = []                               # host plug-ins, see "Packs"
   AI_HOST_APPS = []                           # your app labels the AI may describe/query (needs AI_PACKS to query data)
   AI_CODE_ROOTS = ["ai"]                      # folders the coding tools may read
   AI_SYSADMIN_CHECK = "myapp.ai.is_admin"     # callable(user) -> bool    (default: superuser)
   AI_PERMISSION_CHECK / AI_AUDIT_HOOK / AI_FEATURE_GATE / AI_BASE_CURRENCY / AI_DEFAULT_CURRENCY / AI_EXCHANGE_RATE
   AI_LEGACY_SETTINGS_MODEL = "myapp.Setting"  # copy ai_*/speech_*/image_gen_* rows once into AISetting
   ```
3. **urls.py**: `path("", include("ai.urls"))`
4. **Migrate**: `python manage.py migrate`
5. **Set up**: `python manage.py ai_setup` (checks the wiring, creates `coding_agent/` outside the package; `--check` only reports).
6. Open `/api/settings/ai/` (admin) and configure the model; the chat endpoints are under `/api/financial-advisor/ai/`.

## Packs (optional)
A pack is a package with `pack.py` exposing `register(registry)`; list it in `AI_PACKS`. It can add data providers,
tools, actions, training families, URLs and extension hooks (`ai/packs/__init__.py`). WealthFlow's finance tools live in `core/ai_pack`.

## Not needed
No host models, templates, static files or settings are required. `AISetting` stores the AI settings in `ai_aisetting`.
Optional libraries (openpyxl, reportlab, python-docx, pypdf, Pillow, playwright) enable exports/browser tools; missing ones are reported by `ai_setup`.

## Checks
`python manage.py test ai` (the host-neutral tests) and `ai/tests/test_independence.py` (fails on any `ai -> host` import).
