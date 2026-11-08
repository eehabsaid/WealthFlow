"""Browser E2E as a verification step: mandatory for UI files, run once in the final checks, honest NOT RUN when the machine cannot run it."""

import dataclasses
import json
import sys

import pytest

from ..engine import e2e, verify

SCRIPT_OK = "import sys\nprint('E2E suite ok', sys.argv[1:])\n"
SCRIPT_FAIL = "print('FAILED: tab Budgets did not open')\nraise SystemExit(1)\n"


@pytest.fixture
def final_ctx(ctx, monkeypatch):
    monkeypatch.setattr(e2e, "playwright_available", lambda: True)
    return dataclasses.replace(ctx, package="final")


def script(repo, text):
    (repo.root / "scripts").mkdir(exist_ok=True)
    (repo.root / "scripts" / "run_full_e2e.py").write_text(text, encoding="utf-8")


def step(results):
    return [r for r in results if r["step"] == "browser E2E"]


def test_not_asked_when_no_ui_file_changed(final_ctx):
    assert e2e.run(final_ctx, ["app/calc.py"]) is None
    assert not step(verify.run(final_ctx, ["app/calc.py"]))


def test_runs_once_in_the_final_checks_and_passes(repo, final_ctx):
    script(repo, SCRIPT_OK)
    row = e2e.run(final_ctx, ["static/app.js"])
    assert row["status"] == "PASSED" and row["step"] == "browser E2E"
    assert "run_full_e2e" not in json.dumps(row)            # the command output is not copied into the ledger when it passed


def test_a_package_check_skips_it_because_it_can_take_hours(repo, ctx, monkeypatch):
    monkeypatch.setattr(e2e, "playwright_available", lambda: True)
    script(repo, SCRIPT_OK)
    row = e2e.run(ctx, ["static/app.js"])                    # ctx.package is "P1"
    assert row["status"] == "SKIPPED" and "once" in row["detail"]


def test_failure_is_reported_with_the_output_so_the_model_can_fix_it(repo, final_ctx):
    script(repo, SCRIPT_FAIL)
    row = e2e.run(final_ctx, ["static/app.js"])
    assert row["status"] == "FAILED" and "tab Budgets did not open" in row["detail"]
    assert verify.overall([row]) == "FAILED"


def test_missing_script_is_not_run_with_the_reason(repo, final_ctx):
    row = e2e.run(final_ctx, ["static/x.css"])
    assert row["status"] == "NOT RUN" and "does not exist" in row["detail"]
    assert verify.overall([row]).startswith("NOT VERIFIED")


def test_missing_playwright_is_not_run_not_failed(repo, ctx, monkeypatch):
    monkeypatch.setattr(e2e, "playwright_available", lambda: False)
    script(repo, SCRIPT_OK)
    row = e2e.run(dataclasses.replace(ctx, package="final"), ["static/app.js"])
    assert row["status"] == "NOT RUN" and "Playwright is not installed" in row["detail"]


def test_a_machine_problem_in_the_output_is_not_run_not_failed(repo, final_ctx):
    script(repo, "print(\"Executable doesn't exist at C:/x/chrome.exe: run playwright install\")\nraise SystemExit(1)\n")
    row = e2e.run(final_ctx, ["static/app.js"])
    assert row["status"] == "NOT RUN" and "could not run on this machine" in row["detail"]


def test_timeout_is_a_failure_that_says_so(repo, final_ctx):
    script(repo, "import time\ntime.sleep(30)\n")
    repo.config["e2e"]["timeout_s"] = 1
    row = e2e.run(final_ctx, ["static/app.js"])
    assert row["status"] == "FAILED" and "TIMED OUT" in row["detail"]


def test_a_command_the_guard_denies_never_runs(repo, final_ctx):
    repo.config["e2e"]["command"] = "git push"
    row = e2e.run(final_ctx, ["static/app.js"])
    assert row["status"] == "NOT RUN" and "blocked" in row["detail"]


def test_an_unreadable_command_is_not_run(repo, final_ctx):
    repo.config["e2e"]["command"] = "python 'unterminated"
    assert e2e.run(final_ctx, ["static/app.js"])["status"] == "NOT RUN"


def test_extra_args_from_config_are_appended(repo, final_ctx):
    repo.config["e2e"]["args"] = ["--mode=smoke"]
    assert e2e.command(repo)[-1] == "--mode=smoke" and e2e.command(repo)[0] == "python" and e2e.command(repo)[1].endswith("run_full_e2e.py")
    script(repo, SCRIPT_OK)
    assert e2e.run(final_ctx, ["static/app.js"])["status"] == "PASSED"


def test_stop_cancels_a_running_suite(repo, final_ctx):
    import threading
    import time
    script(repo, "import time\ntime.sleep(60)\n")
    threading.Timer(1.0, lambda: final_ctx.cancel.set("stopped by user")).start()
    started = time.monotonic()
    row = e2e.run(final_ctx, ["static/app.js"])
    assert time.monotonic() - started < 20 and row["status"] == "NOT RUN" and "stopped by user" in row["detail"]


def test_real_interpreter_is_used(repo, final_ctx):
    script(repo, "import sys\nprint(sys.version_info[:2])\nraise SystemExit(0 if sys.version_info >= (3, 8) else 1)\n")
    assert e2e.run(final_ctx, ["static/app.js"])["status"] == "PASSED" and sys.executable
