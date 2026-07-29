"""
WealthFlow Screenshot Logger
Captures before-action, after-action, and failure screenshots:
 - Directory: test_reports/screenshots/
 - Naming format: {step_idx}_{page}_{tab}_{modal}_{action}_{status}.png
"""

import os
import re

class ScreenshotLogger:
    def __init__(self, output_dir="test_reports/screenshots", mode="all"):
        self.output_dir = output_dir
        self.mode = mode  # 'all', 'failures_only', 'off'
        self.step_counter = 0
        os.makedirs(self.output_dir, exist_ok=True)

    def _clean(self, text):
        return re.sub(r'[^a-zA-Z0-9_\-]', '_', str(text).lower())[:30]

    def capture(self, page, page_name="page", tab_name="tab", modal_name="none", action="view", status="ok"):
        if self.mode == "off":
            return None
        if self.mode == "failures_only" and status != "fail":
            return None

        self.step_counter += 1
        fn = f"{self.step_counter:04d}_{self._clean(page_name)}_{self._clean(tab_name)}_{self._clean(modal_name)}_{self._clean(action)}_{status}.png"
        filepath = os.path.join(self.output_dir, fn)
        try:
            page.screenshot(path=filepath, full_page=False)
            return filepath
        except Exception:
            return None
