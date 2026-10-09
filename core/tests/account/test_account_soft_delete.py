"""Soft-delete with a restorable grace period, scheduled purge, last-admin protection, admin Users screen."""

import json
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from core.models import AppSettings, BalanceEntry, UserProfile
from core.services.account import deletion_blocker, grace_days, is_pending_deletion, purge_at, purge_due_users, restore_user, schedule_deletion
from core.services.shared.scheduler_service import SchedulerService
from core.tests.account.support import make_user_with_data

User = get_user_model()
PW = "Pass12345!"


def _post(client, url, body):
    return client.post(url, json.dumps(body), content_type="application/json")


class GraceAndScheduleTests(TestCase):
    def setUp(self):
        self.a = make_user_with_data("alice")

    def test_grace_days_default_setting_and_bad_value(self):
        self.assertEqual(grace_days(), 30)
        AppSettings.set("account_deletion_grace_days", "7")
        self.assertEqual(grace_days(), 7)
        AppSettings.set("account_deletion_grace_days", "oops")
        self.assertEqual(grace_days(), 30)

    def test_schedule_disables_but_keeps_data(self):
        when = schedule_deletion(self.a)
        self.a.refresh_from_db()
        self.assertFalse(self.a.is_active)
        self.assertTrue(is_pending_deletion(self.a))
        self.assertEqual(self.a.profile.account_status, "pending_deletion")
        self.assertEqual(when, purge_at(self.a.profile))
        self.assertTrue(BalanceEntry.objects.filter(owner=self.a).exists())

    def test_restore_reenables_and_clears_marker(self):
        schedule_deletion(self.a)
        self.assertTrue(restore_user(self.a))
        self.a.refresh_from_db()
        self.assertTrue(self.a.is_active)
        self.assertFalse(is_pending_deletion(self.a))
        self.assertEqual(self.a.profile.account_status, "active")
        self.assertFalse(restore_user(self.a))  # nothing pending any more

    def test_scheduling_twice_keeps_original_clock(self):
        stamp = lambda: UserProfile.objects.get(user=self.a).deletion_requested_at
        schedule_deletion(self.a)
        first = stamp()
        self.assertIsNotNone(first)
        schedule_deletion(self.a)
        self.assertEqual(stamp(), first)


class PurgeJobTests(TestCase):
    def setUp(self):
        self.a, self.b = make_user_with_data("alice"), make_user_with_data("bob")

    def _backdate(self, user, days):
        user.profile.deletion_requested_at = timezone.now() - timedelta(days=days)
        user.profile.save(update_fields=["deletion_requested_at"])

    def test_purges_only_accounts_past_grace(self):
        schedule_deletion(self.a)
        schedule_deletion(self.b)
        self._backdate(self.a, 31)
        self._backdate(self.b, 29)
        self.assertEqual(purge_due_users()["purged"], 1)
        self.assertFalse(User.objects.filter(username="alice").exists())
        self.assertFalse(BalanceEntry.objects.filter(owner_id=self.a.id).exists())
        self.assertTrue(User.objects.filter(username="bob").exists())

    def test_active_accounts_are_never_purged(self):
        self.assertEqual(purge_due_users()["purged"], 0)
        self.assertTrue(User.objects.filter(username="alice").exists())

    def test_last_admin_is_kept(self):
        admin = User.objects.create_superuser("root", "root@example.com", PW)
        schedule_deletion(admin)  # bypassing the blocker, as a stale state would
        self._backdate(admin, 99)
        result = purge_due_users()
        self.assertEqual(result["kept_last_admin"], ["root"])
        self.assertTrue(User.objects.filter(username="root").exists())

    def test_job_is_registered_in_scheduler(self):
        schedule_deletion(self.a)
        self._backdate(self.a, 40)
        self.assertEqual(SchedulerService().run_job("account_purge")["purged"], 1)


class LoginAndRestoreTests(TestCase):
    def setUp(self):
        cache.clear()
        self.a = make_user_with_data("alice")
        schedule_deletion(self.a)

    def test_login_is_blocked_with_clear_message_and_restore_link(self):
        res = self.client.post("/accounts/login/", {"username": "alice", "password": PW})
        self.assertContains(res, "auth_status_pending_deletion")
        self.assertContains(res, "/accounts/restore/?username=alice")
        api = _post(self.client, "/api/auth/login/", {"username": "alice", "password": PW})
        self.assertEqual(api.status_code, 400)
        self.assertEqual(api.json()["error_key"], "auth_status_pending_deletion")

    def test_restore_page_needs_right_password(self):
        self.assertEqual(self.client.get("/accounts/restore/").status_code, 200)
        res = self.client.post("/accounts/restore/", {"username": "alice", "password": "wrong"})
        self.assertContains(res, "auth_restore_invalid")
        self.assertTrue(is_pending_deletion(User.objects.get(username="alice")))

    def test_restore_then_login_works(self):
        res = self.client.post("/accounts/restore/", {"username": "alice", "password": PW})
        self.assertContains(res, "auth_restore_done")
        self.assertTrue(self.client.login(username="alice", password=PW))

    def test_restore_is_throttled(self):
        for _ in range(5):
            self.client.post("/accounts/restore/", {"username": "alice", "password": "bad"})
        res = self.client.post("/accounts/restore/", {"username": "alice", "password": PW})
        self.assertContains(res, "auth_restore_too_many")
        self.assertTrue(is_pending_deletion(User.objects.get(username="alice")))

    def test_restore_unknown_or_active_user_gives_same_error(self):
        make_user_with_data("bob")
        for name in ("nobody", "bob"):
            res = self.client.post("/accounts/restore/", {"username": name, "password": PW})
            self.assertContains(res, "auth_restore_invalid")


class AdminUsersScreenTests(TestCase):
    def setUp(self):
        self.admin, self.other = (self._sysadmin("root"), self._sysadmin("root2"))
        self.member = make_user_with_data("alice")
        self.client.force_login(self.admin)

    @staticmethod
    def _sysadmin(name):
        user = User.objects.create_superuser(name, f"{name}@example.com", PW)
        user.profile.is_sysadmin = True
        user.profile.save(update_fields=["is_sysadmin"])
        return user

    def test_delete_schedules_and_list_reports_purge_date(self):
        res = self.client.delete(f"/api/users/{self.member.pk}/")
        self.assertEqual(res.json(), {"deleted": self.member.pk, "scheduled": True})
        row = next(u for u in self.client.get("/api/users/").json()["users"] if u["username"] == "alice")
        self.assertEqual(row["account_status"], "pending_deletion")
        self.assertIsNotNone(row["purge_at"])

    def test_restore_endpoint_and_bulk(self):
        self.client.delete(f"/api/users/{self.member.pk}/")
        self.assertEqual(_post(self.client, f"/api/users/{self.member.pk}/", {"action": "restore"}).status_code, 200)
        self.assertEqual(_post(self.client, f"/api/users/{self.member.pk}/", {"action": "restore"}).status_code, 400)
        self.client.delete(f"/api/users/{self.member.pk}/")
        res = _post(self.client, "/api/users/bulk/", {"action": "restore", "ids": [self.member.pk]})
        self.assertEqual(res.json()["changed"], 1)
        self.assertTrue(User.objects.get(pk=self.member.pk).is_active)

    def test_activate_cancels_pending_deletion(self):
        self.client.delete(f"/api/users/{self.member.pk}/")
        _post(self.client, "/api/users/bulk/", {"action": "activate", "ids": [self.member.pk]})
        self.assertFalse(is_pending_deletion(User.objects.get(pk=self.member.pk)))

    def test_deactivate_skips_pending_deletion_accounts(self):
        self.client.delete(f"/api/users/{self.member.pk}/")
        res = _post(self.client, "/api/users/bulk/", {"action": "deactivate", "ids": [self.member.pk]})
        self.assertEqual(res.json()["changed"], 0)
        self.assertTrue(is_pending_deletion(User.objects.get(pk=self.member.pk)))

    def test_purge_now_only_for_pending_accounts(self):
        self.assertEqual(self.client.delete(f"/api/users/{self.member.pk}/?purge_now=1").status_code, 400)
        self.client.delete(f"/api/users/{self.member.pk}/")
        self.assertEqual(self.client.delete(f"/api/users/{self.member.pk}/?purge_now=1").status_code, 200)
        self.assertFalse(User.objects.filter(pk=self.member.pk).exists())

    def test_last_active_admin_cannot_be_deleted_by_anyone(self):
        self.client.delete(f"/api/users/{self.other.pk}/")  # fine: root remains
        self.assertEqual(self.client.delete(f"/api/users/{self.admin.pk}/").status_code, 409)
        res = _post(self.client, "/api/users/bulk/", {"action": "delete", "ids": [self.admin.pk]})
        self.assertEqual(res.json()["blocked_last_admin"], ["root"])
        self.assertTrue(User.objects.get(pk=self.admin.pk).is_active)

    def test_pending_admin_does_not_count_as_active_admin(self):
        self.client.delete(f"/api/users/{self.other.pk}/")
        self.assertIsNotNone(deletion_blocker(self.admin))


import re  # noqa: E402

from django.core import mail  # noqa: E402
from django.test import override_settings  # noqa: E402

from core.services.account import restore_needs_admin  # noqa: E402


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", DEFAULT_FROM_EMAIL="noreply@example.com")
class ForgottenPasswordSelfServiceTests(TestCase):
    """A user who forgot the password restores the account without an admin: reset by email, then restore."""

    def setUp(self):
        cache.clear()
        AppSettings.set("administrator_notification_email", "owner@example.com")
        AppSettings.set("active_language", "en")
        self.a = make_user_with_data("alice")
        self.a.email = "alice@example.com"
        self.a.save(update_fields=["email"])
        schedule_deletion(self.a)

    def test_reset_by_email_then_restore_with_new_password(self):
        self.client.post("/accounts/forgot-password/", {"email": "alice@example.com", "lang": "en"})
        token = re.search(r"/accounts/reset-password/([^/\s]+)/", mail.outbox[0].body).group(1)
        done = self.client.post(f"/accounts/reset-password/{token}/", {"password": "NewSecure123!", "confirm_password": "NewSecure123!", "lang": "en"})
        self.assertContains(done, "auth_password_reset_success_pending_deletion")
        self.assertContains(done, "/accounts/restore/?username=alice")
        self.assertTrue(is_pending_deletion(User.objects.get(username="alice")))  # the reset alone never restores
        self.assertContains(self.client.post("/accounts/restore/", {"username": "alice", "password": PW}), "auth_restore_invalid")  # old password
        self.assertContains(self.client.post("/accounts/restore/", {"username": "alice", "password": "NewSecure123!"}), "auth_restore_done")
        self.assertTrue(self.client.login(username="alice", password="NewSecure123!"))

    def test_restore_page_links_to_forgot_password(self):
        self.assertContains(self.client.get("/accounts/restore/"), "/accounts/forgot-password/")


class RestoreNeverBypassesAdminDecisionTests(TestCase):
    def setUp(self):
        cache.clear()
        self.a = make_user_with_data("alice")

    def _disable_then_delete(self):
        from core.authentication.services import AuthWorkflowService

        AuthWorkflowService.disable_user(self.a)
        self.a.refresh_from_db()
        schedule_deletion(self.a)

    def test_previously_disabled_account_cannot_self_restore(self):
        self._disable_then_delete()
        self.assertTrue(restore_needs_admin(self.a))
        res = self.client.post("/accounts/restore/", {"username": "alice", "password": PW})
        self.assertContains(res, "auth_restore_needs_admin")
        self.assertTrue(is_pending_deletion(User.objects.get(username="alice")))

    def test_admin_restore_returns_to_previous_disabled_state(self):
        self._disable_then_delete()
        self.assertTrue(restore_user(self.a))
        self.a.refresh_from_db()
        self.assertFalse(self.a.is_active)
        self.assertEqual(self.a.profile.account_status, "disabled")
        self.assertFalse(is_pending_deletion(self.a))

    def test_active_account_still_self_restores(self):
        schedule_deletion(self.a)
        self.assertFalse(restore_needs_admin(self.a))
        self.assertContains(self.client.post("/accounts/restore/", {"username": "alice", "password": PW}), "auth_restore_done")
