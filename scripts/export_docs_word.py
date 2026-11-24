"""Export the product documentation (docs/product_docs/content/*.json) to a formatted Word file with a TOC."""
import json, glob, os
from docx import Document
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

CONTENT = os.path.join("docs", "product_docs", "content")
OUT = os.path.join("docs", "product_docs", "WealthFlow_Product_Documentation.docx")
DOMAIN_ORDER = ["auth_users", "dashboard_goals", "expenses_budgets", "balance_bank",
                "employment_salary", "fixed_assets", "advisor_ai", "settings_billing"]


def text(v):
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    if isinstance(v, (list, tuple)):
        return "\n".join(text(x) for x in v if x not in (None, ""))
    if isinstance(v, dict):
        return "\n".join(f"{k}: {text(val)}" for k, val in v.items())
    return str(v)


def add_rich(par, value, bold=False, mono=False):
    """Add value (str or list) to paragraph; lines starting with '- ' become bullets-lite, '### ' sub-heads."""
    lines = text(value).splitlines()
    first = True
    for line in lines:
        if not line.strip():
            if not first:
                par.add_run().add_break()
            first = False
            continue
        if line.strip().startswith("### "):
            r = par.add_run(line.strip()[4:])
            r.bold = True
            r.font.size = Pt(10.5)
            par.add_run().add_break()
            first = False
            continue
        if line.strip().startswith(("- ", "* ")):
            r = par.add_run("•  " + line.strip()[2:])
        else:
            r = par.add_run(line)
        if bold:
            r.bold = True
        if mono:
            r.font.name = "Consolas"
            r.font.size = Pt(9)
        first = False


def add_section(doc, title, value, mono=False):
    if value in (None, "", []):
        return
    p = doc.add_paragraph()
    r = p.add_run(title)
    r.bold = True
    r.font.color.rgb = RGBColor(0x1F, 0x3A, 0x5F)
    r.font.size = Pt(11)
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(2)
    body = doc.add_paragraph()
    body.paragraph_format.space_after = Pt(6)
    add_rich(body, value, mono=mono)


def add_toc(doc):
    p = doc.add_paragraph()
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), r'TOC \o "1-3" \h \z \u')
    r = OxmlElement("w:r")
    t = OxmlElement("w:t")
    t.text = "Right-click and choose 'Update Field' to populate the Table of Contents with page numbers."
    r.append(t)
    fld.append(r)
    p._p.append(fld)


DOMAIN_NAMES = {
    "auth_users": "Authentication, Account & User Management",
    "dashboard_goals": "Dashboard & Goals",
    "expenses_budgets": "Expenses, Budgets & Recurring Transactions",
    "balance_bank_certificates": "Balance, Banks, Cards & Certificates",
    "employment_salary": "Employment, Salary & Per Diems",
    "fixed_assets": "Fixed Assets, Properties & Vehicles",
    "advisor_ai": "Financial Advisor, AI Chat & Platform",
    "settings_billing_platform": "Settings, Billing & Platform Services",
}


def main():
    files = {os.path.basename(f)[:-5]: f for f in glob.glob(os.path.join(CONTENT, "*.json"))}
    order = [d for d in DOMAIN_ORDER if d in files] + [d for d in sorted(files) if d not in DOMAIN_ORDER]

    doc = Document()
    # Base style
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(10.5)

    # ---- Cover ----
    for _ in range(6):
        doc.add_paragraph()
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = t.add_run("WealthFlow")
    r.bold = True
    r.font.size = Pt(42)
    r.font.color.rgb = RGBColor(0x1F, 0x3A, 0x5F)
    s = doc.add_paragraph()
    s.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = s.add_run("Product Documentation\nThemes · Epics · Features · User Stories")
    r.font.size = Pt(16)
    doc.add_paragraph()
    n_stories = 0
    n_themes = 0
    for d in order:
        data = json.load(open(files[d], encoding="utf-8"))
        n_themes += len(data["themes"])
        n_stories += sum(len(f["stories"]) for th in data["themes"] for e in th["epics"] for f in e["features"])
    info = doc.add_paragraph()
    info.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = info.add_run(f"{len(order)} domains   ·   {n_themes} themes   ·   {n_stories} user stories")
    r.font.size = Pt(12)
    r.font.color.rgb = RGBColor(0x66, 0x66, 0x66)
    doc.add_page_break()

    # ---- TOC ----
    h = doc.add_paragraph()
    r = h.add_run("Table of Contents")
    r.bold = True
    r.font.size = Pt(22)
    add_toc(doc)
    doc.add_page_break()

    # ---- Content ----
    for d in order:
        data = json.load(open(files[d], encoding="utf-8"))
        doc.add_heading(DOMAIN_NAMES.get(data["domain"], data["domain"]), level=1)
        for th in data["themes"]:
            doc.add_heading(th["name"], level=2)
            if th.get("description"):
                p = doc.add_paragraph()
                r = p.add_run(text(th["description"]))
                r.italic = True
            for e in th["epics"]:
                doc.add_heading(e["name"], level=3)
                for f in e["features"]:
                    doc.add_heading(f["name"], level=4)
                    for st in f["stories"]:
                        doc.add_heading(f"{st['id']} — {st['title']}", level=5)
                        add_section(doc, "Roles / Personas", st.get("roles"))
                        add_section(doc, "Description", st.get("description"))
                        add_section(doc, "Preconditions", st.get("preconditions"))
                        add_section(doc, "Business Rules", st.get("business_rules"))
                        add_section(doc, "Acceptance Criteria (Given / When / Then)", st.get("acceptance_criteria"))
                        add_section(doc, "Main Flow", st.get("main_flow"))
                        add_section(doc, "Alternate Flows", st.get("alternate_flows"))
                        add_section(doc, "Error Scenarios", st.get("error_scenarios"))
                        add_section(doc, "Dependencies", st.get("dependencies"))
                        add_section(doc, "Related Stories", st.get("related"))
                        add_section(doc, "Implementation Source", st.get("source"), mono=True)
                        doc.add_paragraph()  # spacing between stories

    # ---- Gaps appendix ----
    doc.add_page_break()
    doc.add_heading("Appendix — Known Gaps, Missing & Inconsistent Functionality", level=1)
    for d in order:
        data = json.load(open(files[d], encoding="utf-8"))
        gaps = data.get("gaps") or []
        if not gaps:
            continue
        doc.add_heading(DOMAIN_NAMES.get(data["domain"], data["domain"]), level=2)
        for g in gaps:
            p = doc.add_paragraph(style="List Bullet")
            add_rich(p, g)

    doc.save(OUT)
    print("WROTE", OUT, os.path.getsize(OUT), "bytes;", n_stories, "stories")


if __name__ == "__main__":
    main()
