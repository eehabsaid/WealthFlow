"""Trajectory examples from REAL patch runs (plan -> approve -> execute with the model scripted and only the verification commands faked): which phases become
examples, which are dropped and why, and the review gate that decides what is ever trained on."""

import json
import os
import tempfile
from unittest.mock import patch

from ai.dev_agent.tests.fakes import edit, final, plan, tool
from ai.services.coding.training import ledger_examples as le
from ai.services.coding.training import ledger_review as review
from ai.services.coding.training import ledger_traj as traj
from ai.tests.coding.ledger_helper import REAL_AGENT_DIR
from ai.tests.coding.traj_helper import FAIL, PASS, SUB, TrajRepo

READ = tool("read_file", path="app/calc.py")
ADD_SUB = edit({"path": "app/calc.py", "replacements": [{"old": "    return a + b\n", "new": "    return a + b\n\n\n" + SUB}]})
FIX_SUB = edit({"path": "app/calc.py", "replacements": [{"old": "    return a - b\n", "new": "    return b - a\n"}]})
PLAN = plan(summary="add sub", steps=[{"title": "add sub", "files": ["app/calc.py"]}])
HAPPY = [READ, PLAN, READ, ADD_SUB, final("added sub()")]


class PatchExamplesTests(TrajRepo):
    def labels(self, found):
        return [(e["label"], e["task_kind"]) for e in found["candidates"]]

    def test_a_verified_patch_gives_a_plan_example_and_a_package_example_exactly_as_received(self):
        ledger = self.patch_run("add a sub function", HAPPY)
        self.assertEqual(ledger.data["status"], "completed")
        found = traj.extract()
        self.assertEqual(self.labels(found), [("plan", "patch"), ("package P1", "patch")], dict(found["stats"]))
        planned, package = found["candidates"]
        system, sent = self.provider.calls[1]    # the plan phase's last request
        self.assertEqual(planned["messages"][:-1], [{"role": "system", "content": system}, *sent])
        self.assertEqual(planned["messages"][-1]["content"], PLAN)
        system, sent = self.provider.calls[-1]   # the package phase's last request
        self.assertEqual(package["messages"][:-1], [{"role": "system", "content": system}, *sent])
        self.assertEqual((package["messages"][-1]["content"], package["tools"]), (final("added sub()"), ["read_file", "edit_files"]))
        self.assertIn('"state": "written"', package["messages"][-2]["content"])
        self.assertNotEqual(planned["messages"][0]["content"], package["messages"][0]["content"], "the plan phase and the package phase have different system prompts")

    def test_the_tasks_own_edits_do_not_count_as_the_repo_having_moved_on(self):
        self.patch_run("add a sub function", HAPPY)
        for example in traj.extract()["candidates"]:
            repo = example["checks"]["repo"]
            self.assertEqual((repo["same"] + repo["task_state"], repo["changed"], repo["missing"], repo["created_exists"]), (1, [], [], []), example["label"])
        self.assertIn("def sub", (self.root / "app/calc.py").read_text(encoding="utf-8"))

    def test_someone_else_changing_the_edited_file_afterwards_drops_the_phases(self):
        self.patch_run("add a sub function", HAPPY)
        self.write("app/calc.py", "def add(a, b):\n    return a + b\n\n\ndef sub(a, b):\n    return a - b  # edited by hand\n")
        found = traj.extract()
        self.assertEqual((found["candidates"], found["stats"]["dropped:repo_changed"]), ([], 2))

    def test_a_plan_that_adds_and_deletes_files_still_qualifies_after_the_task_carried_it_out(self):
        self.write("app/old.py", "OLD = 1\n")
        carried_out = plan(summary="swap old for more", files_add=["app/more.py"], files_edit=[], files_delete=["app/old.py"],
                           steps=[{"title": "swap", "files": ["app/more.py", "app/old.py"]}])
        replies = [tool("read_file", path="app/old.py"), carried_out, tool("read_file", path="app/old.py"),
                   edit({"path": "app/more.py", "content": "MORE = 1\n"}), tool("delete_file", path="app/old.py"), final("swapped")]
        self.assertEqual(self.patch_run("replace old with more", replies).data["status"], "completed")
        self.assertTrue((self.root / "app/more.py").exists() and not (self.root / "app/old.py").exists())
        found = traj.extract()
        self.assertEqual(self.labels(found), [("plan", "patch"), ("package P1", "patch")], dict(found["stats"]))
        for example in found["candidates"]:
            self.assertEqual(example["checks"]["repo"]["task_state"], example["checks"]["repo"]["checked"], example["label"])
        self.assertEqual(found["candidates"][1]["checks"]["repo"]["checked"], 2)

    def test_a_task_that_was_never_approved_is_not_an_example(self):
        ledger = self.agent([READ, PLAN]).plan("add a sub function")
        self.assertEqual(ledger.data["status"], "awaiting_approval")
        found = traj.extract()
        self.assertEqual((found["candidates"], found["stats"]["dropped:task_not_finished_well"]), ([], 1))

    def test_a_rejected_plan_is_dropped_and_the_plan_that_replaced_it_is_kept(self):
        replies = [plan(summary=""), READ, PLAN, READ, ADD_SUB, final("added sub()")]
        self.patch_run("add a sub function", replies)
        found = traj.extract()
        self.assertEqual([e["label"] for e in found["candidates"]], ["plan", "package P1"])
        self.assertEqual(found["stats"]["dropped:plan_rejected"], 1)
        self.assertIn("rejected", found["candidates"][0]["messages"][1]["content"])

    def test_a_package_whose_first_check_failed_is_dropped_and_so_is_its_fix_that_continued_the_conversation(self):
        replies = [READ, PLAN, READ, edit({"path": "app/calc.py", "replacements": [{"old": "    return a + b\n", "new": "    return a + b\n\n\ndef sub(a, b):\n    return a - b\n"}]}),
                   final("added sub()"), READ, FIX_SUB, final("fixed sub()")]
        ledger = self.patch_run("add a sub function", replies, checks=(FAIL, PASS))
        self.assertEqual(ledger.data["status"], "completed")
        found = traj.extract()
        # A fix round now continues the package's own conversation, so what was logged is not the whole conversation: it is not an exact example.
        self.assertEqual(self.labels(found), [("plan", "patch")], dict(found["stats"]))
        self.assertEqual((found["stats"]["dropped:package_failed_first_check"], found["stats"]["dropped:phase_not_clean"]), (1, 1))

    def test_a_trajectory_that_wrote_a_protected_file_is_never_an_example(self):
        plan_money = plan(summary="touch money", files_edit=["app/money.py"], steps=[{"title": "edit", "files": ["app/money.py"]}])
        money = tool("read_file", path="app/money.py")
        change = edit({"path": "app/money.py", "replacements": [{"old": "BALANCE = 1", "new": "BALANCE = 2"}]})
        self.patch_run("change the balance", [money, plan_money, money, change, final("changed")], approve=True)
        found = traj.extract()
        self.assertEqual(found["candidates"], [])
        self.assertEqual((found["stats"]["dropped:plan_stale"], found["stats"]["dropped:protected_file"]), (1, 1))


class ReviewGateTests(TrajRepo):
    def setUp(self):
        super().setUp()
        self.patch_run("add a sub function", HAPPY)
        self.ask("how does add work?", [READ, tool("grep", pattern="def add"), final("add returns a + b (app/calc.py)")])
        self.out = tempfile.mkdtemp()

    def decide(self, **by_label):
        rows = review.load_rows("traj")
        for row in rows.values():
            row["decision"] = by_label.get(row["example"]["label"] + "|" + row["example"]["task_kind"], row["decision"])
        review.write_rows("traj", rows)

    def test_refresh_writes_one_pending_row_per_phase_and_keeps_decisions_on_rerun(self):
        result = review.refresh("traj", log=lambda *_: None)
        rows = review.load_rows("traj")
        self.assertEqual(result["decisions"], {"pending": 3})
        self.assertEqual(sorted(k.rsplit("#", 1)[1] for k in rows), ["0", "0", "1"])
        self.assertTrue(all(k.startswith(r["task_id"] + "#") for k, r in rows.items()))
        self.decide(**{"package P1|patch": "approved", "plan|qa": "rejected"})
        review.refresh("traj", log=lambda *_: None)
        self.assertEqual(sorted(r["decision"] for r in review.load_rows("traj").values()), ["approved", "pending", "rejected"])

    def build_approved(self, held_out_task=None):
        review.refresh("traj", log=lambda *_: None)
        self.decide(**{"plan|patch": "approved", "package P1|patch": "approved", "plan|qa": "approved"})
        with patch.object(le, "held_out", lambda task_id, cfg: task_id == held_out_task):
            built = review.build_traj(self.out, log=lambda *_: None)
        held = json.load(open(built["held_out_file"], encoding="utf-8")) if built["held_out"] else []
        trained = [json.loads(line) for line in open(built["train_file"], encoding="utf-8")]
        return built, held, trained

    def patch_id(self):
        return next(r["task_id"] for r in review.load_rows("traj").values() if r["example"]["task_kind"] == "patch")

    def test_nothing_is_built_until_something_is_approved(self):
        review.refresh("traj", log=lambda *_: None)
        built = review.build_traj(self.out, log=lambda *_: None)
        self.assertEqual((built["train"], built["held_out"], built["train_file"]), (0, 0, ""))

    def test_only_approved_trajectories_reach_the_dataset_in_the_trainer_format(self):
        review.refresh("traj", log=lambda *_: None)
        self.decide(**{"package P1|patch": "approved", "plan|qa": "rejected"})
        with patch.object(le, "held_out", lambda task_id, cfg: False):
            built = review.build_traj(self.out, log=lambda *_: None)
        trained = [json.loads(line) for line in open(built["train_file"], encoding="utf-8")]
        self.assertEqual((built["train"], built["held_out"], len(trained)), (1, 0, 1))
        self.assertEqual(set(trained[0]), {"messages"})
        self.assertEqual([m["role"] for m in trained[0]["messages"]][:3], ["system", "user", "assistant"])
        self.assertTrue(trained[0]["messages"][-1]["content"].startswith('{"final"'))
        self.assertTrue(os.path.basename(built["train_file"]).startswith("coding_agent_loop_"))

    def test_a_held_out_task_is_held_out_in_every_phase_and_never_trained_on(self):
        review.refresh("traj", log=lambda *_: None)
        patch_id = self.patch_id()
        built, held, trained = self.build_approved(held_out_task=patch_id)
        self.assertEqual((built["train"], built["held_out"]), (1, 2))
        self.assertEqual({e["task_id"] for e in held}, {patch_id})
        self.assertEqual(sorted(e["label"] for e in held), ["package P1", "plan"])
        self.assertEqual(len(trained), 1)
        self.assertNotIn("add a sub function", json.dumps(trained))

    def test_the_approval_gate_of_the_training_stage_is_untouched(self):
        cfg = json.loads((REAL_AGENT_DIR / "coding_agent_training.json").read_text(encoding="utf-8"))
        self.assertEqual(cfg["min_traces"], 40)
