"""The implementation plan: validation, normalised paths, the PlanScope the guards enforce, and a short text for the approval prompt."""

from __future__ import annotations

import hashlib
import json

from ai.dev_agent.core.project import PathError


class PlanScope:
    """What the approved plan allows. Edits/creates: any listed add/edit/rename-target file. Deletes and renames: exactly what is listed."""

    def __init__(self, plan: dict, packages: list | None = None, package: str = ""):
        self.write = set(plan["files_add"]) | set(plan["files_edit"]) | {r["to"] for r in plan["files_rename"]}
        self.delete = set(plan["files_delete"])
        self.rename = {r["from"]: r["to"] for r in plan["files_rename"]}
        # Package scope: a file listed only in ANOTHER package's steps belongs to that package. Files in this package's list, files shared by
        # several packages and files no package lists stay allowed. The overall approval is unchanged; "final" (and no package) is unrestricted.
        self.elsewhere: dict[str, str] = {}
        mine = next((set(p["files"]) for p in packages or [] if p["id"] == package), None)
        for p in (packages or []) if mine is not None else []:
            if p["id"] != package:
                self.elsewhere.update({f: p["id"] for f in p["files"] if f not in mine and f not in self.elsewhere})

    def other_package(self, rel: str) -> str:
        return self.elsewhere.get(rel, "")

    def allows(self, op: str, rel: str, dst: str = "") -> bool:
        if op in ("edit", "create"):
            return rel in self.write
        if op == "delete":
            return rel in self.delete
        if op == "rename":
            return rel in self.rename and (not dst or self.rename[rel] == dst)
        return False


def digest(plan: dict) -> str:
    return hashlib.sha256(json.dumps(plan, sort_keys=True).encode("utf-8")).hexdigest()


def _paths(project, raw, key, problems, forbid=False) -> list[str]:
    out = []
    for item in raw.get(key) or []:
        try:
            rel, _ = project.resolve(item)
        except PathError as exc:
            problems.append(f"{key}: {exc}")
            continue
        reason = project.forbidden_reason(rel) or project.secret_reason(rel)
        if forbid and reason:
            problems.append(f"{key}: {rel} is forbidden ({reason}); remove it from the plan")
        else:
            out.append(rel)
    return out


def validate(project, raw) -> tuple[dict, list[str]]:
    """(normalised plan, problems). The plan is usable only when there are no problems."""
    problems: list[str] = []
    if not isinstance(raw, dict):
        return {}, ["the plan must be a JSON object"]
    plan = {"summary": str(raw.get("summary") or "").strip()[:1000], "steps": [],
            "files_add": _paths(project, raw, "files_add", problems, True), "files_edit": _paths(project, raw, "files_edit", problems, True),
            "files_delete": _paths(project, raw, "files_delete", problems, True), "files_rename": [],
            "tests": [str(t)[:300] for t in raw.get("tests") or []], "risks": [str(r)[:300] for r in raw.get("risks") or []]}
    for pair in raw.get("files_rename") or []:
        got = _paths(project, {"x": [pair.get("from"), pair.get("to")] if isinstance(pair, dict) else []}, "x", problems, True)
        if len(got) == 2:
            plan["files_rename"].append({"from": got[0], "to": got[1]})
        else:
            problems.append("files_rename entries need valid `from` and `to`")
    for number, step in enumerate(raw.get("steps") or [], 1):
        if not isinstance(step, dict) or not str(step.get("title") or "").strip():
            problems.append(f"step {number} needs a title")
            continue
        plan["steps"].append({"id": f"S{number}", "title": str(step["title"]).strip()[:200], "files": _paths(project, step, "files", problems)})
    if not plan["summary"]:
        problems.append("the plan needs a summary")
    if not plan["steps"]:
        problems.append("the plan needs at least one step")
    plan["needs_owner_approval"] = sorted({p for key in ("files_add", "files_edit", "files_delete") for p in plan[key] if project.protected_reason(p)}
                                          | {r["from"] for r in plan["files_rename"] if project.protected_reason(r["from"])})
    return plan, problems


def summary_text(plan: dict, packages: list[dict]) -> str:
    lines = [plan["summary"], f"Steps: {len(plan['steps'])}, work packages: {len(packages)}"]
    for key, label in (("files_add", "add"), ("files_edit", "edit"), ("files_delete", "DELETE")):
        if plan[key]:
            lines.append(f"{label} ({len(plan[key])}): " + ", ".join(plan[key][:12]) + (" ..." if len(plan[key]) > 12 else ""))
    if plan["files_rename"]:
        lines.append("RENAME: " + ", ".join(f"{r['from']} -> {r['to']}" for r in plan["files_rename"]))
    if plan["needs_owner_approval"]:
        lines.append("PROTECTED (will ask you before touching): " + ", ".join(plan["needs_owner_approval"]))
    if plan["tests"]:
        lines.append("tests: " + "; ".join(plan["tests"][:6]))
    if plan["risks"]:
        lines.append("risks: " + "; ".join(plan["risks"][:6]))
    over = [p["id"] for p in packages if p["oversize"]]
    if over:
        lines.append(f"WARNING: packages {', '.join(over)} may not fit one context window; split those steps")
    return "\n".join(lines)
