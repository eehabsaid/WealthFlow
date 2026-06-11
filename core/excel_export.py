"""
Excel export — regenerates the original Balance.xlsx format from live DB data,
plus a new Expenses tab.

Exact style match to original:
- Salary sheets: grey col headers, red "Salary Details" title, bold year headings (sz18),
  plain data rows (no fill), bold Total/SUMMARY rows (no fill)
- Bank-Certificates: plain bold headers, no fill
- BALANCE: plain bold headers, no fill
- Exchange Rates: bold sz16 Arabic headers, plain data
- Expenses: new tab with monthly/yearly totals
"""
import io
from itertools import groupby
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, numbers
from openpyxl.utils import get_column_letter

# ── Color constants (from original) ─────────────────────────────────────────
GREY_TEXT   = "FF7F7F7F"   # salary sheet col-header grey text
RED_TEXT    = "FFFF0000"   # "Salary Details" red
WHITE_TEXT  = "FFFFFFFF"
TOTAL_FILL  = "FFD9E1F2"   # monthly total rows in Expenses only
SUMMARY_FILL= "FFBDD7EE"   # yearly total rows in Expenses only
EXP_HDR     = "FF203864"   # Expenses header fill

# ── Style helpers ─────────────────────────────────────────────────────────────

def _font(bold=False, size=11, color=None, name="Calibri"):
    kw = dict(bold=bold, size=size, name=name)
    if color:
        kw["color"] = color
    return Font(**kw)

def _fill(hex_color):
    return PatternFill("solid", fgColor=hex_color)

def _no_fill():
    return PatternFill(fill_type=None)

def _align(h="left", v="center", wrap=False):
    return Alignment(horizontal=h, vertical=v, wrap_text=wrap)


# ── Salary sheet builder ──────────────────────────────────────────────────────

MONTH_ORDER = [
    "January","February","March","April","May","June",
    "July","August","September","October","November","December",
    "Quarter-Bonuses",
]

def _month_sort(m):
    m_str = str(m).strip()
    for i, name in enumerate(MONTH_ORDER):
        if name.lower().startswith(m_str.lower()[:3]):
            return i
    return 99

# Remaining formula per company — matches original exactly
REMAINING_FORMULA = {
    "NTG":                  "=D{r}-C{r}",
    "Giza Systems":         "=D{r}-C{r}",
    "Giza Systems (2)":     "=D{r}-C{r}",
    "ElSeweedy Technology": "=IF(D{r}>0,C{r}-D{r},0)",
    "Dedalus":              "=IF(D{r}>0,C{r}-D{r},0)",
    "Globemed":             "=IF(D{r}>0,C{r}-D{r},0)",
    "Giza Systems (3)":     "=IF(D{r}>0,C{r}-D{r},0)",
}

def build_salary_sheet(ws, company, entries):
    has_bonus = company.name == "Giza Systems (3)"
    remaining_fmt = REMAINING_FORMULA.get(company.name, "=IF(D{r}>0,C{r}-D{r},0)")

    # Row 1: column headers — grey text, no fill, no bold (exact original)
    headers = ["Year", "Month", "Expected",
               "Paid (Salary + Bonus)" if has_bonus else "Paid",
               "Remaining"]
    if has_bonus:
        headers.append("Bonus")

    for col, h in enumerate(headers, 1):
        c = ws.cell(row=1, column=col, value=h)
        # Original: bold only for GS3, grey text for others
        c.font = _font(bold=has_bonus, size=11,
                       color=None if has_bonus else GREY_TEXT)

    # Row 2: " Salary Details" — bold, size 18, red text
    ws.cell(row=2, column=1, value=" Salary Details").font = _font(
        bold=True, size=18, color=RED_TEXT)
    ws.merge_cells(f"A2:{'F' if has_bonus else 'E'}2")

    # Data rows starting at row 4
    row = 4
    total_rows = []

    sorted_entries = sorted(entries, key=lambda e: (e.year, _month_sort(str(e.month))))

    for year, year_group in groupby(sorted_entries, key=lambda e: e.year):
        year_entries = list(year_group)

        # Year heading: bold, size 18, no fill
        ws.cell(row=row, column=1, value=str(year)).font = _font(bold=True, size=18)
        row += 1

        data_start = row
        for entry in year_entries:
            ws.cell(row=row, column=1, value=entry.year)
            ws.cell(row=row, column=2, value=str(entry.month))
            ws.cell(row=row, column=3, value=float(entry.expected))
            ws.cell(row=row, column=4, value=float(entry.paid))
            ws.cell(row=row, column=5, value=remaining_fmt.format(r=row))
            if has_bonus:
                ws.cell(row=row, column=6, value=f"=IF(D{row}>C{row},D{row}-C{row},0)")
            row += 1

        data_end = row - 1

        # Total row: bold, NO fill (exact original)
        paid_count = sum(1 for e in year_entries if float(e.paid) > 0)
        ws.cell(row=row, column=1, value="Total").font = _font(bold=True)
        ws.cell(row=row, column=2,
                value=f'=COUNTIF(D{data_start}:D{data_end},"<> 0.00")' if has_bonus
                else paid_count).font = _font(bold=True)
        ws.cell(row=row, column=3, value=f"=SUM(C{data_start}:C{data_end})").font = _font(bold=True)
        ws.cell(row=row, column=4, value=f"=SUM(D{data_start}:D{data_end})").font = _font(bold=True)
        ws.cell(row=row, column=5, value=f"=D{row}-C{row}").font = _font(bold=False)
        if has_bonus:
            ws.cell(row=row, column=6,
                    value=f"=IF(D{row}>C{row},D{row}-C{row},0)").font = _font(bold=True)

        total_rows.append(row)
        row += 1

    # Grand SUMMARY / Total row — bold, no fill
    sr = row
    label = "Total" if has_bonus else "SUMMARY"
    ws.cell(row=sr, column=1, value=label).font = _font(bold=True)
    b_refs = "+".join(f"B{r}" for r in total_rows)
    # For non-bonus sheets B col is a plain count number, use SUM of those refs
    ws.cell(row=sr, column=2, value=f"={b_refs}").font = _font(bold=True)
    c_refs = "+".join(f"C{r}" for r in total_rows)
    d_refs = "+".join(f"D{r}" for r in total_rows)
    ws.cell(row=sr, column=3, value=f"={c_refs}").font = _font(bold=True)
    ws.cell(row=sr, column=4, value=f"={d_refs}").font = _font(bold=True)
    ws.cell(row=sr, column=5, value=f"=D{sr}-C{sr}").font = _font(bold=False)
    if has_bonus:
        f_refs = "+".join(f"F{r}" for r in total_rows)
        ws.cell(row=sr, column=6, value=f"={f_refs}").font = _font(bold=True)

    # Column widths
    ws.column_dimensions["A"].width = 8
    ws.column_dimensions["B"].width = 15
    ws.column_dimensions["C"].width = 14
    ws.column_dimensions["D"].width = 22 if has_bonus else 14
    ws.column_dimensions["E"].width = 14
    if has_bonus:
        ws.column_dimensions["F"].width = 14

    return sr  # return summary row number for BALANCE cross-references


# ── Exchange Rates sheet ──────────────────────────────────────────────────────

CURRENCY_CODES_ORDER = [
    ("USD","US Dollar"), ("EUR","Euro"), ("GBP","Pound Sterling"),
    ("CAD","Canadian Dollar"), ("DKK","Danish Krone"), ("NOK","Norwegian Krone"),
    ("SEK","Swedish Krona"), ("CHF","Swiss Franc"), ("JPY","Japanese Yen"),
    ("SAR","Saudi Riyal"), ("KWD","Kuwaiti Dinar"), ("AED","UAE Dirham"),
    ("AUD","Australian Dollar"), ("BHD","Bahraini Dinar"), ("OMR","Omani Riyal"),
    ("QAR","Qatari Riyal"), ("JOD","Jordanian Dinar"), ("CNY","Chinese Yuan"),
]

ARABIC_NAMES = {
    "USD":"دولار أمريكى","EUR":"يورو","GBP":"جنيــه إسترليـنى",
    "CAD":"دولار كنـدى","DKK":"كرون دانمركى","NOK":"كرون نرويجى",
    "SEK":"كرون ســويدى","CHF":"فرنك سويسرى","JPY":"100 ين يابانى",
    "SAR":"ريـــال سعـــودى","KWD":"دينــار كويتى","AED":"درهم اماراتى",
    "AUD":"دولار اســـترالى","BHD":"دينــار البحــرين","OMR":"ريـــال عمـــانى",
    "QAR":"ريـــال قطــــرى","JOD":"دينـار اردنـى","CNY":"يوان صينى",
}

def build_exchange_rates_sheet(ws, rates_list, balance_entries):
    # Row 1: bold sz16, no fill (exact original)
    for col, h in enumerate(["العملة","شراء","بيع"], 1):
        ws.cell(row=1, column=col, value=h).font = _font(bold=True, size=16)

    rate_map = {r.currency_code: r for r in rates_list}
    eur_row = sar_row = None

    for i, (code, _) in enumerate(CURRENCY_CODES_ORDER, 2):
        r = rate_map.get(code)
        ws.cell(row=i, column=1, value=ARABIC_NAMES.get(code, code))
        if r:
            buy = float(r.buy_rate)
            sell = float(r.sell_rate)
            if code == "JPY":  # original shows per-100-yen
                buy = round(buy * 100, 4)
                sell = round(sell * 100, 4)
            ws.cell(row=i, column=2, value=buy)
            ws.cell(row=i, column=3, value=sell)
        if code == "EUR": eur_row = i
        if code == "SAR": sar_row = i

    # Side calc block: EUR/USD home balance totals (original cols F-H, rows 5-6)
    from core.models import Currency
    try:
        usd_cur = Currency.objects.get(code="USD")
        eur_cur = Currency.objects.get(code="EUR")
        home_usd = sum(float(be.amount) for be in balance_entries
                       if be.bank_id is None and be.currency_id == usd_cur.id)
        home_eur = sum(float(be.amount) for be in balance_entries
                       if be.bank_id is None and be.currency_id == eur_cur.id)
    except Exception:
        home_usd, home_eur = 0, 0

    ws.cell(row=5, column=6, value=home_eur)
    ws.cell(row=5, column=7, value=home_usd)
    ws.cell(row=5, column=8, value="Total")
    ws.cell(row=6, column=6, value=f"=F5*B{eur_row}")
    ws.cell(row=6, column=7, value=f"=G5*B2")   # USD always row 2
    ws.cell(row=6, column=8, value="=F6+G6")

    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 14
    ws.column_dimensions["C"].width = 14


# ── Gold Price sheet ──────────────────────────────────────────────────────────

def build_gold_price_sheet(ws, gold_qs, balance_entries):
    latest = gold_qs.order_by("-fetched_at").first()

    # Original has generic "Column1..5" as row 1 (just placeholder headers)
    for col, h in enumerate(["Column1","Column2","Column3","Column4","Column5"], 1):
        ws.cell(row=1, column=col, value=h)

    ws.cell(row=2, column=1, value="السعر")
    ws.cell(row=2, column=2, value="شراء")
    ws.cell(row=2, column=3, value="بيع")
    ws.cell(row=2, column=4, value="المزيد")

    carats = [
        ("جرام عيار 24 46 ج", "carat_24k_buy", "carat_24k",  "46 ج"),
        ("جرام عيار 22 42 ج", "carat_22k_buy", "carat_22k",  "42 ج"),
        ("جرام عيار 21 40 ج", "carat_21k_buy", "carat_21k",  "40 ج"),
        ("جرام عيار 18 34 ج", "carat_18k_buy", "carat_18k",  "34 ج"),
    ]
    for i, (label, buy_f, sell_f, karat) in enumerate(carats, 3):
        ws.cell(row=i, column=1, value=label)
        ws.cell(row=i, column=2, value=float(getattr(latest, buy_f, 0)) if latest else 0)
        ws.cell(row=i, column=3, value=float(getattr(latest, sell_f, 0)) if latest else 0)
        ws.cell(row=i, column=4, value=">")
        ws.cell(row=i, column=5, value=karat)

    # 14k approx
    ws.cell(row=7, column=1, value="جرام عيار 14 27 ج")
    ws.cell(row=7, column=2, value=round(float(latest.carat_18k_buy)*(14/18), 0) if latest else 0)
    ws.cell(row=7, column=3, value=round(float(latest.carat_18k)*(14/18), 0) if latest else 0)
    ws.cell(row=7, column=4, value=">")
    ws.cell(row=7, column=5, value="27 ج")

    # Gold grams from balance
    from core.models import Currency
    try:
        gold_cur = Currency.objects.get(code="Gold")
        gold_grams = sum(float(be.amount) for be in balance_entries
                         if be.bank_id is None and be.currency_id == gold_cur.id)
    except Exception:
        gold_grams = 0
    ws.cell(row=7, column=7, value=f"{int(gold_grams)} Grams")

    ws.cell(row=8, column=1, value="الدولار 0 ج")
    ws.cell(row=8, column=2, value=float(latest.usd_to_egp) if latest else 0)
    ws.cell(row=8, column=3, value=float(latest.usd_to_egp) if latest else 0)
    ws.cell(row=8, column=5, value="0 ج")
    ws.cell(row=8, column=7, value="Now")
    ws.cell(row=8, column=8, value="Paid")
    ws.cell(row=8, column=9, value="Diff")

    ws.cell(row=9, column=1, value="الأونصة 0 $")
    ws.cell(row=9, column=2, value=float(latest.usd_per_oz) if latest else 0)
    ws.cell(row=9, column=3, value=float(latest.usd_per_oz) if latest else 0)
    ws.cell(row=9, column=5, value="0 $")
    ws.cell(row=9, column=7, value="=(C3+28.5)*(BALANCE!F2)")
    ws.cell(row=9, column=8, value=897375)   # historical paid value
    ws.cell(row=9, column=9, value="=G9-H9")

    ws.cell(row=10, column=1, value="الجنيه الذهب 320 ج")
    ws.cell(row=10, column=2, value=round(float(latest.carat_21k_buy)*8, 0) if latest else 0)
    ws.cell(row=10, column=3, value=round(float(latest.carat_21k)*8, 0) if latest else 0)
    ws.cell(row=10, column=5, value="320 ج")

    ws.column_dimensions["A"].width = 22


# ── Bank Certificates sheet ───────────────────────────────────────────────────

def build_bank_certificates_sheet(ws, certs_qs):
    # Original: plain bold headers, no fill, no colored text
    headers = ["Amount","Interest Rate","Interest Value","Frequency","Start Date","End Date"]
    for col, h in enumerate(headers, 1):
        ws.cell(row=1, column=col, value=h).font = _font(bold=False, size=11)

    for i, cert in enumerate(certs_qs.order_by("issue_date"), 2):
        ws.cell(row=i, column=1, value=float(cert.amount))
        ws.cell(row=i, column=2, value=float(cert.interest_rate))
        ws.cell(row=i, column=3, value=f"=(A{i}*B{i})/12")
        ws.cell(row=i, column=4, value=cert.frequency)
        ws.cell(row=i, column=5, value=cert.issue_date)
        ws.cell(row=i, column=6, value=cert.expiry_date)
        ws.cell(row=i, column=5).number_format = "YYYY-MM-DD"
        ws.cell(row=i, column=6).number_format = "YYYY-MM-DD"

    ws.column_dimensions["A"].width = 14
    ws.column_dimensions["B"].width = 15
    ws.column_dimensions["C"].width = 16
    ws.column_dimensions["D"].width = 12
    ws.column_dimensions["E"].width = 14
    ws.column_dimensions["F"].width = 14


# ── BALANCE sheet ─────────────────────────────────────────────────────────────

def build_balance_sheet(ws, balance_entries, company_sheet_rows):
    """
    company_sheet_rows: dict mapping company.name -> (sheet_name, summary_row)
    Built after all salary sheets are written so row numbers are exact.
    """
    # Row 1: plain bold headers, no fill (exact original)
    headers = ["Title","EGP","USD","EUR","SAR","Gold",
               "Acct-Number","Card-ID","Swift-Code","Customer-id","Customer-Name"]
    for col, h in enumerate(headers, 1):
        ws.cell(row=1, column=col, value=h).font = _font(bold=True, size=11)

    from core.models import Currency, Bank as BankModel
    cur_map  = {c.id: c.code for c in Currency.objects.all()}
    bank_map = {b.id: b for b in BankModel.objects.all()}

    # Row 2: Home Balance
    home = {cur_map.get(be.currency_id,"?"): float(be.amount)
            for be in balance_entries if be.bank_id is None and be.title == "Home Balance"}

    ws.cell(row=2, column=1, value="Home Balance").font = _font(bold=True, size=11)
    ws.cell(row=2, column=2, value=home.get("EGP", 0)).font = _font(bold=True, size=11)
    ws.cell(row=2, column=3, value=home.get("USD", 0))
    ws.cell(row=2, column=4, value=home.get("EUR", 0))
    ws.cell(row=2, column=5, value=home.get("SAR", 0))
    ws.cell(row=2, column=6, value=home.get("Gold", 0))

    # Bank rows (skip Home Balance and QNB Certificates — cert row added as formula)
    excel_row = 3
    for be in sorted(balance_entries, key=lambda b: b.id):
        if be.title == "Home Balance":
            continue
        if be.title == "QNB Certificates Balance":
            continue
        if cur_map.get(be.currency_id) != "EGP":
            continue  # only EGP rows as main balance row

        ws.cell(row=excel_row, column=1, value=be.title).font = _font(bold=True, size=11)
        ws.cell(row=excel_row, column=2, value=float(be.amount)).font = _font(bold=True, size=11)

        bank = bank_map.get(be.bank_id)
        if bank:
            ws.cell(row=excel_row, column=7,  value=getattr(bank,"account_number","") or "")
            ws.cell(row=excel_row, column=8,  value=getattr(bank,"card_number","")    or "")
            ws.cell(row=excel_row, column=9,  value=getattr(bank,"swift_code","")     or "")
            ws.cell(row=excel_row, column=10, value=getattr(bank,"customer_id","")    or "")
            ws.cell(row=excel_row, column=11, value=getattr(bank,"customer_name","")  or "")
        excel_row += 1

    # QNB Certificates Balance — formula row
    from core.models import BankCertificate
    cert_count = BankCertificate.objects.count()
    cert_row = excel_row
    ws.cell(row=cert_row, column=1, value="QNB Certificates Balance").font = _font(bold=True, size=11)
    ws.cell(row=cert_row, column=2,
            value=f"=SUM('Bank-Certificates'!A2:A{cert_count+1})").font = _font(bold=True, size=11)
    excel_row += 1

    # Total EGP
    total_egp_row = excel_row
    ws.cell(row=total_egp_row, column=1, value="Total EGP Balance").font = _font(bold=True, size=11)
    ws.cell(row=total_egp_row, column=2, value=f"=SUM(B2:B{cert_row})").font = _font(bold=True, size=11)
    excel_row += 1

    # Total all Balances (exact original formula structure)
    total_all_row = excel_row
    ws.cell(row=total_all_row, column=1, value="Total all Balances").font = _font(bold=True, size=11)
    formula = (
        f"=B{total_egp_row}"
        f"+(C2*('Exchange Rates'!B2))"
        f"+(D2*('Exchange Rates'!B3))"
        f"+(E2*('Exchange Rates'!B11))"
        f"+((F2*('Gold Price'!C3))+28.5)"
    )
    ws.cell(row=total_all_row, column=2, value=formula).font = _font(bold=True, size=11)

    # Spacer rows (original has rows 8-10 empty)
    total_pays_row = total_all_row + 4
    total_months_row = total_all_row + 5

    # Build cross-sheet pay/month formulas using ACTUAL sheet names and row numbers
    pay_parts   = []
    month_parts = []
    for company_name, (sheet_name, summary_row) in company_sheet_rows.items():
        # Quote sheet names that contain spaces
        ref = f"'{sheet_name}'!{{col}}{summary_row}" if ' ' in sheet_name \
              else f"{sheet_name}!{{col}}{summary_row}"
        pay_parts.append(ref.format(col="D"))
        month_parts.append(ref.format(col="B"))

    ws.cell(row=total_pays_row,   column=1, value="Total Pays").font = _font(bold=True, size=11)
    ws.cell(row=total_pays_row,   column=2,
            value="=" + "+".join(pay_parts) if pay_parts else 0).font = _font(bold=True, size=11)

    ws.cell(row=total_months_row, column=1, value="Total Work Months").font = _font(bold=True, size=11)
    ws.cell(row=total_months_row, column=2,
            value="=" + "+".join(month_parts) if month_parts else 0).font = _font(bold=True, size=11)

    # Column widths
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 16
    ws.column_dimensions["C"].width = 10
    ws.column_dimensions["D"].width = 10
    ws.column_dimensions["E"].width = 10
    ws.column_dimensions["F"].width = 10
    ws.column_dimensions["G"].width = 18
    ws.column_dimensions["H"].width = 20
    ws.column_dimensions["I"].width = 14
    ws.column_dimensions["J"].width = 14
    ws.column_dimensions["K"].width = 28


# ── Expenses sheet (new) ──────────────────────────────────────────────────────

def build_expenses_sheet(ws, expenses_qs):
    headers = ["Date","Year","Month","Category","Sub-Category",
               "Description","Amount","Currency","Payment Method","Notes"]
    for col, h in enumerate(headers, 1):
        c = ws.cell(row=1, column=col, value=h)
        c.font = Font(bold=True, color=WHITE_TEXT, name="Calibri")
        c.fill = _fill(EXP_HDR)
        c.alignment = _align("center")

    expenses = list(expenses_qs.select_related("category","subcategory","currency")
                    .order_by("year","month","date"))

    row = 2
    year_total_rows = {}

    for year, y_group in groupby(expenses, key=lambda e: e.year):
        year_entries = list(y_group)
        year_start = row

        for month, m_group in groupby(year_entries, key=lambda e: e.month):
            month_entries = list(m_group)
            month_name = MONTH_ORDER[month - 1] if 1 <= month <= 12 else str(month)
            month_start = row

            for exp in month_entries:
                ws.cell(row=row, column=1, value=exp.date).number_format = "YYYY-MM-DD"
                ws.cell(row=row, column=2, value=exp.year)
                ws.cell(row=row, column=3, value=month_name)
                ws.cell(row=row, column=4, value=exp.category.name if exp.category else "")
                ws.cell(row=row, column=5, value=exp.subcategory.name if exp.subcategory else "")
                ws.cell(row=row, column=6, value=exp.description or "")
                ws.cell(row=row, column=7, value=float(exp.amount))
                ws.cell(row=row, column=8, value=exp.currency.code if exp.currency else "EGP")
                ws.cell(row=row, column=9, value=exp.payment_method or "")
                ws.cell(row=row, column=10, value=exp.notes or "")
                row += 1

            month_end = row - 1
            # Month total row
            ws.cell(row=row, column=3, value=f"{month_name} Total")
            ws.cell(row=row, column=7, value=f"=SUM(G{month_start}:G{month_end})")
            for col in range(1, 11):
                ws.cell(row=row, column=col).font = _font(bold=True)
                ws.cell(row=row, column=col).fill = _fill(TOTAL_FILL)
            row += 1

        year_end = row - 1
        # Year total row
        ws.cell(row=row, column=2, value=f"{year} Total")
        ws.cell(row=row, column=7,
                value=f"=SUMIF(B{year_start}:B{year_end},{year},G{year_start}:G{year_end})")
        for col in range(1, 11):
            ws.cell(row=row, column=col).font = _font(bold=True)
            ws.cell(row=row, column=col).fill = _fill(SUMMARY_FILL)
        year_total_rows[year] = row
        row += 2

    # Grand total
    if year_total_rows:
        grand_refs = "+".join(f"G{r}" for r in year_total_rows.values())
        ws.cell(row=row, column=1, value="Grand Total")
        ws.cell(row=row, column=7, value=f"={grand_refs}")
        for col in range(1, 11):
            ws.cell(row=row, column=col).font = Font(bold=True, color=WHITE_TEXT, name="Calibri")
            ws.cell(row=row, column=col).fill = _fill(EXP_HDR)

    widths = [14, 8, 12, 18, 20, 35, 14, 10, 16, 25]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A2"


# ── Main export function ──────────────────────────────────────────────────────

def generate_excel(output_path=None):
    from core.models import (Company, BalanceEntry, BankCertificate,
                              ExchangeRate, GoldPrice, Expense)
    from django.db.models import Max

    wb = Workbook()
    wb.remove(wb.active)

    companies      = list(Company.objects.all().order_by("order"))
    balance_entries = list(BalanceEntry.objects.select_related("currency","bank").all())

    # ── Exchange Rates ───────────────────────────────────────────────────
    ws_ex = wb.create_sheet("Exchange Rates")
    latest_ids = (ExchangeRate.objects.values("currency_code")
                  .annotate(latest=Max("fetched_at")))
    rates_list = []
    for item in latest_ids:
        r = ExchangeRate.objects.filter(
            currency_code=item["currency_code"],
            fetched_at=item["latest"]).first()
        if r:
            rates_list.append(r)
    build_exchange_rates_sheet(ws_ex, rates_list, balance_entries)

    # ── Gold Price ───────────────────────────────────────────────────────
    ws_gold = wb.create_sheet("Gold Price")
    build_gold_price_sheet(ws_gold, GoldPrice.objects, balance_entries)

    # ── Salary sheets — capture summary row per company ──────────────────
    company_sheet_rows = {}   # company.name -> (sheet_name, summary_row)
    for company in companies:
        entries = list(company.salary_entries.all())
        ws_sal = wb.create_sheet(company.name)
        summary_row = build_salary_sheet(ws_sal, company, entries)
        company_sheet_rows[company.name] = (company.name, summary_row)

    # ── Bank Certificates ────────────────────────────────────────────────
    ws_cert = wb.create_sheet("Bank-Certificates")
    build_bank_certificates_sheet(ws_cert, BankCertificate.objects.all())

    # ── BALANCE — uses exact summary rows captured above ─────────────────
    ws_bal = wb.create_sheet("BALANCE")
    build_balance_sheet(ws_bal, balance_entries, company_sheet_rows)

    # ── Expenses (new tab) ───────────────────────────────────────────────
    ws_exp = wb.create_sheet("Expenses")
    build_expenses_sheet(ws_exp, Expense.objects.all())

    if output_path:
        wb.save(output_path)
        return output_path
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf
