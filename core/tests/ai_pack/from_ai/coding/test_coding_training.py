"""Phase 3 of the coding agent: verified dataset built from git history.
A throw-away git repository is built for every test; no real model, no GPU, no Django test run inside it."""

import json
import tempfile
from unittest.mock import patch

from ai.services.coding.training import dataset, history, settings

from ai.tests.coding.repo_helper import Repo


class CandidateTests(Repo):
    def test_a_small_change_with_a_django_test_becomes_an_example(self):
        ex = self.example()
        self.assertEqual((ex["files"], ex["tests"]), (["core/app.py"], ["core.tests.test_app"]))
        self.assertEqual([m["role"] for m in ex["messages"]], ["system", "user", "assistant"])
        self.assertIn("+y = 2", ex["messages"][2]["content"])
        self.assertIn("x = 1", ex["messages"][1]["content"])   # the file as it was BEFORE the change

    def drop_reason(self, files, subject="c"):
        sha = self.change(subject, files)
        return dataset.candidate(next(c for c in history.commits() if c["sha"] == sha), settings())

    def test_unusable_changes_are_dropped_with_a_reason(self):
        self.assertEqual(self.drop_reason({"core/app.py": "x = 5\n"})[1], "no_django_test")
        self.assertEqual(self.drop_reason({"core/tests/test_app.py": "# t3\n"})[1], "no_source_change")
        self.assertEqual(self.drop_reason({"core/services/balance/b.py": "b = 1\n", "core/tests/test_app.py": "# t4\n"})[1], "protected_file")
        many = {f"core/m{i}.py": "a = 1\n" for i in range(8)} | {"core/tests/test_app.py": "# t5\n"}
        self.assertEqual(self.drop_reason(many)[1], "too_many_files")
        self.assertEqual(dataset.candidate(history.commits()[0], settings())[1], "no_parent")

    def test_data_files_in_the_same_commit_never_enter_an_example(self):
        self.write("db.sqlite3", "binary")
        self.write(".env", "SECRET_KEY='abcdefghijklmnopqrstuvwxyz123456'\n")
        ex = self.example()
        self.assertEqual(ex["files"], ["core/app.py"])
        self.assertNotIn("SECRET", json.dumps(ex["messages"]))

    def test_secrets_inside_a_diff_are_masked(self):
        sha = self.change("add key", {"core/app.py": 'x = 1\npassword = "hunter2hunter2"\n', "core/tests/test_app.py": "# t6\n"})
        ex = dataset.candidate(next(c for c in history.commits() if c["sha"] == sha), settings())[0]
        self.assertNotIn("hunter2hunter2", ex["diff"])

    def test_is_test_recognises_any_ai_app_tests_folder_via_the_wildcard_prefix(self):
        cfg = settings()
        for path in ("ai/tests/test_x.py", "ai/dev_agent/tests/test_y.py", "ai/doc_engine/tests/test_z.py", "core/tests/test_app.py", "tests/modules/x.py"):
            self.assertTrue(dataset.is_test(path, cfg), path)
        for path in ("ai/services/coding/training/dataset.py", "ai/training/trainer/train.py"):
            self.assertFalse(dataset.is_test(path, cfg), path)

    def test_the_held_out_split_is_deterministic_and_roughly_one_in_n(self):
        cfg = settings()
        shas = [f"{n:08x}" + "0" * 32 for n in range(1000)]
        picked = [s for s in shas if dataset.held_out(s, cfg)]
        self.assertEqual(picked, [s for s in shas if dataset.held_out(s, cfg)])
        self.assertEqual(len(picked), 1000 // cfg["held_out_every"])


class BuildTests(Repo):
    def test_only_changes_whose_tests_pass_are_kept_and_split(self):
        for n in range(3):
            self.change(f"change {n}", {"core/app.py": f"x = {n + 10}\n", "core/tests/test_app.py": f"# n{n}\n"})
        outcomes = iter([True, False, True])
        with patch.object(dataset, "held_out", side_effect=lambda sha, cfg: False):
            result = dataset.build(runner=lambda sha, labels, timeout: next(outcomes), log=lambda _: None)
        stats = result["stats"]
        self.assertEqual((stats["candidates"], stats["verified"], stats["dropped:tests_do_not_pass"]), (3, 2, 1))
        self.assertEqual((len(result["train"]), len(result["held_out"])), (2, 0))

    def test_without_verification_nothing_is_exported_for_training(self):
        self.change("c", {"core/app.py": "x = 7\n", "core/tests/test_app.py": "# z\n"})
        result = dataset.build(verify=False, log=lambda _: None)
        self.assertEqual((result["stats"]["candidates"], len(result["train"])), (1, 0))

    def test_files_are_written_for_the_trainer(self):
        self.change("c", {"core/app.py": "x = 8\n", "core/tests/test_app.py": "# y\n"})
        with patch.object(dataset, "held_out", side_effect=lambda sha, cfg: False):
            result = dataset.build(runner=lambda *a: True, log=lambda _: None)
        out = dataset.write(result, tempfile.mkdtemp())
        first = json.loads(open(out["train_file"], encoding="utf-8").readline())
        self.assertEqual([m["role"] for m in first["messages"]], ["system", "user", "assistant"])
        self.assertEqual(out["train"], 1)
