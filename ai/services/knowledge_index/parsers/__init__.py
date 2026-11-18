"""Structural parsers. Each returns (symbols, refs):

symbol = {name, qname, kind, line, end, parent, sig, doc}        ref = {line, src, name, kind}
Ref kinds: call, import, ident (a JS identifier that may be a script-global), global_def, fk, route_view, include, url_name,
script_src, handler, i18n, template, test_ref. `src` is the qname of the enclosing symbol.
"""

from __future__ import annotations

import hashlib
import re

from ai.services.investigation import paths
from ai.services.knowledge_index.config import MAX_BODY_CHARS

_CRED_WORDS = ("secret", "password", "passwd", "api_key", "api-key", "apikey", "token", "private_key", "private-key", "privatekey", "hmac", "salt")
_RUN40 = re.compile(r"[A-Za-z0-9+/_-]{40}")
_PLAIN_KINDS = ("i18n_key", "i18n_value", "doc_section", "page_doc", "page_route")   # UI text / docs: not credentials, keep searchable

_SPLIT = re.compile(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])|\d+")


_SUFFIX = re.compile(r"(ing|ed|es|s)$")


def stem(word: str) -> str:
    """Crude plural/tense folding so 'calculated' finds 'calculates' (applied to index tokens and query words alike)."""
    return _SUFFIX.sub("", word) if len(word) > 5 else word


def split_words(text: str) -> str:
    """CamelCase / snake_case / dotted names -> lower-case stemmed words ('ExpenseService.apply_reverse' -> 'expense service apply reverse')."""
    return " ".join(stem(w.lower()) for w in _SPLIT.findall(text or ""))


def safe_text(text: str) -> str:
    """paths.redact, but only invoked when the text could contain a credential (its regexes are slow on every string)."""
    if not text:
        return text or ""
    low = text.lower()
    return paths.redact(text) if any(w in low for w in _CRED_WORDS) or _RUN40.search(text) else text


def make_symbol(name, kind, line, end, *, parent="", sig="", doc="", body="", path_qual="") -> dict:
    qname = f"{parent}.{name}" if parent else name
    if kind not in _PLAIN_KINDS:      # secrets are never indexed: credential-looking assignments are masked before storage
        sig, doc, body = safe_text(sig or ""), safe_text(doc or ""), safe_text(body or "")
    body = (body or "")[:MAX_BODY_CHARS]
    tokens = " ".join((split_words(qname), name.lower(), split_words(doc), re.sub(r"[^\w]+", " ", body).lower()))
    return {"name": name, "qname": qname, "kind": kind, "line": line, "end": max(end, line), "parent": parent,
            "sig": sig[:200], "doc": (doc or "")[:300], "tokens": tokens[: MAX_BODY_CHARS * 2],
            "body_sha": hashlib.sha1(body.encode("utf-8", "replace")).hexdigest()}


def parse(rel: str, text: str, js_result=None) -> tuple[str, list[dict], list[dict]]:
    """(parser name, symbols, refs) for one file. `js_result` is a precomputed Acorn result for .js files, if any."""
    from ai.services.knowledge_index.parsers import data_files, endpoints, js_scan, py_code, web

    if rel.endswith(".py"):
        return ("python-ast", *py_code.parse(rel, text))
    if rel.endswith(".js"):
        name, (symbols, refs) = ("acorn", js_result) if js_result is not None else ("js-scan", js_scan.parse(text))
        endpoints.add(text, symbols, refs)
        return (name, symbols, refs)
    if rel.endswith((".html", ".css")):
        return ("web", *(web.parse_html(text) if rel.endswith(".html") else web.parse_css(text)))
    return ("data", *data_files.parse(rel, text))
