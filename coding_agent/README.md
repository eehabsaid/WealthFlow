# Coding agent (phases 1-2)
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
