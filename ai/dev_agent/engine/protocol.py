"""The plain-text JSON protocol every model speaks (so no provider or model needs special handling), the prompts, and a tolerant parser."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from ai.dev_agent.tools import REGISTRY, specs

RULES = """You are an autonomous software-development agent working inside a local project through tools.
Reply with EXACTLY ONE JSON object per message and nothing else:
  {"tool": "<name>", "args": {...}}      call a tool
  {"final": "<short summary>"}           when the current job is finished
Rules:
- Read a file before you edit it. Make related edits for several files in ONE edit_files call when the JSON payload fits comfortably within the output limit. Keep `old` text short but unique; never emit a partial or truncated tool call.
- Never claim anything is verified: the system runs the checks and reports the real results. In your summary say what you did and what you did not check.
- Guards decide what is allowed. Never try to work around a refusal. Protected files need the owner: if you are refused, use note_proposal to describe the fix and continue with the rest.
- Never hand-write or edit migrations (use `python manage.py makemigrations`). Git is read-only. One command per run_command, no shell operators.
- Keep tool output small: read line ranges, grep narrowly, do not repeat the same call.
- When you CONFIRM something lasting by reading code (structure, a business rule, a lesson), keep it with `remember` and the files you read as evidence. Never remember guesses.
- Follow the project's skills and decisions given below."""

PLAN_FORMAT = """Investigate with the read-only tools, then reply with:
{"plan": {"summary": "...", "steps": [{"title": "...", "files": ["files this step reads or changes"]}],
 "files_add": [], "files_edit": [], "files_delete": [], "files_rename": [{"from": "a", "to": "b"}],
 "tests": ["tests to add or update (paths) and what to run"], "risks": ["..."]}}
List EVERY file you will add, edit, delete or rename: nothing outside the plan may be changed later. Deleting or renaming only works if listed.
If the task is only a question or needs no file changes, answer it with {"final": "your answer"} instead of a plan."""


@dataclass
class Action:
    kind: str                 # tool | final | plan | invalid
    payload: object = None    # tool: (name, args) ; final: text ; plan: dict ; invalid: reason


def system_prompt(readonly: bool) -> str:
    return f"{RULES}\n\nTools:\n{specs(readonly)}"


THINK = re.compile(r"<think>.*?(?:</think>|\Z)", re.S | re.I)
ARG_KEYS = ("args", "arguments", "parameters", "input")


def _parse_args(value):
    """Decode JSON-encoded arguments without changing their type.

    The registry is responsible for rejecting non-object argument shapes. Turning
    them into {} here hides the model's actual mistake and can trigger tools with
    missing fields (for example, an empty grep pattern or read_file path).
    """
    if isinstance(value, str):
        try:
            return json.loads(value)
        except ValueError:
            return value
    return value


def _read(obj: dict) -> Action | None:
    """One JSON object -> an Action. Accepts the documented shapes and the common drift of local models (name/arguments, an unwrapped plan)."""
    if isinstance(obj.get("tool"), str):
        raw = obj.get("args")
        args = {} if raw in (None, "") else _parse_args(raw)
        return Action("tool", (obj["tool"], args))
    if isinstance(obj.get("final"), str):
        return Action("final", obj["final"])
    if isinstance(obj.get("plan"), dict):
        return Action("plan", obj["plan"])
    name = obj.get("name") or (obj.get("function") if isinstance(obj.get("function"), str) else None)
    if isinstance(name, str) and name in REGISTRY:
        key = next((k for k in ARG_KEYS if k in obj), None)
        raw = obj[key] if key else None
        args = {} if raw in (None, "") else _parse_args(raw)
        return Action("tool", (name, args))
    if isinstance(obj.get("summary"), str) and isinstance(obj.get("steps"), list):
        return Action("plan", obj)
    return None


def _scan(text: str) -> Action | None:
    decoder, pos = json.JSONDecoder(), 0
    while (start := text.find("{", pos)) >= 0:
        pos = start + 1
        try:
            obj, _ = decoder.raw_decode(text, start)
        except ValueError:
            continue
        found = _read(obj) if isinstance(obj, dict) else None
        if found:
            return found
    return None


def parse_reply(text: str) -> Action:
    """Find the first usable JSON object (tolerates code fences, chatter and <think> blocks; falls back to JSON inside the thinking)."""
    found = _scan(THINK.sub("", text)) or _scan(text)
    if found:
        return found
    shown = " ".join(THINK.sub("", text).split())[:120] or "(empty reply)"
    return Action("invalid", f"no usable JSON object; the reply began: {shown}")


NUDGE = ("Your last reply was not valid. Reply with EXACTLY ONE JSON object and no other text, for example "
         '{"tool": "read_file", "args": {"path": "app/x.py"}} or {"final": "your answer"} or the {"plan": {...}} object. No explanations outside the JSON.')
