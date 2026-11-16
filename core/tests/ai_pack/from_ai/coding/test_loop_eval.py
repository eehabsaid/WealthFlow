"""The real-loop evaluation harness: held-out tasks in, a working copy per run, the real agent loop, scoring from its own logs, a verdict, saved transcripts - and
the real command line against a fake Ollama. Only the model is a fake."""

import json
import subprocess
import tempfile
import threading
from pathlib import Path

from ai.dev_agent.ledger.ledger import Ledger
from ai.dev_agent.tests import fake_env
from ai.dev_agent.tests.fakes import final
from ai.services.coding.training import loop_eval, loop_snapshot
from ai.tests.coding.traj_helper import ADD_SUB, PATCH_GOAL, PLAN, QA_GOAL, READ, TrajRepo, scripted_runner
HELD = [
    {"task_id": "b-patch", "task_kind": "patch", "goal": PATCH_GOAL, "answer": "x", "label": "plan"},
    {"task_id": "b-patch", "task_kind": "patch", "goal": PATCH_GOAL, "answer": "y", "label": "package P1"},
    {"task_id": "a-qa", "task_kind": "qa", "goal": QA_GOAL, "answer": "add returns a + b (app/calc.py)", "label": "plan"},
    {"task_id": "c-qa", "task_kind": "qa", "goal": "what does total do?", "answer": "it sums", "label": "plan"},
]
CFG = {"eval_min_gain_points": 10, "eval_max_slower_percent": 10 ** 9, "eval_min_tasks": 2, "eval_task_timeout_s": 120}


class TaskSelectionTests(TrajRepo):
    def test_one_task_per_held_out_task_id_with_both_kinds_alternating_under_a_limit(self):
        tasks = loop_eval.tasks_from_heldout(HELD)
        self.assertEqual([(t["task_id"], t["kind"]) for t in tasks], [("a-qa", "qa"), ("b-patch", "patch"), ("c-qa", "qa")])
        self.assertEqual(tasks[0]["answer"], "add returns a + b (app/calc.py)")
        self.assertEqual(tasks[1]["answer"], "", "a patch task has no recorded answer to compare with")
        self.assertEqual([t["task_id"] for t in loop_eval.tasks_from_heldout(HELD, 2)], ["a-qa", "b-patch"])

    def test_no_held_out_tasks_means_nothing_is_run(self):
        outcome = loop_eval.run(("old", "new"), [], tempfile.mkdtemp(), runner=lambda *a: self.fail("nothing should run"))
        self.assertEqual((outcome["status"], outcome["win"]), ("no_tasks", False))


class SnapshotTests(TrajRepo):
    def test_a_plain_folder_is_copied_without_history_or_notes_and_the_model_is_pinned_alone(self):
        (self.root / "coding_agent/tasks/old").mkdir(parents=True)
        (self.root / "coding_agent/tasks/old/ledger.json").write_text("{}", encoding="utf-8")
        (self.root / "coding_agent/memory").mkdir()
        (self.root / "coding_agent/memory/notes.md").write_text("the answer to a held-out task", encoding="utf-8")
        self.write("coding_agent/agent_settings.json", json.dumps({"provider": "anthropic", "model": "x", "context_window": 20000, "reserve_tokens": 5000}))
        dest = Path(tempfile.mkdtemp()) / "snap"
        info = loop_snapshot.snapshot(self.root, dest)
        self.assertEqual(info["git"], False)
        self.assertTrue((dest / "app/calc.py").is_file() and (dest / "coding_agent/config.json").is_file())
        self.assertFalse((dest / "coding_agent/tasks").exists() or (dest / "coding_agent/memory").exists())
        work = loop_snapshot.fresh_copy(dest, Path(tempfile.mkdtemp()) / "work")
        saved = loop_snapshot.pin_model(work, "qwen3.8:27b-recovery")
        self.assertEqual((saved["provider"], saved["model"], saved["context_window"], saved["reserve_tokens"]), ("ollama", "qwen3.8:27b-recovery", 20000, 5000))
        self.assertEqual(json.loads((self.root / "coding_agent/agent_settings.json").read_text(encoding="utf-8"))["model"], "x", "your own settings are never touched")

    def test_a_git_repo_is_copied_as_it_is_on_disk_now_with_history_so_the_git_tool_works(self):
        repo = Path(tempfile.mkdtemp())

        def git(*args):
            return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args], cwd=repo, check=True, capture_output=True, text=True).stdout

        def put(rel, text):
            (repo / rel).parent.mkdir(parents=True, exist_ok=True)
            (repo / rel).write_text(text, encoding="utf-8")

        git("init", "-q")
        for rel, text in {"a.py": "one\n", "b.py": "two\n", ".gitignore": "ignored.txt\ncoding_agent/tasks/\n", "coding_agent/memory/notes.md": "lessons\n"}.items():
            put(rel, text)
        git("add", "."), git("commit", "-q", "-m", "first")
        put("a.py", "one changed\n")
        put("c.py", "untracked\n")
        put("ignored.txt", "never copied\n")
        put("coding_agent/tasks/x/ledger.json", "{}")
        (repo / "b.py").unlink()
        dest = Path(tempfile.mkdtemp()) / "snap"
        info = loop_snapshot.snapshot(repo, dest)
        self.assertEqual(info["git"], True)
        self.assertEqual((dest / "a.py").read_text(encoding="utf-8"), "one changed\n")
        self.assertTrue((dest / "c.py").is_file())
        self.assertFalse(any((dest / rel).exists() for rel in ("b.py", "ignored.txt", "coding_agent/tasks", "coding_agent/memory")))
        status = subprocess.run(["git", "status", "--porcelain"], cwd=dest, capture_output=True, text=True, check=True).stdout
        self.assertIn(" M a.py", status)
        self.assertIn("?? c.py", status)
        self.assertIn(" D b.py", status)
        self.assertEqual(git("log", "--format=%s").strip(), "first")
        self.assertEqual((repo / "a.py").read_text(encoding="utf-8"), "one changed\n")


class TwoModelsTests(TrajRepo):
    def run_both(self, scripts, calls=None):
        out = tempfile.mkdtemp()
        tasks = loop_eval.tasks_from_heldout([h for h in HELD if h["task_id"] != "c-qa"])
        outcome = loop_eval.run(tuple(scripts), tasks, out, runner=scripted_runner(scripts), log=lambda *_: None, restart=(calls.append if calls is not None else lambda m: None),
                                root=self.root, cfg=CFG)
        return outcome, Path(out)

    def test_the_new_model_that_really_does_the_tasks_beats_the_one_that_does_not(self):
        scripts = {"weak": {QA_GOAL: ["Let me read the file first.", "ok", "ok"], PATCH_GOAL: [READ, final("you could add a sub function")]},
                   "good": {QA_GOAL: [READ, final("add returns a + b (app/calc.py)")], PATCH_GOAL: [READ, PLAN, READ, ADD_SUB, final("added sub()")]}}
        calls = []
        outcome, out = self.run_both(scripts, calls)
        self.assertEqual((outcome["status"], outcome["win"], calls), ("done", True, ["weak", "good"]))
        weak, good = outcome["rows"]["weak"], outcome["rows"]["good"]
        self.assertEqual([r["success"] for r in weak], [False, False])
        self.assertEqual([r["success"] for r in good], [True, True])
        why = {r["kind"]: r["why"] for r in weak}
        self.assertTrue(why["qa"].startswith("stopped: "), why)
        self.assertEqual(why["patch"], "answered in words instead of making a plan")
        self.assertIn("NEW MODEL WINS", (out / "loop_eval_report.txt").read_text(encoding="utf-8"))
        self.assertEqual(json.loads((out / "loop_eval_results.json").read_text(encoding="utf-8"))["verdict"], "NEW MODEL WINS on real agent-loop tasks")
        for model in scripts:
            for task_id in ("a-qa", "b-patch"):
                folder = out / "loop_eval" / model / task_id
                self.assertTrue((folder / "ledger.json").is_file() and (folder / "events.jsonl").is_file() and (folder / "run_output.txt").is_file(), (model, task_id))
        self.assertEqual(len((out / "loop_eval/rows.jsonl").read_text(encoding="utf-8").splitlines()), 4)

    def test_your_repo_and_your_task_history_are_never_touched_and_the_copies_are_removed(self):
        scripts = {"a": {QA_GOAL: [READ, final("add returns a + b (app/calc.py)")], PATCH_GOAL: [READ, PLAN, READ, ADD_SUB, final("added sub()")]}}
        scripts["b"] = scripts["a"]
        before = (self.root / "app/calc.py").read_text(encoding="utf-8")
        _, out = self.run_both(scripts)
        self.assertEqual((self.root / "app/calc.py").read_text(encoding="utf-8"), before, "the patch task edited only its own copy")
        self.assertEqual(Ledger.list_ids(self.project), [])
        self.assertFalse((out / "loop_eval/snapshot").exists() or (out / "loop_eval/work").exists())

    def test_two_equal_models_are_not_a_win(self):
        scripts = {"a": {QA_GOAL: [READ, final("add returns a + b (app/calc.py)")], PATCH_GOAL: [READ, PLAN, READ, ADD_SUB, final("added sub()")]}}
        scripts["b"] = scripts["a"]
        outcome, _ = self.run_both(scripts)
        self.assertEqual(outcome["win"], False)
        self.assertTrue(any("NO WIN: only +0.0 points" in line for line in outcome["text"].splitlines()))


class RealCommandLineTests(TrajRepo):
    def serve(self, script):
        server = fake_env.serve(script)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.shutdown)
        self.write("coding_agent/agent_settings.json", json.dumps({"provider": "ollama", "model": "fake", "providers": {"ollama": {"base_url": f"http://127.0.0.1:{server.server_address[1]}"}}}))
        out = Path(tempfile.mkdtemp())
        loop_snapshot.snapshot(self.root, out / "snap")
        return out

    def test_the_real_command_line_answers_a_question_through_a_fake_ollama(self):
        out = self.serve([READ, final("add returns a + b (app/calc.py)")])
        task = {"task_id": "a-qa", "kind": "qa", "goal": QA_GOAL, "answer": "add returns a + b (app/calc.py)"}
        row = loop_eval.run_task("some-model:latest", task, out / "snap", out, loop_eval.run_cli, 120)
        self.assertEqual((row["success"], row["status"], row["tool_calls"], row["returncode"]), (True, "answered", 1, 0), row)
        self.assertGreater(row["seconds"], 0)
        saved = json.loads((out / "some-model_latest/a-qa/ledger.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["goal"], QA_GOAL)

    def test_a_model_that_never_answers_is_cut_off_at_the_timeout_and_reported(self):
        out = self.serve([{"hang": True}])
        task = {"task_id": "a-qa", "kind": "qa", "goal": QA_GOAL, "answer": ""}
        row = loop_eval.run_task("m", task, out / "snap", out, loop_eval.run_cli, 4)
        self.assertEqual((row["success"], row["timed_out"], row["why"]), (False, True, "timed out"))
        self.assertLess(row["seconds"], 30)
