"""Provider proxy for the model path: tells the model the app attaches the download links itself.

Without this, a model asked "list ... and export to Excel" tends to answer "I cannot create files" right
above the working download links. Every pipeline calls provider.generate(messages, ...), so wrapping the
provider once covers the default, workflow, investigator and orchestrator paths alike."""

from __future__ import annotations

from typing import Any

NOTICE = (
    "FILE EXPORT: the user also asked for a downloadable file ({formats}). The application itself attaches "
    "working download links to your answer after you reply, built from your answer text. Therefore: answer the "
    "data question completely (when a list or table is requested, include every row, with a total when sensible), "
    "never say you cannot create, export or attach files, never explain how to export, and never write a link, "
    "URL or file name yourself."
)


class ExportNoticeProvider:
    def __init__(self, provider: Any, formats: list[str]):
        self._provider = provider
        self._notice = NOTICE.format(formats=", ".join(formats))

    def __getattr__(self, name: str) -> Any:
        return getattr(self._provider, name)

    def generate(self, messages: list[dict[str, Any]], *args: Any, **kwargs: Any) -> Any:
        messages = [dict(m) for m in messages or []]
        if messages and messages[0].get("role") == "system":
            messages[0]["content"] = f"{messages[0].get('content', '')}\n\n{self._notice}"
        else:
            messages.insert(0, {"role": "system", "content": self._notice})
        return self._provider.generate(messages, *args, **kwargs)
