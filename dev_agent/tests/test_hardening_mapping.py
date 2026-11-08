"""Hardening 3: every changed Python file needs a test mapping; unmapped files are reported by name and the result is never VERIFIED."""

import json
from pathlib import Path

from ..engine import coverage, verify
from ..core.project import Project

REAL = Path(__file__).resolve().parents[2]


def project(repo, **cfg):
    repo.config.update(cfg)
    return repo


def test_unmapped_python_files_are_listed_and_block_verified(repo, ctx):
    p = project(repo, test_areas={"app/": "tests/test_calc.py"})
    changed = ["app/calc.py", "lib/other.py", "tools/x.py", "tests/test_x.py", "static/a.js"]
    assert coverage.unmapped(p, changed) == ["lib/other.py", "tools/x.py"]
    row = coverage.row(p, changed)
    assert row["status"] == "NOT RUN" and "lib/other.py" in row["detail"] and "tools/x.py" in row["detail"] and "2 changed Python" in row["detail"]
    assert verify.overall([row, {"step": "x", "status": "PASSED", "detail": ""}]).startswith("NOT VERIFIED")


def test_fully_mapped_files_pass_and_non_python_is_ignored(repo):
    p = project(repo, test_areas={"app/": "tests/test_calc.py"})
    assert coverage.row(p, ["app/calc.py"])["status"] == "PASSED"
    assert coverage.row(p, ["static/a.js", "README.md"]) is None


def test_test_files_and_exempt_paths_need_no_mapping(repo):
    p = project(repo, test_exempt=["scripts/*"])
    assert coverage.unmapped(p, ["tests/test_a.py", "pkg/tests/helper.py", "x/test_b.py", "scripts/run.py", "manage.py"]) == ["manage.py"]


def test_pytest_areas_count_as_mapped_and_give_targets(repo):
    p = project(repo, pytest_areas={"dev_agent/": "dev_agent/tests"})
    assert coverage.unmapped(p, ["dev_agent/core/x.py"]) == [] and coverage.pytest_targets(p, ["dev_agent/core/x.py", "app/y.py"]) == ["dev_agent/tests"]


def test_verify_run_reports_the_mapping_row(repo, ctx):
    ctx.project.config.update(test_areas={"app/": "tests/test_calc.py"}, verify_steps=[])
    (repo.root / "lib").mkdir(exist_ok=True)
    (repo.root / "lib/other.py").write_text("X = 1\n")
    rows = verify.run(ctx, ["lib/other.py"])
    row = next(r for r in rows if r["step"] == "test mapping")
    assert row["status"] == "NOT RUN" and "lib/other.py" in row["detail"]
    assert verify.overall(rows).startswith("NOT VERIFIED")


def test_real_config_maps_the_directories_and_stays_string_valued():
    cfg = json.loads((REAL / "coding_agent/config.json").read_text(encoding="utf-8"))
    assert all(isinstance(v, str) for v in cfg["test_areas"].values())
    real = Project(REAL)
    for rel, module in {"ai_training/x.py": "ai_training.tests", "core/integrations/claude_provider/a.py": "core.tests.ai", "core/integrations/gold_price_api.py": "core.tests.rates_and_automation",
                        "core/models/billing/a.py": "core.tests.billing", "core/views/balance/a.py": "core.tests.balance", "core/reports/x.py": "core.tests.reports",
                        "core/reports/generate_report_generator/a.py": "core.tests.certificates", "wealthflow/settings.py": "core.tests.system"}.items():
        assert real.test_module(rel) == module, rel
    assert real.pytest_target("dev_agent/engine/verify.py") == "dev_agent/tests" and real.is_test_file("core/tests/ai/test_x.py")
