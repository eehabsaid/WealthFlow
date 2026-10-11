---
name: WealthFlow rules
alwaysApply: true
---

# WealthFlow project rules
- Stack: Django backend, vanilla JavaScript single-page app. I use Windows and PowerShell.
- Never edit `db.sqlite3` or `.env`. Never print or expose secrets, API keys or password hashes.
- Only change files related to the task. Do not create new routes, templates or files unless I ask.
- Django tests go in `core/tests/<area>/`. Every change needs a test. Run `python manage.py test <module>` after each change and show me the result.
- Every new user-visible text needs a key in `static/i18n/en.json`, `ar.json`, `fr.json` and `de.json`, with identical placeholders.
- Do not rename or change shared services such as currency conversion, base currency or settings access. Only add to them, and list every caller first.
- No `print`, no `console.log`, no commented-out code.
- When asked to investigate, answer only from files you actually read. Name the file paths. Say what you could not find. Do not invent routes, files or functions.
- Do not change anything until I say "implement".
## Feature Development and Regression Prevention
- Before implementation, inspect the relevant backend, frontend, API routes, templates, JavaScript, CSS, translations, models, settings, services, and existing tests. Follow the actual call chain; do not assume how the application works.
- First provide an implementation plan listing the files to change, existing behavior to preserve, dependencies and callers affected, risks, and the tests required. Do not edit anything until I explicitly say "implement".
- Implement only the approved feature and necessary supporting changes. Preserve unrelated behavior and existing public interfaces. Do not refactor unrelated code.
- Before editing, inspect the working-tree changes and avoid overwriting or reverting existing user changes. Never commit, push, or work directly against GitHub.
- Add or update automated tests for every changed behavior, including success cases, validation, permissions, errors, and relevant regression cases.
- Backend: test API behavior, authentication and authorization, validation, persistence, error handling, and business rules as applicable.
- Frontend: test JavaScript behavior, API integration, loading states, empty states, errors, user interactions, and translations as applicable.
- UI/E2E: use the existing browser-testing framework if available. Verify the actual user flow from the UI through the backend and back, including relevant Arabic/RTL behavior and other supported languages. Do not claim E2E testing was performed unless it actually ran.
- Inspect existing test and browser-testing tools before choosing commands or adding dependencies. Do not introduce new testing frameworks without my approval.
- Run the targeted tests first, then the relevant broader test suite. Run existing lint, formatting, and static checks applicable to changed files.
- Review the final diff for unrelated edits, security issues, regressions, missing translations, and accidental changes to shared services.
- If a test fails, investigate and fix failures caused by the changes. Clearly distinguish pre-existing failures, environment limitations, skipped tests, and tests that were not run.
- Never claim a test passed unless its actual command completed successfully. Never claim full E2E verification when only unit tests or mocked API tests ran.
- At completion, report changed files, behavior implemented, exact test commands and results, E2E/UI coverage, known limitations, and any manual verification still required.
- Do not modify `db.sqlite3` or `.env`, expose secrets, or commit/push changes.
## Work Log Requirements
- At the start of every new feature task, read `.continue/AI_WORK_LOG.md` and verify relevant information against the current code.
- After an approved implementation, update `.continue/AI_WORK_LOG.md` with verified changes, files changed, test results, unresolved issues, and next steps.
- Before implementation, do not modify the work log; first present the investigation and wait for approval.
- Never claim tests passed unless they actually ran successfully.
- Keep the log concise and never record secrets.
## File Size and Code Organization
- Every new or modified code file must not exceed 200 lines of code.
- Before editing a file, check its current line count and plan changes to keep it within the 200-line limit.
- If a file would exceed 200 lines, split the implementation into smaller, cohesive modules rather than exceeding the limit.
- Place new files in the appropriate existing domain folders, following the project's current architecture and naming conventions.
- Avoid unnecessary files, duplicated logic, and artificial splitting solely to satisfy the line limit.
- After implementation, verify the line count of every new or modified code file and report the results.
- If the limit cannot be met without compromising correctness or architecture, stop and explain the issue before proceeding.