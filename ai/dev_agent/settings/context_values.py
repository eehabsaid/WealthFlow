"""The context-related values of the agent as one table: what each is, its allowed range, and the single place that changes them.

All eight live in coding_agent/agent_settings.json (coding_agent/config.json holds project rules: its only numbers are max_file_lines, a code-size rule,
and e2e.timeout_s, the browser-test timeout, neither of which is context). `apply()` is what the Web UI and the VS Code extension call: every value is
clamped into its range, the two rules the engine really needs are enforced, the file is written atomically, and the answer lists what changed.

Hard rules (the agent would not start otherwise), checked only for the values a request touches, so saving one value never rewrites another:
  * reserve_tokens <= context_window - MIN_USABLE  (the settings loader already demands reserve < window; the system prompt alone is ~0.9k tokens and
    one task plus a few tool results need a few k, below MIN_USABLE every work package overflows)
  * max_output_tokens <= context_window
Softer findings are only reported as `warnings`, never clamped: a window that is mostly reserve (the agent trims old steps at window - reserve) and a
reply cap bigger than the reserve (a maximum-size reply may not fit). Values already saved are never changed unless the request touches them."""

from __future__ import annotations

from ai.dev_agent.settings.store import DEFAULTS, Settings, SettingsError

MIN_USABLE = 4096   # window - reserve: what the agent may fill before it starts trimming old steps
LOW_SHARE = 0.25    # warn when the usable part is below this share of the window

# key: (label, group, unit, min, max, help)
SPEC = {
    "context_window": ("Context window", "context", "tokens", 4096, 2_000_000,
                       "Tokens the model sees per request (sent to Ollama as num_ctx). Must not exceed what the model and GPU really support."),
    "reserve_tokens": ("Reserve for reasoning", "context", "tokens", 1000, 1_999_000,
                       "Kept free for the reply and final checks. The agent trims old steps once used tokens pass window minus this."),
    "max_output_tokens": ("Max output per reply", "limits", "tokens", 256, 2_000_000,
                          "Cap on one model reply. A tool call cut off at this limit stops the task, so keep it above your biggest edit."),
    "max_tool_result_chars": ("Max tool result", "limits", "characters", 500, 200_000,
                              "A tool result longer than this is cut (start and end kept) before the model sees it."),
    "max_steps_per_package": ("Max steps per phase", "limits", "steps", 1, 1000,
                              "Model calls allowed in one phase (planning, one work package, one fix attempt)."),
    "max_fix_rounds": ("Max fix rounds", "limits", "rounds", 1, 100,
                       "How many times failed checks go back to the model before the task stops."),
    "timeout_s": ("Model request timeout", "time", "seconds", 30, 86_400, "How long one model request may take."),
    "command_timeout_s": ("Command timeout", "time", "seconds", 10, 86_400, "How long one test or lint command may run."),
}
APPLIES = "to the next task (a task that is already running keeps the values it started with)"


def _number(key: str, raw) -> int:
    if isinstance(raw, bool) or raw is None:
        raise SettingsError(f"'{key}' must be a number")
    try:
        number = float(raw.strip().replace(",", "")) if isinstance(raw, str) else float(raw)
    except (ValueError, TypeError) as exc:
        raise SettingsError(f"'{key}' must be a number") from exc
    if number != number or number in (float("inf"), float("-inf")):
        raise SettingsError(f"'{key}' must be a finite number")
    return int(round(number))


def warnings(data: dict) -> list[str]:
    """Findings about the saved values (not errors): what the engine will do with them."""
    window, reserve, out = data["context_window"], data["reserve_tokens"], data["max_output_tokens"]
    usable, found = window - reserve, []
    if usable < window * LOW_SHARE:
        found.append(f"Only {usable:,} of {window:,} tokens can be used before the agent trims old steps: {reserve:,} are reserved. "
                     f"Long tasks will lose earlier steps (reserve is meant to be about 15-20% of the window).")
    if out > reserve:
        found.append(f"A reply may be up to {out:,} tokens but only {reserve:,} are reserved for it, so a maximum-size reply can overflow the window.")
    return found


def describe(data: dict) -> list[dict]:
    return [{"key": key, "label": label, "group": group, "unit": unit, "min": low, "max": high, "help": text, "value": data[key], "default": DEFAULTS[key]}
            for key, (label, group, unit, low, high, text) in SPEC.items()]


def _clamp(data: dict, requested: dict) -> dict[str, str]:
    """Put `requested` into `data` (ranges, then the hard rules for the touched values). Returns {key: why it differs from what was asked}."""
    notes: dict[str, str] = {}
    for key, wanted in requested.items():
        low, high = SPEC[key][3], SPEC[key][4]
        data[key] = min(max(wanted, low), high)
        if data[key] != wanted:
            notes[key] = f"allowed range is {low:,} to {high:,}"
    window = data["context_window"]
    if ("context_window" in requested or "reserve_tokens" in requested) and data["reserve_tokens"] > window - MIN_USABLE:
        data["reserve_tokens"] = max(SPEC["reserve_tokens"][3], window - MIN_USABLE)
        notes["reserve_tokens"] = f"window minus reserve must stay at least {MIN_USABLE:,} or the agent cannot hold a task"
    if ("context_window" in requested or "max_output_tokens" in requested) and data["max_output_tokens"] > window:
        data["max_output_tokens"] = window
        notes["max_output_tokens"] = "one reply cannot be bigger than the whole window"
    return notes


def apply(project, values: dict) -> dict:
    """Validate, clamp, write (atomic, via the settings store) and report. Raises SettingsError for unknown keys or non-numbers and changes nothing."""
    if not isinstance(values, dict) or not values:
        raise SettingsError("give the values to change")
    unknown = [str(key) for key in values if key not in SPEC]
    if unknown:
        raise SettingsError(f"not a context value: {', '.join(sorted(unknown))}")
    requested = {key: _number(key, raw) for key, raw in values.items()}
    store = Settings(project)
    data = store.load()
    before = {key: data[key] for key in SPEC}
    notes = _clamp(data, requested)
    changed, unchanged = [], []
    for key in SPEC:
        row = {"key": key, "label": SPEC[key][0], "old": before[key], "new": data[key]}
        if key in requested:
            row |= {"requested": requested[key], "clamped": data[key] != requested[key], "note": notes.get(key, "")}
        elif key in notes:   # moved only because a hard rule followed another value (e.g. the reserve followed a smaller window)
            row |= {"clamped": True, "note": notes[key]}
        if data[key] != before[key]:
            changed.append(row)
        elif key in requested:
            unchanged.append(row)
    if changed:
        store.save(data)
    return {"file": f"{project.agent_dir.name}/{store.path.name}", "changed": changed, "unchanged": unchanged, "values": describe(data),
            "warnings": warnings(data), "applies": APPLIES}
