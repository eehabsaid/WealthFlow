"""Puts the screenshots into the guide text: one Markdown image right after a screen's "## " heading and after each tab's "### "
heading. A heading is matched by its title; in a translated guide (titles differ) chapters are matched by position when the
guide has as many chapters as the app has screens, and tabs by position when the counts match."""

from __future__ import annotations

import re

from ai.services.guide_shots import store
from ai.services.guide_shots.plan import chapters, same

_HEAD = re.compile(r"^(#{2,3})\s+(?:\d+[.)]?\s+)?(.*?)\s*$")


def _image(target: dict, alt: str) -> str:
    return f"![{alt.replace('[', '(').replace(']', ')')}]({store.URL.format(key=target['key'])})"


def insert(markdown: str, plan: list[dict], have: set[str]) -> str:
    """The guide with an image under every heading whose screenshot was captured (`have` = captured keys)."""
    book = [(c, tabs) for c, tabs in chapters(plan)]
    lines = markdown.splitlines()
    heads = [i for i, line in enumerate(lines) if (m := _HEAD.match(line)) and m.group(1) == "##"]
    by_position = len(heads) == len(book) + 1 or len(heads) == len(book)   # the first chapter may be "Signing up" (no screenshot)
    offset = len(heads) - len(book) if by_position else 0
    out: list[str] = []
    current: tuple[dict, list[dict]] | None = None
    tab_no = 0
    chapter_no = -1
    for line in lines:
        out.append(line)
        m = _HEAD.match(line)
        if not m:
            continue
        title = m.group(2)
        if m.group(1) == "##":
            chapter_no += 1
            current = next(((c, t) for c, t in book if same(c["title"], title)), None)
            if current is None and by_position and 0 <= chapter_no - offset < len(book):
                current = book[chapter_no - offset]
            tab_no = 0
            if current and current[0]["key"] in have:
                out += ["", _image(current[0], title)]
        elif current:
            tabs = current[1]
            tab = next((t for t in tabs if same(t["title"], title)), None)
            if tab is None and by_position and len(tabs) and tab_no < len(tabs) and not any(same(t["title"], title) for t in tabs):
                tab = tabs[tab_no]
            tab_no += 1
            if tab and tab["key"] in have:
                out += ["", _image(tab, title)]
    return "\n".join(out)
