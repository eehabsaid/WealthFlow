"""todo (the model's own checklist), submit_plan (the planning phase's way to hand in a plan) and subagent (a read-only helper conversation)."""

from __future__ import annotations

from ai.dev_agent.tools.registry import ToolError, schema, tool

STATES = ("pending", "in_progress", "done")
ITEM = {"type": "object", "properties": {"text": {"type": "string"}, "status": {"type": "string", "enum": list(STATES)}}, "required": ["text"]}


@tool("todo", "args {items: [{text, status: pending|in_progress|done}]}: write or update your checklist for a task with several steps. Send the WHOLE list each time; keep one item "
      "in_progress. The owner sees it live.", params=schema({"items": {"type": "array", "items": ITEM, "description": "the whole checklist"}}, ["items"]))
def todo(ctx, args):
    items = args.get("items")
    if not isinstance(items, list) or not items or len(items) > 40:
        raise ToolError("`items` must be a list of 1-40 entries like {\"text\": \"...\", \"status\": \"pending\"}")
    clean = []
    for item in items:
        text, status = (str(item.get("text") or "").strip(), str(item.get("status") or "pending").lower()) if isinstance(item, dict) else (str(item).strip(), "pending")
        if not text:
            raise ToolError("every item needs `text`")
        clean.append({"text": text[:200], "status": status if status in STATES else "pending"})
    if ctx.ledger:
        ctx.ledger.data["todos"] = clean
        ctx.ledger.save()
    ctx.emit({"type": "todo", "items": clean})
    return {"ok": True, "items": clean, "open": sum(i["status"] != "done" for i in clean)}


PLAN_PROPS = {"summary": "string", "steps": {"type": "array", "items": {"type": "object", "properties": {"title": {"type": "string"}, "files": {"type": "array", "items": {"type": "string"}}}, "required": ["title"]}},
              "files_add": {"type": "array", "items": {"type": "string"}}, "files_edit": {"type": "array", "items": {"type": "string"}},
              "files_delete": {"type": "array", "items": {"type": "string"}},
              "files_rename": {"type": "array", "items": {"type": "object", "properties": {"from": {"type": "string"}, "to": {"type": "string"}}, "required": ["from", "to"]}},
              "tests": {"type": "array", "items": {"type": "string"}}, "risks": {"type": "array", "items": {"type": "string"}}}


@tool("submit_plan", "args {summary, steps:[{title, files}], files_add, files_edit, files_delete, files_rename:[{from,to}], tests, risks}: hand in the implementation plan for the owner to "
      "approve. List EVERY file you will add, edit, delete or rename. Planning phase only. For a question or a task that needs no file change, just answer in text instead.",
      params=schema(PLAN_PROPS, ["summary", "steps"]), phases=("plan",))
def submit_plan(ctx, args):   # the loop intercepts this call; reaching here means it was used as an ordinary tool
    raise ToolError("submit_plan ends the planning phase; it is handled by the loop")


@tool("subagent", "args {task}: hand a self-contained READ-ONLY investigation to a helper (it can read, search and run read-only lookups, not change anything) and get its written answer. "
      "Use it to keep your own context small, e.g. 'find every caller of X and summarise how it is used'.", mutating=True,
      params=schema({"task": {"type": "string", "description": "what to find out; include the files/areas to look at and the form of the answer"}}, ["task"]), phases=("work",))
def subagent(ctx, args):
    from ai.dev_agent.engine import session
    task = str(args.get("task") or "").strip()
    if not task:
        raise ToolError("give the `task`")
    if ctx.provider is None:
        raise ToolError("no model is available to the subagent")
    sub = type(ctx)(**{**ctx.__dict__, "readonly": True, "scope": None, "seen": {}, "hidden": (*ctx.hidden, "subagent"), "attachments": None})
    res = session.run_phase(sub, ctx.provider, None, f"TASK: {task}\n\nInvestigate with the read-only tools and answer in plain text with file paths and line numbers. Do not plan.", {"final"},
                            min(ctx.settings["max_steps_per_package"], 40), attach=False, label="subagent")
    if res.kind == "stopped":
        raise ToolError(f"the subagent stopped: {res.reason}")
    return {"ok": True, "answer": str(res.payload)[:6000]}
