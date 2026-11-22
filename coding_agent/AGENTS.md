# WealthFlow - rules for the coding agent

These rules are loaded into every conversation of `ai/dev_agent` (see `rules_files` in `coding_agent/config.json`). Edit them like any file; the agent never writes this file.

## Platform and commands
- Windows 11 is the primary platform (PowerShell/cmd). Use `python`, not `python3`.
- Django checks: `python manage.py check`; tests: `python manage.py test` (all) or `python manage.py test <module>`; lint: `python -m pyflakes <files>`.
- Never commit, push, stash, create or switch branches. Git is read-only.
- `python manage.py makemigrations` is allowed; never write or edit a migration by hand.

## Protected areas
- Ask before touching anything that affects balances, salary or cash flow (balance, salary, cash-flow, billing, authentication code). You may read and investigate them and propose a change with `note_proposal`.
- `db.sqlite3` is tracked on purpose so the real data can be inspected: read it, never modify it. Never reset or change user passwords.

## Done means
- New or changed behaviour has new or updated tests (Django tests, and the browser E2E suite for UI changes), the relevant tests pass, and `python -m pyflakes` is clean.
- README/Settings > Documentation are updated when behaviour changes.
- Fix any bug you find on the way, even out of scope, and say so in the final summary. Stop after 3 failed fix attempts on the same error and report it.
- State plainly what you could not run (real browser, Windows, real model).

## Feature standing rules
- Financial Commitments Calendar (Financial Advisor tab) is READ-ONLY: never post expenses, change balances or write to any model from it. Full rules: `.agents/AGENTS.md`, section "Financial Commitments Calendar — Standing Rules".
- Every new page, tab, feature or significant UI change needs ALL six, and is not done until they are verified:
  1. Django unit tests in `core/tests/...` (service + API), plus a Node test for non-trivial JS date/calculation helpers.
  2. A browser E2E module `tests/modules/<feature>.py`, registered in `scripts/e2e_module_dispatch.py` and in the `--module` choices of `scripts/test_ui_human_full_e2e.py`; it must assert real rendered content (not just that a button exists) and be run.
  3. Route/tab registered in `ai/doc_engine/inventory.json` (`id` = the DOM tab id).
  4. A real screenshot from `python scripts/generate_docs.py --lang en --theme dark` in `docs/screenshots/` (never a placeholder or the wrong tab).
  5. English `purpose` + `steps` for `route::tab` in `ai/doc_engine/content/page_descriptions.json` (the engine translates to ar/fr/de) and all i18n labels in en/ar/fr/de.
  6. Keep these rules and `.agents/AGENTS.md` consistent with the doc-engine workflow.
