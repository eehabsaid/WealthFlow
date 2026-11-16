"""The real-task batch for agent-loop training: every task of the list (traj_tasks.py) is run through the REAL dev agent - `python -m ai.dev_agent run "<goal>"`
with the plan approved automatically (`--yes`, you are never asked) - one task at a time, each in its own throw-away copy of this repo (loop_snapshot.py) with the model of your Settings pinned in
the copy. Your files are never changed (a patch task only edits its copy). What comes back is the finished task folder (ledger.json, events.jsonl with the full
tool results, report.md), copied into coding_agent/tasks exactly where a task you ran yourself would be, ready for the trajectory extractor.

Progress is saved after every task (<work>/traj_done.json), so stopping with Ctrl+C and running again simply continues. The runner is a parameter, so the tests need
no model; the default runner is the real command line (loop_eval.run_cli)."""

from __future__ import annotations

import json
import os
import shutil
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Callable

from ai.services.coding.training import loop_eval, loop_score, loop_snapshot, traj_pool, traj_tasks

DONE_NAME = "traj_done.json"
DEFAULT_TIMEOUT_S = 2400


def load_done(work) -> dict:
    """{task id: what happened} of every task already run (empty when none)."""
    try:
        data = json.loads((Path(work) / DONE_NAME).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data.get("tasks", {}) if isinstance(data, dict) else {}


def save_done(work, done: dict) -> None:
    path = Path(work) / DONE_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps({"version": 1, "tasks": done}, indent=1, ensure_ascii=False), encoding="utf-8")
    os.replace(temp, path)   # never a half-written progress file


def is_done(done: dict, task: dict) -> bool:
    return done.get(task["id"], {}).get("goal") == task["goal"]   # a re-made list with another goal under the same id is a new task


def pick(tasks: list[dict], done: dict, start: int = 1, count: int = 0, only=(), redo: bool = False) -> list[dict]:
    """The tasks to run now: from position `start` of the list, only the ids in `only`, not the ones already done (unless `redo`), at most `count`."""
    chosen = [t for number, t in enumerate(tasks, 1) if number >= start and (not only or t["id"] in only) and (redo or not is_done(done, t))]
    return chosen[:count] if count else chosen


def prepare(project, path, work, log: Callable[[str], None] = print) -> list[dict]:
    """The list to run. A list that no longer fits this machine (a file was used by one of your earlier tasks, or was changed) is made again - but only while no
    task has run yet; once the batch is under way its list is kept and the tasks that no longer fit are skipped."""
    path, done = Path(path), load_done(work)
    tasks = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else []
    files = traj_pool.tracked(project.root)
    used = traj_pool.used_files(project, files, ignore={d.get("folder") for d in done.values()})
    stale = traj_tasks.task_problems(project, tasks, files, used) if tasks else {}
    if tasks and not stale:
        return tasks
    if not done:
        tasks = traj_tasks.build(project, files, used)
        problems = traj_tasks.validate(project, tasks, files, used)
        if problems:
            raise ValueError("A valid task list cannot be made from the files of this repo: " + "; ".join(problems[:5]))
        path.write_text(json.dumps(tasks, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        log(f"Made a new task list for the files of this repo: {len(tasks)} tasks ({path.name}).")
        return tasks
    for task in tasks:
        if task["id"] in stale and not is_done(done, task):
            log(f"Skipping {task['id']}: {stale[task['id']]}")
    return [t for t in tasks if t["id"] not in stale or is_done(done, t)]


def ollama_models(base_url: str) -> list[str] | None:
    """The model names Ollama has installed (None when it does not answer)."""
    try:
        with urllib.request.urlopen(base_url.rstrip("/") + "/api/tags", timeout=5) as response:
            return [str(m.get("name", "")) for m in json.load(response).get("models", [])]
    except (OSError, ValueError):
        return None


def preflight(model: str, base_url: str) -> str:
    """'' when Ollama answers and has the model, otherwise one sentence saying what to fix."""
    names = ollama_models(base_url)
    if names is None:
        return f"Ollama does not answer at {base_url}. Start it (ollama serve) and run this again."
    if model not in names and f"{model}:latest" not in names:
        return f"The model '{model}' is not installed in Ollama (installed: {', '.join(sorted(names)) or 'none'})."
    return ""


def context_line(settings: dict) -> str:
    """One sentence on how much context the agent really has with the current settings (the batch runs with YOUR settings, so the data is what the agent really does)."""
    window, reserve = int(settings["context_window"]), int(settings["reserve_tokens"])
    return (f"Agent context: {max(0, window - reserve):,} of {window:,} tokens usable per task (reserve {reserve:,}); a task that needs more is trimmed by the agent "
            "and cannot be used for training (see 'Context & limits').")


def run_one(task: dict, snapshot, real_root, work, model: str, runner: Callable, timeout: int) -> dict:
    """One task in its own copy; the finished task folder is copied back into the real repo's coding_agent/tasks. Returns the scored row (loop_score.score_task)."""
    copy = loop_snapshot.fresh_copy(snapshot, Path(work) / "copies" / task["id"])
    try:
        loop_snapshot.pin_model(copy, model)
        result = runner(copy, task["goal"], timeout)
        row = loop_score.score_task(copy, {"task_id": task["id"], "kind": task["kind"], "goal": task["goal"], "answer": ""}, result)
        folder = loop_score.task_folder(copy)
        if folder and not (Path(real_root) / "coding_agent" / "tasks" / folder.name).exists():
            shutil.copytree(folder, Path(real_root) / "coding_agent" / "tasks" / folder.name)
        logs = Path(work) / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        (logs / f"{task['id']}.txt").write_text(str(result.get("tail") or ""), encoding="utf-8")
        return row
    finally:
        loop_snapshot.remove(copy)


def _summary(todo: list[dict], rows: list[dict], total_done: int, total: int, stopped: bool) -> dict:
    ok = sum(1 for r in rows if r["success"])
    kinds = ", ".join(f"{kind} {sum(1 for r in rows if r['kind'] == kind and r['success'])}/{sum(1 for r in rows if r['kind'] == kind)}" for kind in ("qa", "patch"))
    lines = [("Stopped by you after " if stopped else "Finished ") + f"{len(rows)} of {len(todo)} task(s): {ok} DONE, {len(rows) - ok} FAIL ({kinds}).",
             f"All together {total_done} of {total} tasks of the list have run.",
             "The task folders are in coding_agent/tasks. " + ("Run the same command again to continue." if stopped or len(rows) < len(todo) else
                                                              "Next: python scripts/ledger_train.py --mode loop --stages extract")]
    return {"status": "stopped" if stopped else "done", "ran": len(rows), "done": ok, "failed": len(rows) - ok, "text": "\n".join(lines)}


def run(tasks: list[dict], root, work_dir, model: str, runner: Callable = loop_eval.run_cli, log: Callable[[str], None] = print, timeout: int = DEFAULT_TIMEOUT_S,
        start: int = 1, count: int = 0, only=(), redo: bool = False) -> dict:
    """Runs the tasks `pick` chooses, one at a time, saving progress after each. Ctrl+C ends the batch cleanly (the task in progress is not counted)."""
    work, done = Path(work_dir), load_done(work_dir)
    todo = pick(tasks, done, start, count, only, redo)
    if not todo:
        return {"status": "nothing_to_do", "ran": 0, "done": 0, "failed": 0, "text": "Nothing to run: every task of the list has run. Next: python scripts/ledger_train.py --mode loop --stages extract"}
    info = loop_snapshot.snapshot(root, work / "snapshot")
    log(f"Working copy of the repo: {info['files']} files" + ("" if info["git"] else " (this folder has no git history)"))
    log("Every plan is approved automatically: you are never asked (a protected file or a command that needs approval is refused).")
    began, rows, stopped = time.monotonic(), [], False
    try:
        for number, task in enumerate(todo, 1):
            log(f"[{number}/{len(todo)}] {task['id']} ({task['kind']}) at {datetime.now():%H:%M}: {task['goal'][:110]}")
            row = run_one(task, work / "snapshot", root, work, model, runner, timeout)
            rows.append(row)
            done[task["id"]] = {"goal": task["goal"], "folder": row["folder"], "status": row["status"], "success": row["success"], "why": row["why"], "seconds": row["seconds"],
                                "finished": datetime.now().isoformat(timespec="seconds")}
            save_done(work, done)
            left = round((time.monotonic() - began) / len(rows) * (len(todo) - number) / 60)
            log("    -> " + ("DONE" if row["success"] else f"FAIL: {row['why'] or row['status']}") + f" in {row['seconds']}s" + (f"   (about {left} min left)" if left else ""))
    except KeyboardInterrupt:
        stopped = True
    finally:
        loop_snapshot.remove(work / "snapshot")
        loop_snapshot.remove(work / "copies")
    return _summary(todo, rows, sum(1 for t in tasks if is_done(done, t)), len(tasks), stopped)
