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
    a = agent(repo, [plan(), final("nothing to do, it is already fine")] + [final("still fine")] * 3)
    ledger = a.plan(DOCSTRING)
    a.approve(ledger.id)
    ledger = a.execute(ledger.id)
    assert ledger.data["status"] == "stopped" and "without changing any file" in ledger.data["stop_reason"]   # the answer was refused three times


def test_a_read_only_question_is_still_answered_directly_without_a_plan(repo):
    ledger = agent(repo, [tool("read_file", path="app/calc.py"), final("calc.py holds the arithmetic helpers.")]).plan(QA)
    assert ledger.data["status"] == "answered" and ledger.data["answer"].startswith("calc.py") and not ledger.data["plan"]


def test_the_wording_of_the_batch_goals_is_told_apart():
    assert needs_changes(DOCSTRING) and not needs_changes(QA)
    assert needs_changes("`x` has no docstring: write a clear one for it.") and needs_changes("Add type hints to the functions in `app/calc.py`.")
    assert not needs_changes("Explain how the index is built.") and not needs_changes("Which files import calc?")


def test_no_change_needed_is_accepted_only_when_the_quoted_text_is_really_in_the_file(repo):
    real = final("NO CHANGE NEEDED: calc already works | EVIDENCE: app/calc.py: def add(a, b):")
    ledger = agent(repo, [real]).plan(DOCSTRING)
    assert ledger.data["status"] == "answered" and not ledger.data["plan"]
    fake = final('NO CHANGE NEEDED: it has one | EVIDENCE: app/calc.py: """Calculator helpers."""')
    assert agent(repo, [fake, fake, fake]).plan(DOCSTRING).data["status"] == "stopped"
    outside = final("NO CHANGE NEEDED: x | EVIDENCE: ../secret.txt: whatever text here")
    assert agent(repo, [outside, outside, outside]).plan(DOCSTRING).data["status"] == "stopped"


def test_unusual_wording_is_caught_by_what_the_model_claims_and_by_more_verbs(repo):
    for goal in ("app/calc.py needs a module docstring.", "Read app/calc.py and then introduce a docstring.", "`add` should have type hints.", "Tidy up app/util.py."):
        assert needs_changes(goal), goal
    vague = "Look at app/calc.py and improve its first line."   # not a question, and no marker
    ledger = agent(repo, [CLAIM, CLAIM, CLAIM]).plan(vague)
    assert ledger.data["status"] == "stopped" and ledger.data["stop_reason"].startswith("FAILED:")
    odd = "Have a look at app/calc.py for me."   # unclear wording: a plain answer is fine, but "I added ..." is never accepted
    assert agent(repo, [final("it holds add().")]).plan(odd).data["status"] == "answered"
    assert agent(repo, [CLAIM, CLAIM, CLAIM]).plan(odd).data["status"] == "stopped"


QA_FAILED = "What parameters does `build_instance_kwargs` in `core/services/restore/instance_builder.py` take, what does it return, and what happens on bad input? Answer only; do not plan or change anything."
PROMISE = final("I'll read the file to answer.")   # what the trained model answered in the 16 Nov evaluation, with 0 tool calls


def test_a_promise_to_read_is_not_an_answer_the_model_is_sent_back_to_read(repo):
    a = agent(repo, [PROMISE, tool("read_file", path="app/calc.py"), final("add(a, b) returns a + b (app/calc.py); it never raises for bad input.")])
    ledger = a.plan(QA_FAILED)
    assert ledger.data["status"] == "answered" and ledger.data["answer"].startswith("add(a, b) returns") and not ledger.data["plan"]
    assert "only a promise to read" in a.provider.calls[1][1][0]["content"]


def test_a_model_that_only_keeps_promising_fails_after_three_attempts(repo):
    ledger = agent(repo, [PROMISE, PROMISE, PROMISE]).plan(QA_FAILED)
    assert ledger.data["status"] == "stopped" and ledger.data["stop_reason"].startswith("FAILED:") and "promise to read" in ledger.data["stop_reason"]


def test_real_answers_are_never_taken_for_promises():
    from ai.dev_agent.engine.intent import is_stub

    assert is_stub("I'll read the file to answer.") and is_stub("Let me look at the code first.") and is_stub("Okay, I will check app/calc.py.")
    for real in ("add(a, b) returns a + b.", "Let me explain: add returns a + b, see app/calc.py.", "I read app/calc.py: add returns a + b.",
                 "The function checks the input and returns a + b.", "I'll summarise:\n- add returns a + b"):
        assert not is_stub(real), real
