"""Task routes: list/create/inspect, live events (JSON catch-up or server-sent events), approve/reject/resume/stop, files, diffs, report."""

from __future__ import annotations

import re

from ..core.project import PathError
from ..engine import report as report_mod
from ..service import diffs
from .http import HttpError, Req, Resp
from .sse import stream_events

ID = r"(?P<id>[^/]+)"


def _int(value, default=0) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return default


def list_tasks(r: Req):
    return {"tasks": r.service.list_tasks()}


def create_task(r: Req):
    """Optional: `attachments` (files/images, see engine.attachments) and `provider`/`model` for this task only."""
    body = r.body or {}
    override = {k: body[k] for k in ("provider", "model") if k in body}
    return Resp({"id": r.service.start_task(r.field("goal"), body.get("attachments"), override)}, 202)


def get_task(r: Req):
    data = r.service.ledger(r.match["id"]).data
    return {k: v for k, v in data.items() if k not in ("events", "snapshots")}


def events(r: Req):
    task_id = r.match["id"]
    log = r.service.log(task_id)
    after = max(_int(r.query.get("after")), _int(r.headers.get("Last-Event-ID")))
    if r.query.get("stream") == "1" or "text/event-stream" in (r.headers.get("Accept") or ""):
        return stream_events(log, after, r.server.stopping)
    wait = min(_int(r.query.get("wait")), 25)
    found = log.wait(after, wait) if wait else log.after(after)
    return {"events": found, "next": found[-1]["seq"] if found else after}


def action(name: str):
    def run(r: Req):
        getattr(r.service, {"approve": "approve_plan", "reject": "reject_plan", "resume": "resume"}[name])(r.match["id"])
        return {"ok": True}
    return run


def stop(r: Req):
    return {"stopped": r.service.stop()}


def _counts(ledger, project, rel: str) -> dict:
    """Added/removed line counts for the changed-files list; None when there is no text diff."""
    try:
        found = diffs.line_counts(ledger, project, rel)
    except (diffs.NotInTask, PathError, OSError):
        found = None
    return {"added": found[0] if found else None, "removed": found[1] if found else None}


def files(r: Req):
    ledger = r.service.ledger(r.match["id"])
    return {"files": [{"path": p, **f, **_counts(ledger, r.project, p)} for p, f in sorted(ledger.data["files"].items())]}


def _diff_call(r: Req, fn, *extra):
    ledger = r.service.ledger(r.match["id"])
    try:
        return fn(ledger, r.project, r.need("path"), *extra)
    except diffs.NotInTask as exc:
        raise HttpError(404, "not_found", str(exc)) from exc
    except PathError as exc:
        raise HttpError(400, "bad_request", str(exc)) from exc


def diff(r: Req):
    return _diff_call(r, diffs.file_diff)


def file_content(r: Req):
    version = r.query.get("version", "current")
    if version not in ("original", "current"):
        raise HttpError(400, "bad_request", "version must be original or current")
    data = _diff_call(r, diffs.original_bytes if version == "original" else diffs.current_bytes)
    if data is None:
        raise HttpError(404, "not_found", f"no {version} version of this file (it did not exist then)")
    try:
        return Resp(data.decode("utf-8"), 200, "text/plain; charset=utf-8")
    except UnicodeDecodeError as exc:
        raise HttpError(415, "binary", "binary file") from exc


def report(r: Req):
    ledger = r.service.ledger(r.match["id"])
    path = ledger.dir / "report.md"
    return Resp(path.read_text(encoding="utf-8") if path.is_file() else report_mod.build(ledger), 200, "text/markdown; charset=utf-8")


def approvals(r: Req):
    return {"approvals": r.service.state()["approvals"]}


def answer(r: Req):
    if not r.service.answer_approval(r.match["aid"], bool(r.field("approve", bool))):
        raise HttpError(404, "not_found", "no such pending approval (already answered?)")
    return {"ok": True}


ROUTES = [
    ("GET", re.compile(r"/api/tasks"), list_tasks),
    ("POST", re.compile(r"/api/tasks"), create_task),
    ("GET", re.compile(rf"/api/tasks/{ID}"), get_task),
    ("GET", re.compile(rf"/api/tasks/{ID}/events"), events),
    ("POST", re.compile(rf"/api/tasks/{ID}/approve"), action("approve")),
    ("POST", re.compile(rf"/api/tasks/{ID}/reject"), action("reject")),
    ("POST", re.compile(rf"/api/tasks/{ID}/resume"), action("resume")),
    ("GET", re.compile(rf"/api/tasks/{ID}/files"), files),
    ("GET", re.compile(rf"/api/tasks/{ID}/diff"), diff),
    ("GET", re.compile(rf"/api/tasks/{ID}/file"), file_content),
    ("GET", re.compile(rf"/api/tasks/{ID}/report"), report),
    ("POST", re.compile(r"/api/stop"), stop),
    ("GET", re.compile(r"/api/approvals"), approvals),
    ("POST", re.compile(r"/api/approvals/(?P<aid>a\d+)"), answer),
]
