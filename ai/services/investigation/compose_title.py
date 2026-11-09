"""The guide's title carries the application's name, never a title the model invented ("Personal Finance ... App User Guide")."""

from __future__ import annotations

APP_NAME = "WealthFlow"


def _has_name(line: str) -> bool:
    return APP_NAME.lower() in line.lower()


def guide_title(intro: str) -> str:
    """The introduction under one "# " title that names the app: the model's own title is kept only when it does."""
    lines = intro.strip().splitlines()
    first = lines[0].strip() if lines and lines[0].startswith("# ") else ""
    body = "\n".join(lines[1:] if first else lines).strip()
    return f"{first if first and _has_name(first) else f'# {APP_NAME} user guide'}\n\n{body}".rstrip()


def with_app_name(markdown: str, source: str = "") -> str:
    """A translated guide whose first heading lost the app's name gets it back (language-independent: it is a Latin product name);
    a guide without a title takes the source guide's title."""
    lines = markdown.lstrip().splitlines()
    if lines and lines[0].startswith("# "):
        return markdown if _has_name(lines[0]) else "\n".join([f"{lines[0].rstrip()} – {APP_NAME}", *lines[1:]]).rstrip() + "\n"
    title = next((ln for ln in source.splitlines() if ln.startswith("# ")), f"# {APP_NAME} user guide")
    return f"{title}\n\n{markdown.lstrip()}"
