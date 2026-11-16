"""The 100-task list: every task is about something that really is in a file no earlier task used; patches only where they can succeed and are harmless; the 3 + 2 mix;
the validator catches every way a list can go stale. Run on a small project with known gaps (traj_helper.TASK_FILES) - nothing is guessed."""

import ast
import json
from unittest.mock import patch

from ai.services.coding.training import traj_pool as pool
from ai.services.coding.training import traj_tasks
from ai.tests.coding.traj_helper import SMALL, TaskRepo

EXCLUDED_FROM_PATCHES = {"app/salary_report.py": "money code", "other/unmapped.py": "no test area", "app/huge.py": "too long to patch", "app/money.py": "protected",
                         "app/tests/test_x.py": "a test file"}


class TaskListTests(TaskRepo):
    def build(self, quotas=SMALL, **kw):
        with patch.object(traj_tasks, "QUOTAS", quotas):
            return traj_tasks.build(self.project, **kw)

    def test_the_mix_is_three_questions_and_two_patches_with_real_symbols_and_lines(self):
        tasks = self.build()
        self.assertEqual([t["kind"] for t in tasks], ["qa", "qa", "patch", "qa", "patch"])
        self.assertEqual([t["id"] for t in tasks], ["T001", "T002", "T003", "T004", "T005"])
        for t in tasks:
            self.assertIn(t["file"], t["goal"])
            if t["symbol"]:
                self.assertIn(f"`{t['symbol']}`", t["goal"])
                node = next(n for n in ast.walk(ast.parse((self.root / t["file"]).read_text(encoding="utf-8"))) if getattr(n, "name", None) == t["symbol"])
                self.assertEqual(node.lineno, t["line"], t)
            self.assertEqual(t["kind"] == "qa", t["goal"].endswith(traj_tasks.QA_SUFFIX))
        with patch.object(traj_tasks, "QUOTAS", SMALL):
            self.assertEqual(traj_tasks.validate(self.project, tasks), [])

    def test_patches_never_touch_money_unmapped_protected_too_long_or_test_files_but_questions_may_read_them(self):
        patches = {"hints": 9, "docstring": 9, "module_doc": 9, "class_doc": 9, "bare_except": 9}
        tasks = self.build({"qa": {"module": 20}, "patch": patches})
        chosen = {kind: {t["file"] for t in tasks if t["kind"] == kind} for kind in ("qa", "patch")}
        self.assertEqual(chosen["patch"], {"app/calc.py", "app/util.py", "app/models.py", "app/flow.py", "app/extra.py", "app/views.py"})
        self.assertFalse(chosen["patch"] & set(EXCLUDED_FROM_PATCHES))
        self.assertTrue({"app/salary_report.py", "other/unmapped.py", "app/huge.py"} <= chosen["qa"], "reading money code or a long file changes nothing")
        self.assertFalse(chosen["qa"] & {"app/money.py", "app/tests/test_x.py"})
        self.assertEqual(len([t for t in tasks if t["kind"] == "patch"]), 6, "one task per file, no file twice")

    def test_a_file_an_earlier_task_used_is_left_out_unless_that_folder_is_ignored(self):
        old = self.qa_task("Where is add used? See app/calc.py", "It is called from app/views.py.")
        files = pool.tracked(self.root)
        self.assertEqual(pool.used_files(self.project, files), {"app/calc.py", "app/views.py"})
        self.assertEqual(pool.used_files(self.project, files, ignore={old.id}), set())
        self.write("coding_agent/patch_review.jsonl", json.dumps({"example": {"goal": "tidy app/flow.py", "answer": "", "files": ["app/flow.py"]}}) + "\n")
        self.assertIn("app/flow.py", pool.used_files(self.project, files, ignore={old.id}))
        tasks = self.build({"qa": {"module": 20}, "patch": {"docstring": 9}})
        self.assertFalse({t["file"] for t in tasks} & {"app/calc.py", "app/views.py", "app/flow.py"})

    def test_the_same_seed_gives_the_same_list_and_another_seed_another_order(self):
        quotas = {"qa": {"module": 3, "what_does": 3, "callers": 1, "imports": 1}, "patch": {"docstring": 2, "hints": 3}}
        self.assertEqual(self.build(quotas), self.build(quotas))
        self.assertNotEqual([t["file"] for t in self.build(quotas)], [t["file"] for t in self.build(quotas, seed=7)])

    def test_a_scarce_template_is_topped_up_and_an_impossible_list_is_reported(self):
        tasks = self.build({"qa": {"module": 3}, "patch": {"bare_except": 2}})
        patches = [t for t in tasks if t["kind"] == "patch"]
        self.assertEqual(sorted(t["template"] for t in patches).count("bare_except"), 1, "only one file has a bare except")
        self.assertEqual(len(patches), 2, "the shortage is made up with another kind of patch")
        short = self.build({"qa": {"module": 3}, "patch": {"docstring": 9}})
        self.assertIn("patch: 6 tasks, expected 9", traj_tasks.list_problems(short, {"qa": {"module": 3}, "patch": {"docstring": 9}}), "six files can be patched, nine were asked for")

    def test_the_javascript_facts_and_questions_come_from_the_code(self):
        facts = pool.facts(self.root, "static/js/widget.js")
        self.assertEqual([(f["name"], f["line"], f["body_lines"]) for f in facts["functions"]], [("paintWidget", 1, 4), ("other", 7, 5)])
        tasks = self.build({"qa": {"js_what_does": 1, "js_callers": 1}, "patch": {}})
        self.assertEqual(sorted(t["template"] for t in tasks), ["js_callers", "js_what_does"])
        by = {t["template"]: t for t in tasks}
        self.assertEqual((by["js_callers"]["file"], by["js_callers"]["symbol"], by["js_callers"]["why"]), ("static/js/widget.js", "paintWidget", "used in 1 other files"))
        self.assertEqual((by["js_what_does"]["file"], by["js_what_does"]["symbol"], by["js_what_does"]["line"]), ("static/js/second.js", "listItems", 1))


class ValidateTests(TaskRepo):
    def setUp(self):
        super().setUp()
        with patch.object(traj_tasks, "QUOTAS", SMALL):
            self.tasks = traj_tasks.build(self.project)

    def problems(self, tasks):
        return traj_tasks.task_problems(self.project, tasks)

    def change(self, kind, **changes):
        task = next(t for t in self.tasks if t["kind"] == kind)
        return task, [{**t, **changes} if t is task else t for t in self.tasks]

    def test_a_good_list_has_no_problems(self):
        self.assertEqual(self.problems(self.tasks), {})

    def test_a_line_that_moved_or_a_removed_file_is_caught(self):
        task, moved = self.change("patch", line=999)
        self.assertIn("does not fit", self.problems(moved)[task["id"]])
        (self.root / task["file"]).unlink()
        self.assertIn("not a tracked file", self.problems(self.tasks)[task["id"]])

    def test_a_file_used_in_the_meantime_money_code_protected_files_and_unmapped_files_are_caught(self):
        task = next(t for t in self.tasks if t["kind"] == "patch")
        self.qa_task(f"I looked at {task['file']}", "")
        self.assertIn("already used", self.problems(self.tasks)[task["id"]])
        for rel, symbol, expected in (("app/salary_report.py", "summary", "does not fit"), ("app/money.py", "", "protected"), ("other/unmapped.py", "helper", "does not fit")):
            _, changed = self.change("patch", file=rel, symbol=symbol, line=1)
            self.assertIn(expected, [v for k, v in self.problems(changed).items() if k != task["id"] or rel][0], rel)

    def test_a_goal_that_does_not_name_the_file_or_an_open_question_is_caught(self):
        task, wrong = self.change("patch", goal="Please improve things.")
        self.assertIn("does not name the file", self.problems(wrong)[task["id"]])
        task, open_question = self.change("qa", goal=next(t for t in self.tasks if t["kind"] == "qa")["goal"].replace(traj_tasks.QA_SUFFIX, ""))
        self.assertIn("answer-only", self.problems(open_question)[task["id"]])
        task, unknown = self.change("qa", template="invented")
        self.assertIn("unknown kind", self.problems(unknown)[task["id"]])

    def test_the_list_itself_must_have_the_right_counts_mix_and_no_repeats(self):
        quotas = SMALL
        self.assertEqual(traj_tasks.list_problems(self.tasks, quotas), [])
        swapped = [self.tasks[2], self.tasks[1], self.tasks[0], *self.tasks[3:]]
        self.assertTrue(any("does not mix" in p for p in traj_tasks.list_problems(swapped, quotas)))
        self.assertIn("qa: 2 tasks, expected 3", traj_tasks.list_problems(self.tasks[1:], quotas)[0])
        twice = [self.tasks[0], {**self.tasks[1], "goal": self.tasks[0]["goal"]}, *self.tasks[2:]]
        self.assertTrue(any(p.startswith("goal used twice") for p in traj_tasks.list_problems(twice, quotas)))
