"""The whole training-data job behind ONE command (`python manage.py ai_training`).

Stages, in order: questions from the live data -> ask the model (twice each) -> judge -> export files + report.
It resumes by itself: a question already kept for the same data is skipped, a dropped or unfinished one is asked again.
Later milestones (train, evaluate, switch) are added as further stages here, so the command stays one."""

from __future__ import annotations

import os
from typing import Callable

from django.contrib.auth import get_user_model

from ai_training.models import AgentTrace

from . import export, generator, inspect_file, ollama_stage, runner, testset, train_stage
from .config import load as load_config

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")


def pick_user(username: str = ""):
    """The named user, else the first sysadmin of the app, else the first Django superuser."""
    from core.models import UserProfile

    users = get_user_model().objects
    if username:
        return users.get(username=username)
    profile = UserProfile.objects.filter(is_sysadmin=True).select_related("user").order_by("id").first()
    user = profile.user if profile else users.filter(is_superuser=True).order_by("id").first()
    if user is None:
        raise LookupError("No sysadmin or superuser found; pass --user <username>")
    return user


def split_done(user, cases, fresh: bool = False) -> tuple[list, int]:
    """(cases still to ask, number skipped). Old traces of a case that will be asked again are deleted first."""
    done = {} if fresh else {t.case_key: t.expected for t in AgentTrace.objects.filter(owner=user, verdict=AgentTrace.KEPT, attempt=1)}
    todo = [c for c in cases if done.get(c.key) != c.expected]
    AgentTrace.objects.filter(owner=user, case_key__in=[c.key for c in todo]).delete()
    return todo, len(cases) - len(todo)


def export_files(user, out_dir: str) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    paths = {"jsonl": os.path.join(out_dir, "agent_traces.jsonl"), "excel": os.path.join(out_dir, "agent_runs.xlsx"),
             "report": os.path.join(out_dir, "report.txt")}
    kept = export.export_jsonl(paths["jsonl"], user)
    inspect_file.export_xlsx(paths["excel"], user)
    text = export.format_report(export.report(user))
    with open(paths["report"], "w", encoding="utf-8") as fh:
        fh.write(text + "\n")
    return {"paths": paths, "kept": kept, "report": text}


def collect(user, *, limit: int, seed, fresh: bool, attempts: int, log) -> dict:
    blocked = testset.train_blocked(os.path.join(OUTPUT_DIR, testset.FILE))
    cases = generator.generate(user, limit=limit, seed=seed, blocked=blocked)
    todo, skipped = split_done(user, cases, fresh)
    log(f"{len(cases)} questions from the live data: {len(todo)} to ask, {skipped} already proven.")
    summary = runner.run(user, todo, attempts=attempts, log=log) if todo else {"cases": 0, "kept": 0, "dropped": 0, "reasons": {}}
    return {"asked": summary, "skipped": skipped}


def current_model() -> str:
    from core.models import AppSettings

    return str(AppSettings.get("ai_model", "", user=None) or "").strip()


def train_and_register(user, *, dry_run: bool, fresh: bool, min_traces, log) -> dict:
    cfg = load_config(min_traces=min_traces)
    model = current_model()
    if not model:
        log("No model name is set in Settings > AI Advisor: nothing to train from.")
        return {"status": "no_model"}
    base = ollama_stage.base_name(model, cfg)   # train from and register beside the ORIGINAL model, whichever one Settings holds now
    outcome = train_stage.run(cfg, user, base, dry_run=dry_run, fresh=fresh, log=log)
    if outcome["gguf"]:
        name = cfg.new_model or ollama_stage.new_name(base, cfg.model_suffix)
        ok = ollama_stage.register(base, outcome["gguf"], name, train_stage.run_dir(cfg), log)
        outcome.update({"new_model": name if ok else "", "status": "registered" if ok else "register_failed"})
        log(f"New model '{name}' is in Ollama. Your model in Settings ('{model}') is unchanged and still the one in use." if ok else "Registering the model in Ollama failed.")
    return outcome


def run_all(user, *, limit: int = 0, seed: int | None = None, fresh: bool = False, attempts: int = runner.ATTEMPTS,
            out_dir: str = OUTPUT_DIR, log: Callable[[str], None] = print, stages: tuple = ("collect", "train"),
            dry_run: bool = False, min_traces: int | None = None) -> dict:
    result = {"asked": None, "skipped": 0}
    if "collect" in stages and not dry_run:
        result.update(collect(user, limit=limit, seed=seed, fresh=fresh, attempts=attempts, log=log))
    result.update(export_files(user, out_dir))
    if "train" in stages:
        result["training"] = train_and_register(user, dry_run=dry_run, fresh=fresh, min_traces=min_traces, log=log)
    return result
