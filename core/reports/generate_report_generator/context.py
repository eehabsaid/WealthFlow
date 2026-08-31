"""
context.py
==========
NOTE: Part of the generate_report_generator package split (see package
__init__.py docstring for the full rationale). Defines ReportContext, the
typed dataclass carrier passed between phase functions (data -> styles ->
section builders), mirroring the ForecastContext / BaselineContext pattern
used in net_worth_service and scenario_planner_service.
"""
from dataclasses import dataclass, field


@dataclass
class ReportContext:
    """Carries everything the section builders need to append to `story`."""

    # request/period info
    lang: str
    t: dict
    pdf_font: str
    pdf_font_bold: str
    rtype: str
    year: int
    month: int
    start_date: str
    end_date: str
    title_str: str
    filename: str

    # aggregated data
    expenses: list
    total_exp: float
    total_inc: float
    net_sav: float
    sav_rate: float
    cat_totals: dict

    # reportlab styling (populated by styles.build_styles)
    colors: dict = field(default_factory=dict)
    styles: dict = field(default_factory=dict)

    # output
    story: list = field(default_factory=list)
