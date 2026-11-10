"""The sysadmin's in-app code editing: guarded paths, exact-once edits, confirmation card, the write only on Confirm, local-only."""

import tempfile
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from core.authentication.services import AuthWorkflowService
from ai.models import AISetting
from ai.models.ai_chat_block import AIChatBlock
from ai.services.actions import decide
from ai.services.coding import edit, tools
from ai.services.investigation.defs import CODE_TOOLS, INVESTIGATION_TOOL_DEFS
from ai.services.tools import validate_and_execute_tool

User = get_user_model()


class Base(TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp()).resolve()
        (self.root / "core" / "services" / "balance").mkdir(parents=True)
        (self.root / "app").mkdir()
        (self.root / "app" / "a.py").write_text("x = 1\ny = 2\n", encoding="utf-8")
        patcher = patch.object(edit, "ROOT", self.root)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.admin = User.objects.create_user(username="admin", password="pw12345!")
        profile = AuthWorkflowService.get_profile(self.admin)
        profile.is_sysadmin = True
        profile.save()

    def file(self, rel):
        return (self.root / rel).read_text(encoding="utf-8")


class PathRuleTests(Base):
    def test_unsafe_and_protected_paths_are_refused(self):
        bad = ["../x.py", "/etc/passwd.py", "app/../../x.py", ".env", "db.sqlite3", "core/migrations/0001_x.py", "core/services/balance/a.py",
               ".git/config", "media/a.py", "app/tool.exe", "node_modules/a.js", "app/__pycache__/a.py", "", "a.sqlite3"]
        for path in bad:
            with self.subTest(path=path), self.assertRaises(edit.EditError):
                edit.check_path(path)

    def test_a_normal_file_is_accepted(self):
        self.assertEqual(edit.check_path("app/a.py")[0], "app/a.py")

    def test_the_protected_reason_is_explained(self):
        with self.assertRaisesRegex(edit.EditError, "protected"):
            edit.check_path("core/services/balance/a.py")


class BuildTests(Base):
    def test_edit_needs_the_old_text_exactly_once(self):
        self.assertEqual(edit.build({"path": "app/a.py", "old_str": "y = 2", "new_str": "y = 3"})["op"], "edit")
        for old in ("zzz", "= "):
            with self.assertRaises(edit.EditError):
                edit.build({"path": "app/a.py", "old_str": old, "new_str": "q"})

    def test_invalid_python_and_json_are_rejected_before_any_card(self):
        with self.assertRaisesRegex(edit.EditError, "valid py"):
            edit.build({"path": "app/a.py", "old_str": "y = 2", "new_str": "y ="})
        with self.assertRaisesRegex(edit.EditError, "valid json"):
            edit.build({"path": "app/new.json", "content": "{bad"})

    def test_a_change_that_pushes_a_file_over_the_line_limit_is_refused(self):
        with self.assertRaisesRegex(edit.EditError, "limit"):
            edit.build({"path": "app/big.py", "content": "x = 1\n" * 250})

    def test_new_file_only_when_it_does_not_exist_and_edit_only_when_it_does(self):
        with self.assertRaises(edit.EditError):
            edit.build({"path": "app/a.py", "content": "z = 1\n"})
        with self.assertRaises(edit.EditError):
            edit.build({"path": "app/none.py", "old_str": "a", "new_str": "b"})
        self.assertEqual(edit.build({"path": "app/none.py", "content": "z = 1\n"})["op"], "add")

    def test_nothing_is_written_while_building(self):
        edit.build({"path": "app/a.py", "old_str": "y = 2", "new_str": "y = 3"})
        self.assertEqual(self.file("app/a.py"), "x = 1\ny = 2\n")


class CardFlowTests(Base):
    @override_settings(DEBUG=True)
    def propose(self, **params):
        return tools.propose_edit(self.admin, {"path": "app/a.py", "old_str": "y = 2", "new_str": "y = 3", **params})

    @override_settings(DEBUG=True)
    def test_the_file_changes_only_after_confirm(self):
        card = self.propose()["card_id"]
        self.assertEqual(self.file("app/a.py"), "x = 1\ny = 2\n")
        out, status = decide(self.admin, card, True)
        self.assertEqual((status, out["block"]["status"]), (200, "confirmed"))
        self.assertEqual(self.file("app/a.py"), "x = 1\ny = 3\n")

    @override_settings(DEBUG=True)
    def test_cancel_leaves_the_file_alone(self):
        card = self.propose()["card_id"]
        self.assertEqual(decide(self.admin, card, False)[0]["block"]["status"], "cancelled")
        self.assertEqual(self.file("app/a.py"), "x = 1\ny = 2\n")

    @override_settings(DEBUG=True)
    def test_a_file_changed_after_the_proposal_is_not_overwritten(self):
        card = self.propose()["card_id"]
        (self.root / "app" / "a.py").write_text("x = 9\ny = 2\n", encoding="utf-8")
        out, _ = decide(self.admin, card, True)
        self.assertEqual(out["block"]["status"], "failed")
        self.assertEqual(self.file("app/a.py"), "x = 9\ny = 2\n")

    @override_settings(DEBUG=True)
    def test_crlf_files_keep_their_line_endings_and_new_files_are_added(self):
        (self.root / "app" / "w.py").write_bytes(b"a = 1\r\nb = 2\r\n")
        card = tools.propose_edit(self.admin, {"path": "app/w.py", "old_str": "b = 2", "new_str": "b = 5"})["card_id"]
        decide(self.admin, card, True)
        self.assertEqual((self.root / "app" / "w.py").read_bytes(), b"a = 1\r\nb = 5\r\n")
        card = tools.propose_edit(self.admin, {"path": "app/n.py", "content": "z = 1\n"})["card_id"]
        decide(self.admin, card, True)
        self.assertEqual(self.file("app/n.py"), "z = 1\n")

    @override_settings(DEBUG=True)
    def test_same_proposal_twice_is_one_card(self):
        self.assertEqual(self.propose()["card_id"], self.propose().get("card_id"))
        self.assertEqual(AIChatBlock.objects.count(), 1)

    @override_settings(DEBUG=True)
    def test_a_normal_member_cannot_propose_or_confirm(self):
        member = User.objects.create_user(username="member", password="pw12345!")
        self.assertIn("error", tools.propose_edit(member, {"path": "app/a.py", "old_str": "x", "new_str": "q"}))
        card = self.propose()["card_id"]
        AIChatBlock.objects.filter(pk=card).update(user=member)
        out, _ = decide(member, card, True)
        self.assertEqual(out["block"]["status"], "failed")
        self.assertEqual(self.file("app/a.py"), "x = 1\ny = 2\n")

    @override_settings(DEBUG=False)
    def test_hosted_app_never_changes_code(self):
        self.assertIn("local development", tools.propose_edit(self.admin, {"path": "app/a.py", "old_str": "x", "new_str": "q"})["error"])
        card = AIChatBlock.objects.create(user=self.admin, kind="action", status="pending", payload={
            "record": "code_file", "op": "add", "params": {"path": "app/h.py", "content": "z = 1\n"}, "rows": []}).id
        self.assertEqual(decide(self.admin, card, True)[0]["block"]["status"], "failed")
        self.assertFalse((self.root / "app" / "h.py").exists())

    @override_settings(DEBUG=True)
    def test_protected_file_gets_no_card(self):
        res = tools.propose_edit(self.admin, {"path": "core/services/balance/a.py", "content": "x = 1\n"})
        self.assertIn("protected", res["error"])
        self.assertEqual(AIChatBlock.objects.count(), 0)


class ToolRegistryTests(Base):
    def test_tools_are_sysadmin_only_and_need_the_right_permission_tier(self):
        self.assertTrue({"app_propose_edit", "app_run_checks", "app_git_diff"} <= set(CODE_TOOLS))
        self.assertEqual((INVESTIGATION_TOOL_DEFS["app_propose_edit"]["tier"], INVESTIGATION_TOOL_DEFS["app_run_checks"]["tier"]), ("modify", "execute"))

    @override_settings(DEBUG=True)
    def test_read_only_permission_blocks_the_edit_tool_and_modify_allows_it(self):
        args = {"path": "app/a.py", "old_str": "y = 2", "new_str": "y = 3"}
        audit, _ = validate_and_execute_tool("app_propose_edit", args, self.admin)
        self.assertNotEqual(audit["status"], "success")
        AISetting.set("ai_permission_tier", "modify", user=self.admin)
        audit, result = validate_and_execute_tool("app_propose_edit", args, self.admin)
        self.assertEqual(audit["status"], "success")
        self.assertTrue(result["data"]["pending_confirmation"])

    @override_settings(DEBUG=True)
    def test_run_checks_needs_files_and_reports_the_steps(self):
        self.assertIn("error", tools.run_checks(self.admin, {"files": []}))
        fake = {"overall": "NOT VERIFIED: pyflakes", "steps": [{"step": "pyflakes", "status": "FAILED", "detail": "x" * 900}], "protected_files_changed": [], "files": ["a.py"]}
        with patch("ai.services.coding.verify.verify", return_value=fake) as run:
            out = tools.run_checks(self.admin, {"files": ["a.py"]})
        self.assertEqual((out["overall"], len(out["steps"][0]["detail"]), run.call_args.kwargs["timeout"]), ("NOT VERIFIED: pyflakes", 400, 600))

    @override_settings(DEBUG=False)
    def test_run_checks_is_local_only(self):
        self.assertIn("local development", tools.run_checks(self.admin, {"files": ["a.py"]})["error"])

    def test_git_diff_lists_changes_for_a_sysadmin_only(self):
        member = User.objects.create_user(username="m2", password="pw12345!")
        self.assertIn("error", tools.git_diff(member, {}))
        self.assertIn("output", tools.git_diff(self.admin, {}))
        self.assertIn("error", tools.git_diff(self.admin, {"path": "../etc/passwd"}))
