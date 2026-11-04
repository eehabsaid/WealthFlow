"""ComfyUI provider with mocked HTTP: workflow templates, text-to-image, image editing, connection test, unreachable server."""

from unittest.mock import MagicMock, patch

from core.services.ai.image_generation import generate_image, get_image_config, save_image_settings
from core.services.ai.image_generation import test_connection as check_connection
from core.services.ai.image_generation.providers import ImageProviderError, get_provider_class
from core.services.ai.image_generation.providers.comfyui_workflows import build_graph, model_inputs
from core.tests.ai.test_ai_image_generation import CFG, ImageBase, png


def _resp(code=200, body=None, content=b""):
    r = MagicMock(status_code=code, content=content)
    r.json.return_value = body if body is not None else {}
    return r


class ComfyUITests(ImageBase):
    def setUp(self):
        super().setUp()
        save_image_settings(CFG)

    def test_workflow_placeholders_are_typed_and_model_is_configured_value(self):
        g = build_graph("flux-2-klein-4b.safetensors", "text_to_image", {"prompt": "hi", "width": 512, "height": 256, "seed": 7})
        self.assertEqual(g["6"]["inputs"]["width"], 512)
        self.assertEqual(g["4"]["inputs"]["text"], "hi")
        self.assertEqual(model_inputs(g, "flux-2-klein-4b.safetensors"), [("UNETLoader", "unet_name")])
        with self.assertRaises(ImageProviderError):
            build_graph("unknown-model", "text_to_image", {})

    def _http(self, calls):
        def fake(method, url, **kw):
            calls.append((method, url, kw))
            if url.endswith("/upload/image"):
                return _resp(body={"name": "up.png", "subfolder": ""})
            if url.endswith("/prompt"):
                return _resp(body={"prompt_id": "p1"})
            if "/history/" in url:
                return _resp(body={"p1": {"status": {"completed": True}, "outputs": {"13": {"images": [{"filename": "o.png", "subfolder": "", "type": "output"}]}}}})
            if url.endswith("/view"):
                return _resp(content=png("green"))
            return _resp()
        return fake

    def test_text_to_image_and_edit_need_no_ui(self):
        calls = []
        provider = get_provider_class("comfyui")(get_image_config(include_secret=True), 5)
        with patch("requests.request", side_effect=self._http(calls)):
            out = provider.generate("a cat", width=512, height=512)
            self.assertTrue(out.data.startswith(b"\x89PNG"))
            self.assertFalse(any(u.endswith("/upload/image") for _, u, _ in calls))
            from core.services.ai.image_generation.providers.base import SourceImage
            provider.generate("darker", width=512, height=512, source=SourceImage(png(), "a.png", "image/png"))
        submitted = [kw["json"]["prompt"] for m, u, kw in calls if u.endswith("/prompt")]
        self.assertEqual(submitted[1]["14"]["inputs"]["image"], "up.png")
        self.assertIn("17", submitted[1])

    def test_unreachable_server_is_a_clean_error(self):
        import requests
        provider = get_provider_class("comfyui")(get_image_config(include_secret=True), 5)
        with patch("requests.request", side_effect=requests.ConnectionError("x")):
            with self.assertRaises(ImageProviderError):
                provider.generate("a cat", width=512, height=512)
            self.assertIn("error", generate_image(self.user, {"prompt": "a cat"}))

    def test_connection_reports_missing_model_files(self):
        def fake(method, url, **kw):
            if "/object_info/" in url:
                cls = url.rsplit("/", 1)[-1]
                req = {"UNETLoader": {"unet_name": [["other.safetensors"]]}}.get(cls, {})
                return _resp(body={cls: {"input": {"required": req}}})
            return _resp()
        with patch("requests.request", side_effect=fake):
            with self.assertRaises(ImageProviderError) as ctx:
                check_connection()
        self.assertIn("unet_name=flux-2-klein-4b.safetensors", str(ctx.exception))
