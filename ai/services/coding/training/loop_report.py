"""The plain-text report of a real agent-loop evaluation: one table per model, the verdict, and one line per task and model so every failure can be read."""

from __future__ import annotations


def _line(s: dict) -> str:
    return (f"{s['model']:34} {s['tasks']:>5} {s['success']:>5} {s['success_pct']:>6}% {s['qa']['success']:>4}/{s['qa']['tasks']:<3} {s['patch']['success']:>4}/{s['patch']['tasks']:<3}"
            f" {s['protected_touches']:>9} {s['timeouts']:>8} {s['invalid_replies']:>7} {s['median_seconds']:>9}")


def _cell(row: dict | None) -> str:
    if row is None:
        return "not run"
    return f"DONE {row['seconds']:.0f}s" if row["success"] else f"FAIL {row['seconds']:.0f}s: {row['why'] or row['status']}"[:110]


def report_text(summaries: list[dict], rows: dict[str, list[dict]], verdict_text: str, transcripts: str) -> str:
    head = f"{'model':34} {'tasks':>5} {'done':>5} {'done %':>7} {'qa':>8} {'patch':>8} {'protected':>9} {'timeouts':>8} {'nudges':>7} {'median s':>9}"
    lines = [f"--- real agent loop on {summaries[0]['tasks']} held-out tasks (the real dev agent, in a throw-away copy of the repo) ---", head, *map(_line, summaries), "",
             verdict_text, "",
             "done = qa: a final answer after reading files, citing only files that exist; patch: a plan, executed, and the agent's own final checks said VERIFIED.",
             "nudges = replies the agent had to reject as not valid JSON (the failure that made the single-turn model useless as an agent).",
             f"Full transcripts of every run (ledger, events, report): {transcripts}", "Nothing was switched in Settings. Read some failures and some answers yourself before deciding.", "",
             "--- per task ---"]
    names = [s["model"] for s in summaries]
    by_task = {m: {r["task_id"]: r for r in rows[m]} for m in names}
    kinds = {r["task_id"]: r["kind"] for m in names for r in rows[m]}
    for task_id in sorted(kinds):
        lines.append(f"{task_id} ({kinds[task_id]})")
        lines += [f"    {m:32} {_cell(by_task[m].get(task_id))}" for m in names]
    return "\n".join(lines)
