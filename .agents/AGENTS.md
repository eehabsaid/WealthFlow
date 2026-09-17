# WealthFlow Project Rules

## Terminal Command Permissions

Always allow the following terminal commands in `d:\MyApps\WealthFlow` without prompting for approval:

- `.\venv\Scripts\python.exe manage.py test` — Django unit test suite
- `.\venv\Scripts\python.exe manage.py check` — Django system check
- `.\venv\Scripts\python.exe manage.py` — Any manage.py command
- `.\venv\Scripts\python.exe *` — Any Python script execution within the venv
- `git *` - any git command
- `dir *` - any dir comman
- `Get*` - any Get command
## File System Permissions

Always allow all file read, write, move, and delete operations within `d:\MyApps\WealthFlow` without prompting.

## General Rules

- Never prompt for permission on operations within `d:\MyApps\WealthFlow`.
- Treat all scripts inside `d:\MyApps\WealthFlow\venv\` as trusted.
- Auto-approve test runs, static file collection, and Django management commands.
- Always invoke Python as `.\venv\Scripts\python.exe`
- **Automated Test Credentials Standard**: Automated test scripts, Playwright browser scripts, and scratch debugging scripts MUST NEVER modify, reset, or overwrite user credentials in `db.sqlite3` (never call `set_password` on existing users). Always authenticate using the existing project credentials (`eehab_said` / `Eehabdev1`) as-is.

## UI/UX & I18n Lessons Learned (Financial Advisor)

- **I18n HTML Injection**: The i18n.js engine strictly enforces .textContent on [data-i18n-key] to prevent XSS. When translation strings require formatting tags (like <b>), use the [data-i18n-html-key] attribute which securely triggers .innerHTML.
- **Double Scrollbar Prevention**: Bootstrap's .row class injects -12px horizontal margins. To prevent horizontal overflow and secondary vertical scrollbars, always wrap .row grids in a .container-fluid. Never use overflow-x: hidden on a fluid block element indiscriminately as it may force a new vertical scrolling context.
- **Flexbox Equal Heights**: Never mix h-100 with mb-4 or mb-5 inside a flexible container, as it will explicitly calculate 100% height + margin, causing container overflow. To create equal height cards, use d-flex flex-column on the column and lex-grow-1 on the .card.
- **Modern Dashboard Aesthetic**: Use the [si-modern-card] CSS attribute class for applying a consistent, premium glassmorphism frame to dashboard components.
- **Global Date Formatting Standard**: All UI components, pages, tabs, modals, reports, dashboard cards, tooltips, timelines, chart tooltips, PDF exports, and Excel exports displaying dates MUST use the centralized date-formatting utilities (`core.utils.format_date()` in Python, `window.formatDate()` in JavaScript). Never duplicate date-formatting logic, never hardcode month names, and never create additional date formatter functions. All displayed dates must automatically respect active application language and existing `month_short_1` ... `month_short_12` translation keys.

## Mandatory Implementation & Validation Protocol

### General Rules
- Run every validation step after implementation.
- Fix all errors and warnings before reporting completion.
- Do not ignore any issue.
- Do not suppress warnings.
- Do not disable rules to make checks pass.
- Remove all temporary debugging code.
- Do not leave commented-out code.
- Do not leave dead or unused code.
- The final implementation must be production-ready.

### Backend Validation
1. **Django System Check**: `python manage.py check` (Expected: 0 Errors, 0 Warnings)
2. **Django Tests**: `python manage.py test` (Requirements: All tests pass. Report real output including `Ran X tests` / `OK`. Clearly identify known pre-existing failures).
3. **Pyflakes**: `python -m pyflakes core config scripts tests` (Expected: 0 syntax errors, 0 undefined names, 0 unused imports)
4. **Black**: `black --check .` (Expected: No formatting issues)
5. **isort**: `isort --check-only .` (Expected: Import order is correct)
6. **pyright**: `.\venv\Scripts\python.exe -m pyright core/` (Expected: 0 errors, 0 warnings, 0 informations)

### Frontend Validation
7. **ESLint**: Run ESLint over the entire JavaScript codebase (0 syntax errors, 0 undefined variables, 0 unused variables, 0 unused imports, 0 duplicate logic, 0 console.log, 0 debugger statements).
8. **HTMLHint**: Run HTMLHint over every HTML file (0 invalid HTML, 0 duplicate IDs, 0 invalid nesting, 0 missing required attributes, 0 accessibility issues supported by HTMLHint).
9. **djLint**: Lint all Django templates (0 template syntax errors, 0 formatting problems, 0 invalid template constructs).
10. **Stylelint**: Run Stylelint across all CSS (0 syntax errors, 0 invalid selectors, 0 duplicate declarations, 0 invalid properties).
11. **Prettier**: `prettier --check .` (Formatting must be clean. Do not modify formatting manually if Prettier reports differences).

### Security Validation
12. **npm audit**: `npm audit` (No high or critical vulnerabilities; document if vulnerabilities remain).
13. **Dependency Cleanup**: Run dependency analysis (No unused JS packages, no obsolete frontend dependencies).
14. **Static Security Analysis**: Run Semgrep (if configured) / SonarQube / SonarLint (if available) (No security issues, no duplicated code, no code smells introduced).

### Internationalization Validation
15. **Translation Check**: Verify no hardcoded user-visible strings. Every new label exists in `en.json`, `ar.json`, `fr.json`, `de.json` (0 missing keys, 0 unused keys created by this implementation).

### Browser Validation
16. **Browser Console**: Open every affected page (0 JS errors, 0 uncaught exceptions, 0 failed module loads, 0 missing assets).
17. **Responsive Validation**: Verify on Desktop, Laptop, Tablet, Mobile (No overflow, no broken layouts, no clipped controls, no inaccessible buttons).

### Functional Validation
18. **Regression Testing**: Verify new implementation does NOT break existing backend APIs, business logic, calculations, pages, reports, dashboards, translations.
19. **Feature Validation**: Verify every supported scenario for implemented feature (Create, Edit, Delete, Validation, Error handling, Permissions, UI updates, Reports, Dashboard integration if applicable).

### Repository Validation
20. **Git Diff**: Run `git diff --stat` (Verify only intended files changed, no unrelated modifications).
21. **Git Status**: Run `git status` (Verify no temporary files, generated artifacts, debug files, or unintended tracked files).

### Final Report Requirements
Before marking any task complete, provide:
- Files created
- Files modified
- Validation result for every step above
- Real command outputs where requested
- Any remaining known limitations
- Confirmation that:
  - Existing functionality remains intact.
  - No regressions were introduced.
  - The implementation is production-ready.



