# Runs the real-task batch for agent-loop training: about 100 tasks, one at a time, each in a throw-away copy of this repo (your files are never changed).
# Every plan is approved automatically (python -m ai.dev_agent run --yes): you are never asked. Nothing else is auto-approved - a protected file or a command that
# needs approval is refused, so a task can never stop to wait for you.
# Safe to stop with Ctrl+C: run it again and it continues where it stopped.
#   .\scripts\traj_run.ps1 --dry-run     show what would run
#   .\scripts\traj_run.ps1 --count 5     run only the next 5 tasks (a good first test)
#   .\scripts\traj_run.ps1               run every task that is not done yet
# The same thing without PowerShell: python scripts\traj_run.py [options]
Set-Location (Split-Path -Parent $PSScriptRoot)
python --version
if ($LASTEXITCODE -ne 0) { Write-Host "Python was not found: activate your virtual environment first."; exit 1 }
python scripts\traj_run.py @args
exit $LASTEXITCODE
