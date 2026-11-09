"""Configurable image generation: settings, provider interface, ComfyUI provider (mocked HTTP), the generate_image tool,
owner-scoped storage / download, and graceful behaviour when the feature is off or the provider is down."""

import io
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from PIL import Image

from core.authentication.services import AuthWorkflowService
from core.models import AppSettings
from ai.models.ai_attachment import AIAttachment
from ai.models.ai_conversation import AIConversation
from ai.models.ai_message import AIMessage
from ai.services.image_generation import (
    attach_generated_images, generate_image, get_image_config, image_generation_available, save_image_settings, validate_image_settings,
)
from ai.services.image_generation.providers import ImageProviderError, ImageResult, register
from ai.services.image_generation.providers.base import ImageProvider
from ai.services.tools import get_registered_tool_schemas, validate_and_execute_tool
from core.tests.billing.test_support import grant_ai_workspace_access

User = get_user_model()
CFG = {"image_gen_enabled": True, "image_gen_provider": "comfyui", "image_gen_model": "flux-2-klein-4b.safetensors",
       "image_gen_endpoint": "http://comfy.test:8188", "image_gen_api_key": ""}


def png(color="red", size=(64, 48)):
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "PNG")
    return buf.getvalue()


def names():
    return {s["function"]["name"] for s in get_registered_tool_schemas()}


def make_user(name, sysadmin=False):
    user = User.objects.create_user(username=name, password="pw12345!")
    if sysadmin:
        profile = AuthWorkflowService.get_profile(user)
        profile.is_sysadmin = True
        profile.save(update_fields=["is_sysadmin"])
    grant_ai_workspace_access(user)
    return user


class FakeProvider(ImageProvider):
    key, label, requires_endpoint = "fake", "Fake", False
    calls = []
    fail = False

    def test_connection(self):
        return "fake ok"

    def generate(self, prompt, *, width, height, source=None):
        FakeProvider.calls.append({"prompt": prompt, "w": width, "h": height, "source": source})
        if FakeProvider.fail:
            raise ImageProviderError("provider down")
        return ImageResult(data=png("blue"))


class ImageBase(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        register(FakeProvider)

    def setUp(self):
        FakeProvider.calls, FakeProvider.fail = [], False
        self.user = make_user("img-user")
        self.other = make_user("img-other")

    def tearDown(self):
        AppSettings.objects.filter(owner=None, key__startswith="image_gen_").delete()

    def enable_fake(self):
        save_image_settings({"image_gen_enabled": True, "image_gen_provider": "fake", "image_gen_model": "m"})


class SettingsTests(ImageBase):
    def test_defaults_off_and_tool_hidden(self):
        self.assertFalse(image_generation_available())
        self.assertNotIn("generate_image", names())

    def test_save_masks_key_and_keeps_it_on_masked_resave(self):
        save_image_settings({**CFG, "image_gen_api_key": "secret-123"})
        self.assertTrue(AppSettings.get("image_gen_api_key", user=None).startswith("enc:"))
        masked = get_image_config()["api_key"]
        self.assertNotIn("secret", masked)
        save_image_settings({"image_gen_api_key": masked})
        self.assertEqual(get_image_config(include_secret=True)["api_key"], "secret-123")

    def test_tool_offered_only_when_enabled_and_configured(self):
        save_image_settings({**CFG, "image_gen_enabled": False})
        self.assertNotIn("generate_image", names())
        save_image_settings(CFG)
        self.assertIn("generate_image", names())
        save_image_settings({"image_gen_endpoint": ""})
        self.assertNotIn("generate_image", names())

    def test_validation(self):
        self.assertIsNone(validate_image_settings(CFG))
        self.assertIn("Complete", validate_image_settings({**CFG, "image_gen_model": ""}))
        self.assertIn("http", validate_image_settings({**CFG, "image_gen_endpoint": "ftp://x"}))
        self.assertIn("Unknown", validate_image_settings({**CFG, "image_gen_provider": "nope"}))

    def test_no_settings_key_outside_the_known_fields(self):
        save_image_settings(CFG)
        keys = set(AppSettings.objects.filter(key__startswith="image_gen_").values_list("key", flat=True))
        self.assertTrue(keys <= {f"image_gen_{f}" for f in ("enabled", "provider", "model", "endpoint", "api_key", "start_command")})
        self.assertEqual(len(keys), 5)   # nothing else is created; the optional start command only when one is given


class ToolTests(ImageBase):
    def test_disabled_returns_error_without_calling_provider(self):
        out = generate_image(self.user, {"prompt": "a cat"})
        self.assertIn("error", out)
        self.assertEqual(FakeProvider.calls, [])

    def test_text_to_image_saves_owner_scoped_attachment(self):
        self.enable_fake()
        out = generate_image(self.user, {"prompt": "a cat", "width": 700, "height": 300})
        att = AIAttachment.objects.get(pk=out["image_id"])
        self.assertEqual((att.user, att.kind, att.mime, att.message), (self.user, "image", "image/png", None))
        self.assertEqual((FakeProvider.calls[0]["w"], FakeProvider.calls[0]["h"]), (688, 288))
        self.assertIsNone(FakeProvider.calls[0]["source"])
        self.assertTrue(att.to_dict()["generated"])

    def test_edit_uses_own_image_and_rejects_foreign_one(self):
        self.enable_fake()
        mine = AIAttachment.objects.create(user=self.user, name="a.png", kind="image", mime="image/png", size=1, data=png())
        theirs = AIAttachment.objects.create(user=self.other, name="b.png", kind="image", mime="image/png", size=1, data=png())
        out = generate_image(self.user, {"prompt": "make it dark", "source_image_id": mine.id})
        self.assertTrue(out["edited"])
        self.assertEqual(FakeProvider.calls[0]["source"].name, "a.png")
        self.assertIn("error", generate_image(self.user, {"prompt": "x", "source_image_id": theirs.id}))
        self.assertTrue(generate_image(self.user, {"prompt": "again", "use_previous": True})["ok"])

    def test_unavailable_provider_is_a_plain_error(self):
        self.enable_fake()
        FakeProvider.fail = True
        out = generate_image(self.user, {"prompt": "a cat"})
        self.assertIn("provider down", out["error"])
        with patch("ai.services.image_generation.service.build_provider", side_effect=RuntimeError("boom")):
            self.assertIn("unavailable", generate_image(self.user, {"prompt": "a cat"})["error"])

    def test_invalid_provider_output_is_refused(self):
        self.enable_fake()
        with patch.object(FakeProvider, "generate", return_value=ImageResult(data=b"<svg onload=alert(1)>")):
            self.assertIn("error", generate_image(self.user, {"prompt": "a cat"}))
        self.assertEqual(AIAttachment.objects.count(), 0)

    def test_runs_through_the_agent_tool_executor(self):
        self.enable_fake()
        audit, res = validate_and_execute_tool("generate_image", {"prompt": "logo"}, self.user)
        self.assertEqual(audit["status"], "success")
        self.assertTrue(res["data"]["ok"])
        audit, res = validate_and_execute_tool("generate_image", {}, self.user)
        self.assertEqual(audit["status"], "rejected")

    def test_images_attach_to_the_answer(self):
        self.enable_fake()
        since = timezone.now() - timedelta(seconds=5)
        out = generate_image(self.user, {"prompt": "a cat"})
        convo = AIConversation.objects.create(owner=self.user) if "owner" in [f.name for f in AIConversation._meta.fields] else AIConversation.objects.create(user=self.user)
        msg = AIMessage.objects.create(conversation=convo, role="assistant", content="here")
        attach_generated_images(self.user, since, msg)
        self.assertEqual(AIAttachment.objects.get(pk=out["image_id"]).message_id, msg.id)
        self.assertEqual(msg.to_dict()["attachments"][0]["generated"], True)
