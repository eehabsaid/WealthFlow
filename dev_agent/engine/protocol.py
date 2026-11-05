"""The plain-text JSON protocol every model speaks (so no provider or model needs special handling), the prompts, and a tolerant parser."""

from __future__ import annotations

import json
from dataclasses import dataclass

from ..tools import specs

RULES = """You are an autonomous software-development agent working inside a local project through tools.
Reply with EXACTLY ONE JSON object per message and nothing else:
  {"tool": "<name>", "args": {...}}      call a tool
  {"final": "<short summary>"}           when the current job is finished
Rules:
- Read a file before you edit it. Make related edits for several files in ONE edit_files call. Keep `old` text short but unique.
- Never claim anything is verified: the system runs the checks and reports the real results. In your summary say what you did and what you did not check.
- Guards decide what is allowed. Never try to work around a refusal. Protected files need the owner: if you are refused, use note_proposal to describe the fix and continue with the rest.
- Never hand-write or edit migrations (use `python manage.py makemigrations`). Git is read-only. One command per run_command, no shell operators.
- Keep tool output small: read line ranges, grep narrowly, do not repeat the same call.
- Follow the project's skills and decisions given below."""

PLAN_FORMAT = """Investigate with the read-only tools, then reply with:
{"plan": {"summary": "...", "steps": [{"title": "...", "files": ["files this step reads or changes"]}],
 "files_add": [], "files_edit": [], "files_delete": [], "files_rename": [{"from": "a", "to": "b"}],
 "tests": ["tests to add or update (paths) and what to run"], "risks": ["..."]}}
List EVERY file you will add, edit, delete or rename: nothing outside the plan may be changed later. Deleting or renaming only works if listed."""


@dataclass
class Action:
    kind: str                 # tool | final | plan | invalid
    payload: object = None    # tool: (name, args) ; final: text ; plan: dict ; invalid: reason


def system_prompt(readonly: bool) -> str:
    return f"{RULES}\n\nTools:\n{specs(readonly)}"


def parse_reply(text: str) -> Action:
    """Find the first JSON object in the reply (tolerates code fences and chatter) and read it."""
    decoder, pos = json.JSONDecoder(), 0
    while True:
        start = text.find("{", pos)
        if start < 0:
            return Action("invalid", "no JSON object found")
        try:
            obj, end = decoder.raw_decode(text, start)
        except ValueError:
            pos = start + 1
            continue
        pos = start + 1
        if not isinstance(obj, dict):
            continue
        if isinstance(obj.get("tool"), str):
            return Action("tool", (obj["tool"], obj.get("args") or {}))
        if isinstance(obj.get("final"), str):
            return Action("final", obj["final"])
        if isinstance(obj.get("plan"), dict):
            return Action("plan", obj["plan"])
