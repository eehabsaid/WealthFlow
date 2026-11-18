"""Error investigation: map a traceback / console error / message onto real source, then list root-cause HYPOTHESES.

Only the located frames and the quoted source are confirmed facts. Hypotheses are pattern-based leads, labelled as such, each
with the exact thing to verify next, so the model cannot present a guess as the diagnosis.
"""

from __future__ import annotations

import re

from ai.services.knowledge_index import evidence, relations, search

_PY_FRAME = re.compile(r'File "([^"]+)", line (\d+), in ([\w<>$.]+)')
_JS_FRAME = re.compile(r"(?:at\s+(?:async\s+)?([\w$.<>]+)\s*\(?)?(?:https?://[^/\s]+)?/?([\w./-]+\.(?:js|html)):(\d+)(?::\d+)?")
_EXC = re.compile(r"^\s*([A-Z]\w*(?:Error|Exception|Warning)|DoesNotExist|IntegrityError)\s*:?\s*(.*)$", re.M)
HYPOTHESES = (
    (r"NoneType.*attribute|Cannot read propert(?:y|ies) of (?:undefined|null)", "a value that can be None/undefined is used without a guard",
     "read the line and the code that produces the value; check the caller passes it"),
    (r"KeyError|not defined|ReferenceError", "a missing key / global that is not defined where it runs (for JS: script load order)",
     "app_symbol on the name; for JS check that its file is loaded before the caller (script_src order in the template)"),
    (r"DoesNotExist|MultipleObjectsReturned", "a query assumes exactly one row; owner scoping or missing data changes the count",
     "check the filter includes owner and what creates the row"),
    (r"IntegrityError|NOT NULL|UNIQUE constraint", "a required field is not set or a uniqueness rule is violated", "app_model_relations on the model; compare with the create path"),
    (r"Decimal|InvalidOperation|float|NaN", "mixed Decimal/float or an empty numeric value in a money calculation", "read the arithmetic; trace where each operand is produced"),
    (r"CSRF|403|Forbidden|PermissionDenied", "a permission/CSRF rule rejects the request", "read the view's decorators/mixins and the route wrapper"),
    (r"TypeError", "an argument has the wrong type or count", "compare the call site with the function signature"),
)


def _repo_path(conn, raw: str) -> str | None:
    norm = raw.replace("\\", "/")
    rows = conn.execute("SELECT path FROM files WHERE ? LIKE '%' || path OR path LIKE '%' || ? ORDER BY length(path) DESC LIMIT 1", (norm, norm.lstrip("/"))).fetchone()
    return rows["path"] if rows else None


def _frame_evidence(conn, path: str, line: int, context: int = 4) -> dict:
    row = conn.execute("SELECT id, path, name, qname, kind, line, end_line, parent, sig, doc FROM symbols WHERE path=? AND kind IN ('function','method','class') "
                       "AND line<=? AND end_line>=? ORDER BY end_line-line LIMIT 1", (path, line, line)).fetchone()
    if row is None:
        row = {"id": 0, "path": path, "name": "", "qname": "(module level)", "kind": "module", "line": max(1, line - context), "end_line": line + context,
               "parent": "", "sig": "", "doc": ""}
    item = evidence.build(conn, row, with_relations=bool(row["id"]), max_lines=1)
    item["failing_line"] = line
    if not item["stale"]:
        lo, hi = max(1, line - context), line + context
        item["content"] = "\n".join(evidence.read_lines(path, lo, hi)[0])   # the window around the failing line, whatever the symbol size
        item["line_start"], item["line_end"] = lo, hi
        item.pop("truncated", None)
        item["enclosing_symbol_lines"] = f"{row['line']}-{row['end_line']}" if row["id"] else None
    return item


def diagnose(conn, error_text: str, max_frames: int = 6) -> dict:
    text = (error_text or "")[:6000]
    exc = [m for m in _EXC.finditer(text)]
    last = exc[-1] if exc else None
    frames, seen = [], set()
    for m in _PY_FRAME.finditer(text):
        repo = _repo_path(conn, m.group(1))
        if repo and (repo, m.group(2)) not in seen:
            seen.add((repo, m.group(2)))
            frames.append((repo, int(m.group(2))))
    for m in _JS_FRAME.finditer(text):
        repo = _repo_path(conn, m.group(2))
        if repo and (repo, m.group(3)) not in seen:
            seen.add((repo, m.group(3)))
            frames.append((repo, int(m.group(3))))
    out = {"error": {"type": last.group(1) if last else None, "message": (last.group(2) if last else text.splitlines()[0] if text else "")[:300]},
           "confirmed_frames": [_frame_evidence(conn, p, n) for p, n in frames[:max_frames]]}
    if not frames:
        words = re.sub(r"['\"`]", " ", out["error"]["message"] or text)
        hits = search.search(conn, words, limit=4, max_lines=10)
        out["no_stack_frames"] = "no file:line frames mapped to this repository; closest code by words (NOT confirmed as the failing code)"
        out["candidates"] = hits.get("results", [])
    inner = out["confirmed_frames"][-1] if out["confirmed_frames"] else None
    if inner and inner.get("symbol") not in (None, "(module level)"):
        out["tests_for_failing_symbol"] = relations.find_tests(conn, inner["symbol"].split(".")[-1], 5)["tests"]
    out["hypotheses"] = [{"status": "HYPOTHESIS (not confirmed)", "cause": c, "verify_by": v} for rx, c, v in HYPOTHESES if re.search(rx, text, re.I)][:3]
    out["next_steps"] = ["read the innermost frame's function in full (app_read_file) and follow its arguments back to the caller",
                         "confirm or reject each hypothesis with a tool result before stating a root cause"]
    return out
