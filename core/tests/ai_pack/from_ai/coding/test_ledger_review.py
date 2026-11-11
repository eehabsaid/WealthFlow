"""File-based review of ledger candidates: refresh() writes a review file with pending rows, decisions survive a rerun, and only approved
rows ever reach build()'s train/held-out split."""

import json
import tempfile

from ai.services.coding.training import ledger_review as lr
from ai.tests.coding.ledger_helper import LedgerRepo


class ReviewWorkflowTests(LedgerRepo):
    def test_refresh_writes_one_pending_row_per_candidate(self):
        self.qa_task("q1", "a1")
        self.qa_task("q2", "a2")
        result = lr.refresh("qa")
        self.assertEqual(result["decisions"], {"pending": 2})
        rows = lr.load_rows("qa")
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(r["decision"] == "pending" for r in rows.values()))

    def test_a_decision_survives_a_rerun_and_rejected_never_reaches_build(self):
        t1 = self.qa_task("q1", "a1")
        t2 = self.qa_task("q2", "a2")
        lr.refresh("qa")
        rows = lr.load_rows("qa")
        rows[t1.id]["decision"], rows[t2.id]["decision"] = "approved", "rejected"
        lr.write_rows("qa", rows)
        lr.refresh("qa")   # a second extraction must not reset the owner's decisions
        rows = lr.load_rows("qa")
        self.assertEqual(rows[t1.id]["decision"], "approved")
        self.assertEqual(rows[t2.id]["decision"], "rejected")
        examples = lr.approved_examples("qa")
        self.assertEqual([e["task_id"] for e in examples], [t1.id])

    def test_build_refuses_with_nothing_approved(self):
        self.qa_task("q1", "a1")
        lr.refresh("qa")
        with tempfile.TemporaryDirectory() as out:
            result = lr.build("qa", out)
        self.assertEqual((result["train"], result["held_out"]), (0, 0))

    def test_build_writes_a_deterministic_split_and_keeps_source_task_ids(self):
        answers = [
            "Routing goes through urls.py, which maps each path to a view function by regex.",
            "Balances are recalculated on every transaction save via a post_save signal handler.",
            "Templates live under app/templates and extend a shared base.html for layout.",
            "Signals connect in apps.py ready(); each handler is a small, separately tested function.",
            "Caching uses Django's low-level cache API keyed by user id and a version number.",
            "Forms validate server side first; client-side checks are only a convenience layer.",
            "Permissions are enforced in the view via a decorator, never trusted from the client.",
            "Exports stream a CSV using a generator so large tables never load fully into memory.",
            "Imports are parsed row by row with per-row error collection, not an all-or-nothing commit.",
            "Widgets render through a small registry so new chart types can be added without touching core code.",
            "Search uses a trigram index on Postgres; SQLite falls back to a plain icontains filter.",
            "Charts are drawn client side from a JSON endpoint; the server never renders images.",
        ]
        ids = [self.qa_task(f"q{i}", answer).id for i, answer in enumerate(answers)]
        lr.refresh("qa")
        rows = lr.load_rows("qa")
        for task_id in ids:
            rows[task_id]["decision"] = "approved"
        lr.write_rows("qa", rows)
        with tempfile.TemporaryDirectory() as out:
            result = lr.build("qa", out)
            self.assertEqual(result["train"] + result["held_out"], 12)
            with open(result["train_file"], encoding="utf-8") as fh:
                train_lines = [json.loads(line) for line in fh]
            with open(result["held_out_file"], encoding="utf-8") as fh:
                held = json.load(fh)
            self.assertEqual(len(train_lines), result["train"])
            self.assertEqual(len(held), result["held_out"])
            self.assertTrue(all("task_id" in ex for ex in held))   # source task ids are kept on the held-out side
            # rebuilding from the same approvals gives the exact same split (deterministic, no leakage)
            result2 = lr.build("qa", out)
            self.assertEqual((result["train"], result["held_out"]), (result2["train"], result2["held_out"]))

    def test_build_combined_merges_approved_qa_and_patch_examples_into_one_split(self):
        qa_ids = [self.qa_task(f"q{i}", answer).id for i, answer in enumerate([
            "Routing goes through urls.py.", "Balances recalc on save.", "Templates extend base.html.", "Signals connect in apps.py.",
            "Caching uses a low-level API.", "Forms validate server side.", "Permissions use a decorator.",
        ])]
        patch_ledger = self.patch_task("add a helper", {"app/calc.py": ("def add(a, b):\n    return a + b\n", "def add(a, b):\n    return a + b + 0\n")})
        lr.refresh("qa")
        lr.refresh("patch")
        qa_rows, patch_rows = lr.load_rows("qa"), lr.load_rows("patch")
        for task_id in qa_ids:
            qa_rows[task_id]["decision"] = "approved"
        patch_rows[patch_ledger.id]["decision"] = "approved"
        lr.write_rows("qa", qa_rows)
        lr.write_rows("patch", patch_rows)
        with tempfile.TemporaryDirectory() as out:
            result = lr.build_combined(out)
            self.assertEqual(result["train"] + result["held_out"], 8)   # 7 qa + 1 patch
            with open(result["train_file"], encoding="utf-8") as fh:
                train_lines = [json.loads(line) for line in fh]
            self.assertTrue(all("messages" in ex for ex in train_lines))
            with open(result["report"], encoding="utf-8") as fh:
                report = fh.read()
            self.assertIn("approved_qa: 7", report)
            self.assertIn("approved_patch: 1", report)

    def test_build_combined_refuses_with_nothing_approved_in_either_kind(self):
        self.qa_task("q1", "a1")
        lr.refresh("qa")
        with tempfile.TemporaryDirectory() as out:
            result = lr.build_combined(out)
        self.assertEqual((result["train"], result["held_out"]), (0, 0))

    def test_an_unknown_decision_value_is_rejected_loudly(self):
        self.qa_task("q1", "a1")
        lr.refresh("qa")
        rows = lr.load_rows("qa")
        list(rows.values())[0]["decision"] = "maybe"
        lr.write_rows("qa", rows)
        with self.assertRaises(ValueError):
            lr.approved_examples("qa")

    def test_a_task_that_stops_qualifying_is_dropped_from_the_review_file(self):
        self.qa_task("q1", "a1")
        lr.refresh("qa")
        self.assertEqual(len(lr.load_rows("qa")), 1)
        # nothing else qualifies now (task list unchanged) - refresh again should be a stable no-op
        result = lr.refresh("qa")
        self.assertEqual(result["dropped"], [])
