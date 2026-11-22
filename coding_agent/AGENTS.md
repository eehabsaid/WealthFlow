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
- See `.agents/AGENTS.md` section "Financial Commitments Calendar — Standing Rules" before touching that feature (it is read-only: never post expenses or change balances from it).
- For every new page, tab, feature, or significant UI change, follow `.agents/AGENTS.md` section "Documentation & Testing Deliverables — Standing Rules for Every New Page, Tab, Feature, or Significant UI Change" (unit tests, browser E2E, inventory registration, real screenshot capture, 4-language guide, AI Agent doc support).
