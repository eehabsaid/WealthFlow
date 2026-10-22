"""The user guide as ONE self-contained, accessible HTML page: a sticky contents rail (every chapter and sub-section is a link,
the chapter being read is highlighted), numbered chapters, steps and notes, dark mode, print styles and right-to-left layout.

Built from the guide's own headings by the app (the model never writes the index or the HTML), so the contents always match the
sections. A document counts as a guide when it has several "## " chapters and no code block; any other .html answer stays code."""

from __future__ import annotations

import re
from html import escape

from ..document import ExportDocument, runs
from .guide_html_assets import CSS, JS, LABELS

MIN_CHAPTERS = 3
_NUMBERED = re.compile(r"^(\d+)\.\s+(.*)$")
_RTL = ("ar", "he", "fa", "ur")


def is_guide(doc: ExportDocument) -> bool:
    return sum(1 for b in doc.blocks if b.kind == "heading" and b.level == 2) >= MIN_CHAPTERS and "```" not in doc.source


def _slug(text: str) -> str:
    return re.sub(r"[\W_]+", "-", str(text).lower()).strip("-")[:48] or "section"


def _inline(text: str) -> str:
    return "".join(f"<strong>{escape(t)}</strong>" if bold else escape(t) for t, bold in runs(text))


def _paragraph(text: str, seen: set[str]) -> str:
    key = re.sub(r"\s+", " ", text).strip().casefold()
    if not key or key in seen:
        return ""
    seen.add(key)
    return f'<p class="purpose">{_inline(text)}</p>'


def _list(kind: str, items: list[str]) -> str:
    tag, cls = ("ol", "steps") if kind == "ol" else ("ul", "notes")
    return f'<{tag} class="{cls}">' + "".join(f"<li>{_inline(i)}</li>" for i in items) + f"</{tag}>"


def _table(block) -> str:
    head = "<thead><tr>" + "".join(f"<th>{_inline(h)}</th>" for h in block.header) + "</tr></thead>" if any(block.header) else ""
    rows = "".join("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in r) + "</tr>" for r in block.rows)
    return f'<div class="table-wrap"><table>{head}<tbody>{rows}</tbody></table></div>'


def _body(blocks: list, chapter: int, subs: list, seen: set[str]) -> str:
    """The HTML of one chapter's blocks; sub-section links are collected in `subs` as (id, text)."""
    out, run, kind, sub = [], [], "", 0

    def flush():
        nonlocal run, kind
        if run:
            out.append(_list(kind, run))
        run, kind = [], ""

    for b in blocks:
        step = _NUMBERED.match(b.text) if b.kind == "text" else None
        want = "ol" if step else "ul" if b.kind == "bullet" else ""
        if want != kind:
            flush()
        if want:
            kind = want
            run.append(step.group(2) if step else b.text)
            continue
        if b.kind == "heading":
            sub += 1
            sid = f"sec-{chapter}-{sub}-{_slug(b.text)}"
            subs.append((sid, b.text))
            level = 4 if b.level >= 4 else 3
            out.append(f'<h{level} id="{sid}" class="sub-heading{" l4" if level == 4 else ""}">{escape(b.text)}</h{level}>')
        elif b.kind == "table":
            out.append(_table(b))
        else:
            paragraph = _paragraph(b.text, seen)
            if paragraph:
                out.append(paragraph)
    flush()
    return "\n".join(out)


def build_guide_html(doc: ExportDocument, lang: str) -> bytes:
    labels = LABELS.get(lang, LABELS["en"])
    intro, chapters = [], []
    for b in doc.blocks:
        if b.kind == "heading" and b.level == 2:
            chapters.append((b.text, []))
        elif chapters:
            chapters[-1][1].append(b)
        else:
            intro.append(b)
    toc, sections, seen = [], [], set()
    lead = "\n".join(_paragraph(b.text, seen) for b in intro if b.kind == "text")
    for n, (title, blocks) in enumerate(chapters, 1):
        sid, subs = f"sec-{n}-{_slug(title)}", []
        body = _body(blocks, n, subs, seen)
        sub_links = "".join(f'<li><a href="#{i}">{escape(t)}</a></li>' for i, t in subs)
        toc.append(f'<li class="toc-l1"><a href="#{sid}" data-target="{sid}">{n} {escape(title)}</a>'
                   + (f'<ul class="toc-sub">{sub_links}</ul>' if sub_links else "") + "</li>")
        sections.append(f'<section id="{sid}" class="guide-section" aria-labelledby="{sid}-heading">\n'
                        f'<h2 id="{sid}-heading" class="section-heading">{n} {escape(title)}</h2>\n{body}\n</section>')
    meta = f'<p class="meta">{escape(doc.generated)}</p>' if doc.generated else ""
    page = f"""<!DOCTYPE html>
<html lang="{escape(lang)}" dir="{'rtl' if lang in _RTL else 'ltr'}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(doc.title)}</title>
<style>{CSS}</style>
</head>
<body>
<a href="#main-content" class="skip-link">{escape(labels['skip'])}</a>
<button class="toc-toggle" id="tocToggle" aria-label="{escape(labels['toggle'])}" aria-expanded="false">&#9776;</button>
<div class="layout">
<nav class="toc-rail" id="tocRail" aria-label="{escape(labels['contents'])}">
<h2>{escape(labels['contents'])}</h2>
<ul>
{chr(10).join(toc)}
</ul>
</nav>
<main id="main-content" role="main">
<header>
<h1>{escape(doc.title)}</h1>
{meta}
{lead}
</header>
{chr(10).join(sections)}
</main>
</div>
<script>{JS}</script>
</body>
</html>
"""
    return page.encode("utf-8")
