"""Serves the web UI (dev_agent/web) from a whitelist: no directory listing, no dotfiles, nothing outside the folder, fixed content types."""

from __future__ import annotations

from pathlib import Path

from .http import HttpError, Resp

TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8",
         ".svg": "image/svg+xml", ".png": "image/png", ".ico": "image/x-icon"}
CSP = ("default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; "
       "base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
WEB_DIR = Path(__file__).resolve().parents[1] / "web"


def serve(path: str, web_dir: Path = WEB_DIR) -> Resp:
    rel = "index.html" if path in ("", "/") else path.lstrip("/")
    parts = rel.split("/")
    if any(p in ("", ".", "..") or p.startswith(".") or "\\" in p or ":" in p or "\0" in p for p in parts):
        raise HttpError(404, "not_found", "not found")
    target = (web_dir / rel).resolve()
    ctype = TYPES.get(target.suffix.lower())
    if not ctype or not target.is_relative_to(web_dir.resolve()) or not target.is_file():
        raise HttpError(404, "not_found", "not found")
    headers = {"Content-Security-Policy": CSP, "X-Frame-Options": "DENY"} if ctype.startswith("text/html") else {}
    return Resp(target.read_bytes(), 200, ctype, headers)
