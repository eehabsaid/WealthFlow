"""SQLite storage of the knowledge index: schema, connection, meta values, safe whole-file replacement.

A file's rows are replaced in ONE transaction and its `files` row is written last, with the symbol/ref counts it must
have. A crash therefore leaves either the old complete data or a file the next refresh sees as invalid and re-parses.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager

from ai.services.knowledge_index import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS files (path TEXT PRIMARY KEY, sha TEXT, size INTEGER, mtime_ns INTEGER, lang TEXT, parser TEXT,
  lines INTEGER, is_test INTEGER DEFAULT 0, n_symbols INTEGER, n_refs INTEGER);
CREATE TABLE IF NOT EXISTS symbols (id INTEGER PRIMARY KEY, path TEXT, name TEXT, qname TEXT, kind TEXT, line INTEGER,
  end_line INTEGER, parent TEXT, sig TEXT, doc TEXT, tokens TEXT, body_sha TEXT);
CREATE TABLE IF NOT EXISTS refs (id INTEGER PRIMARY KEY, path TEXT, line INTEGER, src TEXT, name TEXT, kind TEXT);
CREATE TABLE IF NOT EXISTS vectors (symbol_id INTEGER PRIMARY KEY, model TEXT, body_sha TEXT, vec BLOB);
CREATE INDEX IF NOT EXISTS ix_sym_name ON symbols(name); CREATE INDEX IF NOT EXISTS ix_sym_path ON symbols(path);
CREATE INDEX IF NOT EXISTS ix_sym_qname ON symbols(qname); CREATE INDEX IF NOT EXISTS ix_ref_name ON refs(name);
CREATE INDEX IF NOT EXISTS ix_ref_path ON refs(path); CREATE INDEX IF NOT EXISTS ix_ref_src ON refs(src);
"""
TABLES = ("vectors", "refs", "symbols", "files", "meta")


def connect(path=None) -> sqlite3.Connection:
    target = path or config.index_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA)
    return conn


def get_meta(conn, key: str, default: str = "") -> str:
    row = conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def set_meta(conn, key: str, value) -> None:
    conn.execute("INSERT INTO meta(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))
    conn.commit()


def reset(conn) -> None:
    """Drop everything (schema version change or an explicit rebuild)."""
    for table in TABLES:
        conn.execute(f"DELETE FROM {table}")
    conn.commit()


@contextmanager
def transaction(conn):
    try:
        conn.execute("BEGIN")
        yield
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def delete_file(conn, path: str) -> None:
    conn.execute("DELETE FROM vectors WHERE symbol_id IN (SELECT id FROM symbols WHERE path=?)", (path,))
    conn.execute("DELETE FROM symbols WHERE path=?", (path,))
    conn.execute("DELETE FROM refs WHERE path=?", (path,))
    conn.execute("DELETE FROM files WHERE path=?", (path,))


def write_file(conn, rec: dict, symbols: list[dict], refs: list[dict]) -> None:
    """Replace everything stored for rec['path'] atomically (files row last, with the counts used to detect damage)."""
    with transaction(conn):
        delete_file(conn, rec["path"])
        conn.executemany(
            "INSERT INTO symbols(path,name,qname,kind,line,end_line,parent,sig,doc,tokens,body_sha) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            [(rec["path"], s["name"], s["qname"], s["kind"], s["line"], s["end"], s.get("parent", ""), s.get("sig", ""),
              s.get("doc", ""), s.get("tokens", ""), s.get("body_sha", "")) for s in symbols])
        conn.executemany("INSERT INTO refs(path,line,src,name,kind) VALUES(?,?,?,?,?)",
                         [(rec["path"], r["line"], r.get("src", ""), r["name"], r["kind"]) for r in refs])
        conn.execute("INSERT INTO files(path,sha,size,mtime_ns,lang,parser,lines,is_test,n_symbols,n_refs) VALUES(?,?,?,?,?,?,?,?,?,?)",
                     (rec["path"], rec["sha"], rec["size"], rec["mtime_ns"], rec["lang"], rec["parser"], rec["lines"],
                      int(rec["is_test"]), len(symbols), len(refs)))


def rename_file(conn, old: str, new: str) -> None:
    """Same content under a new path: move the rows instead of re-parsing."""
    with transaction(conn):
        for table in ("symbols", "refs", "files"):
            conn.execute(f"UPDATE {table} SET path=? WHERE path=?", (new, old))
