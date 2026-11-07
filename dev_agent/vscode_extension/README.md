# dev_agent for VS Code

A chat sidebar (webview) for the standalone `dev_agent` coding agent, laid out like Continue / Zoo Code: the conversation (plan with Approve/Reject, live steps and
tool calls, commands, check results, changed files, approvals, final report) above, the composer below (model chip, attach file, attach image, Send, Stop).
Changed files open in VS Code's native diff editor. The extension starts and stops the Python agent itself (a hidden `python -m dev_agent serve` on
127.0.0.1 with a random per-session token passed through the environment); you never start a server, and closing the window stops it and any running command.

The chat UI is the same code as the Web UI (`dev_agent/web`), copied into `media/chat` at build time. The page has a strict CSP with no network access;
it talks to the extension host by postMessage only. The host holds the token and API keys and allows a fixed list of requests. API keys are typed into
VS Code's own masked input box (command "dev_agent: Set API key" or the key button in the model picker) and go to the OS keyring, never into the page.

Settings: `devAgent.pythonPath`, `devAgent.projectRoot`, `devAgent.agentPath` (all optional; auto-detected). The model picker writes the shared settings file
(same as the CLI and Web UI); "only for the next task" overrides it for one task.
Install: `npm install && npm run package`, then "Extensions: Install from VSIX...". Development: `npm test` (needs `python3` with the project requirements;
the Chromium test needs Playwright and is skipped without it).
