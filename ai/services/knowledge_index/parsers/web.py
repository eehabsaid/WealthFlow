"""HTML templates and CSS: components (ids), script load order, inline handlers, i18n keys, {% url %}/{% include %}, rules."""

from __future__ import annotations

import re
from html.parser import HTMLParser

from ai.services.knowledge_index.parsers import endpoints, js_scan, make_symbol, split_words

_CALL = re.compile(r"([A-Za-z_$][\w$.]*)\s*\(")
_TAGS = (("url_name", re.compile(r"{%\s*url\s+['\"]([^'\"]+)['\"]")), ("include", re.compile(r"{%\s*(?:include|extends)\s+['\"]([^'\"]+)['\"]")))


class _Collector(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.symbols, self.refs, self.scripts = [], [], []
        self._inline = None

    def handle_starttag(self, tag, attrs):
        line = self.getpos()[0]
        a = {k: v or "" for k, v in attrs}
        if a.get("id") and "{{" not in a["id"]:
            self.symbols.append(make_symbol(a["id"], "component", line, line, sig=f"<{tag} id=\"{a['id']}\">", body=" ".join(a.values())))
        if tag == "script":
            if a.get("src"):
                self.refs.append({"line": line, "src": "", "name": re.sub(r"[?#].*", "", a["src"]).rsplit("/", 1)[-1], "kind": "script_src"})
            else:
                self._inline = (line, [])
        for k, v in a.items():
            if k.startswith("data-i18n"):
                self.refs.append({"line": line, "src": a.get("id", ""), "name": v, "kind": "i18n"})
            elif k.startswith("on") and v:
                for name in _CALL.findall(v):
                    self.refs.append({"line": line, "src": a.get("id", ""), "name": name.split(".")[0] if name.startswith("window.") is False else name[7:],
                                      "kind": "handler"})
            elif k == "class":
                self.refs.extend({"line": line, "src": a.get("id", ""), "name": c, "kind": "css_class"} for c in v.split() if "{" not in c)

    def handle_data(self, data):
        if self._inline is not None:
            self._inline[1].append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self._inline is not None:
            start, chunks = self._inline
            code = "".join(chunks)
            syms, refs = js_scan.parse(code)
            for s in syms:
                s["line"] += start - 1; s["end"] += start - 1
            for r in refs:
                r["line"] += start - 1
            self.symbols += [s for s in syms if s["kind"] != "variable" or s.get("scope") == "global"]
            self.refs += refs
            endpoints.add(code, syms, self.refs, start - 1)
            self._inline = None


def parse_html(text: str) -> tuple[list[dict], list[dict]]:
    col = _Collector()
    try:
        col.feed(text)
    except Exception:  # malformed markup must never stop indexing; keep what was found
        pass
    for no, line in enumerate(text.splitlines(), 1):
        for kind, rx in _TAGS:
            for m in rx.finditer(line):
                col.refs.append({"line": no, "src": "", "name": m.group(1), "kind": kind})
    seen, refs = set(), []
    for r in col.refs:
        key = (r["line"], r["name"], r["kind"])
        if key not in seen:
            seen.add(key); refs.append(r)
    return col.symbols, refs


_RULE = re.compile(r"(?P<sel>[^{}@;]+?)\s*\{", re.M)


def parse_css(text: str) -> tuple[list[dict], list[dict]]:
    clean = re.sub(r"/\*.*?\*/", lambda m: re.sub(r"[^\n]", " ", m.group(0)), text, flags=re.S)
    symbols, refs = [], []
    depth_end = {}
    for m in _RULE.finditer(clean):
        sel = " ".join(m.group("sel").split())
        if not sel or sel.startswith(("from", "to")) or re.fullmatch(r"[\d.%\s,]+", sel):
            continue
        line = clean.count("\n", 0, m.start("sel")) + 1 + (m.group("sel").count("\n") - m.group("sel").lstrip().count("\n"))
        close = clean.find("}", m.end())
        end = clean.count("\n", 0, close if close >= 0 else len(clean)) + 1
        key = (sel, line)
        if key in depth_end:
            continue
        depth_end[key] = end
        symbols.append(make_symbol(sel[:100], "css_rule", line, end, sig=sel[:200], body=clean[m.end(): close if close >= 0 else m.end() + 300]))
        symbols[-1]["tokens"] += " " + split_words(re.sub(r"[.#:\[\]>+~*]", " ", sel))
    for no, row in enumerate(clean.splitlines(), 1):
        refs.extend({"line": no, "src": "", "name": v, "kind": "css_var"} for v in re.findall(r"var\((--[\w-]+)", row))
    return symbols, refs
