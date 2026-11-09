"""Small shared pieces of the task service: the task-id pattern and the record of the one run in progress."""

from __future__ import annotations

import re

TASK_ID = re.compile(r"^\d{8}-\d{6}-[a-z0-9-]{1,60}$")


class Run:
    def __init__(self, task_id: str, cancel, approver):
        self.task_id, self.cancel, self.approver, self.phase, self.thread = task_id, cancel, approver, "starting", None
