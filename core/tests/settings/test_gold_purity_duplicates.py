"""Gold purity settings: a duplicate / empty key must be a clean 4xx, never an unhandled 500 (IntegrityError)."""

import json

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import GoldPuritySetting

URL = "/api/settings/gold-purities/"


class GoldPurityKeyValidationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="gp_user", password="Pw123456!")
        self.other = get_user_model().objects.create_user(username="gp_other", password="Pw123456!")
        self.client.force_login(self.user)

    def post(self, key, **extra):
        return self.client.post(URL, json.dumps({"key": key, "label": key.upper(), **extra}), content_type="application/json")

    def test_create_ok_and_key_gets_k_suffix(self):
        res = self.post("e15")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()["key"], "e15k")

    def test_duplicate_key_is_409_not_500(self):
        self.client.get(URL)                       # seeds the default 24k/22k/21k/18k
        res = self.post("18k")
        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.json()["error_key"], "gold_purity_key_exists")
        self.assertEqual(GoldPuritySetting.objects.filter(owner=self.user, key="18k").count(), 1)

    def test_empty_key_is_400(self):
        res = self.post("")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()["error_key"], "gold_purity_key_required")

    def test_rename_to_existing_key_is_409_and_same_key_is_fine(self):
        self.client.get(URL)
        item = GoldPuritySetting.objects.get(owner=self.user, key="21k")
        put = lambda body: self.client.put(f"{URL}{item.id}/", json.dumps(body), content_type="application/json")  # noqa: E731
        self.assertEqual(put({"key": "24k"}).status_code, 409)
        self.assertEqual(put({"key": "21k", "label": "21 K"}).status_code, 200)

    def test_same_key_for_two_users_is_allowed(self):
        self.assertEqual(self.post("e77").status_code, 201)
        self.client.force_login(self.other)
        self.assertEqual(self.post("e77").status_code, 201)
