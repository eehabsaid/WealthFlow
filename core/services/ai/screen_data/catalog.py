"""The live catalogue of data endpoints, built from the running app (URL resolver, view source, the JS that calls them): nothing
is listed by hand, so a new screen endpoint appears here by itself. Each entry says what the endpoint is, which parts of the UI
call it and which query parameters its view reads (with their defaults)."""

from __future__ import annotations

import ast
import importlib
import inspect
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from django.conf import settings
from django.urls import URLPattern, URLResolver, get_resolver

from . import policy

_PARAM = re.compile(r"""GET\.(?:get|getlist)\(\s*['"]([A-Za-z_]\w*)['"]\s*(?:,\s*([^)]*?))?\s*\)|GET\[\s*['"]([A-Za-z_]\w*)['"]\s*\]""")
_JS_API = re.compile(r"""[\"'`](/api/[^\"'`\s?]*)""")
_JS_EXPR = re.compile(r"\$\{[^}]*\}")
_CONVERTER = re.compile(r"<[^>]+>")
JS_DEPTH = 2


@dataclass(frozen=True)
class Endpoint:
    path: str
    callback: object = field(compare=False, repr=False)
    doc: str = ""
    module_doc: str = ""
    params: tuple = ()
    screens: tuple = ()

    @property
    def words(self) -> str:
        return re.sub(r"[^\w]+", " ", " ".join((self.path, *self.screens))).lower()


def _first_paragraph(text: str) -> str:
    return " ".join(inspect.cleandoc(text or "").split("\n\n")[0].split())


def _params(view) -> tuple:
    try:
        parts = [inspect.getsource(c) for c in view.__mro__ if c.__module__.startswith("core.")]
        module = inspect.getmodule(view)
        parts += [inspect.getsource(f) for _, f in inspect.getmembers(module, inspect.isfunction)
                  if f.__module__ == module.__name__ and "request" in inspect.signature(f).parameters]
    except (OSError, TypeError):
        return ()
    found: dict[str, str] = {}
    for m in _PARAM.finditer("\n".join(parts)):
        name, raw, bracket = m.group(1) or m.group(3), (m.group(2) or "").strip(), m.group(3)
        try:
            default = repr(ast.literal_eval(raw)) if raw else ("required" if bracket else "none")
        except (ValueError, SyntaxError):
            default = "none"
        found.setdefault(name, f"default {default}")
    out = []
    for name, default in sorted(found.items()):
        values = _choices(view, name)
        out.append((name, default + (f"; values seen in the code: {', '.join(values)}" if values else "")))
    return tuple(out)


@lru_cache(maxsize=64)
def _module_text(name: str) -> str:
    try:
        return inspect.getsource(importlib.import_module(name))
    except (OSError, TypeError, ImportError):
        return ""


def _choices(view, name: str) -> tuple:
    """String values the code compares the parameter with (`currency_scope == "total_liquid"`), read from the view's module and
    the core modules it uses: the values a model may pass."""
    module = inspect.getmodule(view)
    mods = {module.__name__} | {m.__module__ for _, m in inspect.getmembers(module, lambda o: inspect.isfunction(o) or inspect.isclass(o))
                                if str(getattr(m, "__module__", "")).startswith("core.")}
    seen: list[str] = []
    for mod in sorted(mods):
        for line in _module_text(mod).splitlines():
            if re.search(r"\b" + re.escape(name) + r"\b", line) and re.search(r"==|!=|\bin\b", line) \
                    and not re.search(r"error|Response|status|raise|log", line, re.I):
                seen += [v for v in re.findall(r"[\"']([A-Za-z][\w\-]{1,30})[\"']", line) if v != name]
    return tuple(dict.fromkeys(seen))[:6]


def _walk(patterns, prefix=""):
    for p in patterns:
        if isinstance(p, URLResolver):
            yield from _walk(p.url_patterns, prefix + str(p.pattern))
        elif isinstance(p, URLPattern):
            yield "/" + (prefix + str(p.pattern)).lstrip("^/").replace("$", ""), p.callback


@lru_cache(maxsize=1)
def _js_calls() -> tuple:
    """((area, url), ...): every /api/ URL written in a script under static/js, with the folder (2 levels) that writes it."""
    root, out = Path(settings.BASE_DIR) / "static" / "js", set()
    for file in root.rglob("*.js"):
        try:
            text = file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        area = "/".join(file.relative_to(root).parts[:-1][:JS_DEPTH]) or file.stem
        out.update((area, _JS_EXPR.sub("1", u)) for u in _JS_API.findall(text))
    return tuple(sorted(out))


def _screens(path: str) -> tuple:
    pattern = re.compile("^" + _CONVERTER.sub("[^/]+", re.escape(path)) + "$")
    hits = {a for a, u in _js_calls() if pattern.match(u if u.endswith("/") else u + "/")}
    return tuple(sorted(hits))[:4]


@lru_cache(maxsize=1)
def endpoints() -> tuple[Endpoint, ...]:
    out, seen = [], set()
    for path, callback in _walk(get_resolver().url_patterns):
        view = getattr(callback, "view_class", None)
        if view is None or not hasattr(view, "get") or path in seen or not policy.allowed(path):
            continue
        seen.add(path)
        module = inspect.getmodule(view)
        out.append(Endpoint(path=path, callback=callback, doc=_first_paragraph(view.__doc__), params=_params(view),
                            module_doc=_first_paragraph(getattr(module, "__doc__", "")), screens=_screens(path)))
    return tuple(sorted(out, key=lambda e: e.path))


def for_callback(callback) -> Endpoint | None:
    return next((e for e in endpoints() if e.callback is callback), None)


def _view(e: Endpoint, detail: bool) -> dict:
    out = {"path": e.path, "used_by_screens": list(e.screens)}
    if e.doc:
        out["what"] = e.doc[:600]
    if detail and e.module_doc:
        out["module_notes"] = e.module_doc[:700]
    if e.params:
        out["query_parameters"] = {name: default for name, default in e.params}
    return out


def search(text: str, limit: int = 10) -> dict:
    tokens = [t[:5] for t in re.findall(r"\w+", str(text or "").lower()) if len(t) > 1]   # a 5-letter stem: projected ~ projection
    if not tokens:
        groups: dict[str, list] = {}
        for e in endpoints():
            groups.setdefault(e.path.split("/")[2], []).append(e.path)
        return {"endpoints_total": len(endpoints()), "groups": {g: {"count": len(v), "examples": v[:3]} for g, v in sorted(groups.items())},
                "note": "call again with search='<words of the screen or figure>' to see the matching endpoints and their parameters"}
    scored = []
    for e in endpoints():
        hay = " ".join((e.words, e.doc.lower(), " ".join(n for n, _ in e.params).lower()))
        path_hay = re.sub(r"[^\w]+", " ", e.path).lower() + " " + " ".join(e.screens).lower().replace("_", " ").replace("/", " ")
        score = sum(3 * bool(re.search(r"\b" + re.escape(t), path_hay)) + bool(re.search(r"\b" + re.escape(t), hay)) for t in tokens)
        if score:
            scored.append((-score, len(e.path), e))
    scored.sort(key=lambda s: s[:2])
    hits = [e for _, _, e in scored[:limit]]
    return {"search": text, "matches": [_view(e, len(hits) <= 3) for e in hits], "endpoints_total": len(endpoints()),
            **({} if hits else {"note": "nothing matched; search again with English words of the screen name, or without search to see all groups"})}
