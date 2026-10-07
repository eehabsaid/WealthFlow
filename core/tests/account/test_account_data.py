"""Own-data export + account deletion: scope coverage, isolation, no orphans, endpoint rules."""

import json

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import (AIMessage, AIPrompt, BalanceEntry, Bank, Currency, CurrencyExchange, Document, FixedAsset)
from core.services.account import build_user_export, classify, deletion_blocker, purge_user
from core.services.backup_serializer import get_model_export_order
from core.tests.account.support import make_user_with_data

User = get_user_model()


class ScopeCoverageTests(TestCase):
    def test_every_backup_table_is_owned_special_or_global(self):
        unknown = [m.__name__ for _p, m, _n in get_model_export_order() if classify(m) == "unclassified"]
        self.assertEqual(unknown, [], "Classify new models in core/services/account/scope.py (owner FK, or GLOBAL_MODELS).")


class ExportTests(TestCase):
    def setUp(self):
        self.a, self.b = make_user_with_data("alice"), make_user_with_data("bob")

    def test_export_contains_only_own_rows_and_no_secrets(self):
        data = build_user_export(self.a)
        blob = json.dumps(data)
        self.assertIn("alice", blob)
        for leak in ("bob", "secret of bob", self.b.email):
            self.assertNotIn(leak, blob)
        user_row = data["tables"]["auth.User"][0]
        self.assertNotIn("password", user_row)
        self.assertNotIn("core.AuthToken", data["tables"])
        for label in ("core.FixedAsset", "core.Document", "core.CurrencyExchange", "core.AIPrompt", "core.AIMessage", "core.BalanceEntry"):
            self.assertEqual(data["row_counts"][label], len([r for r in data["tables"][label]]), label)
            self.assertGreaterEqual(data["row_counts"][label], 1, label)
        self.assertEqual(data["tables"]["core.Document"][0]["file_content"], "YWJj")  # base64 file included

    def test_endpoint_downloads_json_for_signed_in_user_only(self):
        self.assertIn(self.client.get("/api/account/export/").status_code, (302, 401))
        self.client.force_login(self.a)
        res = self.client.get("/api/account/export/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("attachment", res["Content-Disposition"])
        self.assertEqual(json.loads(res.content)["username"], "alice")
        self.assertEqual(self.client.post("/api/account/export/").status_code, 405)


class DeletionTests(TestCase):
    def setUp(self):
        self.a, self.b = make_user_with_data("alice"), make_user_with_data("bob")

    def test_purge_removes_everything_of_one_user_and_nothing_of_the_other(self):
        before_b = {m: m.objects.filter(**f).count() for m, f in self._b_filters().items()}
        purge_user(self.a)
        self.assertFalse(User.objects.filter(username="alice").exists())
        for model in (FixedAsset, BalanceEntry, Bank, Currency):
            self.assertFalse(model.objects.filter(owner_id=self.a.id).exists(), model.__name__)
        self.assertEqual(Document.objects.count(), 1)        # bob's only: no orphaned alice file
        self.assertEqual(CurrencyExchange.objects.count(), 1)
        self.assertEqual(AIPrompt.objects.count(), 1)
        self.assertFalse(AIMessage.objects.filter(content__contains="alice").exists())
        self.assertEqual({m: m.objects.filter(**f).count() for m, f in self._b_filters().items()}, before_b)

    def _b_filters(self):
        return {FixedAsset: {"owner": self.b}, BalanceEntry: {"owner": self.b}, Document: {"uploaded_by": self.b},
                CurrencyExchange: {"user": self.b}, AIPrompt: {"user": self.b}}

    def test_endpoint_requires_confirmation_and_password(self):
        self.client.force_login(self.a)
        post = lambda body: self.client.post("/api/account/delete/", json.dumps(body), content_type="application/json")
        self.assertEqual(post({"password": "Pass12345!"}).status_code, 400)
        self.assertEqual(post({"confirm": "delete me", "password": "Pass12345!"}).status_code, 400)
        self.assertEqual(post({"confirm": "DELETE", "password": "wrong"}).status_code, 403)
        self.assertTrue(User.objects.filter(username="alice").exists())
        res = post({"confirm": "DELETE", "password": "Pass12345!"})
        self.assertEqual(res.status_code, 200)
        self.assertFalse(User.objects.filter(username="alice").exists())
        self.assertIn(self.client.get("/api/account/export/").status_code, (302, 401))  # session ended
        self.assertTrue(User.objects.filter(username="bob").exists())

    def test_last_admin_cannot_delete_but_can_once_another_admin_exists(self):
        admin = User.objects.create_superuser("root", "root@example.com", "Pass12345!")
        self.assertIsNotNone(deletion_blocker(admin))
        self.client.force_login(admin)
        body = json.dumps({"confirm": "DELETE", "password": "Pass12345!"})
        self.assertEqual(self.client.post("/api/account/delete/", body, content_type="application/json").status_code, 409)
        User.objects.create_superuser("root2", "r2@example.com", "Pass12345!")
        self.assertIsNone(deletion_blocker(admin))
        self.assertEqual(self.client.post("/api/account/delete/", body, content_type="application/json").status_code, 200)

    def test_lapsed_user_can_still_export_and_delete(self):
        from datetime import timedelta
        from django.utils import timezone
        from core.models import Plan, Subscription
        plan = Plan.objects.create(code="acct_p", name="P", sort_order=1)
        Subscription.objects.create(owner=self.a, plan=plan, status="trialing", trial_end=timezone.now() - timedelta(days=3))
        self.client.force_login(self.a)
        self.assertEqual(self.client.get("/api/balance/").status_code, 402)
        self.assertEqual(self.client.get("/api/account/export/").status_code, 200)
        res = self.client.post("/api/account/delete/", json.dumps({"confirm": "DELETE", "password": "Pass12345!"}), content_type="application/json")
        self.assertEqual(res.status_code, 200)
