"""
Excel export — exact replica of original Balance.xlsx style, populated from live DB.
Every font, border, number format, column width, row height, merge, and freeze pane
is matched to the original file as inspected cell-by-cell.
"""
import io
from itertools import groupby
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# ── Exact formats from original ───────────────────────────────────────────────
FMT_EGP        = '[$ج.م.\u200f-C01]\\ #,##0.00_-'
FMT_EGP_RED    = '[$ج.م.\u200f-C01]\\ #,##0.00;[Red][$ج.م.\u200f-C01]\\ #,##0.00'
FMT_USD        = '"$"#,##0.00;[Red]"$"#,##0.00'
FMT_EUR        = '[$EUR]\\ #,##0.00;[Red][$EUR]\\ #,##0.00'
FMT_SAR        = '[$SAR]\\ #,##0.00;[Red][$SAR]\\ #,##0.00'
FMT_GOLD       = '0\\ "Grams"'
FMT_EGP_CERT   = '[$EGP]\\ #,##0.00'
FMT_EGP_CERT_R = '[$EGP]\\ #,##0.00;[Red][$EGP]\\ #,##0.00'
FMT_PCT        = '0.00%'
FMT_DATE       = '[$-F800]dddd/\\ mmmm\\ dd/\\ yyyy'
FMT_INT        = '0'

GREY   = 'FF7F7F7F'
RED    = 'FFFF0000'
WHITE  = 'FFFFFFFF'
EXP_BG = 'FF203864'
EXP_MONTH_BG = 'FFD9E1F2'
EXP_YEAR_BG  = 'FFBDD7EE'

def _f(bold=False, size=11, color=None, name='Arial'):
    kw = dict(bold=bold, size=size, name=name)
    if color: kw['color'] = color
    return Font(**kw)

def _thin():
    s = Side(style='thin')
    return Border(left=s, right=s, top=s, bottom=s)

def _thin_lr():
    s = Side(style='thin')
    return Border(left=s, right=s)

def _thin_tb():
    s = Side(style='thin')
    return Border(top=s, bottom=s)

def _thin_b():
    return Border(bottom=Side(style='thin'))

def _thin_t():
    return Border(top=Side(style='thin'))

def _fill(hex_color):
    return PatternFill('solid', fgColor=hex_color)

def _align(h='general', v='bottom', wrap=False):
    return Alignment(horizontal=h, vertical=v, wrap_text=wrap)

def _center():
    return Alignment(horizontal='center', vertical='bottom')


# ── Salary sheet ──────────────────────────────────────────────────────────────

MONTH_ORDER = [
    'January','February','March','April','May','June',
    'July','August','September','October','November','December',
    'Quarter-Bonuses',
]

def _msort(m):
    m = str(m).strip()
    for i, n in enumerate(MONTH_ORDER):
        if n.lower().startswith(m.lower()[:3]):
            return i
    return 99

# Column widths per sheet (exact from original)
SALARY_COL_WIDTHS = {
    'NTG':                  {'A':11.0,'B':10.6,'C':20.9,'D':14.6,'E':14.4},
    'Giza Systems':         {'A':13.7,'B':15.3,'C':16.0,'D':15.7,'E':10.1},
    'Giza Systems (2)':     {'A':13.7,'B':15.3,'C':16.0,'D':15.7,'E':14.3},
    'ElSeweedy Technology': {'A':13.7,'B':16.1,'C':16.0,'D':15.7,'E':15.6},
    'Dedalus':              {'A':13.7,'B':16.1,'C':16.0,'D':15.7,'E':15.6},
    'Globemed':             {'A':13.7,'B':16.1,'C':16.0,'D':15.7,'E':15.6},
    'Giza Systems (3)':     {'A':13.7,'B':16.1,'C':16.0,'D':19.3,'E':15.6,'F':14.3},
}

# Row heights for structural rows
SALARY_ROW_HT = {
    1: 14.25,   # col header
    2: 14.25,   # title row (merged with row 3)
    3: 20.25,   # title row part 2
    4: 22.8,    # first year heading (always)
}
YEAR_ROW_HT = 22.8   # all other year heading rows

# Freeze pane per company (original)
SALARY_FREEZE = {
    'NTG':                  'A48',
    'Giza Systems':         'A36',
    'Giza Systems (2)':     'A52',
    'ElSeweedy Technology': 'A2',
    'Dedalus':              'A2',
    'Globemed':             'A2',
    'Giza Systems (3)':     'A2',
}

def _apply_data_row(ws, row, has_bonus=False):
    cols = 6 if has_bonus else 5
    for c in range(1, cols+1):
        cell = ws.cell(row=row, column=c)
        cell.font = _f(name='Arial')
        cell.border = _thin()
        if c in (3, 4, 5):
            cell.number_format = FMT_EGP
        if has_bonus and c == 6:
            cell.number_format = FMT_EGP

def _apply_total_row(ws, row, has_bonus=False):
    cols = 6 if has_bonus else 5
    for c in range(1, cols+1):
        cell = ws.cell(row=row, column=c)
        cell.font = _f(bold=True, name='Arial')
        cell.border = _thin()
        cell.alignment = _center()
        if c in (3, 4):
            cell.number_format = FMT_EGP
        if c == 5:
            cell.number_format = FMT_EGP
        if has_bonus and c == 6:
            cell.number_format = FMT_EGP

def build_salary_sheet(ws, company, entries):
    name = company.name
    has_bonus = (name == 'Giza Systems (3)')
    cols = 6 if has_bonus else 5
    span = f'A:{"F" if has_bonus else "E"}'
    merge_span = f'A2:{"F" if has_bonus else "E"}3'

    # ── Row heights ──
    ws.row_dimensions[1].height = 14.25
    ws.row_dimensions[2].height = 14.25
    ws.row_dimensions[3].height = 20.25
    ws.row_dimensions[4].height = 22.8

    # ── Column widths ──
    widths = SALARY_COL_WIDTHS.get(name, {'A':13.7,'B':15.3,'C':16.0,'D':15.7,'E':14.3})
    for col, w in widths.items():
        ws.column_dimensions[col].width = w

    # ── Freeze pane ──
    fp = SALARY_FREEZE.get(name)
    if fp:
        ws.freeze_panes = fp

    # ── Row 1: column headers ──
    hdrs = ['Year','Month','Expected','Paid (Salary + Bonus)' if has_bonus else 'Paid','Remaining']
    if has_bonus: hdrs.append('Bonus')
    for c, h in enumerate(hdrs, 1):
        cell = ws.cell(row=1, column=c, value=h)
        cell.font = _f(bold=has_bonus, color=None if has_bonus else GREY, name='Arial')
        cell.border = _thin()
        cell.alignment = _center()

    # ── Rows 2-3: " Salary Details" merged ──
    ws.merge_cells(merge_span)
    c2 = ws.cell(row=2, column=1, value=' Salary Details')
    c2.font = _f(bold=True, size=18, color=RED, name='Times New Roman')
    c2.alignment = _center()
    c2.border = Border(bottom=Side(style='thin')) if not has_bonus else Border(top=Side(style='thin'))

    # ── Data ──
    row = 4
    total_rows = []
    sorted_entries = sorted(entries, key=lambda e: (e.year, _msort(str(e.month))))

    year_rows = []  # track year heading rows for height setting
    for year, ygrp in groupby(sorted_entries, key=lambda e: e.year):
        year_entries = list(ygrp)

        # Year heading row — merged, bold sz18, Times New Roman, borders t+b
        yr_row = row
        year_rows.append(yr_row)
        ws.row_dimensions[yr_row].height = YEAR_ROW_HT
        yr_merge = f'A{yr_row}:{"F" if has_bonus else "E"}{yr_row}'
        try:
            ws.merge_cells(yr_merge)
        except Exception:
            pass  # already merged
        yc = ws.cell(row=yr_row, column=1, value=str(year))
        yc.font = _f(bold=True, size=18, name='Times New Roman')
        yc.alignment = _center()
        # GS3 year rows have NO border (original), others have t+b thin
        if not has_bonus:
            yc.border = Border(top=Side(style='thin'), bottom=Side(style='thin'))
        row += 1

        data_start = row
        for entry in year_entries:
            ws.cell(row=row, column=1, value=entry.year)
            ws.cell(row=row, column=2, value=str(entry.month))
            ws.cell(row=row, column=3, value=float(entry.expected))
            ws.cell(row=row, column=4, value=float(entry.paid))
            # Remaining formula varies by sheet (exact from original)
            if name in ('NTG', 'Giza Systems', 'Giza Systems (2)'):
                rem = f'=D{row}-C{row}'
            elif name == 'Giza Systems (3)':
                rem = f'=IF(C{row}>D{row},C{row}-D{row},0)'
            else:
                rem = f'=IF(C{row}>D{row},C{row}-D{row},0)'
            ws.cell(row=row, column=5, value=rem)
            if has_bonus:
                ws.cell(row=row, column=6, value=float(getattr(entry, 'bonus', 0) or 0))
            _apply_data_row(ws, row, has_bonus)
            row += 1

        data_end = row - 1

        # Total row
        paid_count = sum(1 for e in year_entries if float(e.paid) > 0)
        ws.cell(row=row, column=1, value='Total')
        # B col: NTG first year uses plain count; others use COUNTIF on D col
        if name == 'NTG' and len(total_rows) == 0:
            ws.cell(row=row, column=2, value=paid_count)
        else:
            ws.cell(row=row, column=2,
                    value=f'=COUNTIF(D{data_start}:D{data_end}, "<> 0.00")')
        ws.cell(row=row, column=3, value=f'=SUM(C{data_start}:C{data_end})')
        ws.cell(row=row, column=4, value=f'=SUM(D{data_start}:D{data_end})')
        # E col formula varies
        if name == 'NTG':
            ws.cell(row=row, column=5, value=f'=D{row}-C{row}')
        else:
            ws.cell(row=row, column=5, value=f'=SUM(E{data_start}:E{data_end})')
        # E col on total row: not bold, no alignment (original)
        # (applied again after _apply_total_row below)
        if has_bonus:
            ws.cell(row=row, column=6, value=f'=IF(D{row}>C{row},D{row}-C{row},0)')
        _apply_total_row(ws, row, has_bonus)
        # E col: not bold, no alignment override (original)
        ws.cell(row=row, column=5).font = _f(bold=False, name='Arial')
        ws.cell(row=row, column=5).alignment = Alignment()
        # B col integer format
        ws.cell(row=row, column=2).number_format = 'General'
        total_rows.append(row)
        row += 1

    # Grand summary row
    sr = row
    # Label
    if name == 'NTG':
        label = 'SUMMARY'
    elif name in ('Giza Systems', 'Giza Systems (2)'):
        label = 'Summary' if name == 'Giza Systems' else 'Total'
    else:
        label = 'Total'

    ws.cell(row=sr, column=1, value=label)
    b_ref = '+'.join(f'B{r}' for r in total_rows)
    ws.cell(row=sr, column=2, value=f'={b_ref}')
    ws.cell(row=sr, column=2).number_format = FMT_INT
    c_ref = '+'.join(f'C{r}' for r in total_rows)
    ws.cell(row=sr, column=3, value=f'={c_ref}')
    ws.cell(row=sr, column=3).number_format = FMT_EGP
    # NTG SUMMARY C col skips first total (original: =C23+C37+C51+C60)
    if name == 'NTG':
        c_ref2 = '+'.join(f'C{r}' for r in total_rows[1:])
        ws.cell(row=sr, column=3, value=f'={c_ref2}')
        d_ref2 = '+'.join(f'D{r}' for r in total_rows[1:])
        ws.cell(row=sr, column=4, value=f'={d_ref2}')
    else:
        d_ref = '+'.join(f'D{r}' for r in total_rows)
        ws.cell(row=sr, column=4, value=f'={d_ref}')
    ws.cell(row=sr, column=4).number_format = FMT_EGP
    ws.cell(row=sr, column=5, value=f'=D{sr}-C{sr}')
    ws.cell(row=sr, column=5).number_format = FMT_EGP
    if has_bonus:
        f_ref = '+'.join(f'F{r}' for r in total_rows)
        ws.cell(row=sr, column=6, value=f'={f_ref}')
        ws.cell(row=sr, column=6).number_format = FMT_EGP

    for c in range(1, cols+1):
        cell = ws.cell(row=sr, column=c)
        cell.font = _f(bold=True, name='Arial')
        cell.border = _thin()
        cell.alignment = _center()

    # Single-company sheets (Dedalus, Globemed, ElSeweedy) have an extra
    # "Total" row that mirrors the inner total (original pattern)
    if name in ('ElSeweedy Technology', 'Dedalus', 'Globemed'):
        tr = total_rows[0]
        er = sr
        ws.cell(row=er, column=1, value='Total')
        ws.cell(row=er, column=2, value=f'=B{tr}')
        ws.cell(row=er, column=2).number_format = FMT_INT
        ws.cell(row=er, column=3, value=f'=C{tr}')
        ws.cell(row=er, column=3).number_format = FMT_EGP
        ws.cell(row=er, column=4, value=f'=D{tr}')
        ws.cell(row=er, column=4).number_format = FMT_EGP
        ws.cell(row=er, column=5, value=f'=E{tr}')
        ws.cell(row=er, column=5).number_format = FMT_EGP
        # blank merged row above
        mrow = er - 1
        ws.merge_cells(f'A{mrow}:{"F" if has_bonus else "E"}{mrow}')
        ws.merge_cells(f'A{er}:{"F" if has_bonus else "E"}{er+1}' if False else f'A{er}:{"F" if has_bonus else "E"}{er}')
        for c in range(1, cols+1):
            cell = ws.cell(row=er, column=c)
            cell.font = _f(bold=True, name='Arial')
            cell.border = _thin()
            cell.alignment = _center()

    ws.row_dimensions[sr].height = 21.0 if name == 'NTG' else None

    return sr


# ── Exchange Rates ────────────────────────────────────────────────────────────

CURRENCIES = [
    ('USD','دولار أمريكى'),('EUR','يورو'),('GBP','جنيــه إسترليـنى'),
    ('CAD','دولار كنـدى'),('DKK','كرون دانمركى'),('NOK','كرون نرويجى'),
    ('SEK','كرون ســويدى'),('CHF','فرنك سويسرى'),('JPY','100 ين يابانى'),
    ('SAR','ريـــال سعـــودى'),('KWD','دينــار كويتى'),('AED','درهم اماراتى'),
    ('AUD','دولار اســـترالى'),('BHD','دينــار البحــرين'),('OMR','ريـــال عمـــانى'),
    ('QAR','ريـــال قطــــرى'),('JOD','دينـار اردنـى'),('CNY','يوان صينى'),
]

def build_exchange_rates_sheet(ws, rates_list, balance_entries):
    ws.column_dimensions['A'].width = 10.6
    ws.column_dimensions['B'].width = 9.8
    ws.column_dimensions['C'].width = 8.9
    ws.column_dimensions['F'].width = 14.3
    ws.column_dimensions['G'].width = 15.8
    ws.row_dimensions[1].height = 21.0

    for c, h in enumerate(['العملة','شراء','بيع'], 1):
        cell = ws.cell(row=1, column=c, value=h)
        cell.font = _f(bold=True, size=16, name='Arial')
        cell.alignment = _center()

    rate_map = {r.currency_code: r for r in rates_list}
    eur_row = None

    for i, (code, arabic) in enumerate(CURRENCIES, 2):
        r = rate_map.get(code)
        ws.cell(row=i, column=1, value=arabic).font = _f(name='Arial')
        if r:
            buy  = float(r.buy_rate)
            sell = float(r.sell_rate)
            if code == 'JPY':
                buy  = round(buy  * 100, 4)
                sell = round(sell * 100, 4)
            ws.cell(row=i, column=2, value=buy).font  = _f(name='Arial')
            ws.cell(row=i, column=3, value=sell).font = _f(name='Arial')
        if code == 'EUR': eur_row = i

    # Side block (original cols F-H rows 5-6)
    from core.models import Currency
    try:
        usd_cur = Currency.objects.get(code='USD')
        eur_cur = Currency.objects.get(code='EUR')
        home_usd = sum(float(be.amount) for be in balance_entries
                       if be.bank_id is None and be.currency_id == usd_cur.id)
        home_eur = sum(float(be.amount) for be in balance_entries
                       if be.bank_id is None and be.currency_id == eur_cur.id)
    except Exception:
        home_usd = home_eur = 0

    ws.cell(row=5, column=6, value=home_eur).font = _f(name='Arial')
    ws.cell(row=5, column=7, value=home_usd).font = _f(name='Arial')
    ws.cell(row=5, column=8, value='Total').font   = _f(name='Arial')
    ws.cell(row=6, column=6, value=f'=F5*B{eur_row}').font = _f(name='Arial')
    ws.cell(row=6, column=7, value='=G5*B2').font          = _f(name='Arial')
    ws.cell(row=6, column=8, value='=F6+G6').font          = _f(name='Arial')


# ── Gold Price ────────────────────────────────────────────────────────────────

def build_gold_price_sheet(ws, gold_qs, balance_entries):
    ws.column_dimensions['A'].width = 18.6
    ws.column_dimensions['B'].width = 10.7
    ws.column_dimensions['C'].width = 10.7
    ws.column_dimensions['F'].width = 32.7
    ws.column_dimensions['G'].width = 15.8
    ws.column_dimensions['H'].width = 14.3

    latest = gold_qs.order_by('-fetched_at').first()

    for c, h in enumerate(['Column1','Column2','Column3','Column4','Column5'], 1):
        ws.cell(row=1, column=c, value=h).font = _f(name='Arial')

    ws.cell(row=2, column=1, value='السعر').font     = _f(name='Arial')
    ws.cell(row=2, column=2, value='شراء').font      = _f(name='Arial')
    ws.cell(row=2, column=3, value='بيع').font       = _f(name='Arial')
    ws.cell(row=2, column=4, value='المزيد').font    = _f(name='Arial')

    carats = [
        ('جرام عيار 24 40 ج','carat_24k_buy','carat_24k','40 ج'),
        ('جرام عيار 22 37 ج','carat_22k_buy','carat_22k','37 ج'),
        ('جرام عيار 21 35 ج','carat_21k_buy','carat_21k','35 ج'),
        ('جرام عيار 18 30 ج','carat_18k_buy','carat_18k','30 ج'),
    ]
    for i,(label,bf,sf,karat) in enumerate(carats, 3):
        ws.cell(row=i,column=1,value=label).font = _f(name='Arial')
        ws.cell(row=i,column=2,value=round(float(getattr(latest,bf,0)),0) if latest else 0).font = _f(name='Arial')
        ws.cell(row=i,column=3,value=round(float(getattr(latest,sf,0)),0) if latest else 0).font = _f(name='Arial')
        ws.cell(row=i,column=4,value='>').font = _f(name='Arial')
        ws.cell(row=i,column=5,value=karat).font = _f(name='Arial')

    ws.cell(row=7,column=1,value='جرام عيار 14 27 ج').font = _f(name='Arial')
    ws.cell(row=7,column=2,value=round(float(latest.carat_18k_buy)*(14/18),0) if latest else 0).font = _f(name='Arial')
    ws.cell(row=7,column=3,value=round(float(latest.carat_18k)*(14/18),0) if latest else 0).font     = _f(name='Arial')
    ws.cell(row=7,column=4,value='>').font = _f(name='Arial')
    ws.cell(row=7,column=5,value='27 ج').font = _f(name='Arial')

    # Gold grams + merge G7:I7
    from core.models import Currency
    try:
        gold_cur = Currency.objects.get(code='Gold')
        grams = sum(float(be.amount) for be in balance_entries
                    if be.bank_id is None and be.currency_id == gold_cur.id)
    except Exception:
        grams = 0
    ws.merge_cells('G7:I7')
    ws.cell(row=7,column=7,value=f'{int(grams)} Grams').font = _f(name='Arial')

    ws.cell(row=8,column=1,value='الدولار 0 ج').font = _f(name='Arial')
    ws.cell(row=8,column=2,value=float(latest.usd_to_egp) if latest else 0).font = _f(name='Arial')
    ws.cell(row=8,column=3,value=float(latest.usd_to_egp) if latest else 0).font = _f(name='Arial')
    ws.cell(row=8,column=5,value='0 ج').font = _f(name='Arial')
    ws.cell(row=8,column=7,value='Now').font  = _f(name='Arial')
    ws.cell(row=8,column=8,value='Paid').font = _f(name='Arial')
    ws.cell(row=8,column=9,value='Diff').font = _f(name='Arial')

    ws.cell(row=9,column=1,value='الأونصة 0 $').font = _f(name='Arial')
    ws.cell(row=9,column=2,value=float(latest.usd_per_oz) if latest else 0).font = _f(name='Arial')
    ws.cell(row=9,column=3,value=float(latest.usd_per_oz) if latest else 0).font = _f(name='Arial')
    ws.cell(row=9,column=5,value='0 $').font = _f(name='Arial')
    ws.cell(row=9,column=7,value='=(C3+28.5)*(BALANCE!F2)').font = _f(name='Arial')
    ws.cell(row=9,column=8,value=897375).font = _f(name='Arial')
    ws.cell(row=9,column=9,value='=G9-H9').font = _f(name='Arial')

    ws.cell(row=10,column=1,value='الجنيه الذهب 320 ج').font = _f(name='Arial')
    ws.cell(row=10,column=2,value=round(float(latest.carat_21k_buy)*8,0) if latest else 0).font = _f(name='Arial')
    ws.cell(row=10,column=3,value=round(float(latest.carat_21k)*8,0) if latest else 0).font     = _f(name='Arial')
    ws.cell(row=10,column=5,value='320 ج').font = _f(name='Arial')


# ── Bank-Certificates ─────────────────────────────────────────────────────────

def build_bank_certificates_sheet(ws, certs_qs):
    ws.column_dimensions['A'].width = 15.2
    ws.column_dimensions['B'].width = 15.7
    ws.column_dimensions['C'].width = 16.4
    ws.column_dimensions['D'].width = 14.3
    ws.column_dimensions['E'].width = 26.6
    ws.column_dimensions['F'].width = 29.5
    ws.row_dimensions[1].height = 27.6

    hdrs = [('Amount',FMT_EGP_CERT),('Interest Rate',FMT_PCT),
            ('Interest Value',FMT_EGP_CERT_R),('Frequency',None),
            ('Start Date',FMT_DATE),('End Date',FMT_DATE)]
    for c,(h,fmt) in enumerate(hdrs, 1):
        cell = ws.cell(row=1, column=c, value=h)
        cell.font = _f(name='Arial')
        if fmt: cell.number_format = fmt

    for i, cert in enumerate(certs_qs.order_by('issue_date'), 2):
        ws.cell(row=i,column=1,value=float(cert.amount)).number_format = FMT_EGP_CERT
        ws.cell(row=i,column=2,value=float(cert.interest_rate)).number_format = FMT_PCT
        ws.cell(row=i,column=3,value=f'=(A{i}*B{i})/12').number_format = FMT_EGP_CERT_R
        ws.cell(row=i,column=4,value=cert.frequency)
        ws.cell(row=i,column=5,value=cert.issue_date).number_format = FMT_DATE
        ws.cell(row=i,column=6,value=cert.expiry_date).number_format = FMT_DATE
        for c in range(1,7):
            ws.cell(row=i,column=c).font = _f(name='Arial')


# ── BALANCE ───────────────────────────────────────────────────────────────────

def build_balance_sheet(ws, balance_entries, company_sheet_rows):
    ws.column_dimensions['A'].width = 26.5
    ws.column_dimensions['B'].width = 14.6
    ws.column_dimensions['C'].width = 12.5
    ws.column_dimensions['D'].width = 13.1
    ws.column_dimensions['F'].width = 11.0
    ws.column_dimensions['G'].width = 14.4
    ws.column_dimensions['H'].width = 17.1
    ws.column_dimensions['I'].width = 12.7
    ws.column_dimensions['J'].width = 12.0
    ws.column_dimensions['K'].width = 29.7
    ws.row_dimensions[7].height = 18.0

    # Row 1 headers — bold, Arial, borders
    hdrs = ['Title','EGP','USD','EUR','SAR','Gold',
            'Acct-Number','Card-ID','Swift-Code','Customer-id','Customer-Name']
    border_map = {
        1:_thin(), 2:_thin(), 3:_thin(),
        4:_thin_lr(), 5:_thin_lr(), 6:_thin_lr(), 7:_thin_lr(), 8:_thin_lr(),
        9:_thin(), 10:_thin(), 11:_thin()
    }
    for c, h in enumerate(hdrs, 1):
        cell = ws.cell(row=1, column=c, value=h)
        cell.font = _f(bold=True, name='Arial')
        cell.border = border_map.get(c, _thin())

    from core.models import Currency, Bank as BankModel
    cur_map  = {c.id: c.code for c in Currency.objects.all()}
    bank_map = {b.id: b for b in BankModel.objects.all()}

    # Row 2: Home Balance
    home = {cur_map.get(be.currency_id,'?'): float(be.amount)
            for be in balance_entries if be.bank_id is None and be.title == 'Home Balance'}

    ws.cell(row=2,column=1,value='Home Balance').font    = _f(bold=True, name='Arial')
    ws.cell(row=2,column=1).border = _thin()
    b2 = ws.cell(row=2,column=2,value=home.get('EGP',0))
    b2.font = _f(bold=True, name='Arial'); b2.border = _thin()
    b2.number_format = FMT_EGP_RED
    c2 = ws.cell(row=2,column=3,value=home.get('USD',0))
    c2.border=_thin(); c2.number_format=FMT_USD; c2.font=_f(name='Arial')
    d2 = ws.cell(row=2,column=4,value=home.get('EUR',0))
    d2.border=_thin(); d2.number_format=FMT_EUR; d2.font=_f(name='Arial')
    e2 = ws.cell(row=2,column=5,value=home.get('SAR',0))
    e2.border=_thin(); e2.number_format=FMT_SAR; e2.font=_f(name='Arial')
    f2 = ws.cell(row=2,column=6,value=home.get('Gold',0))
    f2.border=_thin(); f2.number_format=FMT_GOLD; f2.font=_f(name='Arial')

    # Bank rows
    excel_row = 3
    for be in sorted(balance_entries, key=lambda b: b.id):
        if be.title in ('Home Balance','QNB Certificates Balance'):
            continue
        if cur_map.get(be.currency_id) != 'EGP':
            continue

        a = ws.cell(row=excel_row,column=1,value=be.title)
        a.font=_f(bold=True,name='Arial'); a.border=_thin()
        b = ws.cell(row=excel_row,column=2,value=float(be.amount))
        b.font=_f(bold=True,name='Arial'); b.border=_thin()
        b.number_format = FMT_EGP_RED

        bank = bank_map.get(be.bank_id)
        if bank:
            for col, attr in [(7,'account_number'),(8,'card_number'),(9,'swift_code'),(10,'customer_id'),(11,'customer_name')]:
                v = getattr(bank, attr, '') or ''
                cell = ws.cell(row=excel_row, column=col, value=v)
                cell.font = _f(bold=True, name='Arial')
                cell.border = _thin()
                if col in (7,8): cell.number_format = FMT_INT
        excel_row += 1

    # QNB Certificates formula row
    from core.models import BankCertificate
    cert_count = BankCertificate.objects.count()
    cr = excel_row
    ws.cell(row=cr,column=1,value='QNB Certificates Balance').font = _f(bold=True,name='Arial')
    ws.cell(row=cr,column=1).border = _thin()
    bc = ws.cell(row=cr,column=2,value=f"=SUM('Bank-Certificates'!A2:A{cert_count+1})")
    bc.font=_f(bold=True,name='Arial'); bc.border=_thin()
    bc.number_format = FMT_EGP_RED
    excel_row += 1

    # Total EGP
    ter = excel_row
    ws.cell(row=ter,column=1,value='Total EGP Balance').font = _f(bold=True,name='Arial')
    ws.cell(row=ter,column=1).border = _thin()
    te = ws.cell(row=ter,column=2,value=f'=SUM(B2:B{cr})')
    te.font=_f(bold=True,name='Arial'); te.border=_thin()
    te.number_format = FMT_EGP_RED
    excel_row += 1

    # Total all Balances — merged B:F, row height 18
    tar = excel_row
    ws.row_dimensions[tar].height = 18.0
    ws.merge_cells(f'B{tar}:F{tar}')
    ws.cell(row=tar,column=1,value='Total all Balances').font = _f(bold=True,name='Arial')
    ws.cell(row=tar,column=1).border = _thin()
    formula = (f"=B{ter}"
               f"+(C2*('Exchange Rates'!B2))"
               f"+(D2*('Exchange Rates'!B3))"
               f"+(E2*('Exchange Rates'!B11))"
               f"+((F2*('Gold Price'!C3))+28.5)")
    ta = ws.cell(row=tar,column=2,value=formula)
    ta.font=_f(bold=True,name='Arial'); ta.border=_thin()
    ta.number_format = FMT_EGP_RED
    excel_row += 1

    # Spacer rows then Total Pays / Total Work Months
    tpr = excel_row + 3
    tmr = tpr + 1

    pay_parts, month_parts = [], []
    for cname, (sname, srow) in company_sheet_rows.items():
        ref = f"'{sname}'!{{c}}{srow}" if ' ' in sname else f"{sname}!{{c}}{srow}"
        pay_parts.append(ref.format(c='D'))
        month_parts.append(ref.format(c='B'))

    ws.cell(row=tpr,column=1,value='Total Pays').font = _f(bold=True,name='Arial')
    tp = ws.cell(row=tpr,column=2,value='='+'+'.join(pay_parts) if pay_parts else 0)
    tp.font=_f(bold=True,name='Arial'); tp.number_format=FMT_EGP_RED

    ws.cell(row=tmr,column=1,value='Total Work Months').font = _f(bold=True,name='Arial')
    tm = ws.cell(row=tmr,column=2,value='='+'+'.join(month_parts) if month_parts else 0)
    tm.font=_f(bold=True,name='Arial')


# ── Expenses (new) ────────────────────────────────────────────────────────────

def build_expenses_sheet(ws, expenses_qs):
    hdrs = ['Date','Year','Month','Category','Sub-Category',
            'Description','Amount','Currency','Payment Method','Notes']
    for c, h in enumerate(hdrs, 1):
        cell = ws.cell(row=1, column=c, value=h)
        cell.font = Font(bold=True, color=WHITE, name='Arial')
        cell.fill = _fill(EXP_BG)
        cell.alignment = _center()
    widths = [14,8,12,18,20,35,14,10,16,25]
    for i,w in enumerate(widths,1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = 'A2'

    expenses = list(expenses_qs.select_related('category','subcategory','currency')
                    .order_by('year','month','date'))
    row = 2
    year_total_rows = {}

    for year, yg in groupby(expenses, key=lambda e: e.year):
        year_entries = list(yg)
        year_start = row
        for month, mg in groupby(year_entries, key=lambda e: e.month):
            month_entries = list(mg)
            mname = MONTH_ORDER[month-1] if 1<=month<=12 else str(month)
            mstart = row
            for exp in month_entries:
                ws.cell(row=row,column=1,value=exp.date).number_format='YYYY-MM-DD'
                ws.cell(row=row,column=2,value=exp.year)
                ws.cell(row=row,column=3,value=mname)
                ws.cell(row=row,column=4,value=exp.category.name if exp.category else '')
                ws.cell(row=row,column=5,value=exp.subcategory.name if exp.subcategory else '')
                ws.cell(row=row,column=6,value=exp.description or '')
                ws.cell(row=row,column=7,value=float(exp.amount)).number_format=FMT_EGP_CERT
                ws.cell(row=row,column=8,value=exp.currency.code if exp.currency else 'EGP')
                ws.cell(row=row,column=9,value=exp.payment_method or '')
                ws.cell(row=row,column=10,value=exp.notes or '')
                row += 1
            mend = row-1
            ws.cell(row=row,column=3,value=f'{mname} Total')
            ws.cell(row=row,column=7,value=f'=SUM(G{mstart}:G{mend})')
            for c in range(1,11):
                ws.cell(row=row,column=c).font=_f(bold=True,name='Arial')
                ws.cell(row=row,column=c).fill=_fill(EXP_MONTH_BG)
            row += 1
        year_end = row-1
        ws.cell(row=row,column=2,value=f'{year} Total')
        ws.cell(row=row,column=7,
                value=f'=SUMIF(B{year_start}:B{year_end},{year},G{year_start}:G{year_end})')
        for c in range(1,11):
            ws.cell(row=row,column=c).font=_f(bold=True,name='Arial')
            ws.cell(row=row,column=c).fill=_fill(EXP_YEAR_BG)
        year_total_rows[year] = row
        row += 2

    if year_total_rows:
        grand = '+'.join(f'G{r}' for r in year_total_rows.values())
        ws.cell(row=row,column=1,value='Grand Total')
        ws.cell(row=row,column=7,value=f'={grand}')
        for c in range(1,11):
            ws.cell(row=row,column=c).font=Font(bold=True,color=WHITE,name='Arial')
            ws.cell(row=row,column=c).fill=_fill(EXP_BG)


# ── Main ──────────────────────────────────────────────────────────────────────

def generate_excel(output_path=None):
    from core.models import (Company, BalanceEntry, BankCertificate,
                              ExchangeRate, GoldPrice, Expense)
    from django.db.models import Max

    wb = Workbook()
    wb.remove(wb.active)

    companies       = list(Company.objects.all().order_by('order'))
    balance_entries = list(BalanceEntry.objects.select_related('currency','bank').all())

    # Exchange Rates
    ws_ex = wb.create_sheet('Exchange Rates')
    latest_ids = ExchangeRate.objects.values('currency_code').annotate(latest=Max('fetched_at'))
    rates = []
    for item in latest_ids:
        r = ExchangeRate.objects.filter(currency_code=item['currency_code'],
                                        fetched_at=item['latest']).first()
        if r: rates.append(r)
    build_exchange_rates_sheet(ws_ex, rates, balance_entries)

    # Gold Price
    ws_gold = wb.create_sheet('Gold Price')
    build_gold_price_sheet(ws_gold, GoldPrice.objects, balance_entries)

    # Salary sheets — capture summary rows
    company_sheet_rows = {}
    for company in companies:
        entries = list(company.salary_entries.all())
        ws_sal = wb.create_sheet(company.name)
        sr = build_salary_sheet(ws_sal, company, entries)
        # For single-company sheets the BALANCE references the outer Total row
        if company.name in ('ElSeweedy Technology','Dedalus','Globemed'):
            company_sheet_rows[company.name] = (company.name, sr)
        else:
            company_sheet_rows[company.name] = (company.name, sr)

    # Bank-Certificates
    ws_cert = wb.create_sheet('Bank-Certificates')
    build_bank_certificates_sheet(ws_cert, BankCertificate.objects.all())

    # BALANCE
    ws_bal = wb.create_sheet('BALANCE')
    build_balance_sheet(ws_bal, balance_entries, company_sheet_rows)

    # Expenses
    ws_exp = wb.create_sheet('Expenses')
    build_expenses_sheet(ws_exp, Expense.objects.all())

    if output_path:
        wb.save(output_path)
        return output_path
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf
