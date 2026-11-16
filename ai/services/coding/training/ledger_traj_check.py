"""Checks of a logged trajectory against the real repo as it is NOW and against the agent's own protocol: never a similarity score.

  replay       every assistant message is parsed by the agent's real reply parser; every tool call names a real tool and is answered by the matching
               "TOOL RESULT <name>:" message; the conversation ends with `final` (or `plan`). A trajectory that does not replay is not an example.
  repo_check   for every file the model read or changed, the file's sha the first time the model saw it is compared with the file today. The repo still
               matches when the file is exactly as the model saw it (same), or in a state this very task wrote (task_state: a finished patch task has its own
               edits in place). Anything else means the repo moved on, so the logged tool results describe code that is no longer there (changed / missing /
               created_exists).
  plan_check   the accepted plan is run through the agent's own plan validator, its files must still exist (or still be absent for files to add) unless the
               task itself has since created, deleted or moved them, and it must not need owner approval (no protected file).
  protected    a trajectory that wrote to a protected file is never an example.
  cited_paths  paths a final answer mentions that do not exist in the repo (a flag for the reviewer: library paths and removed files are false alarms)."""

from __future__ import annotations

import re

from ai.dev_agent.core import fsutil
from ai.dev_agent.engine.protocol import parse_reply
from ai.dev_agent.ledger import plan as planlib
from ai.dev_agent.tools import REGISTRY   # importing the package registers every tool

CITED = re.compile(r"(?<![\w/.:-])((?:[\w.-]+/)+[\w.-]+\.[A-Za-z0-9]{1,5})(?::\d+)?(?![\w/-])")


def replay(messages: list[dict]) -> list[str]:
    """Why the conversation does not replay through the real protocol (empty list = it does)."""
    body = [m for m in messages if m["role"] != "system"]
    problems = []
    for i, message in enumerate(body):
        if message["role"] != ("user", "assistant")[i % 2]:
            problems.append(f"message {i}: roles do not alternate")
            break
        if message["role"] != "assistant":
            continue
        action = parse_reply(message["content"])
        if action.kind == "invalid":
            problems.append(f"message {i}: not valid protocol JSON")
        elif action.kind == "tool":
            name = action.payload[0]
            if name not in REGISTRY:
                problems.append(f"message {i}: unknown tool {name}")
            following = body[i + 1]["content"] if i + 1 < len(body) else ""
            if not following.startswith(f"TOOL RESULT {name}:\n"):
                problems.append(f"message {i}: the next message is not the result of {name}")
        elif i != len(body) - 1:
            problems.append(f"message {i}: {action.kind} before the end")
    if not body or body[-1]["role"] != "assistant" or parse_reply(body[-1]["content"]).kind not in ("final", "plan"):
        problems.append("does not end with final or plan")
    return problems


def _result(row: dict) -> dict:
    return row["result"] if isinstance(row.get("result"), dict) else {}


def first_seen(results: list[dict]) -> dict[str, str | None]:
    """{path: the file's sha when the model first saw or changed it; None = the file did not exist then (the task created it)}."""
    seen: dict[str, str | None] = {}
    for row in results:
        result, name = _result(row), row["tool"]
        if name == "read_file" and row["ok"] and result.get("path") and result.get("sha"):
            seen.setdefault(result["path"], result["sha"])
        elif name == "edit_files":
            for item in result.get("files") or []:
                if item.get("path") and item.get("state") != "rejected":   # a rejected edit never looked at the file
                    seen.setdefault(item["path"], item.get("sha_before"))
        elif name == "delete_file" and result.get("path"):
            seen.setdefault(result["path"], result.get("sha_before"))
        elif name == "rename_file" and result.get("from") and result.get("to"):
            seen.setdefault(result["from"], result.get("sha"))
            seen.setdefault(result["to"], None)
    return seen


def task_wrote(results: list[dict]) -> dict[str, set]:
    """{path: every state the TASK ITSELF left the file in: the sha after each edit, None when it was absent (deleted, moved, or an edit rolled back)}."""
    wrote: dict[str, set] = {}
    for row in results:
        result, name = _result(row), row["tool"]
        if name == "edit_files":
            for item in result.get("files") or []:
                if item.get("path") and item.get("state") != "rejected":
                    wrote.setdefault(item["path"], set()).add(item.get("sha_now"))
        elif name == "delete_file" and result.get("path"):
            wrote.setdefault(result["path"], set()).add(None)
        elif name == "rename_file" and result.get("from") and result.get("to"):
            wrote.setdefault(result["from"], set()).add(None)
            wrote.setdefault(result["to"], set()).add(result.get("sha"))
    return wrote


def _now(project, path: str) -> str | None:
    """The file's sha today, None when it is absent (or not a project path)."""
    try:
        full = project.resolve(path)[1]
    except ValueError:
        return None
    return fsutil.sha(fsutil.read_bytes(full)) if full.is_file() else None


def repo_check(project, results: list[dict], history: list[dict] | None = None) -> dict:
    """{"checked", "same", "task_state", "changed": [...], "missing": [...], "created_exists": [...]} for the files of one trajectory.
    `history` = the tool results of the WHOLE task (every phase), so a file a later package edited still counts as the task's own state."""
    wrote = task_wrote(history if history is not None else results)
    out = {"checked": 0, "same": 0, "task_state": 0, "changed": [], "missing": [], "created_exists": []}
    for path, seen in sorted(first_seen(results).items()):
        out["checked"] += 1
        now = _now(project, path)
        if now == seen:
            out["same"] += 1   # exactly as the model saw it (still absent, for a file the task created)
        elif now in wrote.get(path, ()):
            out["task_state"] += 1
        elif seen is None:
            out["created_exists"].append(path)
        elif now is None:
            out["missing"].append(path)
        else:
            out["changed"].append(path)
    return out


def repo_matches(check: dict) -> bool:
    return not (check["changed"] or check["missing"] or check["created_exists"])


def protected_writes(project, results: list[dict]) -> list[str]:
    """Protected files (balances, salary, billing, auth ... as configured in config.json) this trajectory wrote to; such a trajectory is never an example."""
    return sorted(path for path in task_wrote(results) if project.protected_reason(path))


def plan_check(project, payload, files_log: dict | None = None) -> list[str]:
    """Problems with an accepted plan against the repo today (empty list = it still holds). `files_log` is the finished task's own ledger record of what it
    wrote (ledger.data["files"]): a file the task has since created, deleted or moved is not a problem, it is the plan having been carried out."""
    log = files_log or {}
    plan, problems = planlib.validate(project, payload)
    problems = list(problems)

    def gone(rel: str) -> bool:
        return not project.resolve(rel)[1].exists()

    def done(rel: str, *states: str) -> bool:
        return (log.get(rel) or {}).get("state") in states

    problems += [f"files_edit: {f} does not exist" for f in plan["files_edit"] if gone(f) and not done(f, "deleted", "renamed")]
    problems += [f"files_delete: {f} does not exist" for f in plan["files_delete"] if gone(f) and not done(f, "deleted")]
    problems += [f"files_rename: {r['from']} does not exist" for r in plan["files_rename"] if gone(r["from"]) and not done(r["from"], "renamed")]
    problems += [f"files_add: {f} already exists" for f in plan["files_add"] if not gone(f) and not (done(f, "written") and log[f].get("sha_before") is None)]
    if plan["needs_owner_approval"]:
        problems.append("the plan touches protected files: " + ", ".join(plan["needs_owner_approval"]))
    return problems


def cited_missing(project, text: str) -> list[str]:
    found = []
    for path in dict.fromkeys(CITED.findall(text)):
        try:
            if not project.resolve(path)[1].exists():
                found.append(path)
        except ValueError:
            found.append(path)
    return found
