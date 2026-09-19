"""
WealthFlow Comprehensive QA Reporter
Generates:
 1. Interactive HTML Report (test_reports/report.html)
 2. Machine-Readable JSON Report (test_reports/report.json)
 3. Coverage Summary Report detailing pages visited, tabs visited, modals opened, CRUDs executed, exports tested, and overall coverage percentage.

Split into a flat sibling (200-line rule):
  - reporter_html.py : ReporterHtmlMixin (_build_html_report)
  - reporter.py (this file) : QAReporter class with __init__, add_step,
    record_crud, calculate_coverage, generate_reports
"""

import os
import json
import time

from tests.core.reporter_html import ReporterHtmlMixin


class QAReporter(ReporterHtmlMixin):
    def __init__(self, output_dir="test_reports"):
        self.output_dir = output_dir
        self.start_time = time.time()
        os.makedirs(self.output_dir, exist_ok=True)

        self.pages_visited = set()
        self.subpages_visited = set()
        self.tabs_visited = set()
        self.modals_opened = set()
        self.cruds_executed = []
        self.exports_tested = []
        self.validations_performed = []
        self.skipped_items = []

        self.test_steps = []
        self.passed_count = 0
        self.failed_count = 0
        self.skipped_count = 0

        self.expected_pages = 14
        self.expected_tabs = 40
        self.expected_modals = 18
        self.expected_exports = 8

    def add_step(self, name, page_name, status="PASS", details="", screenshot_path=None, duration_ms=0):
        rel_screenshot = None
        if screenshot_path:
            rel_screenshot = os.path.relpath(screenshot_path, self.output_dir).replace("\\", "/")

        step = {
            "index": len(self.test_steps) + 1,
            "name": name,
            "page": page_name,
            "status": status,
            "details": details,
            "screenshot": rel_screenshot,
            "duration_ms": duration_ms,
            "timestamp": time.strftime("%H:%M:%S")
        }
        self.test_steps.append(step)

        if status == "PASS":
            self.passed_count += 1
        elif status == "FAIL":
            self.failed_count += 1
        elif status == "SKIP":
            self.skipped_count += 1

    def record_crud(self, entity_name, steps_passed, total_steps=17):
        self.cruds_executed.append({
            "entity": entity_name,
            "steps_passed": steps_passed,
            "total_steps": total_steps,
            "status": "PASS" if steps_passed == total_steps else "PARTIAL"
        })

    def calculate_coverage(self):
        p_cov = min(1.0, len(self.pages_visited) / self.expected_pages) if self.expected_pages else 1.0
        t_cov = min(1.0, len(self.tabs_visited) / self.expected_tabs) if self.expected_tabs else 1.0
        m_cov = min(1.0, len(self.modals_opened) / self.expected_modals) if self.expected_modals else 1.0
        e_cov = min(1.0, len(self.exports_tested) / self.expected_exports) if self.expected_exports else 1.0

        overall_pct = round(((p_cov * 0.25) + (t_cov * 0.25) + (m_cov * 0.25) + (e_cov * 0.25)) * 100, 1)
        return {
            "overall_percentage": overall_pct,
            "pages_count": len(self.pages_visited),
            "tabs_count": len(self.tabs_visited),
            "modals_count": len(self.modals_opened),
            "cruds_count": len(self.cruds_executed),
            "exports_count": len(self.exports_tested),
        }

    def generate_reports(self):
        duration_sec = round(time.time() - self.start_time, 2)
        cov = self.calculate_coverage()

        # 1. JSON Report
        json_data = {
            "summary": {
                "total_steps": len(self.test_steps),
                "passed": self.passed_count,
                "failed": self.failed_count,
                "skipped": self.skipped_count,
                "duration_seconds": duration_sec,
                "coverage": cov
            },
            "pages_visited": list(self.pages_visited),
            "tabs_visited": list(self.tabs_visited),
            "modals_opened": list(self.modals_opened),
            "cruds_executed": self.cruds_executed,
            "exports_tested": self.exports_tested,
            "steps": self.test_steps
        }

        json_path = os.path.join(self.output_dir, "report.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=2)

        # 2. Interactive HTML Report
        html_content = self._build_html_report(cov, duration_sec)

        html_path = os.path.join(self.output_dir, "report.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"\n[REPORT GENERATED] HTML Report: {html_path}")
        print(f"[REPORT GENERATED] JSON Report: {json_path}")
        return html_path, json_path
