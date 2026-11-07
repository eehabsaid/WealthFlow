# dev_agent for VS Code

Native front end for the standalone `dev_agent` coding agent. It has its own sidebar (Tasks, Plan, Progress, Changed files), native diff editors,
modal approval dialogs, an Output channel (`dev_agent`) and a status bar item. No webview. It starts and stops the Python agent itself
(a hidden `python -m dev_agent serve` bound to 127.0.0.1 with a random per-session token passed through the environment); you never start a server.

Settings: `devAgent.pythonPath`, `devAgent.projectRoot`, `devAgent.agentPath` (all optional; auto-detected).
Install: `npm install && npm run package`, then "Extensions: Install from VSIX...". Development: `npm test` (needs `python3` with the project requirements).
