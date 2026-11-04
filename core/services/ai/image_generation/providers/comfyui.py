"""ComfyUI provider: talks to ComfyUI's HTTP API only (POST /prompt, GET /history, GET /view, POST /upload/image).

ComfyUI's own browser UI does not have to be open. The workflow comes from a JSON template matched to the configured model
(comfyui_workflows.py); the URL, model and optional credentials come from the saved settings.
"""

from __future__ import annotations

import logging
import random
import time
import uuid

import requests

from .base import ImageProvider, ImageProviderError, ImageResult, SourceImage
from .comfyui_workflows import MODES, build_graph, pick_template
from .registry import register

logger = logging.getLogger(__name__)
POLL_S = 1.0
_UNREACHABLE = "ComfyUI is not reachable with the saved API URL and credentials."


def _problems(body) -> str:
    """The readable reasons inside a ComfyUI error body (workflow validation errors name the node and what is wrong)."""
    if not isinstance(body, dict):
        return ""
    parts = [str((body.get("error") or {}).get("message") or "")] if isinstance(body.get("error"), dict) else []
    for node in (body.get("node_errors") or {}).values():
        for err in node.get("errors", []):
            parts.append(f"{node.get('class_type', 'node')}: {err.get('message', '')} {str(err.get('details') or '')[:80]}".strip())
    return "; ".join(p for p in parts if p)[:400]


@register
class ComfyUIProvider(ImageProvider):
    key = "comfyui"
    label = "ComfyUI (API)"
    requires_endpoint = True
    requires_api_key = False
    supports_edit = True

    def _url(self, path: str) -> str:
        return self.cfg["endpoint"].rstrip("/") + path

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.cfg['api_key']}"} if self.cfg.get("api_key") else {}

    def _call(self, method: str, path: str, **kw):
        try:
            return requests.request(method, self._url(path), headers=self._headers(), timeout=min(self.timeout, 60), **kw)
        except requests.RequestException as exc:   # the cause (refused, timeout, proxy, TLS...) is shown: "not reachable" alone hides it
            logger.warning("ComfyUI request %s %s failed: %r", method, path, exc)
            raise ImageProviderError(f"{_UNREACHABLE} Cause: {type(exc).__name__}: {str(exc)[:200]}") from None

    def _json(self, response, what: str):
        if response.status_code >= 400:
            try:
                detail = _problems(response.json())
            except ValueError:
                detail = ""
            raise ImageProviderError(f"ComfyUI {what} failed (HTTP {response.status_code}){': ' + detail if detail else ''}")
        try:
            return response.json()
        except ValueError:
            raise ImageProviderError(f"ComfyUI {what} returned an unreadable answer.") from None

    def test_connection(self) -> str:
        self._json(self._call("GET", "/system_stats"), "connection test")
        template = pick_template(self.cfg["model"])
        graphs = {m: build_graph(self.cfg["model"], m, {"prompt": "", "width": 512, "height": 512, "seed": 0, "source": ""}) for m in MODES if m in template}
        classes = sorted({n["class_type"] for g in graphs.values() for n in g.values()})
        info, missing = {}, []
        for cls in classes:
            response = self._call("GET", f"/object_info/{cls}")
            if response.status_code != 200 or cls not in (response.json() or {}):
                missing.append(cls)
            else:
                info[cls] = response.json()[cls]
        if missing:
            raise ImageProviderError(f"ComfyUI is reachable but lacks the nodes this workflow needs: {', '.join(missing)}. Update ComfyUI.")
        absent = []
        for node in graphs["text_to_image"].values():   # every model / text-encoder / VAE file the workflow names must exist on the server
            for name, spec in info[node["class_type"]].get("input", {}).get("required", {}).items():
                options, value = (spec[0] if spec else None), node["inputs"].get(name)
                if isinstance(options, list) and isinstance(value, str) and value not in options:
                    absent.append(f"{name}={value}")
        if absent:
            raise ImageProviderError(f"ComfyUI is reachable but these files are not installed on it: {', '.join(absent)}.")
        return "ComfyUI is reachable; the workflow nodes and model files are installed."

    def _upload(self, source: SourceImage) -> str:
        ext = source.name.rsplit(".", 1)[-1].lower() if "." in source.name else "png"
        files = {"image": (f"wealthflow-{uuid.uuid4().hex}.{ext}", source.data, source.mime or "image/png")}
        body = self._json(self._call("POST", "/upload/image", files=files, data={"overwrite": "true", "type": "input"}), "image upload")
        name = body.get("name") if isinstance(body, dict) else None
        if not name:
            raise ImageProviderError("ComfyUI did not accept the source image.")
        return f"{body['subfolder']}/{name}" if body.get("subfolder") else name

    def _queue(self, graph: dict) -> str:
        body = self._json(self._call("POST", "/prompt", json={"prompt": graph, "client_id": uuid.uuid4().hex}), "workflow submit")
        if not isinstance(body, dict) or not body.get("prompt_id"):
            raise ImageProviderError("ComfyUI did not queue the workflow.")
        return str(body["prompt_id"])

    def _wait(self, prompt_id: str) -> dict:
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            entry = (self._json(self._call("GET", f"/history/{prompt_id}"), "status check") or {}).get(prompt_id)
            if entry:
                status = entry.get("status") or {}
                if status.get("status_str") == "error":
                    raise ImageProviderError("ComfyUI stopped with an error while generating the image.")
                for output in (entry.get("outputs") or {}).values():
                    if output.get("images"):
                        return output["images"][0]
                if status.get("completed"):
                    raise ImageProviderError("ComfyUI finished without producing an image.")
            time.sleep(POLL_S)
        raise ImageProviderError("ComfyUI did not finish within the time limit.")

    def generate(self, prompt: str, *, width: int, height: int, source: SourceImage | None = None) -> ImageResult:
        values = {"prompt": prompt, "width": width, "height": height, "seed": random.randint(0, 2**53 - 1)}
        if source is not None:
            values["source"] = self._upload(source)
        graph = build_graph(self.cfg["model"], "image_edit" if source is not None else "text_to_image", values)
        image = self._wait(self._queue(graph))
        params = {"filename": image.get("filename", ""), "subfolder": image.get("subfolder", ""), "type": image.get("type", "output")}
        response = self._call("GET", "/view", params=params)
        if response.status_code != 200 or not response.content:
            raise ImageProviderError("ComfyUI produced the image but it could not be downloaded.")
        return ImageResult(data=response.content)
