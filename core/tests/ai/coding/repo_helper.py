"""Throw-away git repository used by the coding-training tests."""

import os
import subprocess
import tempfile
from unittest.mock import patch

from django.test import SimpleTestCase

from core.services.ai.coding.training import dataset, history, settings


class Repo(SimpleTestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.git("init", "-q")
        self.git("config", "user.email", "t@t")
        self.git("config", "user.name", "t")
        self.write("core/app.py", "x = 1\n")
        self.write("core/tests/test_app.py", "# t\n")
        self.commit("start")
        patcher = patch.object(history, "ROOT", self.root)
        patcher.start()
        self.addCleanup(patcher.stop)

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.root, capture_output=True, text=True, check=True).stdout

    def write(self, rel, text):
        path = os.path.join(self.root, *rel.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)

    def commit(self, subject, body=""):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", subject, *(["-m", body] if body else []))
        return self.git("rev-parse", "HEAD").strip()

    def change(self, subject, files):
        for rel, text in files.items():
            self.write(rel, text)
        return self.commit(subject)

    def example(self):
        sha = self.change("add y", {"core/app.py": "x = 1\ny = 2\n", "core/tests/test_app.py": "# t2\n"})
        return dataset.candidate(next(c for c in history.commits() if c["sha"] == sha), settings())[0]
