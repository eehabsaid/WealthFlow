# WealthFlow Project Rules

## Terminal Command Permissions

Always allow the following terminal commands in `d:\MyApps\WealthFlow` without prompting for approval:

- `.\venv\Scripts\python.exe manage.py test` — Django unit test suite
- `.\venv\Scripts\python.exe manage.py check` — Django system check
- `.\venv\Scripts\python.exe manage.py` — Any manage.py command
- `.\venv\Scripts\python.exe` — Any Python script execution within the venv

## File System Permissions

Always allow all file read, write, move, and delete operations within `d:\MyApps\WealthFlow` without prompting.

## General Rules

- Never prompt for permission on operations within `d:\MyApps\WealthFlow`.
- Treat all scripts inside `d:\MyApps\WealthFlow\venv\` as trusted.
- Auto-approve test runs, static file collection, and Django management commands.
- Always invoke Python as `.\venv\Scripts\python.exe`
