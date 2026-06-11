"""
Excel export — regenerates the original Balance.xlsx format from live DB data,
plus a new Expenses tab.
"""
import io
from itertools import groupby
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side, numbers
from openpyxl.utils import get_column_letter


# ── Style helpers ────────────────────────────────────────────────────────────

def _font(bold=False, size=11, color=None, name="Calibri"):
    kw = dict(bold=bold, size=size, name=name)
    if color:
        kw["color"] = color
    return Font(**kw)

def _fill(hex_color):
    return PatternFill("solid", fgColor=hex_color)

def _border(style="thin"):
    s = Side(style=style)
    return Border(left=s, right=s, top=s, bottom=s)

def _align(h="left", v="center", wrap=False):
    return Alignment(horizontal=h, vertical=v, wrap_text=wrap)

GREY_HEADER   = "FF7F7F7F"   # column-label grey
RED_TITLE     = "FFFF0000"   # "Salary Details" red
YEAR_BLUE     = "FF1F3864"   # year heading fill (dark blue)
TOTAL_FILL    = "FFD9E1F2"   # total row light blue
SUMMARY_FILL  = "FFBDD7EE"   # summary/grand-total row
HEADER_FILL   = "FF2F75B6"   # sheet column-header fill (blue)
EXPENSES_HDR  = "FF203864"   # Expenses header fill


# ── Salary sheet builder ─────────────────────────────────────────────────────

MONTH_ORDER = [
    "January","February","March","April","May","June",
    "July","August","September","October","November","December"
]

def _month_sort(m):
    m_str = str(m).strip()
    for i, name in enumerate(MONTH_ORDER):
        if name.lower().startswith(m_str.lower()[:3]):
            return i
    return 99

def build_salary_sheet(ws, company, entries):
    has_bonus = company.name == "Giza Systems (3)"

    # ── Column headers (row 1) ─────────────────────────────────────────────
    headers = ["Year", "Month", "Expected", "Paid (Salary + Bonus)" if has_bonus else "Paid", "Remaining"]
    if has_bonus:
        headers.append("Bonus")

    for col, h in enumerate(headers, 1):
        c = ws.cell(row=1, column=col, value=h)
        c.font = _font(bold=has_bonus, size=11, color=None if has_bonus else GREY_HEADER)
        c.alignment = _align()

    # ── Title row 2 ───────────────────────────────────────────────────────
    ws.cell(row=2, column=1, value=" Salary Details").font = _font(bold=True, size=18, color=RED_TITLE)
    ws.merge_cells(f"A2:{'F' if has_bonus else 'E'}2")

    # ── Data rows ─────────────────────────────────────────────────────────
    row = 4
    total_rows = []

    sorted_entries = sorted(entries, key=lambda e: (e.year, _month_sort(str(e.month))))
    grouped = groupby(sorted_entries, key=lambda e: e.year)

    for year, year_group in grouped:
        year_entries = list(year_group)

        # Year heading
        yc = ws.cell(row=row, column=1, value=str(year))
        yc.font = _font(bold=True, size=18)
        row += 1

        data_start = row
        for entry in year_entries:
            ws.cell(row=row, column=1, value=entry.year)
            ws.cell(row=row, column=2, value=str(entry.month))
            ws.cell(row=row, column=3, value=float(entry.expected))
            ws.cell(row=row, column=4, value=float(entry.paid))
            ws.cell(row=row, column=5, value=f"=IF(D{row}>0,C{row}-D{row},0)")
            if has_bonus:
                ws.cell(row=row, column=6, value=f"=IF(D{row}>C{row},D{row}-C{row},0)")
            row += 1

        data_end = row - 1

        # Total row
        paid_count = sum(1 for e in year_entries if float(e.paid) > 0)
        tc = ws.cell(row=row, column=1, value="Total")
        tc.font = _font(bold=True)
        ws.cell(row=row, column=2, value=f'=COUNTIF(D{data_start}:D{data_end},"<> 0.00")' if has_bonus else paid_count)
        ws.cell(row=row, column=3, value=f"=SUM(C{data_start}:C{data_end})")
        ws.cell(row=row, column=4, value=f"=SUM(D{data_start}:D{data_end})")
        ws.cell(row=row, column=5, value=f"=SUM(E{data_start}:E{data_end})")
        if has_bonus:
            ws.cell(row=row, column=6, value=f"=IF(D{row}>C{row},D{row}-C{row},0)")

        for col in range(1, (7 if has_bonus else 6)):
            ws.cell(row=row, column=col).font = _font(bold=True)
            ws.cell(row=row, column=col).fill = _fill(TOTAL_FILL)

        total_rows.append(row)
        row += 1

    # ── Grand SUMMARY row ────────────────────────────────────────────────
    row += 0  # blank already added by loop end
    sr = row
    ws.cell(row=sr, column=1, value="Total" if has_bonus else "SUMMARY")
    b_refs = "+".join(f"B{r}" for r in total_rows)
    c_refs = "+".join(f"C{r}" for r in total_rows)
    d_refs = "+".join(f"D{r}" for r in total_rows)
    ws.cell(row=sr, column=2, value=f"={b_refs}")
    ws.cell(row=sr, column=3, value=f"={c_refs}")
    ws.cell(row=sr, column=4, value=f"={d_refs}")
    ws.cell(row=sr, column=5, value=f"=D{sr}-C{sr}")
    if has_bonus:
        f_refs = "+".join(f"F{r}" for r in total_rows)
        ws.cell(row=sr, column=6, value=f"={f_refs}")

    for col in range(1, (7 if has_bonus else 6)):
        ws.cell(row=sr, column=col).font = _font(bold=True)
        ws.cell(row=sr, column=col).fill = _fill(SUMMARY_FILL)

    # ── Column widths ─────────────────────────────────────────────────────
    ws.column_dimensions["A"].width = 8
    ws.column_dimensions["B"].width = 15
    ws.column_dimensions["C"].width = 14
    ws.column_dimensions["D"].width = 22 if has_bonus else 14
    ws.column_dimensions["E"].width = 14
    if has_bonus:
        ws.column_dimensions["F"].width = 14


# ── Exchange Rates sheet ─────────────────────────────────────────────────────

CURRENCY_CODES_ORDER = [
    ("USD","US Dollar"),("EUR","Euro"),("GBP","Pound Sterling"),
    ("CAD","Canadian Dollar"),("DKK","Danish Krone"),("NOK","Norwegian Krone"),
    ("SEK","Swedish Krona"),("CHF","Swiss Franc"),("JPY","Japanese Yen"),
    ("SAR","Saudi Riyal"),("KWD","Kuwaiti Dinar"),("AED","UAE Dirham"),
    ("AUD","Australian Dollar"),("BHD","Bahraini Dinar"),("OMR","Omani Riyal"),
    ("QAR","Qatari Riyal"),("JOD","Jordanian Dinar"),("CNY","Chinese Yuan"),
]

ARABIC_NAMES = {
    "USD":"دولار أمريكى","EUR":"يورو","GBP":"جنيــه إسترليـنى",
    "CAD":"دولار كنـدى","DKK":"كرون دانمركى","NOK":"كرون نرويجى",
    "SEK":"كرون ســويدى","CHF":"فرنك سويسرى","JPY":"100 ين يابانى",
    "SAR":"ريـــال سعـــودى","KWD":"دينــار كويتى","AED":"درهم اماراتى",
    "AUD":"دولار اســـترالى","BHD":"دينــار البحــرين","OMR":"ريـــال عمـــانى",
    "QAR":"ريـــال قطــــرى","JOD":"دينـار اردنـى","CNY":"يوان صينى",
}

def build_exchange_rates_sheet(ws, rates_qs, balance_entries):
    # Header
    for col, h in enumerate(["العملة","شراء","بيع"], 1):
        c = ws.cell(row=1, column=col, value=h)
        c.font = _font(bold=True, size=16)

    rate_map = {r.currency_code: r for r in rates_qs}
    usd_row = None
    eur_row = None
    sar_row = None

    for i, (code, _) in enumerate(CURRENCY_CODES_ORDER, 2):
        r = rate_map.get(code)
        name = ARABIC_NAMES.get(code, code)
        ws.cell(row=i, column=1, value=name)
        if r:
            buy = float(r.buy_rate)
            sell = float(r.sell_rate)
            # JPY — original shows per 100 yen
            if code == "JPY":
                buy = round(buy * 100, 4)
                sell = round(sell * 100, 4)
            ws.cell(row=i, column=2, value=buy)
            ws.cell(row=i, column=3, value=sell)
        if code == "USD": usd_row = i
        if code == "EUR": eur_row = i
        if code == "SAR": sar_row = i

    # Side calculations (home currency foreign balance totals) — original columns F-H row 5-6
    # Get home EUR and USD amounts from balance entries
    from core.models import Currency
    try:
        usd_cur = Currency.objects.get(code="USD")
        eur_cur = Currency.objects.get(code="EUR")
        home_usd = sum(float(be.amount) for be in balance_entries if be.bank_id is None and be.currency_id == usd_cur.id)
        home_eur = sum(float(be.amount) for be in balance_entries if be.bank_id is None and be.currency_id == eur_cur.id)
    except Exception:
        home_usd = 0
        home_eur = 0

    ws.cell(row=5, column=6, value=home_eur)
    ws.cell(row=5, column=7, value=home_usd)
    ws.cell(row=5, column=8, value="Total")
    ws.cell(row=6, column=6, value=f"=F5*B{eur_row}")
    ws.cell(row=6, column=7, value=f"=G5*B{usd_row}")
    ws.cell(row=6, column=8, value="=F6+G6")

    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 14
    ws.column_dimensions["C"].width = 14


# ── Gold Price sheet ──────────────────────────────────────────────────────────

def build_gold_price_sheet(ws, gold_qs, balance_entries):
    latest = gold_qs.order_by("-fetched_at").first()

    # Headers (match original column names)
    for col, h in enumerate(["Column1","Column2","Column3","Column4","Column5"], 1):
        ws.cell(row=1, column=col, value=h)

    # Row 2 labels
    ws.cell(row=2, column=1, value="السعر")
    ws.cell(row=2, column=2, value="شراء")
    ws.cell(row=2, column=3, value="بيع")
    ws.cell(row=2, column=4, value="المزيد")

    carats = [
        ("جرام عيار 24 46 ج", "carat_24k_buy", "carat_24k", "46 ج"),
        ("جرام عيار 22 42 ج", "carat_22k_buy", "carat_22k", "42 ج"),
        ("جرام عيار 21 40 ج", "carat_21k_buy", "carat_21k", "40 ج"),
        ("جرام عيار 18 34 ج", "carat_18k_buy", "carat_18k", "34 ج"),
    ]

    for i, (label, buy_field, sell_field, karat_label) in enumerate(carats, 3):
        ws.cell(row=i, column=1, value=label)
        ws.cell(row=i, column=2, value=float(getattr(latest, buy_field, 0)) if latest else 0)
        ws.cell(row=i, column=3, value=float(getattr(latest, sell_field, 0)) if latest else 0)
        ws.cell(row=i, column=4, value=">")
        ws.cell(row=i, column=5, value=karat_label)

    # 14k row (approximate from 18k)
    ws.cell(row=7, column=1, value="جرام عيار 14 27 ج")
    ws.cell(row=7, column=2, value=round(float(latest.carat_18k_buy) * (14/18), 0) if latest else 0)
    ws.cell(row=7, column=3, value=round(float(latest.carat_18k) * (14/18), 0) if latest else 0)
    ws.cell(row=7, column=4, value=">")
    ws.cell(row=7, column=5, value="27 ج")

    # Get gold grams from balance
    from core.models import Currency
    try:
        gold_grams = sum(float(be.amount) for be in balance_entries if be.bank_id is None and be.currency_id == 5)
    except Exception:
        gold_grams = 0

    ws.cell(row=7, column=7, value=f"{gold_grams} Grams")

    # USD/Oz rows
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
    ws.cell(row=9, column=7, value=f"=(C3+28.5)*(BALANCE!F2)")
    ws.cell(row=9, column=8, value=897375)  # historical paid value preserved
    ws.cell(row=9, column=9, value="=G9-H9")

    # Pound of gold
    ws.cell(row=10, column=1, value="الجنيه الذهب 320 ج")
    ws.cell(row=10, column=2, value=float(latest.carat_21k_buy) * 8 if latest else 0)
    ws.cell(row=10, column=3, value=float(latest.carat_21k) * 8 if latest else 0)
    ws.cell(row=10, column=5, value="320 ج")

    ws.column_dimensions["A"].width = 22


# ── Bank Certificates sheet ───────────────────────────────────────────────────

def build_bank_certificates_sheet(ws, certs_qs):
    headers = ["Amount","Interest Rate","Interest Value","Frequency","Start Date","End Date"]
    for col, h in enumerate(headers, 1):
        c = ws.cell(row=1, column=col, value=h)
        c.font = _font(bold=True)
        c.fill = _fill(HEADER_FILL)
        c.font = Font(bold=True, color="FFFFFFFF", name="Calibri")

    for i, cert in enumerate(certs_qs.order_by("issue_date"), 2):
        ws.cell(row=i, column=1, value=float(cert.amount))
        ws.cell(row=i, column=2, value=float(cert.interest_rate))
        ws.cell(row=i, column=3, value=f"=(A{i}*B{i})/12")
        ws.cell(row=i, column=4, value=cert.frequency)
        ws.cell(row=i, column=5, value=cert.issue_date)
        ws.cell(row=i, column=6, value=cert.expiry_date)
        ws.cell(row=i, column=5).number_format = "YYYY-MM-DD"
        ws.cell(row=i, column=6).number_format = "YYYY-MM-DD"
        ws.cell(row=i, column=2).number_format = "0.00%"

    ws.column_dimensions["A"].width = 14
    ws.column_dimensions["B"].width = 15
    ws.column_dimensions["C"].width = 16
    ws.column_dimensions["D"].width = 12
    ws.column_dimensions["E"].width = 14
    ws.column_dimensions["F"].width = 14


# ── BALANCE sheet ─────────────────────────────────────────────────────────────

def build_balance_sheet(ws, balance_entries, companies):
    headers = ["Title","EGP","USD","EUR","SAR","Gold","Acct-Number","Card-ID","Swift-Code","Customer-id","Customer-Name"]
    for col, h in enumerate(headers, 1):
        c = ws.cell(row=1, column=col, value=h)
        c.font = _font(bold=True)
        c.fill = _fill(HEADER_FILL)
        c.font = Font(bold=True, color="FFFFFFFF", name="Calibri")

    # Group balance entries by title
    from core.models import Currency, Bank as BankModel
    try:
        cur_map = {c.id: c.code for c in Currency.objects.all()}
        bank_map = {b.id: b for b in BankModel.objects.all()}
    except Exception:
        cur_map = {}
        bank_map = {}

    # Build structured rows matching original layout
    # Row 2: Home Balance
    home = {cur_map.get(be.currency_id,"?"): float(be.amount)
            for be in balance_entries if be.bank_id is None and be.title == "Home Balance"}

    ws.cell(row=2, column=1, value="Home Balance").font = _font(bold=True)
    ws.cell(row=2, column=2, value=home.get("EGP", 0)).font = _font(bold=True)
    ws.cell(row=2, column=3, value=home.get("USD", 0))
    ws.cell(row=2, column=4, value=home.get("EUR", 0))
    ws.cell(row=2, column=5, value=home.get("SAR", 0))
    ws.cell(row=2, column=6, value=home.get("Gold", 0))  # gold grams (currency code="Gold")

    # Bank rows — group by title
    data_rows = {}
    for be in balance_entries:
        if be.title not in data_rows:
            data_rows[be.title] = {"bank_id": be.bank_id, "amounts": {}}
        data_rows[be.title]["amounts"][cur_map.get(be.currency_id,"?")] = float(be.amount)

    excel_row = 3
    bank_rows = {}  # title -> excel row number
    for title, info in data_rows.items():
        if title == "Home Balance":
            bank_rows[title] = 2
            continue
        if title == "QNB Certificates Balance":
            continue  # added separately as formula row below
        egp_val = info["amounts"].get("EGP", 0)
        r = ws.cell(row=excel_row, column=1, value=title)
        r.font = _font(bold=True)
        v = ws.cell(row=excel_row, column=2, value=egp_val)
        v.font = _font(bold=True)

        bank = bank_map.get(info["bank_id"])
        if bank:
            ws.cell(row=excel_row, column=7, value=getattr(bank, "account_number", "") or "")
            ws.cell(row=excel_row, column=8, value=getattr(bank, "card_number", "") or "")
            ws.cell(row=excel_row, column=9, value=getattr(bank, "swift_code", "") or "")
            ws.cell(row=excel_row, column=10, value=getattr(bank, "customer_id", "") or "")
            ws.cell(row=excel_row, column=11, value=getattr(bank, "customer_name", "") or "")
        bank_rows[title] = excel_row
        excel_row += 1

    # Certs row — formula linking to Bank-Certificates
    cert_row = excel_row
    ws.cell(row=cert_row, column=1, value="QNB Certificates Balance").font = _font(bold=True)
    # Count certs in sheet
    from core.models import BankCertificate
    cert_count = BankCertificate.objects.count()
    cert_end = cert_count + 1  # row 2 to row cert_count+1
    ws.cell(row=cert_row, column=2, value=f"=SUM('Bank-Certificates'!A2:A{cert_end})").font = _font(bold=True)
    excel_row += 1

    # Total EGP
    total_egp_row = excel_row
    ws.cell(row=total_egp_row, column=1, value="Total EGP Balance").font = _font(bold=True)
    ws.cell(row=total_egp_row, column=2, value=f"=SUM(B2:B{cert_row})").font = _font(bold=True)
    excel_row += 1

    # Total all balances — original formula structure
    total_all_row = excel_row
    ws.cell(row=total_all_row, column=1, value="Total all Balances").font = _font(bold=True)
    formula = (
        f"=B{total_egp_row}"
        f"+(C2*('Exchange Rates'!B2))"
        f"+(D2*('Exchange Rates'!B3))"
        f"+(E2*('Exchange Rates'!B11))"
        f"+((F2*('Gold Price'!C3))+28.5)"
    )
    ws.cell(row=total_all_row, column=2, value=formula).font = _font(bold=True)
    excel_row += 1

    # Build company summary references for Total Pays and Total Work Months
    # Map company names to their sheet summary row
    company_refs = {
        "NTG": ("NTG", "D61", "B61"),
        "Giza Systems": ("Giza Systems", "D44", "B44"),
        "Giza Systems (2)": ("Giza Systems (2)", "D63", "B63"),
        "ElSeweedy Technology": ("ElSewedyTechnology", "D16", "B16"),
        "Dedalus": ("Dedalus", "D9", "B9"),
        "Globemed": ("Globemed", "D8", "B8"),
        "Giza Systems (3)": ("Giza Systems (3)", "D70", "B70"),
    }

    # Dynamically build based on actual companies in DB
    pay_parts = []
    month_parts = []
    for c in companies:
        ref = company_refs.get(c.name)
        if ref:
            sheet_name, d_ref, b_ref = ref
            pay_parts.append(f"'{sheet_name}'!{d_ref}" if ' ' in sheet_name else f"{sheet_name}!{d_ref}")
            month_parts.append(f"'{sheet_name}'!{b_ref}" if ' ' in sheet_name else f"{sheet_name}!{b_ref}")

    # Blank spacer rows
    excel_row += 3

    total_pays_row = excel_row
    ws.cell(row=total_pays_row, column=1, value="Total Pays").font = _font(bold=True)
    ws.cell(row=total_pays_row, column=2, value="=" + "+".join(pay_parts) if pay_parts else 0).font = _font(bold=True)
    excel_row += 1

    total_months_row = excel_row
    ws.cell(row=total_months_row, column=1, value="Total Work Months").font = _font(bold=True)
    ws.cell(row=total_months_row, column=2, value="=" + "+".join(month_parts) if month_parts else 0).font = _font(bold=True)

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
    headers = ["Date","Year","Month","Category","Sub-Category","Description","Amount","Currency","Payment Method","Notes"]
    for col, h in enumerate(headers, 1):
        c = ws.cell(row=1, column=col, value=h)
        c.font = Font(bold=True, color="FFFFFFFF", name="Calibri")
        c.fill = _fill(EXPENSES_HDR)
        c.alignment = _align("center")

    # Group by year then month
    from itertools import groupby as gb
    expenses = list(expenses_qs.select_related("category","subcategory","currency").order_by("year","month","date"))

    row = 2
    year_section_rows = {}

    for year, y_group in gb(expenses, key=lambda e: e.year):
        year_entries = list(y_group)
        year_start = row

        for month, m_group in gb(year_entries, key=lambda e: e.month):
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
            # Month total
            ws.cell(row=row, column=3, value=f"{month_name} Total")
            ws.cell(row=row, column=7, value=f"=SUM(G{month_start}:G{month_end})")
            for col in range(1, 11):
                ws.cell(row=row, column=col).font = _font(bold=True)
                ws.cell(row=row, column=col).fill = _fill(TOTAL_FILL)
            row += 1

        year_end = row - 1
        # Year total
        ws.cell(row=row, column=2, value=f"{year} Total")
        ws.cell(row=row, column=7, value=f"=SUMIF(B{year_start}:B{year_end},{year},G{year_start}:G{year_end})")
        for col in range(1, 11):
            ws.cell(row=row, column=col).font = _font(bold=True)
            ws.cell(row=row, column=col).fill = _fill(SUMMARY_FILL)
        year_section_rows[year] = row
        row += 2

    # Grand total
    if year_section_rows:
        grand_refs = "+".join(f"G{r}" for r in year_section_rows.values())
        ws.cell(row=row, column=1, value="Grand Total")
        ws.cell(row=row, column=7, value=f"={grand_refs}")
        for col in range(1, 11):
            ws.cell(row=row, column=col).font = Font(bold=True, color="FFFFFFFF", name="Calibri")
            ws.cell(row=row, column=col).fill = _fill(EXPENSES_HDR)

    # Column widths
    widths = [14, 8, 12, 18, 20, 35, 14, 10, 16, 25]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    # Freeze header row
    ws.freeze_panes = "A2"


# ── Main export function ──────────────────────────────────────────────────────

def generate_excel(output_path=None):
    import django
    from core.models import (Company, SalaryEntry, BalanceEntry,
                              BankCertificate, ExchangeRate, GoldPrice, Expense)

    wb = Workbook()
    wb.remove(wb.active)  # remove default sheet

    companies = list(Company.objects.all().order_by("order"))

    # ── Exchange Rates ──────────────────────────────────────────────────
    ws_ex = wb.create_sheet("Exchange Rates")
    # Get latest rate per currency (SQLite-compatible - no DISTINCT ON)
    from django.db.models import Max
    latest_ids = (ExchangeRate.objects
                  .values("currency_code")
                  .annotate(latest=Max("fetched_at"))
                  .values("currency_code", "latest"))
    rates_list = []
    for item in latest_ids:
        r = ExchangeRate.objects.filter(currency_code=item["currency_code"], fetched_at=item["latest"]).first()
        if r:
            rates_list.append(r)
    rates = rates_list
    balance_entries = list(BalanceEntry.objects.select_related("currency","bank").all())
    build_exchange_rates_sheet(ws_ex, rates, balance_entries)

    # ── Gold Price ──────────────────────────────────────────────────────
    ws_gold = wb.create_sheet("Gold Price")
    build_gold_price_sheet(ws_gold, GoldPrice.objects, balance_entries)

    # ── Salary sheets (one per company) ────────────────────────────────
    for company in companies:
        entries = list(company.salary_entries.all())
        ws_sal = wb.create_sheet(company.name)
        build_salary_sheet(ws_sal, company, entries)

    # ── Bank Certificates ───────────────────────────────────────────────
    ws_cert = wb.create_sheet("Bank-Certificates")
    build_bank_certificates_sheet(ws_cert, BankCertificate.objects.all())

    # ── BALANCE ─────────────────────────────────────────────────────────
    ws_bal = wb.create_sheet("BALANCE")
    build_balance_sheet(ws_bal, balance_entries, companies)

    # ── Expenses (new tab) ───────────────────────────────────────────────
    ws_exp = wb.create_sheet("Expenses")
    build_expenses_sheet(ws_exp, Expense.objects.all())

    if output_path:
        wb.save(output_path)
        return output_path
    else:
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        return buf
