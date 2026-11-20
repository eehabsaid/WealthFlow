"""The plain-text JSON protocol every model speaks (so no provider or model needs special handling), the prompts, and a tolerant parser."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass

from ai.dev_agent.tools import REGISTRY, specs

RULES = """You are an autonomous software-development agent working inside a local project through tools. You work in a loop: call a tool, read its result, decide the next call, and repeat until the task is done.
How to work:
- Look before you change: list_dir, glob, grep, search_index and read_file (read a range, not whole big files). Read a file before you edit it: edits are SHA-checked against what you read.
- Change files with edit_file (one exact replacement), edit_files (related changes in several files at once), write_file (new files). Keep each call small; never send a partial or truncated call.
- Use shell for everything else: run the tests, the linter, a build, a script, a query. One line, `&&` and `|` allowed. Prefer the project's own test command; run the tests that cover what you changed.
- For a task with several steps keep a checklist with todo and update it as you go. Use subagent for a big read-only investigation so your own context stays small. Use web_search/web_fetch for documentation.
- Tool errors are information: read the message, fix the call, and try a different approach; never repeat the same failing call. A refusal is final: do not work around it.
- The system asks the owner before risky actions (deleting or moving files, destructive or system commands, installs, paths outside the project, protected files such as balances, salary and cash flow). Do not ask yourself: just make the call. If it is refused, describe the change with note_proposal and continue with the rest.
- Never hand-write or edit migrations (run `python manage.py makemigrations`). Git is read-only. Never change coding_agent/.
- Never claim something is verified: after you finish, the system runs the project's checks and reports the real results. When you are done, say what you did and what you did not check.
- Follow the project's rules and decisions given below."""

PROTOCOL = """Reply with EXACTLY ONE JSON object per message and nothing else:
  {"tool": "<name>", "args": {...}}      call a tool
  {"final": "<short summary>"}           when the current job is finished
No text outside the JSON."""

FINISH_NATIVE = "When you are done, reply in plain text (a short summary) without calling a tool."
FINISH_TEXT = 'When you are done, reply {"final": "<short summary>"}.'

PLAN_FORMAT = """Investigate with the read-only tools, then hand in your plan:
{"plan": {"summary": "...", "steps": [{"title": "...", "files": ["files this step reads or changes"]}],
 "files_add": [], "files_edit": [], "files_delete": [], "files_rename": [{"from": "a", "to": "b"}],
 "tests": ["tests to add or update (paths) and what to run"], "risks": ["..."]}}
List EVERY file you will add, edit, delete or rename: files outside the plan ask the owner again later, and deleting or renaming needs its own approval.
If the task is only a question or needs no file changes, answer it in text instead of planning."""

PLAN_FORMAT_NATIVE = """Investigate with the read-only tools, then call submit_plan with: summary, steps [{title, files}], files_add, files_edit, files_delete, files_rename [{from, to}], tests, risks.
List EVERY file you will add, edit, delete or rename: files outside the plan ask the owner again later, and deleting or renaming needs its own approval.
If the task is only a question or needs no file changes, answer it in text instead of planning."""

QUICK = ("\nQUICK MODE: this is a small task. Look only at what you need (a search or two, read the one file), then reply with a plan of ONE or TWO steps. "
         "Include every file you may need to touch; do not add steps for tests or documentation unless the task asks for them.")


@dataclass
class Action:
    kind: str                 # tool | final | plan | invalid
    payload: object = None    # tool: (name, args) ; final: text ; plan: dict ; invalid: reason


def platform_note() -> str:
    if os.name == "nt":
        return "Platform: Windows 11. `shell` runs through cmd.exe (use dir, type, findstr and `&&`; no bash syntax); / and \\ both work in paths. `python` is the project's interpreter."
    return "Platform: POSIX. `shell` runs through sh."


def system_prompt(readonly: bool, native: bool = False, rules: str = "", hidden=()) -> str:
    """The system prompt. Native tool calling: the tools travel in the API's own `tools` field. Text protocol: the JSON protocol and the tool list are part of the prompt."""
    parts = [RULES, platform_note()]
    if not native:
        parts += [PROTOCOL, "Tools:\n" + specs(readonly, hidden)]
    if rules:
        parts.append(rules)
    return "\n\n".join(parts)


THINK = re.compile(r"\u003cthink\u003e.*?(?:\u003c/think\u003e|\Z)", re.S | re.I)
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


def _scan(text: str):
    """Return (action|None, best_error|None), preferring the candidate decoded furthest."""
    decoder, pos = json.JSONDecoder(), 0
    best_err = None
    while (start := text.find("{", pos)) >= 0:
        pos = start + 1
        try:
            obj, _ = decoder.raw_decode(text, start)
        except json.JSONDecodeError as exc:
            if best_err is None or exc.pos - start > best_err[1].pos - best_err[0]:
                best_err = (start, exc)
            continue
        found = _read(obj) if isinstance(obj, dict) else None
        if found:
            return found, best_err
    return None, best_err


def _describe_error(text: str, first_err) -> str | None:
    if not first_err:
        return None
    start, exc = first_err
    msg = getattr(exc, "msg", None) or str(exc)
    pos = getattr(exc, "pos", None)
    here = pos if isinstance(pos, int) else start
    window = text[max(0, here - 60):min(len(text), here + 60)].replace("\n", "\\n")
    return f"JSON broke at char {here} ({msg}); context: ...{window}..."


def error_details(action: Action) -> dict:
    """Structured JSON error position/message from an invalid Action, for the ledger."""
    if action.kind != "invalid":
        return {}
    m = re.search(r"JSON broke at char (\d+) \(([^)]*)\)", str(action.payload))
    if not m:
        return {}
    return {"json_error_char": int(m.group(1)), "json_error_msg": m.group(2)}


def parse_reply(text: str) -> Action:
    """Find the first usable JSON object (tolerates code fences, chatter and thinking blocks; falls back to JSON inside the thinking)."""
    stripped = THINK.sub("", text)
    found, best_err, err_text = None, None, None
    for src in (stripped, text):
        action, err = _scan(src)
        if action:
            found = action
            break
        if err is not None and (best_err is None or err[1].pos - err[0] > best_err[1].pos - best_err[0]):
            best_err, err_text = err, src
    if found:
        return found
    shown = " ".join(stripped.split())[:120] or "(empty reply)"
    payload = f"no usable JSON object; the reply began: {shown}"
    if best_err:
        payload += "; " + _describe_error(err_text, best_err)
    return Action("invalid", payload)


NUDGE = ("Your last reply was not valid. Reply with EXACTLY ONE JSON object and no other text, for example "
         '{"tool": "read_file", "args": {"path": "app/x.py"}} or {"final": "your answer"} or the {"plan": {...}} object. No explanations outside the JSON.')
NUDGE_NATIVE = ("Your last reply looked like a tool call but could not be used. Call the tool again with valid JSON arguments (one call, small payload), "
                "or, if you are finished, answer in plain text without any JSON or tool markup.")
LOOKS_LIKE_CALL = re.compile(r'"(?:tool|name|arguments|args|function)"\s*:|<tool_call>|<function=|^\s*[{\[]|```(?:json)?\s*[{\[]', re.I)


def looks_like_call(text: str) -> bool:
    """A native-tool-calling model that writes its call as text (broken JSON, markup) instead of using the tool API."""
    return bool(LOOKS_LIKE_CALL.search(THINK.sub("", text or "")))


def nudge_for(action: Action, native: bool = False) -> str:
    """Explain a parse failure without asking the model to repeat a large payload."""
    payload = str(action.payload)
    base = NUDGE_NATIVE if native else NUDGE
    if action.kind == "invalid" and "JSON broke at char" in payload:
        detail = payload[payload.index("JSON broke at char"):]
        return base + " The previous tool call was not run. Return a fresh, smaller tool call; do not resend a large file payload. " + detail[:240]
    return base + f" ({payload[:160]})"
