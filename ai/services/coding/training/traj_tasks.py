"""The task list for the agent-loop training batch: 100 real tasks (60 questions, 40 small patches), mixed 3 + 2 in every block of five, drawn from source files
no earlier task used. Every symbol, line number and gap ("no type hint", "no docstring", "bare except", "used in 3 other files") is read from the code
(traj_pool.py), so a task always asks about something that really is there, and validate() re-checks the whole list against the repo.

Patches are only made where they can really succeed and where a change is harmless: in files whose folder maps to a test area (otherwise the agent's own checks can
never say VERIFIED) and never in money, salary, billing or login code (traj_pool.SENSITIVE). Questions only read, so they may be about any file.
Nothing here writes an answer or a diff: the answers and the changes come from the real agent, and only what you approve is ever trained on. Selection is seeded,
so the list is reproducible, and it spreads over the folders of the project instead of clustering in one."""

from __future__ import annotations

import random
from itertools import cycle, zip_longest

from ai.services.coding.training import traj_pool as pool

SEED = 20261115
QA_SUFFIX = " Answer only; do not plan or change anything."
QUOTAS = {"qa": {"what_does": 14, "callers": 12, "module": 10, "params": 8, "imports": 4, "class": 4, "js_what_does": 5, "js_callers": 3},
          "patch": {"hints": 16, "docstring": 14, "module_doc": 6, "class_doc": 2, "bare_except": 2}}
KIND = {template: kind for kind, quota in QUOTAS.items() for template in quota}
FILL_ORDER = ("bare_except", "class_doc", "imports", "js_callers", "js_what_does", "class", "callers", "params", "what_does", "module_doc", "module", "hints", "docstring")
TOP_UP = {"qa": ("what_does", "module", "params", "callers"), "patch": ("docstring", "hints", "module_doc")}   # make up a shortage of a scarce template
PATCH_MAX_LINES = 180   # the project's 200-line limit leaves room for the change
PHRASES = {
    "what_does": ["What does `{symbol}` in `{file}` do? Explain it from the code.", "Explain what the function `{symbol}` in `{file}` does and when it is called."],
    "callers": ["Where is `{symbol}` (defined in `{file}`) used in this project? List the files and say what each one does with it.",
                "Which parts of the code call or import `{symbol}` from `{file}`? Say briefly what each caller needs it for."],
    "module": ["What is `{file}` for? List its main functions or classes with one line each.", "Summarize the module `{file}`: its purpose and its public functions."],
    "params": ["What parameters does `{symbol}` in `{file}` take, what does it return, and what happens on bad input?",
               "Describe the inputs and the return value of `{symbol}` in `{file}`, and any case where it returns early or raises."],
    "imports": ["Which other modules of this project does `{file}` import from, and what does it use each one for?"],
    "class": ["How does the class `{symbol}` in `{file}` work? List its methods and say what each one is for."],
    "js_what_does": ["What does the JavaScript function `{symbol}` in `{file}` do? Explain it from the code."],
    "js_callers": ["Where is the JavaScript function `{symbol}` (defined in `{file}`) used? List the files, scripts and templates, and say what each one does with it."],
    "hints": ["Add type hints to the parameters and the return value of `{symbol}` in `{file}`. Do not change what it does and do not touch any other function.",
              "In `{file}`, add type annotations to `{symbol}` (every parameter and the return type). Keep the behavior exactly the same and change nothing else."],
    "docstring": ["Add a short docstring to `{symbol}` in `{file}` saying what it does, what it takes and what it returns. Change nothing else.",
                  "`{symbol}` in `{file}` has no docstring: write a clear two or three line one from reading its code. Change nothing else."],
    "class_doc": ["Add a short docstring to the class `{symbol}` in `{file}` saying what it is for. Change nothing else."],
    "module_doc": ["Add a one-line module docstring at the top of `{file}` that says what the module is for (read the file first). Change nothing else."],
    "bare_except": ["In `{file}` there is a bare `except:` clause. Replace it with `except Exception:` and keep everything else the same."],
}


def _fns(f: dict, test, why) -> list[dict]:
    return [{"symbol": fn["name"], "line": fn["line"], "why": why(fn)} for fn in f["functions"] if test(fn)]


def rule(template: str, f: dict, use: dict) -> list[dict]:
    """Every way `template` fits the file `f` (empty = it does not fit): [{"symbol", "line", "why"}]. The one place that says what a good task is."""
    path = f["path"]
    if template.startswith("js_") != path.endswith(".js"):
        return []
    if KIND[template] == "patch" and (pool.SENSITIVE.search(path) or not f.get("mapped") or f["lines"] > PATCH_MAX_LINES):
        return []
    outside = lambda name: sorted(use.get(name, set()) - {path})  # noqa: E731
    public = [fn for fn in f["functions"] if fn["public"]]
    if template in ("what_does", "js_what_does"):
        return _fns(f, lambda fn: fn["public"] and fn["body_lines"] >= 4, lambda fn: f"{fn['body_lines']} lines")
    if template in ("callers", "js_callers"):
        return _fns(f, lambda fn: fn["public"] and fn["body_lines"] >= 3 and 1 <= len(outside(fn["name"])) <= 6, lambda fn: f"used in {len(outside(fn['name']))} other files")
    if template == "params":
        return _fns(f, lambda fn: fn["public"] and len(fn["args"]) >= 2 and fn["body_lines"] >= 5, lambda fn: f"{len(fn['args'])} parameters")
    if template == "module":
        return [{"symbol": "", "line": 1, "why": f"{len(public)} public functions, {len(f['classes'])} classes"}] if len(public) + len(f["classes"]) >= 2 else []
    if template == "imports":
        return [{"symbol": "", "line": 1, "why": f"imports from {len(f['imports'])} project modules"}] if len(f["imports"]) >= 2 else []
    if template == "class":
        return [{"symbol": c["name"], "line": c["line"], "why": f"{c['methods']} methods"} for c in f["classes"] if c["methods"] >= 2]
    if template == "hints":
        return _fns(f, lambda fn: fn["public"] and fn["missing_hints"] and 1 <= len(fn["args"]) <= 4 and fn["body_lines"] >= 2, lambda fn: "no type hint for " + ", ".join(fn["missing_hints"]))
    if template == "docstring":
        return _fns(f, lambda fn: fn["public"] and not fn["doc"] and fn["body_lines"] >= 3, lambda fn: f"no docstring, {fn['body_lines']} lines")
    if template == "class_doc":
        return [{"symbol": c["name"], "line": c["line"], "why": f"no docstring, {c['methods']} methods"} for c in f["classes"] if not c["doc"] and c["methods"] >= 1]
    if template == "module_doc":
        return [{"symbol": "", "line": 1, "why": "no module docstring"}] if not f["module_doc"] and (public or f["classes"]) else []
    if template == "bare_except":
        return [{"symbol": "", "line": f["bare_except"][0], "why": f"bare except at line {f['bare_except'][0]}"}] if f["bare_except"] else []
    raise ValueError(f"unknown template {template}")


def _spread(paths: list[str], rng: random.Random) -> list[str]:
    """Shuffled, then dealt out folder by folder so consecutive picks come from different parts of the project."""
    groups: dict[str, list[str]] = {}
    for rel in paths:
        groups.setdefault("/".join(rel.split("/")[:3]), []).append(rel)
    ordered = [groups[g] for g in sorted(groups)]
    rng.shuffle(ordered)
    for g in ordered:
        rng.shuffle(g)
    return [rel for row in zip_longest(*ordered) for rel in row if rel]


def build(project, files: list[str] | None = None, used: set[str] | None = None, seed: int = SEED, quotas: dict | None = None) -> list[dict]:
    """The task list. A template that finds fewer files than its quota is topped up with plentiful templates of the same kind; validate() reports any shortage."""
    quotas = quotas or QUOTAS
    files = files if files is not None else pool.tracked(project.root)
    used = used if used is not None else pool.used_files(project, files)
    rng = random.Random(seed)
    infos = {rel: pool.read(project, rel) for rel in pool.candidates(project, files, used)}
    infos = {rel: f for rel, f in infos.items() if f}
    use = pool.usage(project.root, files, {fn["name"] for f in infos.values() for fn in f["functions"] if fn["public"]})
    order, taken, made = _spread(sorted(infos), rng), set(), {"qa": [], "patch": []}

    def fill(template: str, limit: int) -> None:
        kind = KIND[template]
        have = sum(1 for t in made[kind] if t["template"] == template)
        for rel in order:
            if have >= limit:
                return
            fits = rule(template, infos[rel], use) if rel not in taken else []
            if fits:
                pick = rng.choice(fits)
                taken.add(rel)
                text = rng.choice(PHRASES[template]).format(file=rel, symbol=pick["symbol"]) + (QA_SUFFIX if kind == "qa" else "")
                made[kind].append({"kind": kind, "template": template, "goal": text, "file": rel, "symbol": pick["symbol"], "line": pick["line"], "why": pick["why"]})
                have += 1

    for template in FILL_ORDER:
        fill(template, quotas.get(KIND[template], {}).get(template, 0))
    for kind in ("qa", "patch"):
        wanted, stalled, spots = sum(quotas.get(kind, {}).values()), 0, cycle(TOP_UP[kind])
        while len(made[kind]) < wanted and stalled < len(TOP_UP[kind]):
            template, before = next(spots), len(made[kind])
            fill(template, sum(1 for t in made[kind] if t["template"] == template) + 1)
            stalled = 0 if len(made[kind]) > before else stalled + 1
        rng.shuffle(made[kind])
    qa, patch = iter(made["qa"]), iter(made["patch"])
    merged = [next(src, None) for _ in range(len(made["qa"]) + len(made["patch"]) + 5) for src in (qa, qa, patch, qa, patch)]
    return [{"id": f"T{number:03d}", **t} for number, t in enumerate([t for t in merged if t], 1)]


def list_problems(tasks: list[dict], quotas: dict | None = None) -> list[str]:
    """What is wrong with the list as a list: the number of questions and patches, the 3 + 2 mix, and anything used twice."""
    problems = []
    for kind, quota in (quotas or QUOTAS).items():
        got = sum(1 for t in tasks if t["kind"] == kind)
        if got != sum(quota.values()):
            problems.append(f"{kind}: {got} tasks, expected {sum(quota.values())}")
    for block in range(0, len(tasks), 5):
        if [t["kind"] for t in tasks[block:block + 5]] != ["qa", "qa", "patch", "qa", "patch"][:len(tasks[block:block + 5])]:
            problems.append(f"block {block // 5 + 1} does not mix 3 questions and 2 patches in that order")
    for what in ("id", "goal", "file"):
        seen = [t[what] for t in tasks]
        problems += [f"{what} used twice: {x}" for x in sorted({x for x in seen if seen.count(x) > 1})]
    return problems


def task_problems(project, tasks: list[dict], files: list[str] | None = None, used: set[str] | None = None) -> dict[str, str]:
    """{task id: why it no longer fits the repo as it is now} - an empty dict means every task asks about something real that no earlier task touched."""
    files = files if files is not None else pool.tracked(project.root)
    used = used if used is not None else pool.used_files(project, files)
    infos = {t["file"]: pool.read(project, t["file"]) for t in tasks if t["file"] in files}
    use = pool.usage(project.root, files, {t["symbol"] for t in tasks if t["symbol"]})
    found = {}
    for t in tasks:
        f = infos.get(t["file"])
        if t["template"] not in KIND:
            why = "unknown kind of task"
        elif f is None:
            why = "not a tracked file that can be read"
        elif t["file"] in used:
            why = "an earlier task already used this file"
        elif project.protected_reason(t["file"]):
            why = "protected file"
        elif not any(p["symbol"] == t["symbol"] and p["line"] == t["line"] for p in rule(t["template"], f, use)):
            why = f"'{t['symbol']}' at line {t['line']} does not fit this kind of task in the file as it is now (changed, not verifiable, or money/login code)"
        elif t["file"] not in t["goal"] or (t["symbol"] and t["symbol"] not in t["goal"]):
            why = "the goal does not name the file and symbol"
        elif t["kind"] == "qa" and not t["goal"].endswith(QA_SUFFIX):
            why = "a question must say it is answer-only"
        else:
            continue
        found[t["id"]] = f"{t['template']} {t['file']}: {why}"
    return found


def validate(project, tasks: list[dict], files: list[str] | None = None, used: set[str] | None = None, quotas: dict | None = None) -> list[str]:
    """Every problem of a task list against the repo as it is now (empty list = good to run)."""
    return list_problems(tasks, quotas) + [f"{task_id} {why}" for task_id, why in task_problems(project, tasks, files, used).items()]
