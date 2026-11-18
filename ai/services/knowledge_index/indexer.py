"""Full and incremental indexing with versioning, rebuild and recovery from interrupted runs."""

from __future__ import annotations

import threading
import time
import uuid

from ai.services.knowledge_index import config, relations, scan, store
from ai.services.knowledge_index.parsers import js_acorn, parse, split_words

_LOCK = threading.Lock()


def _lang(rel: str) -> str:
    return rel.rsplit(".", 1)[-1]


def _is_test(rel: str) -> bool:
    name = rel.rsplit("/", 1)[-1]
    return "/tests/" in "/" + rel or name.startswith("test_") or name.endswith(("_test.py", ".test.js", ".spec.js"))


def _record(cand, sha, parser, text, symbols, refs) -> dict:
    return {"path": cand.rel, "sha": sha, "size": cand.size, "mtime_ns": cand.mtime_ns, "lang": _lang(cand.rel), "parser": parser,
            "lines": text.count("\n") + 1, "is_test": _is_test(cand.rel)}


def _read(cand) -> str:
    return cand.abs.read_text(encoding="utf-8", errors="replace")


def _index_files(conn, cands: list, shas: dict) -> int:
    from ai.services.knowledge_index import vectors

    engine = config.js_engine()
    js = [(c.rel, c.abs) for c in cands if c.rel.endswith(".js")]
    acorn = js_acorn.parse_many(js) if engine in ("auto", "acorn") else {}
    done = 0
    for cand in cands:
        text = _read(cand)
        sha = shas.get(cand.rel) or scan.sha_of(cand.abs)
        try:
            parser, symbols, refs = parse(cand.rel, text, acorn.get(cand.rel))
        except Exception as exc:   # one unparseable file must not stop the run: record it as an error symbol
            from ai.services.knowledge_index.parsers import make_symbol
            parser, symbols, refs = "error", [make_symbol("<parse-error>", "error", 1, 1, doc=str(exc)[:200])], []
        path_words = split_words(cand.rel.rsplit(".", 1)[0].replace("/", " "))
        for sym in symbols:               # the file's own name is part of what a symbol means (expense_mirror_engine.py -> mirror, engine)
            sym["tokens"] = f"{sym['tokens']} {path_words}"
        keep = vectors.snapshot(conn, cand.rel)
        store.write_file(conn, _record(cand, sha, parser, text, symbols, refs), symbols, refs)
        vectors.restore(conn, cand.rel, keep)
        done += 1
    return done


def refresh(conn=None, *, full: bool = False) -> dict:
    """Bring the index in line with the repository. Safe to call at any time and from several threads."""
    with _LOCK:
        own = conn is None
        conn = conn or store.connect()
        try:
            return _refresh(conn, full)
        finally:
            if own:
                conn.close()


def _refresh(conn, full: bool) -> dict:
    started = time.monotonic()
    summary = {"rebuilt": False, "recovered": store.get_meta(conn, "state") == "building"}   # a previous run died mid-way
    if full or store.get_meta(conn, "version") != str(config.INDEX_VERSION) or store.get_meta(conn, "js_engine") != config.js_engine():
        store.reset(conn)
        summary["rebuilt"] = True
        store.set_meta(conn, "version", config.INDEX_VERSION)     # recorded up front: a crash during the first build resumes, not restarts
        store.set_meta(conn, "js_engine", config.js_engine())
    run_id = uuid.uuid4().hex[:8]
    store.set_meta(conn, "state", "building")
    store.set_meta(conn, "run_id", run_id)
    delta = scan.diff(conn, scan.walk())
    for path in delta["deleted"]:
        with store.transaction(conn):
            store.delete_file(conn, path)
    for old, cand in delta["renamed"]:
        store.rename_file(conn, old, cand.rel)
        conn.execute("UPDATE files SET mtime_ns=?, size=? WHERE path=?", (cand.mtime_ns, cand.size, cand.rel))
    for cand in delta["touched"]:      # only the timestamp moved: remember it so the hash is not recomputed next time
        conn.execute("UPDATE files SET mtime_ns=?, size=? WHERE path=?", (cand.mtime_ns, cand.size, cand.rel))
    conn.commit()
    parsed = _index_files(conn, delta["added"] + delta["changed"], delta["shas"])
    store.set_meta(conn, "version", config.INDEX_VERSION)
    store.set_meta(conn, "js_engine", config.js_engine())
    store.set_meta(conn, "built_at", time.time())
    store.set_meta(conn, "state", "ready")
    summary.update(added=len(delta["added"]), changed=len(delta["changed"]), deleted=len(delta["deleted"]), renamed=len(delta["renamed"]),
                   invalid_repaired=len(delta["invalid"]), parsed=parsed, seconds=round(time.monotonic() - started, 2),
                   files=conn.execute("SELECT COUNT(*) FROM files").fetchone()[0], run_id=run_id)
    return summary


def status(conn=None) -> dict:
    """Index health WITHOUT changing it: version, state, counts, and which files differ from disk right now."""
    own = conn is None
    conn = conn or store.connect()
    try:
        delta = scan.diff(conn, scan.walk())
        counts = {k: conn.execute(f"SELECT COUNT(*) FROM {k}").fetchone()[0] for k in ("files", "symbols", "refs", "vectors")}
        stale = len(delta["added"]) + len(delta["changed"]) + len(delta["deleted"]) + len(delta["renamed"]) + len(delta["invalid"])
        return {"version": store.get_meta(conn, "version"), "expected_version": config.INDEX_VERSION, "state": store.get_meta(conn, "state") or "empty",
                "built_at": store.get_meta(conn, "built_at"), "js_engine": store.get_meta(conn, "js_engine"), "counts": counts,
                "stale_files": stale, "current": stale == 0 and store.get_meta(conn, "state") == "ready"
                and store.get_meta(conn, "version") == str(config.INDEX_VERSION),
                "translations_missing": {k: v["missing"] for k, v in relations.i18n_gaps(conn).items()},
                "pending": {"added": [c.rel for c in delta["added"]][:20], "changed": [c.rel for c in delta["changed"]][:20],
                            "deleted": delta["deleted"][:20], "invalid": delta["invalid"][:20]}}
    finally:
        if own:
            conn.close()
