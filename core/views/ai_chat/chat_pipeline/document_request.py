"""What kind of file a chat request asks for (a written document, HTML only, the output-token limit it needs)."""

from __future__ import annotations


def wants_written_document(text: str) -> bool:
    """Word / PDF / text / HTML file requested: the file must contain a document (see investigation/compose.py)."""
    from core.services.ai.exports import requested

    return any(f.key in ("docx", "pdf", "txt", "html") for f in requested(text))


def html_only(text: str) -> bool:
    """Only an HTML file is asked for: that may be code (a page the user wants built), so the app writes the guide itself only when
    the model confirms the request is about the app (see compose.compose_document strict)."""
    from core.services.ai.exports import requested

    return all(f.key == "html" for f in requested(text))


def document_write_tokens(provider, user_text: str) -> int | None:
    """Output-token limit for the model's own writing while a Word / PDF / text document is requested (None: the chat limit)."""
    from core.services.ai.agent.settings import document_max_tokens

    return document_max_tokens(provider) if wants_written_document(user_text) else None
