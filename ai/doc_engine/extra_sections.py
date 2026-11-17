"""Guide chapters for parts of WealthFlow that are not pages of the web app (so the screenshot capture never finds them), such as the standalone coding agent.

The text lives in content/page_descriptions.json like every other page (key `dev-agent` and `dev-agent::<part>`); the chapter titles are locale keys (en/ar/fr/de).
They are technical chapters: the admin guide and the technical guide carry them, the user guide does not. A key missing from the content file means no chapter."""

from __future__ import annotations

from ai.doc_engine.models import DocNode

ROUTE = "dev-agent"
PARTS = (("settings", "docgen_sec_dev_agent_settings"), ("run", "docgen_sec_dev_agent_run"), ("training", "docgen_sec_dev_agent_training"))
TITLE = "docgen_sec_dev_agent"


def _node(key: str, title_key: str, nav: list[str], content: dict) -> DocNode | None:
    entry = content.get(key)
    if not entry:
        return None
    node = DocNode(key, title_key, entry.get("purpose", ""), nav, entry.get("steps", []), None, True)
    node.route = ROUTE
    return node


def extra_nodes(content: dict) -> list[DocNode]:
    top = _node(ROUTE, TITLE, [TITLE], content)
    if top is None:
        return []
    for part, title_key in PARTS:
        child = _node(f"{ROUTE}::{part}", title_key, [TITLE, title_key], content)
        if child is not None:
            top.children.append(child)
    return [top]
