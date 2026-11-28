# AGENTS.md — Rules for the Hermes agent (WealthFlow)

These rules apply to every session of the Hermes agent in this repo. `coding_agent/` is shared with the other local agent and is the single source of truth for memory and task logs.

## Communication
- Answers short, plain, focused. The user is non-technical: give PowerShell commands only.
- Ask all questions at the START of a task (max 3). Never ask after finishing.
- Show ONE plan, wait for approval, then do everything in one go without stopping.

## Git
- Git is read-only: never commit, push, stash, branch, reset, checkout or clean.
- Before starting, run `git fetch` and tell the user if the local repo is behind origin/main.
- Never trust memory for repo state (what's done, line counts). Always check the live code.

## Protected areas
- Stop and ask before changing anything that touches balances, salary, cash flow, billing or auth. Investigating and proposing is allowed.
- Migrations: use `.\venv\Scripts\python.exe manage.py makemigrations` only. Never write or edit migration files by hand.
- Delete or rename files only if listed in the approved plan.
- Ask before installing anything, destructive commands or system changes.
- Bugs found while working (even out of scope): fix them and report them, except in protected areas.

## Data
- db.sqlite3 is tracked on purpose. Read it to check real data. Never say you can't see it.
- Expected results must come from real data or code, never guessed. Never loosen tests, judges or gates without asking.

## Code rules
- Every code file (py/js/css/html) is max 200 lines. Split if needed.
- Python splits: package folder + `__init__.py` re-exporting everything (keeps mock.patch paths). Short sibling names, absolute imports. Watch for flat-file vs package name collisions.
- `management/commands` files stay flat; heavy logic goes to `core/services/`.
- JS splits: put 2+ related files in `static/js/<domain>/`, replace the old `<script>` tag with the new ones at the same position in `templates/index.html`. Use plain function names when called across files.
- CSS splits: `index.css` with `@import`; check every path exists.
- No hardcoded user-visible text: add every new label to en/ar/fr/de.json.
- No dead code, commented-out code, print/console.log, or hardcoded config.

## Every change must also
1. Update Django tests so `.\venv\Scripts\python.exe manage.py test` covers it.
2. Update the E2E UI test suite (scripts/run_full_e2e.py) for UI changes.
3. Update Settings > Documentation (screenshots and generated docs).

## Validation (run once at the end, report each result)
1. `.\venv\Scripts\python.exe manage.py check`
2. `.\venv\Scripts\python.exe manage.py test`
3. `.\venv\Scripts\python.exe -m pyflakes .`
4. ESLint
5. HTML validation
6. CSS validation
7. i18n keys in all 4 languages
8. Security untouched (auth/CSRF/sessions)
9. Code quality
10. `git diff` shows only intended files
11. Final report: files changed, results, what was NOT run and why.
- Also run the extra validators listed in .agents/AGENTS.md (black, isort, pyright, Prettier, HTMLHint, djLint, Stylelint, npm audit).
- Max 3 failed fix attempts on the same error, then stop and report.
- Revert incidental changes to ai_knowledge/ and db.sqlite3 caused by test runs.
- Never claim E2E passed unless it was actually run.

## Finish
- Give a short commit message in chat. The user commits and pushes themselves.

## coding_agent/ memory and task log
- At the start of every task, read all files in `coding_agent/memory/` and check recent folders in `coding_agent/tasks/` for related past work.
- Use them as reminders, not truth: re-check live code and data whenever accuracy matters.
- Create a task folder only when given a real task: `coding_agent/tasks/<YYYYMMDD-HHMMSS>-<goal-slug>/` with the SAME files and format as existing folders (`ledger.json`, `events.jsonl`; `report.md` when done).
- Open 2-3 existing task folders first and copy their structure exactly. Add `"agent": "hermes"` to `ledger.json`.
- Never delete or rewrite other agents' task folders.
- Log every step in events.jsonl: your text, each tool call, and its FULL output — every trace must include the complete tool result, not a summary (the log is used for model training).
- Compute `sha_before` / `sha_now` as SHA-256 hex (64 chars) of the file's raw bytes, and `plan_sha` as SHA-256 of `json.dumps(plan, sort_keys=True)` (UTF-8) — the same way the existing ledgers do (`ai/dev_agent/ledger/plan.py`, `ai/dev_agent/core/fsutil.py`). Never write fake or empty hashes.
- Set `status` and `stop_reason` honestly: completed / rejected / failed / cancelled. Add `report.md` when done.
- When a task ends, append its one-line record to `coding_agent/memory/tasks.jsonl` in the same format as existing lines (`id, date, goal, status, files, reason, checks`).
- Update `coding_agent/memory/` with new decisions, results and lessons: edit existing entries, never duplicate, keep the same file format.
- Keep the `YYYY-MM-DD: ` prefix on every new memory line.
- Do not use Hermes's own memory as the main source; `coding_agent/` is the single source of truth.
