"""The behaviour switches of the agent (Settings > Behavior in the Web UI and the VS Code panel), saved in coding_agent/agent_settings.json.

Every switch is true/false. The first four are APPROVALS: true = the agent asks you (the strict behaviour of earlier versions), false = it goes ahead on its own.
Whatever the switches say, these stay blocked: secret files, git internals, forbidden files, hand-written migrations, git writes, commands on the project's deny
list, deleting or renaming a file that is not in the approved plan (that still asks you), destructive commands, installs, network and paths outside the project."""

from __future__ import annotations

from ai.dev_agent.settings.store import DEFAULTS, FLAGS, Settings, SettingsError

# key: (label, group, help)
SPEC = {
    "require_plan_approval": ("Ask me to approve the plan", "approvals",
                              "On: the agent waits for your OK after planning. Off: it runs right after planning (the plan is still shown and saved in the report)."),
    "ask_outside_plan": ("Ask before editing files outside the plan", "approvals",
                         "On: any file the plan does not list needs your OK. Off: it may edit or create extra files it finds it needs (deleting or renaming still needs the plan or your OK)."),
    "ask_other_commands": ("Ask before running commands not on the whitelist", "approvals",
                           "On: every command not on the project's allow list asks. Off: harmless ones run (destructive, install, network, outside-project and git-write commands still ask or stay blocked)."),
    "ask_protected_files": ("Ask before changing protected files", "approvals",
                            "On (recommended): files listed as protected in coding_agent/config.json (balances, salary, cash flow, billing, authentication) always ask. Off: they are changed without asking."),
    "deep_search": ("Deep search", "speed",
                    "Longer file reads (1,200 lines per call), more search and grep results, 3x bigger tool results and more room to repeat a lookup: finds the right files faster."),
    "quick_mode": ("Quick mode for small tasks", "speed",
                   "The plan is kept short (one or two steps) and runs right after planning (like turning the plan approval off), and the work is verified once instead of twice."),
    "light_verification": ("Lighter verification", "speed",
                           "Skips the line-limit and test-mapping checks that stop small tasks. Syntax checks, lint and tests that are mapped still run; the report says what was skipped."),
}
APPLIES = "to the next task (a task that is already running keeps the values it started with)"


def describe(data: dict) -> list[dict]:
    return [{"key": key, "label": label, "group": group, "help": text, "value": data[key], "default": DEFAULTS[key]} for key, (label, group, text) in SPEC.items()]


def _flag(key: str, raw) -> bool:
    if isinstance(raw, bool):
        return raw
    raise SettingsError(f"'{key}' must be true or false")


def apply(project, values: dict) -> dict:
    """Validate, write (atomic, via the settings store) and report the switches that changed. Unknown keys or non-booleans change nothing."""
    if not isinstance(values, dict) or not values:
        raise SettingsError("give the switches to change")
    unknown = sorted(str(k) for k in values if k not in FLAGS)
    if unknown:
        raise SettingsError(f"not a behavior switch: {', '.join(unknown)}")
    requested = {key: _flag(key, raw) for key, raw in values.items()}
    store = Settings(project)
    data = store.load()
    changed = [{"key": k, "label": SPEC[k][0], "old": data[k], "new": v} for k, v in requested.items() if data[k] != v]
    data.update(requested)
    if changed:
        store.save(data)
    return {"file": f"{project.agent_dir.name}/{store.path.name}", "changed": changed, "values": describe(data), "applies": APPLIES}
