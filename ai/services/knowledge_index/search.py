"""Hybrid retrieval: exact keyword + symbol + path/kind filters + dependency context + optional embeddings, ranked together."""

from __future__ import annotations

import math
import re

from ai.services.knowledge_index import evidence, vectors
from ai.services.knowledge_index.parsers import split_words

_IDENT = re.compile(r"[A-Za-z_$][\w$.]{2,}")
_STOP = frozenset("the and for how does what where why with from this that into are was not can use used which when who".split())
KIND_WEIGHT = {"function": 1.0, "method": 1.0, "class": 1.0, "route": 1.0, "page_doc": 0.8, "page_route": 0.8, "component": 0.8, "field": 0.8,
               "doc_section": 0.7, "variable": 0.6, "i18n_key": 0.5, "migration_op": 0.5, "css_rule": 0.4, "module": 0.5}
DEFAULT_SKIP = ("i18n_value", "error")
COLS = "id, path, name, qname, kind, line, end_line, parent, sig, doc, tokens"


def query_terms(query: str) -> tuple[list[str], list[str]]:
    """(words, exact identifiers): 'how does ExpenseService.apply_reverse work' -> words + ['ExpenseService.apply_reverse']."""
    idents = [m for m in _IDENT.findall(query) if m.lower() not in _STOP and ("_" in m or "." in m or any(c.isupper() for c in m))]
    words = [w for w in dict.fromkeys(split_words(query).split()) if len(w) > 2 and w not in _STOP]
    return words[:10], idents[:5]


def _fetch(conn, term: str, path: str | None, kinds, cap: int = 1500):
    sql, args = f"SELECT {COLS} FROM symbols WHERE instr(tokens, ?) > 0", [term]
    if path:
        sql += " AND (path = ? OR path LIKE ?)"
        args += [path.rstrip("/"), path.rstrip("/") + "/%"]
    if kinds:
        sql += f" AND kind IN ({','.join('?' * len(kinds))})"
        args += list(kinds)
    else:
        sql += f" AND kind NOT IN ({','.join('?' * len(DEFAULT_SKIP))})"
        args += list(DEFAULT_SKIP)
    return conn.execute(sql + " LIMIT ?", args + [cap]).fetchall()


def _exact(conn, ident: str, path, kinds):
    last = ident.split(".")[-1]
    rows = conn.execute(f"SELECT {COLS} FROM symbols WHERE name=? OR qname=? LIMIT 50", (last, ident)).fetchall()
    return [r for r in rows if (not path or r["path"].startswith(path.rstrip("/"))) and (not kinds or r["kind"] in kinds)]


def search(conn, query: str, *, path: str | None = None, kinds=None, limit: int = 8, context_paths=(), max_lines: int = 25) -> dict:
    words, idents = query_terms(query)
    if not words and not idents:
        return {"error": "query has no searchable words; give a function, class, model, screen or feature name"}
    total_syms = conn.execute("SELECT COUNT(*) FROM symbols").fetchone()[0] or 1
    cand: dict[int, dict] = {}
    for term in words:
        rows = _fetch(conn, term, path, kinds)
        idf = math.log(1 + total_syms / (1 + len(rows)))
        for r in rows:
            c = cand.setdefault(r["id"], {"row": r, "lex": 0.0, "named": set()})
            if term in split_words(r["qname"]).split():
                c["lex"] += idf * 3.0
                c["named"].add(term)
            elif term in r["path"].lower() or term in split_words(r["doc"]).split():
                c["lex"] += idf * 1.5
                c["named"].add(term)
            else:
                c["lex"] += idf * 0.4         # only mentioned somewhere in the body: weak evidence
    for ident in idents:
        for r in _exact(conn, ident, path, kinds):
            c = cand.setdefault(r["id"], {"row": r, "lex": 0.0, "named": set()})
            c["lex"] += (14.0 if r["name"] == ident.split(".")[-1] else 8.0) * (1.0 if r["name"][:1] == ident.split(".")[-1][:1] else 0.7)
    sims = vectors.similarities(conn, query) if cand or words else None
    for sid, sim in (sims or {}).items():
        if sid not in cand and sim >= 0.55:
            row = conn.execute(f"SELECT {COLS} FROM symbols WHERE id=?", (sid,)).fetchone()
            if row and (not path or row["path"].startswith(path.rstrip("/"))) and (not kinds or row["kind"] in kinds):
                cand[sid] = {"row": row, "lex": 0.0, "named": set()}
    if not cand:
        return {"query": query, "results": [], "mode": "none", "note": "no indexed symbol matches; try other words, a different spelling "
                "(snake_case vs camelCase), or app_grep for raw text. Do NOT assume the thing exists."}
    top_lex = max(c["lex"] for c in cand.values()) or 1.0
    wants_tests = "test" in query.lower()
    ranked = []
    for sid, c in cand.items():
        row = c["row"]
        coverage = (len(c["named"]) / len(words)) if words else 1.0
        score = c["lex"] / top_lex * KIND_WEIGHT.get(row["kind"], 0.7) * (0.5 + 0.5 * coverage)
        score += 0.6 * (sims or {}).get(sid, 0.0)
        if row["path"] in context_paths:
            score += 0.3
        elif any(row["path"].rsplit("/", 1)[0] == p.rsplit("/", 1)[0] for p in context_paths):
            score += 0.1
        if ("/tests/" in "/" + row["path"] or "/test_" in "/" + row["path"]) and not wants_tests:
            score *= 0.5
        if row["name"].startswith("__") and row["name"].endswith("__"):
            score *= 0.6                       # constructors / dunders are almost never what a question is about
        ranked.append((score, row))
    ranked.sort(key=lambda x: -x[0])
    for i, (score, row) in enumerate(ranked[:40]):   # tie-break: widely used definitions are more central to the app
        uses = conn.execute("SELECT COUNT(*) FROM refs WHERE name=? AND kind IN ('call','ident','import','handler','route_view')", (row["name"],)).fetchone()[0]
        ranked[i] = (score + 0.08 * min(1.0, math.log10(1 + uses) / 2), row)
    ranked.sort(key=lambda x: -x[0])
    picked, per_file = [], {}
    for score, row in ranked:          # diversity: at most 2 hits per file, so one big class cannot fill the answer
        if per_file.get(row["path"], 0) < 2 and per_file.get(row["qname"], 0) < 2:   # also: same-named copies in many files must not fill the list
            per_file[row["path"]] = per_file.get(row["path"], 0) + 1
            per_file[row["qname"]] = per_file.get(row["qname"], 0) + 1
            picked.append((score, row))
        if len(picked) >= limit:
            break
    results = [evidence.build(conn, row, score=score, max_lines=max_lines) for score, row in picked]
    return {"query": query, "mode": "hybrid" if sims else "keyword", "results": results,
            "total_candidates": len(cand), "note": None if sims else "keyword/symbol ranking only (no embeddings available)"}
