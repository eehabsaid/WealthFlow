"""Design system layer: token coverage, 200-line rule, wiring, money formatter."""

import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

STATIC = Path(settings.BASE_DIR) / "static"
DESIGN = STATIC / "css" / "design"
REQUIRED_TOKENS = [
    "--positive",
    "--negative",
    "--warning",
    "--info",
    "--focus-ring-color",
    "--chart-grid",
] + [f"--chart-{i}" for i in range(1, 9)]


def _read(path):
    return Path(path).read_text(encoding="utf-8")


class DesignSystemFilesTests(SimpleTestCase):
    def test_design_files_respect_200_line_rule(self):
        for css in DESIGN.glob("*.css"):
            self.assertLessEqual(len(_read(css).splitlines()), 200, css.name)

    def test_tokens_defined_for_dark_and_light(self):
        text = _read(DESIGN / "tokens.css")
        light_at = text.index('[data-theme="light"] {')
        dark_part, light_part = text[:light_at], text[light_at:]
        for token in REQUIRED_TOKENS:
            self.assertRegex(dark_part, rf"{re.escape(token)}\s*:", f"dark missing {token}")
            self.assertRegex(light_part, rf"{re.escape(token)}\s*:", f"light missing {token}")

    def test_no_raw_hex_outside_tokens_file(self):
        for css in DESIGN.glob("*.css"):
            if css.name == "tokens.css":
                continue
            self.assertIsNone(re.search(r"#[0-9a-fA-F]{3,8}\b", _read(css)), css.name)

    def test_layer_imported_before_responsive(self):
        main = _read(STATIC / "css" / "main" / "index.css")
        self.assertIn("../design/index.css", main)
        self.assertLess(main.index("../design/index.css"), main.index("../responsive/index.css"))

    def test_every_design_file_is_imported(self):
        index = _read(DESIGN / "index.css")
        for css in DESIGN.glob("*.css"):
            if css.name != "index.css":
                self.assertIn(css.name, index)


class DesignScriptTests(SimpleTestCase):
    def test_design_tokens_script_registered_before_use(self):
        partial = _read(Path(settings.BASE_DIR) / "templates/partials/scripts/02_reports_app_shell.html")
        self.assertIn("js/app/design_tokens.js", partial)
        self.assertLess(partial.index("js/app/formatting.js"), partial.index("js/app/design_tokens.js"))

    def test_helpers_exposed(self):
        js = _read(STATIC / "js/app/design_tokens.js")
        for name in ("cssVar", "chartPalette", "chartTheme", "readableChartColor", "isLightTheme"):
            self.assertIn(f"function {name}(", js)

    def test_money_formatter_and_language_refresh(self):
        self.assertIn("function fmtMoney(", _read(STATIC / "js/app/formatting.js"))
        self.assertIn(".num-fmtmoney", _read(STATIC / "js/i18n/apply_translations.js"))

    def test_money_kpis_use_two_decimal_formatter(self):
        overview = _read(STATIC / "js/balance/overview.js")
        self.assertNotIn("num-fmtpresent", overview)
        self.assertIn("fmtMoney(", overview)
        self.assertIn("fmtMoney(", _read(STATIC / "js/financial_advisor/utils.js"))

    def test_no_money_formatter_collision_left_on_four_decimals(self):
        # _money / _fmtDelta are script-global and defined in several files; the last one loaded wins,
        # so every definition must use the 2-decimal money formatter.
        for rel in (
            "financial_advisor/utils.js",
            "financial_advisor/what_if_simulator/what_if_state.js",
            "financial_advisor/what_if_simulator/what_if_chart/helpers.js",
            "financial_advisor/scenario_planner/state.js",
        ):
            js = _read(STATIC / "js" / rel)
            self.assertNotIn("fmtpresent", js, rel)

    def test_dashboard_chart_uses_theme_and_readable_colors(self):
        js = _read(STATIC / "js/salary/dashboard_render.js")
        self.assertIn("readableChartColor(", js)
        self.assertIn("chartTheme()", js)
        self.assertNotIn("#7b93c9", js)
