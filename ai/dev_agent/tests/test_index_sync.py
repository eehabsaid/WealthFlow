from ai.dev_agent.core.index import Index


def test_index_initializes_and_reports_status(repo):
    idx = Index(repo)
    res = idx.ensure_current()
    assert res["status"] in {"updated", "current"}
    status = idx.status()
    assert status["indexed_files"] >= 5
    assert status["status"] == "current"
    assert status["indexed_symbols"] >= 2


def test_index_detects_added_modified_deleted_and_renamed_files(repo):
    idx = Index(repo)
    idx.ensure_current()

    (repo.root / "app/new_service.py").write_text("def helper():\n    return 42\n", encoding="utf-8")
    (repo.root / "app/calc.py").write_text("def add(a, b):\n    return a + b + 1\n", encoding="utf-8")

    changes = idx.detect_changes()
    assert "app/new_service.py" in changes["added"]
    assert "app/calc.py" in changes["modified"]
    assert idx.is_stale() is True

    util = repo.root / "app/util.py"
    renamed = repo.root / "app/renamed_util.py"
    util.rename(renamed)
    changes = idx.detect_changes()
    assert any(item["to"] == "app/renamed_util.py" for item in changes["renamed"])

    (repo.root / "app/old.py").unlink()
    changes = idx.detect_changes()
    assert "app/old.py" in changes["removed"]


def test_search_refreshes_stale_indexes(repo):
    idx = Index(repo)
    idx.ensure_current()
    (repo.root / "app/finance.py").write_text("def total_budget():\n    return 9000\n", encoding="utf-8")

    results = idx.search("total_budget", 5)
    assert results and results[0]["path"] == "app/finance.py"
    assert idx.status()["status"] == "current"


def test_index_rebuilds_after_state_reset(repo):
    idx = Index(repo)
    idx.ensure_current()
    idx._state = {"version": 1, "files": {}, "manifest": {}, "last_successful_update": None, "errors": []}

    res = idx.ensure_current()
    assert res["status"] == "updated"
    status = idx.status()
    assert status["status"] == "current"
    assert status["indexed_files"] >= 5


def test_index_tracks_external_delete_and_post_edit_refresh(repo):
    idx = Index(repo)
    idx.ensure_current()
    (repo.root / "app/calc.py").write_text("def add(a, b):\n    return a + b + 1\n", encoding="utf-8")
    assert "app/calc.py" in idx.detect_changes()["modified"]

    to_delete = repo.root / "app/old.py"
    if to_delete.exists():
        to_delete.unlink()
        assert "app/old.py" in idx.detect_changes()["removed"]

    res = idx.refresh()
    assert res["status"] == "updated"
    assert idx.status()["status"] == "current"
