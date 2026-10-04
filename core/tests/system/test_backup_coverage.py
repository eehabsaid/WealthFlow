"""Backup completeness: every table of the app is in the backup, and the tables that were once missed survive a round trip
(Budgets, login-attempt tables, admin log, permissions and the user/group/permission links).

Regression: Budget and RecurringTransaction (added with the budgets feature) were missing from
get_model_export_order(), so a backup silently dropped them. The guard below fails the moment a new model is
added without being registered (or being listed here as intentionally not backed up).
"""

import os
import shutil
import tempfile
import zipfile
from datetime import date
from decimal import Decimal

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from core.services.backup_serializer import get_model_export_order

# Only login sessions are deliberately NOT part of a backup: restoring them would re-open other people's logged-in
# sessions on another server. Everything else, including axes login attempts, admin log, permissions, content types and
# the auth link tables, IS backed up. Adding to this set needs an explicit decision.
NOT_BACKED_UP = {"sessions.Session"}


class BackupCoverageTests(TestCase):
    def test_every_model_is_backed_up_or_explicitly_excluded(self):
        registered = {m for _, m, _ in get_model_export_order()}
        missing = sorted(m._meta.label for m in apps.get_models(include_auto_created=True) if m not in registered and m._meta.label not in NOT_BACKED_UP)
        self.assertEqual(missing, [], f"Models missing from get_model_export_order() (backup would drop them): {missing}")

    def test_export_order_has_no_duplicates_and_unique_prefixes(self):
        order = get_model_export_order()
        self.assertEqual(len({m for _, m, _ in order}), len(order))
        self.assertEqual(len({p for p, _, _ in order}), len(order))

    def test_budgets_and_recurring_transactions_round_trip(self):
        from core.models import Budget, Currency, Expense, ExpenseCategory, RecurringTransaction

        user = get_user_model().objects.create_user(username="bk_budget_user", password="Pw123456!")
        egp = Currency.objects.get_or_create(owner=user, code="EGP", defaults={"symbol": "E", "name": "Egyptian Pound"})[0]   # new users get default currencies
        cat = ExpenseCategory.objects.create(owner=user, name="Food")
        Budget.objects.create(owner=user, name="Food budget", category=cat, period="monthly", amount=Decimal("1500.00"),
                              currency=egp, amount_base=Decimal("1500.00"), alert_threshold_percent=75)
        RecurringTransaction.objects.create(owner=user, name="Netflix", category=cat, amount=Decimal("199.00"), currency=egp,
                                            frequency="monthly", interval=1, start_date=date(2026, 1, 1), next_run_date=date(2026, 11, 1))
        tmp = tempfile.mkdtemp()
        try:
            path = os.path.join(tmp, "b.wfbackup")
            call_command("backup_data", output=tmp, filename="b.wfbackup", no_compress=True)
            with zipfile.ZipFile(path) as zf:
                names = zf.namelist()
            self.assertTrue(any(n.endswith("_budget.json") for n in names), names)
            self.assertTrue(any(n.endswith("_recurringtransaction.json") for n in names), names)

            Budget.objects.all().delete()
            RecurringTransaction.objects.all().delete()
            call_command("restore_data", path)

            b = Budget.objects.get(owner=user)
            self.assertEqual((b.name, b.amount, b.alert_threshold_percent, b.category_id, b.currency_id), ("Food budget", Decimal("1500.00"), 75, cat.id, egp.id))
            r = RecurringTransaction.objects.get(owner=user)
            self.assertEqual((r.name, r.amount, r.next_run_date, r.category_id), ("Netflix", Decimal("199.00"), date(2026, 11, 1), cat.id))
            self.assertEqual(Expense.objects.filter(owner=user).count(), 0)   # restore must not invent expenses
        finally:
            shutil.rmtree(tmp)

    def test_ai_answer_feedback_round_trip(self):
        """Zip 2: thumbs up/down (the AI's learned examples) survive backup -> delete -> restore, with their message."""
        from core.models import AIAnswerFeedback, AIConversation, AIMessage

        user = get_user_model().objects.create_user(username="bk_ai_fb_user", password="Pw123456!")
        conv = AIConversation.objects.create(user=user, title="t")
        AIMessage.objects.create(conversation=conv, role="user", content="where do I record a laptop?")
        up = AIMessage.objects.create(conversation=conv, role="assistant", content="As an asset.", sources=["app_knowledge"])
        down = AIMessage.objects.create(conversation=conv, role="assistant", content="Wrong answer.")
        AIAnswerFeedback.objects.create(owner=user, message=up, question="where do I record a laptop?", answer="As an asset.", rating=1, kind="workflow")
        AIAnswerFeedback.objects.create(owner=user, message=down, question="where do I record a laptop?", answer="Wrong answer.", rating=-1, kind="workflow")
        tmp = tempfile.mkdtemp()
        try:
            path = os.path.join(tmp, "f.wfbackup")
            call_command("backup_data", output=tmp, filename="f.wfbackup", no_compress=True)
            with zipfile.ZipFile(path) as zf:
                self.assertTrue(any(n.endswith("_aianswerfeedback.json") for n in zf.namelist()), zf.namelist())
            conv.delete()   # cascades to the messages and the feedback
            self.assertEqual(AIAnswerFeedback.objects.count(), 0)
            call_command("restore_data", path)
            rows = {r.rating: r for r in AIAnswerFeedback.objects.filter(owner=user)}
            self.assertEqual(set(rows), {1, -1})
            self.assertEqual((rows[1].answer, rows[1].kind, rows[1].message.sources), ("As an asset.", "workflow", ["app_knowledge"]))
            self.assertEqual(rows[-1].message.content, "Wrong answer.")
        finally:
            shutil.rmtree(tmp)


class AuthAndSecurityTablesRoundTripTests(TestCase):
    """Login attempts, admin log, permissions and who-holds-what survive backup -> delete -> restore."""

    def _backup(self, tmp):
        call_command("backup_data", output=tmp, filename="a.wfbackup", no_compress=True)
        return os.path.join(tmp, "a.wfbackup")

    def test_login_attempts_admin_log_and_permission_links_round_trip(self):
        from axes.models import AccessAttempt, AccessLog
        from django.contrib.admin.models import ADDITION, LogEntry
        from django.contrib.auth.models import Group, Permission
        from django.contrib.contenttypes.models import ContentType

        user = get_user_model().objects.create_user(username="bk_auth_user", password="Pw123456!")
        group = Group.objects.create(name="bk_group")
        perm_a = Permission.objects.get(codename="add_group")
        perm_b = Permission.objects.get(codename="view_user")
        group.permissions.add(perm_a)
        user.groups.add(group)
        user.user_permissions.add(perm_b)
        AccessAttempt.objects.create(username="bk_auth_user", ip_address="10.1.2.3", user_agent="UA", get_data="", post_data="",
                                     http_accept="", path_info="/accounts/login/", failures_since_start=3)
        AccessLog.objects.create(username="bk_auth_user", ip_address="10.1.2.3", user_agent="UA", http_accept="", path_info="/accounts/login/")
        LogEntry.objects.create(user=user, content_type=ContentType.objects.get_for_model(Group), object_id=str(group.pk),
                                object_repr="bk_group", action_flag=ADDITION, change_message="created")
        perm_count, ct_count = Permission.objects.count(), ContentType.objects.count()
        tmp = tempfile.mkdtemp()
        try:
            path = self._backup(tmp)
            with zipfile.ZipFile(path) as zf:
                names = " ".join(zf.namelist())
            for needle in ("_contenttype.json", "_permission.json", "_group_permissions.json", "_user_groups.json", "_user_user_permissions.json",
                           "_accessattempt.json", "_accesslog.json", "_accessfailurelog.json", "_accessattemptexpiration.json", "_logentry.json"):
                self.assertIn(needle, names)

            AccessAttempt.objects.all().delete()
            AccessLog.objects.all().delete()
            LogEntry.objects.all().delete()
            group.permissions.clear()
            user.groups.clear()
            user.user_permissions.clear()
            call_command("restore_data", path)

            self.assertEqual(AccessAttempt.objects.get(username="bk_auth_user").failures_since_start, 3)
            self.assertEqual(AccessLog.objects.filter(username="bk_auth_user").count(), 1)
            self.assertEqual(LogEntry.objects.get(object_repr="bk_group").content_type, ContentType.objects.get_for_model(Group))
            self.assertEqual(list(group.permissions.all()), [perm_a])
            self.assertEqual(list(user.groups.all()), [group])
            self.assertEqual(list(user.user_permissions.all()), [perm_b])
            self.assertEqual((Permission.objects.count(), ContentType.objects.count()), (perm_count, ct_count))   # nothing duplicated or lost
        finally:
            shutil.rmtree(tmp)

    def test_restore_maps_permissions_by_natural_key_not_by_id(self):
        """The ids of permissions differ between databases: a backup row whose permission_id points at a DIFFERENT
        permission must still resolve to the permission named in its hint, and must never delete another one."""
        from django.contrib.auth.models import Group, Permission

        from core.services.restore.helpers import get_field_map
        from core.services.restore.instance_builder import build_instance_kwargs
        from core.services.restore.natural_restore import natural_restore_row

        wanted = Permission.objects.get(codename="add_group")
        other = Permission.objects.get(codename="view_user")
        group = Group.objects.create(name="bk_nat_group")
        through = Group.permissions.through
        row = {"id": 99999, "group_id": 424242, "permission_id": other.pk,   # wrong ids on purpose
               "__group__group": "bk_nat_group", "__permission__perm": "auth.group.add_group"}
        kwargs = build_instance_kwargs(row, get_field_map(through), through, {})
        self.assertEqual((kwargs["group_id"], kwargs["permission_id"]), (group.pk, wanted.pk))
        self.assertEqual(natural_restore_row(through, kwargs, overwrite=True), "created")
        self.assertEqual(natural_restore_row(through, kwargs, overwrite=True), "skipped")   # idempotent
        self.assertTrue(Permission.objects.filter(pk=other.pk).exists())
        # a permission that no longer exists in this code base is skipped, not an error
        gone = build_instance_kwargs({**row, "__permission__perm": "nope.nothing.add_nothing"}, get_field_map(through), through, {})
        self.assertEqual(natural_restore_row(through, gone, overwrite=True), "skipped")
