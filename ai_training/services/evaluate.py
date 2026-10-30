"""The model test: the same fixed questions for the old and the new model, judged by the same code judges, then a report.

For each model: Ollama is restarted (clean GPU), the model name in Settings is set to it, one warm-up question loads it (not counted), then
every test question is asked once through the real chat endpoint and timed. At the end (or after a crash / Ctrl+C) the model name in Settings is
put back; if the PC itself dies mid-test, the next run puts it back first. Nothing is ever switched for good: this only reports."""

from __future__ import annotations

import json
import os
import time
from datetime import datetime
from typing import Callable

from ai_training.models import AgentTrace

from . import eval_report, judges, ollama_ctl, runner, testset, train_stage
from .config import TrainConfig
from .config import load as load_config

MARKER = "eval_restore.json"


class EvalError(Exception):
    """A plain-words reason the test cannot go on."""


def set_model(name: str, user=None) -> None:
    from core.models import AppSettings

    AppSettings.set("ai_model", name, user=None)
    if user is not None and AppSettings.get("ai_model", "", user=user) != name:
        raise EvalError(f"The user has their own AI model setting, so '{name}' would not be used. Set 'use general AI settings' for this user and run again.")


def recover(out_dir: str, log: Callable[[str], None]) -> None:
    """An earlier test was killed before it could restore the model name: restore it now."""
    path = os.path.join(out_dir, MARKER)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            original = json.load(fh).get("ai_model", "")
        if original:
            set_model(original)
            log(f"An earlier test did not finish: your model '{original}' is set again in Settings.")
        os.remove(path)


def names(current: str, suffix: str) -> tuple[str, str]:
    """(old, new): the model in Settings and the same name + suffix; if Settings already holds the new one, the old is the name without it."""
    return (current[: -len(suffix)], current) if suffix and current.endswith(suffix) else (current, current + suffix)


def prepare(cfg: TrainConfig, model: str, models: tuple, url: str, user, log: Callable[[str], None]) -> str:
    """Clean start for one model; returns how: 'restarted' or 'unloaded'."""
    how = "restarted"
    if not ollama_ctl.restart(cfg.ollama_models_dir, url, log):
        for other in models:   # cannot restart: at least make sure neither model sits in the GPU
            train_stage.free_gpu(other, log)
        how = "unloaded"
    seen = ollama_ctl.installed(url)
    if seen is None:
        raise EvalError("Ollama does not answer. Start Ollama and run again.")
    if ollama_ctl.normal(model) not in seen:
        raise EvalError(f"Ollama cannot see the model '{model}' (it sees: {', '.join(sorted(seen)) or 'nothing'}). If Ollama was just restarted, "
                        f"close it in Task Manager, open it from the Start menu and run again.")
    set_model(model, user)
    return how


def timed_ask(user, case) -> tuple[dict, AgentTrace | None]:
    start = time.monotonic()
    trace, problem = runner.ask(user, case, 1, source=AgentTrace.SOURCE_EVAL)
    return {"seconds": round(time.monotonic() - start, 1), "problem": problem}, trace


def run_model(user, cases, model: str, log: Callable[[str], None]) -> list[dict]:
    log(f"Warm-up for {model} (loads it into the GPU; not counted) ...")
    _, warm = timed_ask(user, cases[0])
    if warm:
        warm.delete()
    rows = []
    for i, case in enumerate(cases, 1):
        timing, trace = timed_ask(user, case)
        reasons = [timing["problem"]] if trace is None else judges.judge_attempt(trace)
        rows.append({"key": case.key, "question": case.question, "expected": case.expected, "passed": not reasons, "reasons": reasons,
                     "seconds": timing["seconds"], "answer": trace.answer if trace else ""})
        if trace:
            trace.delete()
        log(f"[{model}] [{i}/{len(cases)}] {'PASS' if not reasons else 'FAIL'} {case.key} {timing['seconds']}s {', '.join(reasons)}")
    return rows


def run(user, cfg: TrainConfig, current: str, *, out_dir: str, log: Callable[[str], None] = print) -> dict:
    from core.models import AppSettings

    if str(AppSettings.get("ai_provider", "ollama", user=None) or "ollama").lower() != "ollama":
        return {"status": "not_ollama", "report": "The test needs Ollama as the AI provider (Settings > AI Advisor)."}
    os.makedirs(out_dir, exist_ok=True)
    recover(out_dir, log)
    old, new = names(current, cfg.model_suffix)
    cases = testset.build(user, limit=cfg.eval_questions, seed=cfg.eval_seed)
    if not cases:
        return {"status": "no_questions", "report": "No test questions could be built from your data."}
    AgentTrace.objects.filter(source=AgentTrace.SOURCE_EVAL).delete()
    url, marker, results, how = ollama_ctl.base_url(), os.path.join(out_dir, MARKER), {}, {}
    log(f"Test: {len(cases)} questions for each of '{old}' and '{new}'. Do not use the AI in the app until it ends. Your model name is restored at the end.")
    with open(marker, "w", encoding="utf-8") as fh:
        json.dump({"ai_model": current}, fh)
    try:
        for model in (old, new):
            how[model] = prepare(cfg, model, (old, new), url, user, log)
            results[model] = run_model(user, cases, model, log)
    except EvalError as exc:
        return {"status": "blocked", "report": str(exc)}
    finally:
        set_model(current)
        if os.path.exists(marker):
            os.remove(marker)
        AgentTrace.objects.filter(source=AgentTrace.SOURCE_EVAL).delete()
    sides = {k: {"name": m, "rows": results[m], "stats": eval_report.stats(results[m])} for k, m in (("old", old), ("new", new))}
    head, why = eval_report.verdict(sides["old"]["stats"], sides["new"]["stats"], cfg.eval_min_gain_points, cfg.eval_max_slower_percent)
    info = {"when": datetime.now().strftime("%Y-%m-%d %H:%M"), "verdict": head, "why": why, **sides,
            "reset": "restarted" if set(how.values()) == {"restarted"} else "NOT restarted, only unloaded (speed less clean)"}
    paths = eval_report.write_files(out_dir, info)
    return {"status": "done", "verdict": head, "report": eval_report.format_text(info), "paths": paths}


def dry(user, cfg: TrainConfig, current: str, log: Callable[[str], None] = print) -> dict:
    """Readiness check, no questions asked and nothing restarted: how many test questions exist and whether Ollama sees both models."""
    old, new = names(current, cfg.model_suffix)
    cases = testset.build(user, limit=cfg.eval_questions, seed=cfg.eval_seed)
    seen = ollama_ctl.installed(ollama_ctl.base_url())
    log(f"Test questions: {len(cases)} (each model gets all of them; fewer than {eval_report.MIN_QUESTIONS} = no fair decision).")
    for model in (old, new):
        log(f"[{'ok' if seen is not None and ollama_ctl.normal(model) in seen else 'MISSING'}] Ollama has the model '{model}'")
    return {"status": "dry_run", "questions": len(cases), "ready": bool(seen is not None and len(cases) >= eval_report.MIN_QUESTIONS
                                                                      and all(ollama_ctl.normal(m) in seen for m in (old, new)))}


def current_model() -> str:
    from core.models import AppSettings

    return str(AppSettings.get("ai_model", "", user=None) or "").strip()


def stage(user, *, dry_run: bool, out_dir: str, log: Callable[[str], None]) -> dict:
    """The `evaluate` stage of the one command: the model in Settings against the same name + suffix."""
    model = current_model()
    if not model:
        log("No model name is set in Settings > AI Advisor: nothing to test.")
        return {"status": "no_model", "report": "No model name is set in Settings > AI Advisor."}
    cfg = load_config()
    return dry(user, cfg, model, log) if dry_run else run(user, cfg, model, out_dir=out_dir, log=log)
