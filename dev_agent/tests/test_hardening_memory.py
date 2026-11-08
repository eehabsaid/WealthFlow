"""Hardening 4: richer persistent memory (rules kind, remember tool, dedupe, redaction, no guesses, committed only for finished tasks)."""

import pytest

from ..memory import capture, quality, store
from ..memory.recall import pick, render
from ..tools import call


def test_rules_kind_exists_and_old_memory_folders_stay_compatible(repo):
    assert "rules" in store.KINDS and store.entries(repo, "rules") == []
    old = repo.agent_dir / "memory"
    old.mkdir(parents=True, exist_ok=True)
    (old / "lessons.md").write_text("- 2026-01-01: old lesson about calc rounding\n", encoding="utf-8")
    assert store.entries(repo, "lessons") == ["2026-01-01: old lesson about calc rounding"]
    store.add(repo, "rules", "Salary raises apply from the month after the effective date")
    assert "calc" in " ".join(pick(repo, "calc rounding")["lessons"]) and "Confirmed business rules" in render(pick(repo, "salary raises effective date"))


def test_near_duplicates_are_not_stored_twice(repo):
    store.add(repo, "architecture", "Services call models only through the repository layer")
    assert store.add(repo, "architecture", "services call models only through the repository layer.") == "already recorded"
    assert store.add(repo, "architecture", "Services call models only through the repository layer now") == "already recorded"
    assert len(store.entries(repo, "architecture")) == 1


@pytest.mark.parametrize("text", ["the limit is probably 5", "I think the rule is X", "maybe it rounds up", "uses api_key abc", "key sk-abcdefghijklmnop1234", "Zk9aQ3JvbmFiY2RlZmdoaWprbG1ub3A1ZA9"])
def test_guesses_and_secrets_are_refused(repo, text):
    with pytest.raises(store.MemoryRefused):
        store.add(repo, "lessons", text)


def test_personal_data_is_redacted_not_stored(repo):
    row = store.add(repo, "lessons", "Support mail ehab@example.com failed for account 1234 5678 9012 3456 during import")
    assert "example.com" not in row and "3456" not in row and "[email]" in row and "[number]" in row
    assert not quality.refusal("core/services/financial_advisor/cash_flow_forecast_service/forecast_engine_helpers.py")


def test_remember_needs_evidence_read_in_this_phase_and_is_only_staged(repo, ctx):
    args = {"kind": "rules", "text": "Calc add keeps integers", "evidence": ["app/calc.py"]}
    assert "evidence" in call(ctx, "remember", args)["error"]
    call(ctx, "read_file", {"path": "app/calc.py"})
    assert call(ctx, "remember", args)["staged"] is True
    assert call(ctx, "remember", args)["staged"] is False
    assert call(ctx, "remember", {**args, "kind": "tasks"})["error"]
    assert "guess" in call(ctx, "remember", {**args, "text": "probably integers"})["error"]
    assert store.entries(repo, "rules") == [] and len(ctx.ledger.data["memory_notes"]) == 1


def _staged(ctx, status):
    call(ctx, "read_file", {"path": "app/calc.py"})
    call(ctx, "remember", {"kind": "architecture", "text": "calc module holds the add function", "evidence": ["app/calc.py"]})
    ctx.ledger.data["status"] = status
    capture.capture(ctx.ledger)


def test_staged_findings_are_saved_only_for_finished_tasks(repo, ctx):
    _staged(ctx, "stopped")
    assert not any("calc module" in e for e in store.entries(repo, "architecture"))
    _staged(ctx, "answered")
    assert any("calc module holds the add function (evidence: app/calc.py)" in e for e in store.entries(repo, "architecture"))
    _staged(ctx, "completed")
    assert sum("calc module" in e for e in store.entries(repo, "architecture")) == 1   # no duplicate on a repeated capture


def test_failed_then_fixed_checks_become_a_lesson(repo, ctx):
    ctx.ledger.add_verification("round1", [{"step": "pyflakes", "status": "FAILED", "detail": "x"}])
    ctx.ledger.add_verification("final", [{"step": "pyflakes", "status": "PASSED", "detail": ""}])
    ctx.ledger.data["status"] = "completed"
    capture.capture(ctx.ledger)
    assert any("failed first and passed after fixing: pyflakes" in e for e in store.entries(repo, "lessons"))
