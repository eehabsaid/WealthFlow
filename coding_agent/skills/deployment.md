# Deployment
- Local: Windows + PowerShell, `python manage.py runserver 8000`, Ollama for the AI (`setup-ollama.bat`, guide: `WealthFlow Deployment & Ollama Setup Guide.txt`).
- Production target: PythonAnywhere (env-driven hardening in `wealthflow/settings.py`; DEBUG and tracked `.env`/`db.sqlite3` are accepted only until selling).
- Scheduled work runs through `python manage.py run_automation` (purge of deleted accounts, rates, recurring transactions): it must be scheduled in the host's Tasks.
- Payments: Paymob (test mode + regional accounts); webhook is the only CSRF-exempt endpoint.
- Never push or commit from the agent. Deliver files + `COMMIT_MESSAGE.txt` + `IMPLEMENTATION_NOTES.txt`.
