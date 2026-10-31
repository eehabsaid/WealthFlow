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

from . import eval_report, judges, ollama_ctl, ollama_stage, runner, testset, train_stage
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


def names(current: str, cfg) -> tuple[str, str, str]:
    """(original, current best, new): the base model, base + an earlier suffix, base + the new suffix. Whichever one Settings holds, the base is found."""
    base = ollama_stage.base_name(current, cfg)
    return base, cfg.best_model or base + cfg.previous_suffixes[0], cfg.new_model or base + cfg.model_suffix


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
                     "category": case.meta.get("category", ""), "lang": case.meta.get("lang", ""),
                     "seconds": timing["seconds"], "answer": trace.answer if trace else ""})
        if trace:
            trace.delete()
        log(f"[{model}] [{i}/{len(cases)}] {'PASS' if not reasons else 'FAIL'} {case.key} {timing['seconds']}s {', '.join(r.split(':')[0] for r in reasons)}")
    return rows


def lineup(cfg: TrainConfig, current: str, seen) -> list[tuple[str, str]]:
    """[(role, model)] in test order: original, current best (only if Ollama has it), new."""
    base, best, new = names(current, cfg)
    have = lambda m: seen is not None and ollama_ctl.normal(m) in seen   # noqa: E731
    return [("original", base)] + ([("current best", best)] if have(best) else []) + [("new", new)]


def run(user, cfg: TrainConfig, current: str, *, out_dir: str, log: Callable[[str], None] = print) -> dict:
    from core.models import AppSettings

    if str(AppSettings.get("ai_provider", "ollama", user=None) or "ollama").lower() != "ollama":
        return {"status": "not_ollama", "report": "The test needs Ollama as the AI provider (Settings > AI Advisor)."}
    os.makedirs(out_dir, exist_ok=True)
    recover(out_dir, log)
    url = ollama_ctl.base_url()
    roles = lineup(cfg, current, ollama_ctl.installed(url))
    cases, retired = testset.build(user, out_dir=out_dir, per_category=cfg.eval_per_category, seed=cfg.eval_seed)
    if not cases:
        return {"status": "no_questions", "report": "No test questions could be built from your data."}
    AgentTrace.objects.filter(source=AgentTrace.SOURCE_EVAL).delete()
    marker, results, how = os.path.join(out_dir, MARKER), {}, {}
    log(f"Test: {len(cases)} frozen questions for each of: " + ", ".join(f"{r} '{m}'" for r, m in roles) + ". Do not use the AI in the app until it ends. Your model name is restored at the end.")
    with open(marker, "w", encoding="utf-8") as fh:
        json.dump({"ai_model": current}, fh)
    try:
        for _, model in roles:
            how[model] = prepare(cfg, model, tuple(m for _, m in roles), url, user, log)
            results[model] = run_model(user, cases, model, log)
    except EvalError as exc:
        return {"status": "blocked", "report": str(exc)}
    finally:
        set_model(current)
        if os.path.exists(marker):
            os.remove(marker)
        AgentTrace.objects.filter(source=AgentTrace.SOURCE_EVAL).delete()
    sides = [{"role": r, "name": m, "rows": results[m], "stats": eval_report.stats(results[m])} for r, m in roles]
    rival = sides[-2]
    head, why = eval_report.verdict(rival["stats"], sides[-1]["stats"], cfg.eval_min_gain_points, cfg.eval_max_slower_percent)
    info = {"when": datetime.now().strftime("%Y-%m-%d %H:%M"), "verdict": head, "why": why, "models": sides, "rival": f"{rival['role']} {rival['name']}",
            "retired": retired, "regressions": eval_report.regressions(rival["rows"], sides[-1]["rows"]),
            "reset": "restarted" if set(how.values()) == {"restarted"} else "NOT restarted, only unloaded (speed less clean)"}
    paths = eval_report.write_files(out_dir, info)
    return {"status": "done", "verdict": head, "report": eval_report.format_text(info), "paths": paths}


def dry(user, cfg: TrainConfig, current: str, out_dir: str, log: Callable[[str], None] = print) -> dict:
    """Readiness check, no questions asked and nothing restarted: how many frozen test questions exist and whether Ollama sees the models."""
    seen = ollama_ctl.installed(ollama_ctl.base_url())
    base, _, new = names(current, cfg)
    cases, retired = testset.build(user, out_dir=out_dir, per_category=cfg.eval_per_category, seed=cfg.eval_seed)
    log(f"Frozen test questions: {len(cases)} (retired: {len(retired)}; fewer than {eval_report.MIN_QUESTIONS} = no fair decision).")
    for role, model in lineup(cfg, current, seen):
        log(f"[ok] Ollama has the {role} model '{model}'")
    ready = seen is not None and all(ollama_ctl.normal(m) in seen for m in (base, new))
    if not ready:
        log(f"[MISSING] The test needs both '{base}' and '{new}' in Ollama.")
    return {"status": "dry_run", "questions": len(cases), "ready": bool(ready and len(cases) >= eval_report.MIN_QUESTIONS)}


def current_model() -> str:
    from core.models import AppSettings

    return str(AppSettings.get("ai_model", "", user=None) or "").strip()


def stage(user, *, dry_run: bool, out_dir: str, log: Callable[[str], None]) -> dict:
    """The `evaluate` stage of the one command: original, current best and new model on the same frozen questions."""
    model = current_model()
    if not model:
        log("No model name is set in Settings > AI Advisor: nothing to test.")
        return {"status": "no_model", "report": "No model name is set in Settings > AI Advisor."}
    cfg = load_config()
    return dry(user, cfg, model, out_dir, log) if dry_run else run(user, cfg, model, out_dir=out_dir, log=log)
