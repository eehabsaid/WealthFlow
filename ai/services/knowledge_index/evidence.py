"""Source evidence: every answer item carries file, line range, symbol, REAL source text and relations.

The text is read from the file on disk at call time, and the file's hash is compared with the indexed one: if the file changed
since indexing, the item is returned with stale=True and NO content, so outdated index data is never shown as current source.
"""

from __future__ import annotations

from ai.services.investigation import paths
from ai.services.knowledge_index import config, scan

MAX_LINES = 40
_cache: dict = {}


def _file_state(conn, rel: str) -> str:
    """'fresh' | 'stale' | 'missing' for one indexed file (hash compared only when size/mtime differ)."""
    row = conn.execute("SELECT sha, size, mtime_ns FROM files WHERE path=?", (rel,)).fetchone()
    target = config.base_dir() / rel
    if row is None or not target.is_file():
        return "missing"
    st = target.stat()
    if (row["size"], row["mtime_ns"]) == (st.st_size, st.st_mtime_ns):
        return "fresh"
    return "fresh" if scan.sha_of(target) == row["sha"] else "stale"


def read_lines(rel: str, start: int, end: int, limit: int = MAX_LINES) -> tuple[list[str], int]:
    """(numbered redacted lines, total lines) of rel[start..end] from disk; at most `limit` lines."""
    text = paths.read_text(config.base_dir() / rel) or ""
    lines = text.splitlines()
    end = min(end, start + limit - 1, len(lines))
    return [f"{n}: {paths.redact(lines[n - 1])}" for n in range(max(1, start), end + 1)], len(lines)


def relations(conn, row) -> dict:
    name, qname, path = row["name"], row["qname"], row["path"]
    calls = conn.execute("SELECT DISTINCT r.name FROM refs r WHERE r.path=? AND r.src=? AND r.kind IN ('call','fk','route_view') "
                         "AND EXISTS (SELECT 1 FROM symbols s WHERE s.name=r.name AND s.kind IN ('function','method','class','model'))"
                         " LIMIT 8", (path, qname)).fetchall()
    n_def = conn.execute("SELECT COUNT(*) FROM symbols WHERE name=? AND kind IN ('function','method','class','variable')", (name,)).fetchone()[0]
    users = conn.execute("SELECT path, line, src FROM refs WHERE name=? AND kind IN ('call','ident','import','handler','route_view','fk') "
                         "AND NOT (path=? AND line BETWEEN ? AND ?) LIMIT 5", (name, path, row["line"], row["end_line"])).fetchall()
    total = conn.execute("SELECT COUNT(*) FROM refs WHERE name=? AND kind IN ('call','ident','import','handler','route_view','fk') "
                         "AND NOT (path=? AND line BETWEEN ? AND ?)", (name, path, row["line"], row["end_line"])).fetchone()[0]
    return {"calls": [c["name"] for c in calls], "used_by": [f"{u['path']}:{u['line']}" + (f" ({u['src']})" if u["src"] else "") for u in users],
            "used_by_total": total,
            "match": "unique name" if n_def <= 1 else f"name shared by {n_def} definitions: callers are matched by NAME only"}


def build(conn, row, *, score: float | None = None, with_relations: bool = True, max_lines: int = MAX_LINES) -> dict:
    state = _file_state(conn, row["path"])
    item = {"path": row["path"], "line_start": row["line"], "line_end": row["end_line"], "symbol": row["qname"], "kind": row["kind"],
            "signature": row["sig"], "stale": state != "fresh"}
    if score is not None:
        item["score"] = round(score, 3)
    if state != "fresh":
        item["content"] = None
        item["warning"] = (f"{row['path']} changed or was removed after it was indexed; this entry is NOT current source. "
                           "Re-run the search (the index refreshes automatically) or read the file directly.")
        return item
    lines, total = read_lines(row["path"], row["line"], row["end_line"], max_lines)
    item["content"] = "\n".join(lines)
    if row["end_line"] > row["line"] + max_lines - 1:
        item["truncated"] = f"showing {len(lines)} of {row['end_line'] - row['line'] + 1} lines; read the rest with app_read_file"
    if with_relations:
        item["relations"] = relations(conn, row)
    return item
