from datetime import timedelta
import json
from datetime import date
from django.contrib.auth import get_user_model
from django.test import TestCase
from core.models import UserProfile

User = get_user_model()


class ProfileBirthdayUpdateTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="profileuser",
            email="profile@example.com",
            password="SecurePass123!",
            is_active=True,
        )
        self.client.force_login(self.user)

    def test_profile_update_sets_birthday(self):
        response = self.client.post(
            "/api/auth/profile/",
            data=json.dumps({"full_name": "Profile User", "birthday": "1992-10-15"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["profile"]["birthday"], "1992-10-15")

        profile = UserProfile.objects.get(user=self.user)
        self.assertEqual(profile.birthday, date(1992, 10, 15))

    def test_profile_update_allows_clearing_birthday(self):
        profile = UserProfile.objects.get(user=self.user)
        profile.birthday = date(1990, 1, 1)
        profile.save(update_fields=["birthday", "updated_at"])

        response = self.client.post(
            "/api/auth/profile/",
            data=json.dumps({"birthday": ""}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        profile.refresh_from_db()
        self.assertIsNone(profile.birthday)

    def test_profile_update_rejects_invalid_birthday_format(self):
        response = self.client.post(
            "/api/auth/profile/",
            data=json.dumps({"birthday": "15-10-1992"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid birthday format", response.json().get("error", ""))

    def test_profile_update_rejects_future_birthday(self):
        future_birthday = (date.today() + timedelta(days=3)).isoformat()
        response = self.client.post(
            "/api/auth/profile/",
            data=json.dumps({"birthday": future_birthday}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json().get("error"), "Birthday cannot be in the future.")
