"""
Interactive HTML report building for QAReporter.

Split out of the former monolithic tests/core/reporter.py (200-line rule).
Follows the flat-sibling convention already used by tests/core/ (no
subfolder — assertions.py, crud_verifier.py, etc. are all flat siblings
here, unlike tests/modules/, which uses subfolders per module).
"""


class ReporterHtmlMixin:
    def _build_html_report(self, cov, duration_sec):
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
        return html_content
