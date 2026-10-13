"""The reminder banner must never sit on top of an open modal (it swallowed clicks on the modal's buttons)."""

import json
import shutil
import subprocess
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

HARNESS = r"""
const listeners = {}; const body = []; let modalOpen = false; const out = [];
global.document = {
  addEventListener: (n, f) => { listeners[n] = f; },
  getElementById: (id) => body.find((b) => b.id === id) || null,
  querySelector: (sel) => (sel === ".modal.show" && modalOpen ? {} : null),
  createElement: () => ({ style: {}, remove() { body.splice(body.indexOf(this), 1); } }),
  body: { appendChild: (el) => body.push(el) },
};
global.t = (k, d) => d; global.esc = (s) => s; global._reminderIcon = () => "";
global.setTimeout = () => 0;
%s
const rem = [{ rule_name: "r", message: "m", rule_type: "x" }];
modalOpen = true;  _showReminderBanner(rem);  out.push(body.length);          // held while a modal is open
modalOpen = false; listeners["hidden.bs.modal"](); out.push(body.length);      // shown once it closes
modalOpen = true;  listeners["show.bs.modal"](); out.push(body.length);        // opening a modal drops it
modalOpen = true;  _showReminderBanner(rem); listeners["show.bs.modal"]();
modalOpen = false; listeners["hidden.bs.modal"](); out.push(body.length);      // a dropped one is not resurrected
process.stdout.write(JSON.stringify(out));
"""


class ReminderBannerModalTests(SimpleTestCase):
    def test_banner_waits_for_modals(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node not available")
        js = Path(settings.BASE_DIR, "static/js/reminders/banner.js").read_text(encoding="utf-8")
        out = subprocess.run([node, "-e", HARNESS % js], capture_output=True, text=True, check=True).stdout
        self.assertEqual(json.loads(out), [0, 1, 0, 0])
