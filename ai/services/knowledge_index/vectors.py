"""Optional semantic layer: symbol embeddings through the app's existing Ollama embedding setting (ai_embed_model).

Never required: with no embeddings (Ollama down, model not pulled, nothing embedded yet) search is keyword + symbol only.
Vectors are keyed to a symbol's content hash, so an unchanged symbol is never embedded twice, even after its file is re-parsed.
"""

from __future__ import annotations

from array import array

from ai.models import AISetting
from ai.services.retrieval import embeddings

MAX_SCAN = 4000


def model_name() -> str:
    return str(AISetting.get("ai_embed_model", embeddings.DEFAULT_EMBED_MODEL))


def pack(vec: list[float]) -> bytes:
    return array("f", vec).tobytes()


def unpack(blob: bytes) -> array:
    arr = array("f")
    arr.frombytes(blob)
    return arr


def snapshot(conn, path: str) -> dict:
    rows = conn.execute("SELECT s.qname, s.kind, s.body_sha, v.model, v.vec FROM symbols s JOIN vectors v ON v.symbol_id=s.id WHERE s.path=?", (path,))
    return {(r["qname"], r["kind"], r["body_sha"]): (r["model"], r["vec"]) for r in rows}


def restore(conn, path: str, keep: dict) -> None:
    if not keep:
        return
    for row in conn.execute("SELECT id, qname, kind, body_sha FROM symbols WHERE path=?", (path,)).fetchall():
        hit = keep.get((row["qname"], row["kind"], row["body_sha"]))
        if hit:
            conn.execute("INSERT OR REPLACE INTO vectors(symbol_id, model, body_sha, vec) VALUES(?,?,?,?)", (row["id"], hit[0], row["body_sha"], hit[1]))
    conn.commit()


def embed_pending(conn, limit: int = 200) -> dict:
    """Embed up to `limit` symbols that have no vector for the current model. Returns {embedded, remaining, available}."""
    model = model_name()
    rows = conn.execute(
        "SELECT s.id, s.qname, s.sig, s.doc, s.tokens, s.body_sha FROM symbols s LEFT JOIN vectors v ON v.symbol_id=s.id AND v.model=? "
        "WHERE v.symbol_id IS NULL AND s.kind NOT IN ('variable','error','css_rule','i18n_value','field','migration_op') LIMIT ?", (model, limit)).fetchall()
    done = 0
    for r in rows:
        vec = embeddings._embed(f"{r['qname']} {r['sig']} {r['doc']} {r['tokens'][:600]}")
        if vec is None:
            return {"embedded": done, "remaining": None, "available": False}
        conn.execute("INSERT OR REPLACE INTO vectors(symbol_id, model, body_sha, vec) VALUES(?,?,?,?)", (r["id"], model, r["body_sha"], pack(vec)))
        done += 1
    conn.commit()
    left = conn.execute("SELECT COUNT(*) FROM symbols s LEFT JOIN vectors v ON v.symbol_id=s.id AND v.model=? WHERE v.symbol_id IS NULL", (model,)).fetchone()[0]
    return {"embedded": done, "remaining": left, "available": True}


def similarities(conn, query: str, ids: set[int] | None = None) -> dict[int, float] | None:
    """{symbol_id: cosine} for the query vs stored vectors of the current model; None when no query embedding / no vectors."""
    q = embeddings._embed_query(query)
    if q is None:
        return None
    sql = "SELECT symbol_id, vec FROM vectors WHERE model=?"
    rows = conn.execute(sql + " LIMIT ?", (model_name(), MAX_SCAN)).fetchall()
    out = {}
    qn = sum(x * x for x in q) ** 0.5 or 1.0
    for r in rows:
        if ids is not None and r["symbol_id"] not in ids:
            continue
        v = unpack(r["vec"])
        if len(v) != len(q):
            continue
        dot = sum(a * b for a, b in zip(q, v))
        norm = sum(b * b for b in v) ** 0.5 or 1.0
        out[r["symbol_id"]] = max(0.0, dot / (qn * norm))
    return out or None
