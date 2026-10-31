"""Judges the runs already stored in the database again with the CURRENT judges. No model is asked, so it takes seconds, not hours.
Used after a judge was corrected: a question dropped only because the old judge was too strict becomes kept (and the reverse). Only questions
whose runs are all stored (both attempts) are re-judged; test runs ("eval") are never touched."""

from __future__ import annotations

from collections import defaultdict
from typing import Callable

from ai_training.models import AgentTrace

from . import runner


def run(user, log: Callable[[str], None] = print) -> dict:
    groups = defaultdict(list)
    for t in AgentTrace.objects.filter(owner=user, source=AgentTrace.SOURCE_GENERATED).order_by("case_key", "attempt", "id"):
        groups[t.case_key].append(t)
    changed = {"now_kept": 0, "now_dropped": 0}
    for key, traces in groups.items():
        if len(traces) < 2 or traces[0].verdict == AgentTrace.PENDING:
            continue
        drop = runner.judge_case(traces)
        verdict = AgentTrace.DROPPED if drop else AgentTrace.KEPT
        if verdict != traces[0].verdict:
            changed["now_kept" if verdict == AgentTrace.KEPT else "now_dropped"] += 1
        for t in traces:
            t.verdict, t.drop_reasons = verdict, drop
            t.save(update_fields=["verdict", "drop_reasons"])
    log(f"Judged {len(groups)} stored questions again (no model asked): {changed['now_kept']} are now kept, {changed['now_dropped']} are now dropped.")
    return {"questions": len(groups), **changed}
