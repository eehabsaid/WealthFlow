"""Generated / edited images live in AIAttachment (the chat's existing attachment table): owner-scoped, served by the existing
attachment endpoint, linked to the answer that produced them. Nothing is kept outside the database."""

from __future__ import annotations

import io

from PIL import Image

from core.models import AIAttachment
from core.models.ai_attachment import GENERATED_PREFIX

from .providers.base import ImageProviderError, SourceImage

FORMATS = {"PNG": ("image/png", "png"), "JPEG": ("image/jpeg", "jpg"), "WEBP": ("image/webp", "webp")}
MAX_BYTES = 20 * 1024 * 1024


def inspect_image(data: bytes) -> tuple[str, str, tuple[int, int]]:
    """(mime, extension, (width, height)) from the image's own bytes; anything that is not PNG / JPEG / WEBP is refused."""
    try:
        with Image.open(io.BytesIO(data)) as img:
            img.verify()
        with Image.open(io.BytesIO(data)) as img:
            fmt, size = img.format, img.size
    except Exception:
        raise ImageProviderError("The provider did not return a valid image.") from None
    if fmt not in FORMATS or len(data) > MAX_BYTES:
        raise ImageProviderError("The provider returned an unsupported or oversized image.")
    return FORMATS[fmt][0], FORMATS[fmt][1], size


def save_generated(user, data: bytes, prompt: str) -> AIAttachment:
    mime, ext, _ = inspect_image(data)
    count = AIAttachment.objects.filter(user=user, text__startswith=GENERATED_PREFIX).count() + 1
    return AIAttachment.objects.create(user=user, name=f"generated-{count}.{ext}", kind="image", mime=mime, size=len(data),
                                       text=GENERATED_PREFIX + prompt[:2000], data=data)


def resolve_source(user, source_id=None, use_previous: bool = False) -> SourceImage | None:
    """The user's OWN image to edit: by id, or their most recent image. None when no image was asked for; an unknown id raises."""
    qs = AIAttachment.objects.filter(user=user, kind="image")
    if source_id not in (None, ""):
        item = qs.filter(pk=source_id).first() if str(source_id).isdigit() else None
        if item is None:
            raise ImageProviderError("The image to edit was not found among your images.")
    elif use_previous:
        item = qs.order_by("-id").first()
        if item is None:
            raise ImageProviderError("There is no earlier image to edit. Ask the user to attach one.")
    else:
        return None
    return SourceImage(data=bytes(item.data or b""), name=item.name, mime=item.mime)


def attach_generated_images(user, since, message) -> None:
    """After an answer is saved: the images generated while writing it belong to that answer (like charts and cards)."""
    AIAttachment.objects.filter(user=user, message__isnull=True, created_at__gte=since, text__startswith=GENERATED_PREFIX).update(message=message)
