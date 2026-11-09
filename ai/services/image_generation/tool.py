"""The `generate_image` AI tool: provider-independent text-to-image and image editing.

Offered to the model only while image generation is enabled and configured (see defs.get_registered_tool_schemas and
investigation_tool_schemas). The model decides when to call it; the app saves the picture and shows it under the answer."""

from __future__ import annotations

from ai.services.image_generation.service import generate_image
from ai.services.image_generation.settings import image_generation_available

NAME = "generate_image"
_S, _I, _B = ({"type": t} for t in ("string", "integer", "boolean"))
_DESC = ("Create a new image from a text description, or edit an image the user attached or that was made earlier in this chat. "
         "Call it when the user asks to draw, design, mock up, illustrate, generate or change a picture. `prompt` is a detailed visual description "
         "(subject, layout, style, colours, text to show) written in English; for an edit describe the change to make. To edit, pass "
         "`source_image_id` (the id of an attached image) or `use_previous`=true for the most recent image. The app shows the image under "
         "your answer with a download button: never write a link or a file name.")
NOTICE = ("IMAGES: you CAN create and edit pictures: call generate_image when the user asks for an image, drawing, design or mockup, or to change "
          "a picture. Never say you cannot create images.")

TOOL_DEF = {
    "name": NAME, "description": _DESC, "is_read_only": True, "tier": "read", "domain": "image_generation", "offer_if": image_generation_available,
    "handler": lambda user, params: generate_image(user, params),
    "schema": {"type": "function", "function": {"name": NAME, "description": _DESC, "parameters": {"type": "object", "properties": {
        "prompt": {**_S, "description": "what the image should show, or for an edit what to change"},
        "source_image_id": {**_I, "description": "id of the image to edit (an attached image); omit for a new image"},
        "use_previous": {**_B, "description": "edit the most recent image of this user instead of making a new one"},
        "width": {**_I, "description": "optional pixel width (256-2048)"},
        "height": {**_I, "description": "optional pixel height (256-2048)"},
    }, "required": ["prompt"]}}},
}
