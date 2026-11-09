"""ComfyUI workflow templates: JSON data files in workflows/, never code.

A template is {"match": [substring, ...], "text_to_image": {graph}, "image_edit": {graph}} in ComfyUI's API format. The one whose
`match` substring occurs in the configured model name is used. Placeholders "{{model}}", "{{prompt}}", "{{width}}", "{{height}}",
"{{seed}}", "{{source}}" are filled in at run time (an exact "{{name}}" string becomes the typed value). To support another model
family, add a template file; no Python changes.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

from ai.services.image_generation.providers.base import ImageProviderError

DIR = Path(__file__).parent / "workflows"
MODES = ("text_to_image", "image_edit")


def _load_all() -> list[dict]:
    out = []
    for path in sorted(DIR.glob("*.json")):
        try:
            out.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            continue
    return out


def pick_template(model: str) -> dict:
    name = str(model or "").lower()
    for template in _load_all():
        if any(str(m).lower() in name for m in template.get("match", [])):
            return template
    raise ImageProviderError(f"No ComfyUI workflow template matches the model '{model}'. Add one to the workflows folder.")


def _fill(value, values: dict):
    if isinstance(value, dict):
        return {k: _fill(v, values) for k, v in value.items()}
    if isinstance(value, str) and "{{" in value:
        exact = value.strip()
        if exact.startswith("{{") and exact.endswith("}}") and exact[2:-2] in values:
            return values[exact[2:-2]]
        for key, replacement in values.items():
            value = value.replace("{{" + key + "}}", str(replacement))
    return value


def build_graph(model: str, mode: str, values: dict) -> dict:
    """The ready-to-submit API graph for `mode` with every placeholder filled."""
    template = pick_template(model)
    if mode not in template:
        raise ImageProviderError(f"The workflow for '{model}' has no {mode.replace('_', '-')} mode.")
    return _fill(copy.deepcopy(template[mode]), {"model": model, **values})


def model_inputs(graph: dict, model: str) -> list[tuple[str, str]]:
    """[(class_type, input_name)] of the nodes that load the configured model (used to check it exists on the server)."""
    return [(n["class_type"], k) for n in graph.values() for k, v in n.get("inputs", {}).items() if v == model]
