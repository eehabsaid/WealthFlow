"""Chat attachments: upload (extract by code), link to the message, build the model input."""

from __future__ import annotations

from ai.models.ai_attachment import AIAttachment

from ai.services.attachments.extract import MIME_BY_EXT, AttachmentError, ext_of, extract

__all__ = ["AttachmentError", "save_upload", "link_to_message", "model_input", "MAX_PER_MESSAGE"]
MAX_PER_MESSAGE = 5


def save_upload(user, name: str, raw: bytes) -> AIAttachment:
    name = (name or "file").replace("\\", "/").rsplit("/", 1)[-1][:200]
    kind, text = extract(name, raw)
    return AIAttachment.objects.create(user=user, name=name, kind=kind, mime=MIME_BY_EXT.get(ext_of(name), ""), size=len(raw), text=text,
                                       data=raw if kind == "image" else None)


def link_to_message(user, ids, message) -> list[AIAttachment]:
    """The user's own, still unlinked attachments from `ids`, attached to the message they just sent."""
    clean = [int(i) for i in (ids or []) if str(i).isdigit()][:MAX_PER_MESSAGE]
    rows = list(AIAttachment.objects.filter(user=user, pk__in=clean, message__isnull=True))
    AIAttachment.objects.filter(pk__in=[a.pk for a in rows]).update(message=message)
    return rows


def model_input(question: str, attachments, char_budget: int) -> tuple[str, list[str]]:
    """(user text with every file's text inside, base64 pictures). The text is cut to the budget and says so."""
    import base64

    per_file = max(2000, char_budget // max(1, sum(1 for a in attachments if a.kind != "image")))
    blocks, images = [], []
    for a in attachments:
        if a.kind == "image":
            images.append(base64.b64encode(bytes(a.data or b"")).decode())
            continue
        text = a.text if len(a.text) <= per_file else a.text[:per_file] + f"\n[CUT: only the first {per_file} of {len(a.text)} characters fit the model's context size]"
        blocks.append(f"=== ATTACHED FILE: {a.name} ===\n{text}\n=== END OF {a.name} ===")
    return ("\n\n".join(blocks) + "\n\n" if blocks else "") + question, images
