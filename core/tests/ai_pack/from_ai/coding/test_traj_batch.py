"""The real-task batch: each task runs in its own throw-away copy with the model pinned, the finished task folder comes back to coding_agent/tasks, your own files
never change, progress survives Ctrl+C and a second run, and the list is re-made only before the first task. Only the model is a fake: a real Agent is driven by a
script, like `python -m ai.dev_agent run` would."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from ai.dev_agent.ledger.ledger import Ledger
from ai.dev_agent.tests.fakes import final
from ai.services.coding.training import traj_batch, traj_tasks
from ai.tests.coding.traj_helper import ADD_SUB, PATCH_GOAL, PLAN, QA_GOAL, READ, SMALL, TaskRepo, TrajRepo, scripted_runner

MODEL = "qwen-test:recovery"
QA = {"id": "T001", "kind": "qa", "template": "what_does", "goal": QA_GOAL, "file": "app/calc.py", "symbol": "add", "line": 1, "why": ""}
PATCH = {"id": "T002", "kind": "patch", "template": "hints", "goal": PATCH_GOAL, "file": "app/calc.py", "symbol": "add", "line": 1, "why": ""}
SCRIPTS = {MODEL: {QA_GOAL: [READ, final("add returns a + b (app/calc.py)")], PATCH_GOAL: [READ, PLAN, READ, ADD_SUB, final("added sub()")]}}
STUCK = {"returncode": -1, "timed_out": True, "seconds": 3.0, "tail": "the model never answered"}


class BatchRunTests(TrajRepo):
    def setUp(self):
        super().setUp()
        self.work, self.lines, self.calls, self.copies = Path(tempfile.mkdtemp()), [], [], []

    def run_batch(self, tasks=(QA, PATCH), runner=None, **kw):
        real = runner or scripted_runner(SCRIPTS)

        def counted(root, goal, timeout):
            self.calls.append(goal)
            self.copies.append(sorted(p.name for p in (self.work / "copies").iterdir()))
            return real(root, goal, timeout)

        return traj_batch.run(list(tasks), self.root, self.work, MODEL, runner=counted, log=self.lines.append, **kw)

    def test_each_task_runs_in_its_own_copy_and_its_task_folder_comes_back_while_your_files_never_change(self):
        before = (self.root / "app/calc.py").read_text(encoding="utf-8")
        outcome = self.run_batch()
        self.assertEqual((outcome["status"], outcome["ran"], outcome["done"], outcome["failed"]), ("done", 2, 2, 0), outcome["text"])
        self.assertIn("Next: python scripts/ledger_train.py --mode loop --stages extract", outcome["text"])
        self.assertEqual((self.root / "app/calc.py").read_text(encoding="utf-8"), before, "the patch task edited only its own copy")
        folders = {Ledger.load(self.project, i).data["goal"]: i for i in Ledger.list_ids(self.project)}
        self.assertEqual(sorted(folders), sorted([QA_GOAL, PATCH_GOAL]))
        for name in ("ledger.json", "events.jsonl", "report.md"):
            self.assertTrue((self.root / "coding_agent/tasks" / folders[QA_GOAL] / name).is_file(), name)
        done = traj_batch.load_done(self.work)
        self.assertEqual({k: (v["folder"], v["success"]) for k, v in done.items()}, {"T001": (folders[QA_GOAL], True), "T002": (folders[PATCH_GOAL], True)})
        self.assertFalse((self.work / "copies").exists() or (self.work / "snapshot").exists(), "the copies are removed")
        self.assertEqual(self.copies, [["T001"], ["T002"]], "each task had its own copy and the one before was already gone")
        self.assertTrue((self.work / "logs/T001.txt").is_file())

    def test_a_second_run_continues_with_what_is_left_and_redo_runs_a_task_again(self):
        self.run_batch(count=1)
        self.assertEqual(self.calls, [QA_GOAL])
        outcome = self.run_batch()
        self.assertEqual((self.calls, outcome["ran"]), ([QA_GOAL, PATCH_GOAL], 1))
        self.assertIn("All together 2 of 2 tasks of the list have run", outcome["text"])
        self.assertEqual(self.run_batch()["status"], "nothing_to_do")
        self.assertEqual(len(self.calls), 2)
        self.run_batch(only={"T001"}, redo=True)
        self.assertEqual(self.calls[2:], [QA_GOAL])
        self.run_batch(start=2, redo=True)
        self.assertEqual(self.calls[3:], [PATCH_GOAL])

    def test_ctrl_c_ends_the_batch_cleanly_and_the_unfinished_task_is_not_counted(self):
        real = scripted_runner(SCRIPTS)

        def interrupted(root, goal, timeout):
            if goal == PATCH_GOAL:
                raise KeyboardInterrupt
            return real(root, goal, timeout)

        outcome = self.run_batch(runner=interrupted)
        self.assertEqual((outcome["status"], outcome["ran"]), ("stopped", 1))
        self.assertIn("Run the same command again to continue", outcome["text"])
        self.assertEqual(sorted(traj_batch.load_done(self.work)), ["T001"])
        self.assertFalse((self.work / "copies").exists() or (self.work / "snapshot").exists())

    def test_a_task_that_never_finishes_is_recorded_as_failed_and_not_repeated(self):
        outcome = self.run_batch(runner=lambda root, goal, timeout: STUCK, tasks=(QA,))
        self.assertEqual((outcome["done"], outcome["failed"]), (0, 1))
        entry = traj_batch.load_done(self.work)["T001"]
        self.assertEqual((entry["folder"], entry["success"], entry["why"]), ("", False, "timed out"))
        self.assertIn("never answered", (self.work / "logs/T001.txt").read_text(encoding="utf-8"))
        self.assertEqual(traj_batch.pick([QA], traj_batch.load_done(self.work)), [])
        self.assertEqual(Ledger.list_ids(self.project), [])

    def test_a_task_with_a_new_goal_under_an_old_id_is_a_new_task(self):
        self.run_batch(tasks=(QA,))
        remade = {**QA, "goal": "a different question about app/calc.py"}
        self.assertEqual([t["id"] for t in traj_batch.pick([remade], traj_batch.load_done(self.work))], ["T001"])

    def test_progress_is_saved_atomically_and_a_broken_progress_file_means_nothing_done(self):
        traj_batch.save_done(self.work, {"T001": {"goal": "g"}})
        self.assertEqual(traj_batch.load_done(self.work), {"T001": {"goal": "g"}})
        self.assertFalse(list(self.work.glob("*.tmp")))
        (self.work / traj_batch.DONE_NAME).write_text("{not json", encoding="utf-8")
        self.assertEqual(traj_batch.load_done(self.work), {})


class PrepareTests(TaskRepo):
    def setUp(self):
        super().setUp()
        self.work, self.path, self.lines = Path(tempfile.mkdtemp()), Path(tempfile.mkdtemp()) / "tasks.json", []
        patcher = patch.object(traj_tasks, "QUOTAS", SMALL)
        patcher.start()
        self.addCleanup(patcher.stop)

    def prepare(self):
        return traj_batch.prepare(self.project, self.path, self.work, self.lines.append)

    def test_a_missing_list_is_made_and_a_valid_one_is_kept_as_it_is(self):
        tasks = self.prepare()
        self.assertEqual(len(tasks), 5)
        self.assertEqual(json.loads(self.path.read_text(encoding="utf-8")), tasks)
        self.assertIn("Made a new task list", self.lines[0])
        self.lines.clear()
        self.assertEqual(self.prepare(), tasks)
        self.assertEqual(self.lines, [])

    def test_a_list_with_a_file_your_earlier_tasks_used_is_made_again_before_the_first_task(self):
        tasks = self.prepare()
        self.qa_task(f"an old question about {tasks[0]['file']}", "")
        remade = self.prepare()
        self.assertNotIn(tasks[0]["file"], {t["file"] for t in remade})
        self.assertEqual(len(remade), 5)

    def test_once_the_batch_is_under_way_its_list_is_kept_and_only_the_stale_tasks_are_skipped(self):
        tasks = self.prepare()
        traj_batch.save_done(self.work, {tasks[0]["id"]: {"goal": tasks[0]["goal"], "folder": ""}})
        stale = tasks[1]
        (self.root / stale["file"]).unlink()
        kept = self.prepare()
        self.assertEqual([t["id"] for t in kept], [t["id"] for t in tasks if t["id"] != stale["id"]])
        self.assertTrue(any(f"Skipping {stale['id']}" in line for line in self.lines))
        self.assertEqual(json.loads(self.path.read_text(encoding="utf-8")), tasks, "the list file is not rewritten")

    def test_a_task_the_batch_itself_finished_does_not_make_its_own_list_stale(self):
        tasks = self.prepare()
        ledger = self.qa_task(tasks[0]["goal"], f"an answer about {tasks[0]['file']} that also mentions {tasks[1]['file']}")
        traj_batch.save_done(self.work, {tasks[0]["id"]: {"goal": tasks[0]["goal"], "folder": ledger.id}})
        self.assertEqual(self.prepare(), tasks, "the later task is not 'used by an earlier task' just because the batch's own answer named its file")

    def test_a_repo_that_cannot_fill_the_list_says_so_instead_of_running_a_short_list(self):
        for rel in [r for r in self.project.root.rglob("*.py") if "app" in r.parts]:
            rel.unlink()
        with self.assertRaises(ValueError) as caught:
            self.prepare()
        self.assertIn("valid task list cannot be made", str(caught.exception))
