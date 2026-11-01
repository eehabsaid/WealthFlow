# Testing
- Django tests: `core/tests/<area>/test_*.py`; run `python manage.py test core.tests.<area>` (targeted first, then the full suite). One known sandbox-only failure: the Playwright single-page-failure-isolation test; known on main: `test_speech_api` Arabic Piper test.
- Users in tests get currencies/categories automatically: use `get_or_create`, not `create`.
- Static checks: `python -m pyflakes core tests scripts wealthflow doc_engine manage.py`, `npm run validate`, `python manage.py check`, `makemigrations --check`.
- Browser E2E: `scripts/run_full_e2e.py --headless` on the owner's PC only. Every change adds a module under `tests/modules/<name>.py`, wired in `scripts/e2e_module_dispatch.py`, `scripts/test_ui_human_full_e2e.py` and `tests/core/reporter.py` (page denominators).
- Never claim a test passed unless its command finished successfully; say plainly what was NOT run.
- Automated gate: `python scripts/agent_verify.py` (checks, targeted tests, pyflakes, migrations, i18n, line limits).
