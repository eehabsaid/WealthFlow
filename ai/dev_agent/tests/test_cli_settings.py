"""`python -m ai.dev_agent settings`: shows how much context one task really has, warns when the saved values leave too little, and `settings set reserve_tokens N` is the
one-line fix (it changes only that value, never the model or anything else)."""

from ai.dev_agent import cli
from ai.dev_agent.settings.store import Settings

SAVED = {"context_window": "150000", "reserve_tokens": "140000", "max_output_tokens": "81920"}   # what coding_agent/agent_settings.json holds


def run(repo, capsys, *args):
    code = cli.main(["--root", str(repo.root), "settings", *args])
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_the_saved_values_leave_10000_tokens_and_the_command_prints_the_one_line_fix(repo, capsys):
    Settings(repo).update(SAVED)
    code, out, _ = run(repo, capsys, "show")
    assert code == 0 and "usable per task: 10,000 of 150,000 tokens" in out
    assert "WARNING: Only 10,000 of 150,000 tokens" in out and "To fix: python -m ai.dev_agent settings set reserve_tokens 90000" in out


def test_the_fix_changes_only_the_reserve_and_the_warning_is_gone(repo, capsys):
    store = Settings(repo)
    store.update({**SAVED, "model": "qwen-keep"})
    before = store.load()
    code, out, _ = run(repo, capsys, "set", "reserve_tokens", "90000")
    after = Settings(repo).load()
    assert code == 0 and "usable per task: 60,000 of 150,000 tokens" in out and "WARNING" not in out and "To fix" not in out
    assert {k: v for k, v in after.items() if k != "reserve_tokens"} == {k: v for k, v in before.items() if k != "reserve_tokens"}
    assert (after["reserve_tokens"], after["model"]) == (90000, "qwen-keep")


def test_a_reserve_the_window_cannot_hold_is_refused_and_changes_nothing(repo, capsys):
    before = Settings(repo).load()
    code, _, err = run(repo, capsys, "set", "reserve_tokens", "160000")
    assert code == 2 and "smaller than context_window" in err and Settings(repo).load() == before
