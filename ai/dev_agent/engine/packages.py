"""Work packages. The loop runs a whole plan as ONE conversation (the model keeps its own context, engine/budget.py compacts it), so a plan is ONE package that lists every
step and file. The package record stays because the ledger, the UI progress, the report and crash recovery are built on it."""

from __future__ import annotations


def single(plan: dict) -> list[dict]:
    """One package holding all steps and files of the plan."""
    files = sorted({f for step in plan["steps"] for f in step["files"]})
    title = plan["steps"][0]["title"] if len(plan["steps"]) == 1 else f"{plan['steps'][0]['title']} + {len(plan['steps']) - 1} more"
    return [{"id": "P1", "title": title, "steps": [s["id"] for s in plan["steps"]], "files": files, "est_tokens": 0, "status": "pending", "summary": "", "oversize": False}]
