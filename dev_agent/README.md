# dev_agent - standalone autonomous coding agent (Milestone 1: command line)

Python 3.12+. No Django. WealthFlow-specific rules live in `coding_agent/config.json`, not in code.

## Setup (once)
    pip install -r dev_agent/requirements.txt        # keyring only; cryptography is already in WealthFlow's requirements
    python -m dev_agent settings set provider ollama        # ollama | anthropic | openai | gemini
    python -m dev_agent settings set model qwen3.8:27b-agent2
    python -m dev_agent set-key anthropic                   # cloud providers only; hidden prompt; Ollama needs no key
Credentials: OS keyring first (Windows Credential Manager). If no usable keyring, an encrypted file at `%APPDATA%\dev_agent\secrets.enc`
(never inside the repo). Its key comes from a passphrase (scrypt, 12+ characters, fresh salt per save) and is never stored. Set
`DEV_AGENT_PASSPHRASE` for unattended runs.

## Use
    python -m dev_agent plan "task"        # investigate read-only, print the plan, write nothing
    python -m dev_agent run "task"         # plan -> you approve once -> execute -> verify -> report
    python -m dev_agent execute <task-id>  # approve and run a saved plan, or resume a stopped task
    python -m dev_agent status [task-id]   # list tasks / show a report
Run from anywhere inside the repo, or pass `--root <folder>`.

## Rules enforced in code (each has tests)
- Nothing is written before the plan is approved; only files listed in the plan may change; delete/rename only if listed.
- Protected files (config.json) ask you first; forbidden files (migrations, db.sqlite3, .env, secrets, .git) are never edited or read.
- Git is strictly read-only: status, diff, log, show, blame, ls-files, rev-parse ... Everything else, and any option that can write, is blocked and cannot be approved.
- Commands run as argv (no shell). Whitelisted ones run, unknown/destructive/install ones ask, `&& | > ;` and shells (cmd, powershell, bash, wsl) are blocked.
- Multi-file edits are all-or-nothing on validation, SHA-checked at read time and again under locks right before writing; a write failure rolls back; the result lists each file's exact state.
- 3 failed fix attempts on the same error -> stop and report. Work is split into packages that fit the context window (150K minus a 28K reserve).
- The report says VERIFIED only when every applicable check ran and passed; anything not run is listed.

## Tests
    python -m pytest dev_agent/tests -q
Scripted fake models only: no real Ollama/cloud model, real keyring, Windows or VS Code is exercised by them.
