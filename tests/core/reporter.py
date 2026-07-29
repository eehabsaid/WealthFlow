"""
WealthFlow Comprehensive QA Reporter
Generates:
 1. Interactive HTML Report (test_reports/report.html)
 2. Machine-Readable JSON Report (test_reports/report.json)
 3. Coverage Summary Report detailing pages visited, tabs visited, modals opened, CRUDs executed, exports tested, and overall coverage percentage.
"""

import os
import json
import time

class QAReporter:
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
        step_rows = []
        for s in self.test_steps:
            shot_html = '<span style="color:#64748b">N/A</span>'
            if s.get("screenshot"):
                shot_html = f'<a href="{s["screenshot"]}" target="_blank"><img src="{s["screenshot"]}" style="max-height:48px;border-radius:4px;border:1px solid #475569" title="Click to view full screenshot"></a>'
            
            badge_cls = "badge-pass" if s["status"] == "PASS" else "badge-fail"
            step_rows.append(f"""<tr>
                <td>{s['index']}</td>
                <td>{s['timestamp']}</td>
                <td>{s['page']}</td>
                <td><b>{s['name']}</b></td>
                <td><span class="badge {badge_cls}">{s['status']}</span></td>
                <td>{s['details']}</td>
                <td>{shot_html}</td>
            </tr>""")

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>WealthFlow Human QA Regression Suite Report</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 24px; }}
        h1, h2, h3 {{ color: #38bdf8; }}
        .summary-card {{ display: flex; gap: 16px; margin-bottom: 24px; }}
        .metric-box {{ background: #1e293b; padding: 16px 24px; border-radius: 12px; border: 1px solid #334155; flex: 1; text-align: center; }}
        .metric-val {{ font-size: 28px; font-weight: bold; margin-top: 8px; }}
        .val-pass {{ color: #4ade80; }}
        .val-fail {{ color: #f87171; }}
        .val-pct {{ color: #38bdf8; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 16px; background: #1e293b; border-radius: 8px; overflow: hidden; }}
        th, td {{ padding: 12px 16px; text-align: left; border-bottom: 1px solid #334155; vertical-align: middle; }}
        th {{ background: #0f172a; color: #94a3b8; }}
        .badge {{ padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }}
        .badge-pass {{ background: #166534; color: #4ade80; }}
        .badge-fail {{ background: #991b1b; color: #f87171; }}
        img:hover {{ transform: scale(1.8); transition: transform 0.2s ease; cursor: pointer; }}
    </style>
</head>
<body>
    <h1>WealthFlow Human QA E2E Regression Report</h1>
    <div class="summary-card">
        <div class="metric-box">
            <div>Coverage Score</div>
            <div class="metric-val val-pct">{cov['overall_percentage']}%</div>
        </div>
        <div class="metric-box">
            <div>Passed Steps</div>
            <div class="metric-val val-pass">{self.passed_count}</div>
        </div>
        <div class="metric-box">
            <div>Failed Steps</div>
            <div class="metric-val val-fail">{self.failed_count}</div>
        </div>
        <div class="metric-box">
            <div>Duration</div>
            <div class="metric-val">{duration_sec}s</div>
        </div>
    </div>

    <h2>Test Coverage Summary</h2>
    <ul>
        <li><b>Pages Visited:</b> {len(self.pages_visited)} / {self.expected_pages} pages</li>
        <li><b>Sub-Tabs Visited:</b> {len(self.tabs_visited)} / {self.expected_tabs} tabs</li>
        <li><b>Modals Verified:</b> {len(self.modals_opened)} / {self.expected_modals} modals</li>
        <li><b>17-Step CRUD Lifecycle Runs:</b> {len(self.cruds_executed)} entities</li>
        <li><b>File Exports & Downloads Tested:</b> {len(self.exports_tested)} / {self.expected_exports} exports</li>
    </ul>

    <h2>Execution Step Log</h2>
    <table>
        <thead>
            <tr>
                <th>#</th>
                <th>Time</th>
                <th>Page</th>
                <th>Action / Step</th>
                <th>Status</th>
                <th>Details</th>
                <th>Screenshot</th>
            </tr>
        </thead>
        <tbody>
            {"".join(step_rows)}
        </tbody>
    </table>
</body>
</html>"""

        html_path = os.path.join(self.output_dir, "report.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"\n[REPORT GENERATED] HTML Report: {html_path}")
        print(f"[REPORT GENERATED] JSON Report: {json_path}")
        return html_path, json_path
