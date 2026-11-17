# dev_agent - standalone autonomous coding agent (M1 core, M2 interfaces, M3 E2E + memory + recovery)

Python 3.12+. No Django. Project-specific rules live in `coding_agent/config.json`, not in code. In another Django project `python manage.py ai_setup` creates `coding_agent/` from `ai/coding_agent_template/` (see `ai/INSTALL.md`).

## Setup (once)
    pip install -r ai/dev_agent/requirements.txt        # keyring only; cryptography is already in WealthFlow's requirements
    python -m ai.dev_agent settings set provider ollama        # ollama | anthropic | openai | gemini
    python -m ai.dev_agent settings set model qwen3.8:27b-agent2
    python -m ai.dev_agent set-key anthropic                   # cloud providers only; hidden prompt; Ollama needs no key
Credentials: OS keyring first (Windows Credential Manager). If no usable keyring, an encrypted file at `%APPDATA%\dev_agent\secrets.enc`
(never inside the repo). Its key comes from a passphrase (scrypt, 12+ characters, fresh salt per save) and is never stored. Set
`DEV_AGENT_PASSPHRASE` for unattended runs.

## Use
    python -m ai.dev_agent plan "task"        # investigate read-only, print the plan, write nothing
    python -m ai.dev_agent run "task"         # plan -> you approve once -> execute -> verify -> report
    python -m ai.dev_agent execute <task-id>  # approve and run a saved plan, or resume a stopped task
    python -m ai.dev_agent status [task-id]   # list tasks / show a report (also recovers tasks a crash left running)
    python -m ai.dev_agent memory show|add|forget [architecture|decisions|lessons] [text]   # what the agent remembers
Run from anywhere inside the repo, or pass `--root <folder>`.

## Three interfaces, one engine (M2)
The CLI, the Web UI and the VS Code extension all drive the same `Agent`; each works on its own.
    python -m ai.dev_agent serve --open       # local server + Web UI; the address printed contains your private token (#token=...)
- **Web UI** (`ai/dev_agent/web`, plain HTML/JS/CSS, no build step): task, plan review/approve, live steps, diffs, Stop, provider/model/key settings, approvals.
- **VS Code extension** (`ai/dev_agent/vscode_extension`): a chat sidebar (webview) with the same UI as the Web UI: plan Approve/Reject, live steps, approvals,
  changed files (native diff editor), final report, model picker, file/image attachments (images only for vision models), Stop. It starts and stops the
  Python server itself. Install: `cd ai/dev_agent/vscode_extension && npm install && npm run package`, then VS Code > Extensions > ... > Install from VSIX.
  Settings: `devAgent.pythonPath` / `projectRoot` / `agentPath` (all optional).
- Server security: binds 127.0.0.1 only (exclusive port on Windows); bearer token on every /api call (extension: random per session via environment, never argv/logs);
  exact Host check (DNS rebinding), cross-site Origin refused, no CORS, JSON-only bodies, 1 MB limit, task ids validated, file/diff only for files recorded in the task,
  API keys never returned, strict CSP, the server exits if the editor that started it disappears.
- Stop (any interface) cancels the model request and kills the running command's whole process tree (Windows Job Object + `taskkill /T /F`; POSIX process group).
- Local API: `/api/tasks` (GET/POST), `/api/tasks/<id>` (+ `/events` JSON or SSE with Last-Event-ID, `/approve`, `/reject`, `/resume`, `/files`, `/diff?path=`,
  `/file?path=&version=original|current`, `/report`), `/api/stop`, `/api/approvals[/<id>]`, `/api/state`, `/api/settings`, `/api/keys[/<provider>|/unlock]`, `/api/models`, `/api/shutdown`.

## Browser E2E, memory, recovery (M3)
- **Browser E2E**: when a changed file matches `e2e.paths` in `coding_agent/config.json` (UI files), the final checks run `e2e.command` (default
  `python scripts/run_full_e2e.py`, optional `e2e.args`, `e2e.timeout_s` default 7200). It runs once, at the end, can take hours, and Stop cancels it. The command comes from
  config only. If it cannot run (script missing, Playwright not installed, Chromium missing) the step is **NOT RUN** with the exact reason, the report says
  NOT VERIFIED, and running it is left to you. A real failure goes back to the model like any other failed check.
- **Memory** (inside the repo, tracked by git): `coding_agent/memory/{tasks.jsonl, architecture.md, decisions.md, lessons.md}`. Written automatically from the ledger when a task ends
  (goal, files, check results; lessons from stops; decisions from refused approvals and rejected plans; added/removed/renamed files). Entries sharing words with a new task
  are put in its planning context (max 2000 characters). Never stores secrets (entries that look like one are refused); each file is capped at 150 entries.
  `MEMORY.md` stays the owner's own hand-written decisions file.
- **Crash/resume**: a run takes `tasks/<id>/run.lock` (process id), so two processes cannot run one task. If the process dies, the next `status`, `execute` or server start marks the task
  `stopped` ("interrupted ... Resume continues it"), marks the interrupted package, and makes the ledger match the files on disk. Resume repeats no finished package.
  Lock files and the event log also survive a crash (stale locks of dead processes are broken; a torn last log line no longer corrupts the next event).

## Context & limits, context meter, full trace
- **Context & limits** (Web UI and VS Code chat: the button next to the meter; in VS Code also "Context & limits…" in the key menu): every real context value in one place - context window, reserve, max output per reply, max tool result,
  max steps per phase, max fix rounds, model request timeout, command timeout - all stored in `coding_agent/agent_settings.json`. Each value is checked and kept inside its range;
  the two rules the engine needs are enforced (reserve <= window - 4,096; max output <= window); softer problems (a window that is mostly reserve, a reply cap above the reserve) are
  shown as warnings and never changed silently. The file is written atomically, the answer lists exactly what changed (old -> new, and when a value was clamped), values you did not touch
  are never rewritten, and they survive a restart. A new value applies to the next task (a running task keeps its own). API: `GET/PUT /api/settings/context`.
- **Context meter** (under the chat box, one per session): after every model step the engine writes a `context` event and the meter shows used / window and what is left before the agent
  trims old steps. Used = what the provider reported for the last call; if it reports nothing, or Ollama's prompt cache makes the number far too low, the agent's own estimate is shown and the
  tooltip says which one it is. Orange at 80% and red at 95% of the usable part (window - reserve); the agent starts trimming old steps at 100%.
- **Full trace in `tasks/<id>/events.jsonl`** (`type: "trace"` events, written for every new task): per phase the exact system prompt and first message, how the provider was called, every model reply
  exactly as received (with token usage), every tool call with its FULL result and the exact text sent back to the model, nudges, trimming (`compact`) and how the phase ended. Everything passes
  the redactor (`core/redact.py`) first: secrets always; emails, phone numbers and currency amounts; plain numbers, dates, ids, versions, paths and git hashes are kept (a bug that masked
  plain amounts and long numbers is fixed). `service/trajectory.py` rebuilds the conversations from these events; the trajectory extractor (`ai/training/README.md`) is its first user.
- **Auto-approve for batches**: `python -m ai.dev_agent run --yes "<task>"` (and `execute --yes <id>`) approves the plan without asking, so a list of tasks runs with nobody typing y. It approves the
  PLAN only: a protected file or a command that needs approval still needs your answer in a terminal, and when there is none (a batch, stdin closed) it is refused - a task never waits for you.
- `grep` no longer searches `coding_agent/tasks` (the agent's own logs and earlier answers), so a question cannot find its own history.

## Rules enforced in code (each has tests)
- Nothing is written before the plan is approved; only files listed in the plan may change; delete/rename only if listed.
- Protected files (config.json) ask you first; forbidden files (migrations, db.sqlite3, .env, secrets, .git) are never edited or read.
- Git is strictly read-only: status, diff, log, show, blame, ls-files, rev-parse ... Everything else, and any option that can write, is blocked and cannot be approved.
- Commands run as argv (no shell). Whitelisted ones run, unknown/destructive/install ones ask, `&& | > ;` and shells (cmd, powershell, bash, wsl) are blocked.
- Multi-file edits are all-or-nothing on validation, SHA-checked at read time and again under locks right before writing; a write failure rolls back; the result lists each file's exact state.
- 3 failed fix attempts on the same error -> stop and report. Work is split into packages that fit the context window (window minus reserve, both in Context & limits).
- The report says VERIFIED only when every applicable check ran and passed AND an automated test (Django, pytest or browser E2E) passed; lint alone is "NOT VERIFIED (no automated test ran)". It shows counts (passed / failed / skipped / not run), a per-test line and an explicit "Browser E2E" line (NOT PERFORMED, NOT RUN with the reason, PASSED or FAILED).
- `coding_agent/` (config, safety rules, skills, memory, task history) is agent-internal: tasks cannot edit, create, delete or rename it, and plans listing it are rejected. Reading is allowed; memory and settings are written only by the agent's own commands.
- A work package can only change files in its own step list: a file listed only in another package is refused (shared or unlisted files stay allowed; the single plan approval is unchanged).
- Every changed .py file needs a test mapping (`test_areas` Django module, `pytest_areas` pytest path, test files and `test_exempt` excepted). Unmapped files are listed by name in a `test mapping` row (NOT RUN), so the result can never be VERIFIED.
- Memory keeps verified facts only: kinds architecture, decisions, lessons, rules (confirmed business rules). The `remember` tool stages a finding with the files read as evidence; it is saved only when the task completes or is answered. Near-duplicates, guesses ("probably...") and secrets are refused; emails and long numbers are redacted. Existing memory files stay valid.

## Tests
    python -m pytest ai/dev_agent/tests -q
    cd ai/dev_agent/vscode_extension && npm test              # extension: real Python server + fake Ollama; extension code against a mocked `vscode`; the real chat UI in Chromium under the webview CSP
Scripted fake models only: no real Ollama/cloud model, real keyring, Windows or real VS Code is exercised by them.
Windows-only test to run on your PC: `python -m pytest ai/dev_agent/tests/test_cancel.py -k windows -v` (Stop kills cmd/python grandchildren).
Browser tests (`test_web_e2e.py`) need Playwright + Chromium and skip themselves otherwise.
The real `scripts/run_full_e2e.py` is never started by the tests (they use a stand-in script); run it yourself once on your PC.

## A change request is never finished by words
`engine/intent.py` reads the task text: an imperative edit goal ("Add a one-line module docstring at the top of ...") needs a plan. If the model answers `final` instead,
it is asked again (up to 3 times) and then the task stops as `FAILED: the model claimed the task was done without a plan or an edit`. An approved plan whose run changed no
file also ends `FAILED`, never `completed`. A change task that is really already done may answer `NO CHANGE NEEDED: <why> | EVIDENCE: <path>: <exact text>`; it is accepted only when that text is in that file (checked, not believed). The same refusal applies to any answer that says "I added/updated/fixed ..." in the read-only planning phase, whatever the task wording. A question, or a task that says "Answer only; do not plan ...", is still answered directly without a plan.
