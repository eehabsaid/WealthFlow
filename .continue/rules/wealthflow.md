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