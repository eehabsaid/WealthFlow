# Coding agent (phases 1-3)
Files here are read by the scripts in `scripts/` (VS Code / Continue / Zoo Code) and by the sysadmin's Agent mode in the app.
- `config.json`: protected files and the test package of each folder (edit it, no code change).
- `skills/*.md`: how this project works, one topic per file.
- `MEMORY.md`: decisions that survive between sessions.
Commands (run from the project folder):
- `python scripts/agent_index.py [query]`: search the auto-built repo index.
- `python scripts/agent_context.py "task text"`: the skills, decisions and files relevant to a task, cut to a size.
- `python scripts/agent_plan.py file1 file2`: protected files, callers, tests and line counts before you change them.
- `python scripts/agent_verify.py [files...] [--full]`: checks, targeted tests, pyflakes, migrations, i18n, line limits.
- `python scripts/agent_memory.py add "text"` / `list`.
Agent mode tools (sysadmin, local dev server only for edits): `app_propose_edit` (card, nothing written until Confirm), `app_run_checks`, `app_git_diff`.
Phase 3 (coding-only training, separate from business training): `training.json` holds the settings.
- `python scripts/agent_train.py --stages dataset [--limit N] [--no-verify]`: verified examples from git history (a change counts only if its Django tests pass on that commit; every 5th goes to the held-out set).
- `--stages train`: needs at least `min_examples` verified examples, fine-tunes in WSL, registers `<current model>-coder`; never switches the app model.
- `--stages evaluate`: runs the old and the new model on the held-out tasks, applies each patch and runs the real tests; reports correctness, regressions, protected-file touches, speed.

## Standalone agent (`dev_agent/`, M1)
An autonomous coding agent that works on this repo from the command line; independent of Django, the database and WealthFlow's AI settings.
- It reads this folder: `config.json` (protected/forbidden files, commands, verify steps, test areas), `skills/`, `MEMORY.md`.
- It writes here: `agent_settings.json` (provider/model, no secrets), `tasks/<id>/ledger.json` and `report.md`.
- Credentials are never here: OS keyring, or an encrypted file outside the repo (`%APPDATA%\dev_agent\secrets.enc` on Windows).
- Details and commands: `dev_agent/README.md`.
