"""Chat attachments: read by code, totals computed by the app, owner scoping, and the chat stage."""

import base64
import io
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from core.models import AIAttachment, AIConversation, AIMessage
from core.services.ai.attachments import link_to_message, model_input
from core.services.ai.attachments.extract import AttachmentError, extract
from core.tests.billing.test_support import grant_ai_workspace_access

User = get_user_model()
API = "/api/financial-advisor/ai/"
CSV = b"date,amount,note\n2026-01-01,100,a\n2026-01-02,250.5,b\n2026-01-03,50,c\n"


def _xlsx():
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.append(["item", "cost"])
    ws.append(["x", 10])
    ws.append(["y", 32])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _docx():
    from docx import Document
    d = Document()
    d.add_paragraph("Lease starts in March")
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


class ExtractTests(TestCase):
    def test_csv_totals_are_computed_by_code(self):
        kind, text = extract("a.csv", CSV)
        self.assertEqual(kind, "table")
        self.assertIn("amount: sum 400.5, min 50, max 250.5, count 3", text)
        self.assertIn("3 data rows", text)

    def test_xlsx_docx_txt_and_pdf_text(self):
        self.assertIn("cost: sum 42", extract("a.xlsx", _xlsx())[1])
        self.assertIn("Lease starts in March", extract("a.docx", _docx())[1])
        self.assertEqual(extract("n.txt", "مرحبا بك".encode())[1], "مرحبا بك")

    def test_image_has_no_text_and_bad_files_are_refused_with_a_reason(self):
        self.assertEqual(extract("p.png", b"\x89PNG")[0:2], ("image", ""))
        for name, raw, why in (("a.exe", b"x", "unsupported_type"), ("a.csv", b"", "empty"), ("a.xlsx", b"not a zip", "unreadable"), ("big.txt", b"x" * (10 * 1024 * 1024 + 1), "too_large")):
            with self.assertRaises(AttachmentError) as ctx:
                extract(name, raw)
            self.assertEqual(str(ctx.exception), why)

    def test_big_table_says_totals_cover_only_the_rows_read(self):
        rows = "n\n" + "\n".join(["1"] * 2500)
        text = extract("big.csv", rows.encode())[1]
        self.assertIn("FIRST 2000 ROWS ONLY (file has 2500)", text)


class UploadTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="member", password="pw12345!")
        self.other = User.objects.create_user(username="other", password="pw12345!")
        for u in (self.user, self.other):
            grant_ai_workspace_access(u)
        self.client.force_login(self.user)

    def up(self, name="a.csv", raw=CSV):
        return self.client.post(API + "attachments/", {"file": SimpleUploadedFile(name, raw)})

    def test_upload_and_unsupported_and_missing(self):
        res = self.up()
        self.assertEqual((res.status_code, res.json()["attachment"]["kind"]), (201, "table"))
        self.assertEqual(self.up("a.exe", b"x").status_code, 400)
        self.assertEqual(self.client.post(API + "attachments/").status_code, 400)

    def test_cannot_link_or_delete_someone_elses_file(self):
        att = AIAttachment.objects.create(user=self.other, name="s.txt", kind="text", text="secret")
        conv = AIConversation.objects.create(user=self.user)
        msg = AIMessage.objects.create(conversation=conv, role="user", content="q")
        self.assertEqual(link_to_message(self.user, [att.id], msg), [])
        self.assertEqual(self.client.delete(API + f"attachments/{att.id}/").status_code, 404)
        self.assertTrue(AIAttachment.objects.filter(pk=att.id, message__isnull=True).exists())

    def test_image_is_served_only_to_its_owner(self):
        att = AIAttachment.objects.create(user=self.user, name="p.png", kind="image", mime="image/png", data=b"\x89PNG")
        self.assertEqual(self.client.get(API + f"attachments/{att.id}/").status_code, 200)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(API + f"attachments/{att.id}/").status_code, 404)


class ModelInputTests(TestCase):
    def test_text_goes_in_front_of_the_question_and_images_become_base64(self):
        user = User.objects.create_user(username="u", password="pw12345!")
        t = AIAttachment.objects.create(user=user, name="a.txt", kind="text", text="FILE BODY")
        i = AIAttachment.objects.create(user=user, name="p.png", kind="image", data=b"abc")
        text, images = model_input("What is it?", [t, i], 10000)
        self.assertTrue(text.startswith("=== ATTACHED FILE: a.txt ==="))
        self.assertTrue(text.endswith("What is it?"))
        self.assertEqual(images, [base64.b64encode(b"abc").decode()])

    def test_long_text_is_cut_and_says_so(self):
        user = User.objects.create_user(username="u", password="pw12345!")
        t = AIAttachment.objects.create(user=user, name="a.txt", kind="text", text="x" * 9000)
        text, _ = model_input("q", [t], 3000)
        self.assertIn("[CUT: only the first 3000 of 9000", text)


class ChatStageTests(UploadTests):
    test_upload_and_unsupported_and_missing = test_cannot_link_or_delete_someone_elses_file = test_image_is_served_only_to_its_owner = None
    def chat(self, ids, reply="The total is 400.5"):
        provider = MagicMock()
        provider.generate.return_value = {"content": reply, "tool_calls": None, "error": None}
        with patch("core.views.ai_chat.ai_chat_core_views.get_active_ai_provider", return_value=provider):
            res = self.client.post(API + "chat/", data={"message": "What is the total amount?", "attachment_ids": ids}, content_type="application/json")
        return res, provider

    def test_files_reach_the_model_and_skip_instant_answers(self):
        att_id = self.up().json()["attachment"]["id"]
        res, provider = self.chat([att_id])
        self.assertEqual(res.json()["message"]["content"], "The total is 400.5")
        sent = provider.generate.call_args[0][0]
        self.assertIn("amount: sum 400.5", sent[-1]["content"])
        self.assertEqual(sent[0]["role"], "system")
        att = AIAttachment.objects.get(pk=att_id)
        self.assertEqual(att.message.content, "What is the total amount?")
        self.assertEqual(res.json()["message"]["sources"], ["a.csv"])

    def test_attachments_come_back_with_the_message_in_history(self):
        att_id = self.up().json()["attachment"]["id"]
        res, _ = self.chat([att_id])
        conv_id = res.json()["conversation_id"]
        msgs = self.client.get(API + f"conversations/{conv_id}/").json()["conversation"]["messages"]
        self.assertEqual(msgs[0]["attachments"][0]["name"], "a.csv")

    def test_picture_is_sent_as_an_image_and_a_failed_model_call_is_reported(self):
        att_id = self.up("p.png", b"\x89PNGdata").json()["attachment"]["id"]
        _, provider = self.chat([att_id])
        self.assertEqual(len(provider.generate.call_args[0][0][-1]["images"]), 1)
        att2 = self.up().json()["attachment"]["id"]
        provider = MagicMock()
        provider.generate.return_value = {"content": "", "tool_calls": None, "error": "model offline"}
        with patch("core.views.ai_chat.ai_chat_core_views.get_active_ai_provider", return_value=provider):
            res = self.client.post(API + "chat/", data={"message": "total?", "attachment_ids": [att2]}, content_type="application/json")
        self.assertFalse(res.json()["ok"])
