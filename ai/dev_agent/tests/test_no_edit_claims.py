"""A change request is never DONE on the model's word alone (evaluation 16 Nov 2026: the trained model read the file, said "the docstring was added" and the task
counted as finished with nothing changed). Read-only questions still get a direct answer, without a plan."""

from ai.dev_agent.engine.intent import needs_changes
from ai.dev_agent.engine.loop import Agent
from ai.dev_agent.settings.store import Settings
from ai.dev_agent.tests.fakes import Approver, Scripted, edit, final, plan, tool

DOCSTRING = "Add a one-line module docstring at the top of `app/calc.py` that says what the module is for. Do not change anything else."
QA = "What does `app/calc.py` do? Answer only; do not plan or change anything."
CLAIM = final("I added the one-line module docstring to app/calc.py.")


def agent(repo, replies, yes=False):
    return Agent(repo, Scripted(replies), Settings(repo).load(), Approver(yes), events=True)


def test_the_exact_failed_docstring_task_is_failed_when_the_model_only_claims_it(repo):
    before = (repo.root / "app/calc.py").read_text(encoding="utf-8")
    ledger = agent(repo, [tool("read_file", path="app/calc.py"), CLAIM, CLAIM, CLAIM]).plan(DOCSTRING)
    assert ledger.data["status"] == "stopped" and ledger.data["stop_reason"].startswith("FAILED:") and not ledger.data["plan"]
    assert (repo.root / "app/calc.py").read_text(encoding="utf-8") == before


def test_a_claim_is_answered_with_a_demand_for_a_plan_and_a_real_plan_then_goes_on(repo):
    a = agent(repo, [CLAIM, plan(), edit({"path": "app/calc.py", "old": "", "new": ""}), final("done")])
    ledger = a.plan(DOCSTRING)
    assert ledger.data["status"] == "awaiting_approval" and "never finished by words" in a.provider.calls[1][1][0]["content"]


def test_the_docstring_task_reaches_completed_only_after_plan_approval_edit_and_verification(repo):
    body = "app/calc.py"
    change = {"path": body, "replacements": [{"old": "def add(a, b):", "new": '"""Calculator helpers."""\n\n\ndef add(a, b):'}]}
    a = agent(repo, [plan(), tool("read_file", path=body), edit(change), final("added the docstring")])
    ledger = a.plan(DOCSTRING)
    assert ledger.data["status"] == "awaiting_approval"
    a.approve(ledger.id)
    ledger = a.execute(ledger.id)
    assert ledger.data["status"] == "completed" and (repo.root / body).read_text(encoding="utf-8").startswith('"""Calculator helpers."""')


def test_an_approved_plan_whose_package_changes_nothing_is_not_completed(repo):
    a = agent(repo, [plan(), final("nothing to do, it is already fine")])
    ledger = a.plan(DOCSTRING)
    a.approve(ledger.id)
    ledger = a.execute(ledger.id)
    assert ledger.data["status"] == "stopped" and "no file was changed" in ledger.data["stop_reason"]


def test_a_read_only_question_is_still_answered_directly_without_a_plan(repo):
    ledger = agent(repo, [tool("read_file", path="app/calc.py"), final("calc.py holds the arithmetic helpers.")]).plan(QA)
    assert ledger.data["status"] == "answered" and ledger.data["answer"].startswith("calc.py") and not ledger.data["plan"]


def test_the_wording_of_the_batch_goals_is_told_apart():
    assert needs_changes(DOCSTRING) and not needs_changes(QA)
    assert needs_changes("`x` has no docstring: write a clear one for it.") and needs_changes("Add type hints to the functions in `app/calc.py`.")
    assert not needs_changes("Explain how the index is built.") and not needs_changes("Which files import calc?")
