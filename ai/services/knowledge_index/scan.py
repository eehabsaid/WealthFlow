"""Repository scan + diff against the stored index: added / changed / deleted / renamed / invalid files, by content hash.

Stat (size, mtime) is only a cheap pre-filter: a file is re-parsed only when its SHA-256 really changed, and a deleted + added
pair with the same hash is a rename (rows are moved, nothing is re-parsed).
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path

from ai.services.investigation import paths
from ai.services.knowledge_index import config

SKIP_DIRS = paths.BLOCKED_DIRS | {"runtime", "coding_agent_cache"}


@dataclass
class Candidate:
    rel: str
    abs: Path
    size: int
    mtime_ns: int


def sha_of(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def walk(base: Path | None = None) -> list[Candidate]:
    base = base or config.base_dir()
    out = []
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS and not d.startswith("."))
        for name in sorted(filenames):
            if paths.is_blocked_name(name):
                continue
            full = Path(dirpath, name)
            rel = full.relative_to(base).as_posix()
            if not config.is_indexable(rel):
                continue
            try:
                st = full.stat()
            except OSError:
                continue
            if st.st_size <= paths.MAX_FILE_BYTES:
                out.append(Candidate(rel, full, st.st_size, st.st_mtime_ns))
    return out


def invalid_paths(conn) -> set[str]:
    """Files whose stored symbol/ref counts differ from the rows actually present (an interrupted or damaged write)."""
    rows = conn.execute(
        "SELECT f.path FROM files f WHERE f.n_symbols != (SELECT COUNT(*) FROM symbols s WHERE s.path=f.path) "
        "OR f.n_refs != (SELECT COUNT(*) FROM refs r WHERE r.path=f.path)").fetchall()
    orphans = conn.execute("SELECT DISTINCT path FROM symbols WHERE path NOT IN (SELECT path FROM files)").fetchall()
    return {r["path"] for r in rows} | {r["path"] for r in orphans}


def diff(conn, candidates: list[Candidate]) -> dict:
    """{added, changed, deleted, renamed:[(old,new)], touched, invalid} using the hash only when the stat changed."""
    known = {r["path"]: r for r in conn.execute("SELECT path, sha, size, mtime_ns FROM files")}
    current = {c.rel: c for c in candidates}
    invalid = invalid_paths(conn)
    added, changed, touched, shas = [], [], [], {}
    for rel, cand in current.items():
        row = known.get(rel)
        if row is None:
            added.append(cand)
        elif rel in invalid:
            changed.append(cand)
        elif (row["size"], row["mtime_ns"]) != (cand.size, cand.mtime_ns):
            digest = sha_of(cand.abs)
            shas[rel] = digest
            (touched if digest == row["sha"] else changed).append(cand)
    deleted = [p for p in known if p not in current]
    by_sha = {known[p]["sha"]: p for p in deleted}
    renamed = []
    for cand in list(added):
        digest = sha_of(cand.abs)
        shas[cand.rel] = digest
        old = by_sha.get(digest)
        if old and old in deleted:
            renamed.append((old, cand))
            deleted.remove(old)
            added.remove(cand)
    return {"added": added, "changed": changed, "deleted": deleted, "renamed": renamed, "touched": touched,
            "invalid": sorted(invalid), "shas": shas}
