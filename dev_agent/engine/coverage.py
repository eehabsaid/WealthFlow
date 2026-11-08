"""Test-mapping coverage: every changed Python file must map to a Django test module (test_areas) or a pytest target (pytest_areas).
Files without a mapping are listed by name and make the overall result NOT VERIFIED; they are never silently treated as covered."""

from __future__ import annotations


def unmapped(project, changed: list[str]) -> list[str]:
    return sorted(f for f in changed if f.endswith(".py") and not project.is_test_file(f) and not project.test_module(f) and not project.pytest_target(f))


def pytest_targets(project, changed: list[str]) -> list[str]:
    return sorted({t for f in changed if (t := project.pytest_target(f))})


def row(project, changed: list[str]) -> dict | None:
    """One result row for the mapping check; None when no Python file changed."""
    py = [f for f in changed if f.endswith(".py") and not project.is_test_file(f)]
    if not py:
        return None
    missing = unmapped(project, changed)
    if missing:
        return {"step": "test mapping", "status": "NOT RUN",
                "detail": f"{len(missing)} changed Python file(s) have NO test mapping, so no automated test covers them: " + ", ".join(missing)
                          + " (add them to test_areas / pytest_areas in coding_agent/config.json, or test them by hand and say so)"}
    return {"step": "test mapping", "status": "PASSED", "detail": f"all {len(py)} changed Python file(s) map to a test area"}
