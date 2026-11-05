# Task 20261105-105633-explain-what-dev-agent-guard-c
Goal: Explain what dev_agent/guard/commands.py does and list which files would need to change to also block the 'npm' command. Do not plan anything else.
Status: ANSWERED

## Answer (no file changes were made)
dev_agent/guard/commands.py is a pure-function command guard that classifies a single command line (argv) as allow / ask / deny before it may run. It: (1) split_command() parses one line with shlex (no shell), rejecting newlines and shell operators; (2) exe_name() normalizes argv[0] (strips .exe/.cmd etc., maps python3/py to 'python'); (3) classify() then applies a decision ladder — deny shell WRAPPERS (cmd, powershell, bash, sudo, ...); treat git as STRICTLY read-only via _git() (only GIT_READ subcommands, blocks write-capable flags); check the project's deny list (_prefix against commands['deny']); flag 'ask_args' tokens; _path_escape() to ask when a path/URL leaves the project root; then allow-list, ask-list, DESTRUCTIVE set (ask), INSTALLERS set (ask), and default to ask. A deny can never be overridden.

Regarding npm: it is ALREADY handled — 'npm' is in the INSTALLERS set (line 19) and classify() returns ask() for it (line 132). So npm is not silently allowed; it requires approval.

To actually BLOCK (deny) npm instead of asking, the only file that needs to change is dev_agent/guard/commands.py: add an explicit deny for 'npm' (e.g. a check in classify() before the INSTALLERS branch, or a new BLOCKED set) and remove it from INSTALLERS. If there are guard tests, they would need updating — check for a test module (e.g. dev_agent/guard/test_commands.py or similar) and add/adjust a case asserting npm is denied. No other source files depend on this behavior.

## Work done

## Files changed (exact state)
- none

## Verification
Overall: NOT VERIFIED - the final checks did not run (the task did not finish).

## Not run / open issues
- Browser E2E, real model quality and anything not listed above as PASSED were not verified by this run.

Tokens (as reported by the provider): in 6804, out 574
