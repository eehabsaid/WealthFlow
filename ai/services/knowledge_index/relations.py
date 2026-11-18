"""Relationship lookup over the index: definitions, callers, callees, call traces, model relations, tests.

Callers/callees are matched by NAME (Python calls and JS script-globals have no import graph to follow). Results say so when a
name has several definitions, so a trace is never presented as more certain than it is.
"""

from __future__ import annotations

COLS = "id, path, name, qname, kind, line, end_line, parent, sig, doc"
USES = ("call", "ident", "import", "handler", "route_view", "fk", "endpoint")
DEF_KINDS = ("function", "method", "class", "variable", "route", "component")


def lite(row) -> dict:
    return {"symbol": row["qname"], "kind": row["kind"], "path": row["path"], "line_start": row["line"], "line_end": row["end_line"]}


def definitions(conn, name: str, kinds=DEF_KINDS) -> list:
    last = name.split(".")[-1]
    marks = ",".join("?" * len(kinds))
    return conn.execute(f"SELECT {COLS} FROM symbols WHERE (name=? OR qname=?) AND kind IN ({marks}) ORDER BY kind='class' DESC, path LIMIT 20",
                        (last, name, *kinds)).fetchall()


def callers(conn, name: str, limit: int = 25) -> list[dict]:
    last = name.split(".")[-1]
    defs = definitions(conn, last)
    rows = conn.execute("SELECT path, line, src, kind FROM refs WHERE name=? AND kind IN (%s) ORDER BY path, line LIMIT 400" % ",".join("?" * len(USES)),
                        (last, *USES)).fetchall()
    inside = {(d["path"], n) for d in defs for n in range(d["line"], d["end_line"] + 1)}
    out, seen = [], set()
    for r in rows:
        key = (r["path"], r["line"], r["src"])
        if (r["path"], r["line"]) in inside or key in seen:
            continue
        seen.add(key)
        out.append({"path": r["path"], "line": r["line"], "in": r["src"] or "(top level)", "how": r["kind"]})
    return out[:limit]


def callees(conn, path: str, qname: str) -> list[dict]:
    rows = conn.execute("SELECT DISTINCT name, kind FROM refs WHERE path=? AND (src=? OR src LIKE ?) AND kind IN ('call','ident','fk','route_view','endpoint') "
                        "LIMIT 200", (path, qname, qname + ".%")).fetchall()
    out = []
    for r in rows:
        if r["kind"] == "endpoint":
            out.append({"name": r["name"], "kind": "endpoint", "defs": []})
            continue
        defs = [d for d in definitions(conn, r["name"], ("function", "method", "class")) if (d["path"], d["qname"]) != (path, qname)]
        if defs:
            out.append({"name": r["name"], "kind": r["kind"], "defs": [lite(d) for d in defs[:3]], "ambiguous": len(defs) > 3 or None})
    return out


def trace_calls(conn, name: str, direction: str = "both", depth: int = 2, width: int = 8) -> dict:
    defs = definitions(conn, name, ("function", "method", "class"))
    if not defs:
        return {"symbol": name, "found": False, "note": "no function/method/class with that name in the index; use app_search"}
    root = defs[0]
    out = {"symbol": root["qname"], "found": True, "definition": lite(root),
           "other_definitions": [lite(d) for d in defs[1:4]] or None}
    if direction in ("up", "both"):
        levels, frontier, seen = [], [root["name"]], {root["name"]}
        for _ in range(depth):
            level = []
            for n in frontier:
                level += [{**c, "of": n} for c in callers(conn, n, width)]
            levels.append(level[: width * 3])
            frontier = [c["in"].split(".")[-1] for c in level if c["in"] != "(top level)" and c["in"].split(".")[-1] not in seen][:width]
            seen.update(frontier)
        out["callers"] = levels
    if direction in ("down", "both"):
        levels, frontier, seen = [], [(root["path"], root["qname"])], {root["qname"]}
        for _ in range(depth):
            level, nxt = [], []
            for p, q in frontier:
                for c in callees(conn, p, q)[:width]:
                    level.append({**c, "of": q})
                    nxt += [(d["path"], d["symbol"]) for d in c["defs"][:1] if d["symbol"] not in seen]
                    seen.update(d["symbol"] for d in c["defs"][:1])
            levels.append(level)
            frontier = nxt[:width]
        out["callees"] = levels
    return out


def _test_refs(conn, names: list[str], module: str = "") -> dict:
    by_file: dict = {}
    for name in names:
        rows = conn.execute("SELECT r.path, r.line, r.src, r.kind FROM refs r JOIN files f ON f.path=r.path WHERE f.is_test=1 AND "
                            "(r.name=? OR (?<>'' AND r.name LIKE ?)) AND r.kind IN ('call','ident','import') ORDER BY r.path, r.line LIMIT 200",
                            (name, module, module + "%")).fetchall()
        for r in rows:
            by_file.setdefault(r["path"], []).append({"line": r["line"], "in": r["src"], "how": r["kind"], "name": name})
    return by_file


def find_tests(conn, target: str, limit: int = 15) -> dict:
    is_path = "/" in target or target.endswith((".py", ".js"))
    last = target.rsplit("/", 1)[-1].rsplit(".", 1)[0] if is_path else target.split(".")[-1]
    module = target[:-3].replace("/", ".") if target.endswith(".py") else ""
    direct = _test_refs(conn, [last], module)
    seeds = [r["name"] for r in conn.execute("SELECT name FROM symbols WHERE path=? AND parent='' AND kind IN ('function','class') LIMIT 25", (target,))] if is_path \
        else [last]
    importers = {r["path"] for r in conn.execute("SELECT DISTINCT path FROM refs WHERE kind='import' AND name LIKE ?", (module + "%",))} if module else None
    callers_of = {c["in"].split(".")[0] for n in seeds for c in callers(conn, n, 30) if c["in"] != "(top level)" and "/tests/" not in "/" + c["path"]
                  and (importers is None or c["path"] in importers)}
    second = {c["in"].split(".")[0] for n in sorted(callers_of)[:15] for c in callers(conn, n, 20) if c["in"] != "(top level)" and "/tests/" not in "/" + c["path"]}
    indirect = {p: h for p, h in _test_refs(conn, sorted(callers_of | second)[:40]).items() if p not in direct}
    names = conn.execute("SELECT path, qname, line FROM symbols WHERE kind='method' AND path IN (SELECT path FROM files WHERE is_test=1) AND "
                         "instr(tokens, ?) > 0 LIMIT 10", (last.lower().replace("_", " "),)).fetchall()
    fmt = lambda src: [{"path": p, "references": h[:5], "reference_count": len(h)} for p, h in list(src.items())[:limit]]   # noqa: E731
    return {"target": target, "tests": fmt(direct), "test_files": len(direct), "indirect_tests": fmt(indirect),
            "indirect_note": "tests that exercise the code only through its callers, up to two call levels (listed in 'via_callers')" if indirect else None,
            "via_callers": sorted(callers_of | second)[:12] if indirect else None,
            "tests_named_after_it": [f"{n['path']}:{n['line']} {n['qname']}" for n in names],
            "covered": bool(direct or indirect), "directly_tested": bool(direct),
            "note": "matched by name: a test file that mentions the name, not a measured coverage report"}


def model_relations(conn, model: str) -> dict:
    cls = [d for d in definitions(conn, model, ("class",)) if conn.execute("SELECT 1 FROM symbols WHERE parent=? AND kind='field' AND path=? LIMIT 1",
                                                                          (d["name"], d["path"])).fetchone()]
    if not cls:
        return {"model": model, "found": False, "note": "no Django model with that name in the index; app_search 'ClassName' to find the real name"}
    m = cls[0]
    fields = conn.execute("SELECT name, sig, line FROM symbols WHERE parent=? AND kind='field' AND path=? ORDER BY line", (m["name"], m["path"])).fetchall()
    out_fk = conn.execute("SELECT src, name, line FROM refs WHERE kind='fk' AND path=? AND src LIKE ?", (m["path"], m["name"] + ".%")).fetchall()
    in_fk = conn.execute("SELECT path, src, line FROM refs WHERE kind='fk' AND name=? ORDER BY path", (m["name"],)).fetchall()
    ops = conn.execute("SELECT path, name, line FROM symbols WHERE kind='migration_op' AND instr(lower(name), ?) > 0 ORDER BY path LIMIT 15",
                       (m["name"].lower(),)).fetchall()
    layers: dict = {}
    for r in conn.execute("SELECT path, COUNT(*) n FROM refs WHERE name=? AND kind IN ('call','ident','import') AND path<>? GROUP BY path ORDER BY n DESC LIMIT 12",
                          (m["name"], m["path"])):
        layers.setdefault(r["path"].split("/")[1] if r["path"].count("/") > 1 else r["path"], []).append(f"{r['path']} ({r['n']})")
    names = [f["name"] for f in fields]
    return {"model": m["qname"], "found": True, "definition": lite(m), "fields": [{"name": f["name"], "line": f["line"], "def": f["sig"][:110]} for f in fields],
            "multi_tenant_owner_field": "owner" in names, "has_legacy_user_field": "user" in names and "owner" not in names,
            "foreign_keys_out": [{"field": r["src"], "to": r["name"], "line": r["line"]} for r in out_fk],
            "referenced_by": [{"model_field": r["src"], "path": r["path"], "line": r["line"]} for r in in_fk],
            "migrations": [f"{o['path']}:{o['line']} {o['name']}" for o in ops], "used_in": layers, "tests": find_tests(conn, m["name"], 6)["tests"]}


def i18n_gaps(conn, limit: int = 20) -> dict:
    """Translation keys present in en but missing in ar / fr / de (from the indexed locale files)."""
    en = {r["name"] for r in conn.execute("SELECT name FROM symbols WHERE kind='i18n_key'")}
    out = {}
    for lang in ("ar", "fr", "de"):
        have = {r["name"] for r in conn.execute("SELECT name FROM symbols WHERE kind='i18n_value' AND parent=?", (lang,))}
        missing = sorted(en - have) if have else []
        out[lang] = {"missing": len(missing), "examples": missing[:limit]}
    return out
