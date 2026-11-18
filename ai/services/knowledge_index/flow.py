"""Feature tracing (screen -> JS -> endpoint -> route -> view -> service -> model -> tests) and implementation comparison."""

from __future__ import annotations

import difflib
import re

from ai.services.knowledge_index import evidence, relations, search
from ai.services.knowledge_index.relations import lite

_HOLE = re.compile(r"<[^>]+>|\(\?P<[^>]+>[^)]*\)")


def _route_regex(pattern: str):
    esc = re.escape(pattern.lstrip("/")).replace("\\<", "<").replace("\\>", ">")
    return re.compile("^" + _HOLE.sub("[^/]+", esc).replace("\\^", "").replace("\\$", "") + "$")


def routes_for(conn, endpoint: str) -> list:
    url = endpoint.replace("{}", "x").lstrip("/")
    hits = []
    for r in conn.execute("SELECT id, path, name, qname, kind, line, end_line, parent, sig, doc FROM symbols WHERE kind='route'"):
        try:
            if _route_regex(r["name"]).match(url) or r["name"] and url.endswith(r["name"].lstrip("/")) and len(r["name"]) > 8:
                hits.append(r)
        except re.error:
            continue
    return hits


def _js_reach(conn, start: list, depth: int = 3) -> tuple[list, list]:
    """JS functions reachable from the start symbols (by global name) and the endpoint literals they contain."""
    seen, frontier, funcs, endpoints = set(), list(start), [], []
    for _ in range(depth):
        nxt = []
        for row in frontier:
            key = (row["path"], row["qname"])
            if key in seen:
                continue
            seen.add(key)
            funcs.append(row)
            endpoints += conn.execute("SELECT name, path, line, src FROM refs WHERE kind='endpoint' AND path=? AND src=?", (row["path"], row["qname"])).fetchall()
            for c in relations.callees(conn, row["path"], row["qname"]):
                nxt += [d for d in conn.execute("SELECT id, path, name, qname, kind, line, end_line, parent, sig, doc FROM symbols WHERE name=? "
                                                "AND path LIKE '%.js' AND kind IN ('function','method')", (c["name"],)).fetchall()]
        frontier = nxt[:12]
    return funcs, endpoints


def _python_side(conn, route) -> dict:
    views = [r["name"] for r in conn.execute("SELECT name FROM refs WHERE kind='route_view' AND path=? AND src=?", (route["path"], route["name"]))]
    layers = {"view": [], "service": [], "model": []}
    for v in views[:2]:
        for d in relations.definitions(conn, v, ("class", "function"))[:1]:
            layers["view"].append(lite(d))
            for lvl in relations.trace_calls(conn, d["qname"], "down", 2, 8).get("callees", []):
                for c in lvl:
                    for t in c["defs"][:1]:
                        if conn.execute("SELECT 1 FROM symbols WHERE kind='field' AND parent=? LIMIT 1", (c["name"],)).fetchone():
                            layers["model"].append(t)
                        elif "/models/" not in t["path"] and "/tests/" not in t["path"]:
                            layers["service"].append(t)
    return {k: list({(x["path"], x["symbol"]): x for x in v}.values())[:8] for k, v in layers.items()}


def trace_flow(conn, target: str) -> dict:
    out = {"target": target, "layers": [], "gaps": []}
    js = [r for r in relations.definitions(conn, target, ("function", "method")) if r["path"].endswith(".js")]
    routes = [r for r in conn.execute("SELECT id, path, name, qname, kind, line, end_line, parent, sig, doc FROM symbols WHERE kind='route' AND instr(lower(name), ?) > 0 LIMIT 6",
                                      (target.lower().strip("/"),))] if "/" in target or "-" in target or not js else []
    if not js and not routes:
        hits = search.search(conn, target, kinds=("function", "route", "component", "page_route", "page_doc"), limit=5, max_lines=3)
        out["resolved_from_search"] = [f"{h['symbol']} ({h['path']}:{h['line_start']})" for h in hits.get("results", [])]
        js = [r for r in (relations.definitions(conn, h["symbol"], ("function", "method")) for h in hits.get("results", [])) for r in r if r["path"].endswith(".js")][:3]
        routes = [r for h in hits.get("results", []) if h["kind"] == "route" for r in conn.execute("SELECT * FROM symbols WHERE kind='route' AND qname=?", (h["symbol"],))][:3]
    if js:
        ui = [c for r in js for c in relations.callers(conn, r["name"], 8) if c["how"] == "handler" or c["path"].endswith(".html")]
        out["layers"].append({"layer": "ui (templates / handlers)", "items": ui[:8] or []})
        if not ui:
            out["gaps"].append("no template handler or script tag references the JS entry point; it may be called from other JS only")
        funcs, endpoints = _js_reach(conn, js)
        out["layers"].append({"layer": "frontend JS", "items": [lite(f) for f in funcs[:10]]})
        out["layers"].append({"layer": "API calls found in that JS", "items": [{"endpoint": e["name"], "path": e["path"], "line": e["line"], "in": e["src"]} for e in endpoints[:10]]})
        if not endpoints:
            out["gaps"].append("no '/api/...' string literal in the JS reachable from here: the URL may be built dynamically, or the screen only uses local data")
        for e in endpoints[:6]:
            routes += routes_for(conn, e["name"])
    seen = set()
    for r in routes:
        if r["id"] in seen:
            continue
        seen.add(r["id"])
        pat = _route_regex(r["name"])
        front = [{"endpoint": e["name"], "path": e["path"], "line": e["line"], "in": e["src"]} for e in
                 conn.execute("SELECT name, path, line, src FROM refs WHERE kind='endpoint' AND path NOT LIKE '%.py'") if pat.match(e["name"].replace("{}", "x"))]
        out["layers"].append({"layer": f"route {r['name']}", "items": [lite(r)], "frontend_callers": front[:8], **_python_side(conn, r)})
    if not any(l["layer"].startswith("route") for l in out["layers"]):
        out["gaps"].append("no Django route matched; the data may come from an inline template context, a different endpoint spelling, or an include() prefix")
    return out


def compare(conn, a: str, b: str, max_lines: int = 60) -> dict:
    ra, rb = relations.definitions(conn, a, ("function", "method", "class")), relations.definitions(conn, b, ("function", "method", "class"))
    if not ra or not rb:
        return {"error": f"definition not found for {a if not ra else b}; use app_search to get the exact name"}
    ea, eb = (evidence.build(conn, r[0], max_lines=max_lines) for r in (ra, rb))
    if ea["stale"] or eb["stale"]:
        return {"error": "a file changed since indexing; retry", "a": ea, "b": eb}
    la, lb = [x.split(": ", 1)[-1] for x in ea["content"].splitlines()], [x.split(": ", 1)[-1] for x in eb["content"].splitlines()]
    diff = list(difflib.unified_diff(la, lb, a, b, lineterm="", n=1))[:80]
    ca, cb = set(ea["relations"]["calls"]), set(eb["relations"]["calls"])
    return {"a": ea, "b": eb, "only_in_a_calls": sorted(ca - cb), "only_in_b_calls": sorted(cb - ca), "shared_calls": sorted(ca & cb), "diff": "\n".join(diff),
            "other_definitions": {"a": len(ra) - 1, "b": len(rb) - 1}}
