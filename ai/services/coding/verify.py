"""Automated verification of a change. Runs the project's own checks on the changed files and reports each as PASSED / FAILED / NOT RUN.
The overall line says 'VERIFIED' only when every step that ran passed; browser E2E is always reported NOT RUN (it runs on the owner's PC)."""

from __future__ import annotations

import json
import re
import subprocess
import sys

from ai.services.coding import ROOT
from ai.services.coding.config import load, protected_reason, test_module

PLACEHOLDER = re.compile(r"\{[^{}]*\}")
CODE_EXT = (".py", ".js", ".css", ".html")


def _run(name: str, cmd: list[str], timeout: int = 1800) -> dict:
    try:
        done = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"step": name, "status": "FAILED", "detail": f"could not run: {exc.__class__.__name__}"}
    tail = "\n".join((done.stdout + done.stderr).strip().splitlines()[-6:])
    return {"step": name, "status": "PASSED" if done.returncode == 0 else "FAILED", "detail": tail}


def i18n_parity() -> dict:
    langs = {c: json.loads((ROOT / "static" / "i18n" / f"{c}.json").read_text(encoding="utf-8")) for c in ("en", "ar", "fr", "de")}
    problems = []
    for code, data in langs.items():
        if code == "en":
            continue
        problems += [f"{code}: missing {k}" for k in langs["en"] if k not in data][:5]
        problems += [f"{code}: extra {k}" for k in data if k not in langs["en"]][:5]
        problems += [f"{code}: placeholders differ in {k}" for k, v in langs["en"].items() if k in data and sorted(PLACEHOLDER.findall(str(v))) != sorted(PLACEHOLDER.findall(str(data[k])))][:5]
    return {"step": "i18n parity (en/ar/fr/de)", "status": "FAILED" if problems else "PASSED", "detail": "; ".join(problems[:6])}


def line_limits(files: list[str]) -> dict:
    limit = load()["max_file_lines"]
    over = []
    for f in files:
        p = ROOT / f
        if f.endswith(CODE_EXT) and p.is_file():
            n = p.read_text(encoding="utf-8", errors="replace").count("\n") + 1
            if n > limit:
                over.append(f"{f} ({n})")
    return {"step": f"files <= {limit} lines", "status": "FAILED" if over else "PASSED", "detail": ", ".join(over)}


def changed_files() -> list[str]:
    out = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True).stdout
    return [l[3:].strip().strip('"').replace("\\", "/") for l in out.splitlines() if l[3:].strip()]


def verify(files: list[str] | None = None, full_suite: bool = False, timeout: int = 1800) -> dict:
    files = [f for f in (files if files is not None else changed_files()) if f]
    py = [f for f in files if f.endswith(".py") and (ROOT / f).is_file()]
    steps = [_run("manage.py check", [sys.executable, "manage.py", "check"])]
    modules = sorted({m for m in (test_module(f) for f in files) if m})
    if full_suite or not modules:
        steps.append(_run("full Django test suite", [sys.executable, "manage.py", "test"], timeout))
    else:
        steps.append(_run("targeted tests: " + ", ".join(modules), [sys.executable, "manage.py", "test", *modules], timeout))
    steps.append(_run("pyflakes on changed files", [sys.executable, "-m", "pyflakes", *py]) if py else {"step": "pyflakes", "status": "NOT RUN", "detail": "no Python files changed"})
    steps += [_run("makemigrations --check", [sys.executable, "manage.py", "makemigrations", "--check", "--dry-run"]), i18n_parity(), line_limits(files)]
    steps.append({"step": "browser E2E (scripts/run_full_e2e.py)", "status": "NOT RUN", "detail": "runs on the owner's PC only; never claim it passed"})
    approvals = [f"{f}: {protected_reason(f)}" for f in files if protected_reason(f)]
    ran = [s for s in steps if s["status"] != "NOT RUN"]
    ok = all(s["status"] == "PASSED" for s in ran)
    overall = ("VERIFIED (automated steps above passed; browser E2E not run)" if ok else "NOT VERIFIED: " + ", ".join(s["step"] for s in ran if s["status"] == "FAILED"))
    return {"overall": overall, "steps": steps, "protected_files_changed": approvals, "files": files}


def render(result: dict) -> str:
    lines = [f"{s['status']:8} {s['step']}" + (f"\n         {s['detail']}" if s["detail"] and s["status"] != "PASSED" else "") for s in result["steps"]]
    if result["protected_files_changed"]:
        lines.append("OWNER APPROVAL NEEDED for: " + "; ".join(result["protected_files_changed"]))
    return "\n".join(lines + ["", result["overall"]])
