import ssl as _ssl
import urllib.request as _ur
import re
from html.parser import HTMLParser

class GoldTableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_table = False
        self.in_tr = False
        self.in_td = False
        self.current_cell = None
        self.current_row = []
        self.rows = []

    def handle_starttag(self, tag, attrs):
        if tag == "table" and not self.in_table:
            self.in_table = True
            return
        if not self.in_table:
            return
        if tag == "tr":
            self.in_tr = True
            self.current_row = []
        elif self.in_tr and tag == "td":
            self.in_td = True
            self.current_cell = {"text": "", "data_val": None}
            attrs = dict(attrs)
            if "data-val" in attrs:
                self.current_cell["data_val"] = attrs["data-val"]

    def handle_data(self, data):
        if self.in_td and self.current_cell is not None:
            self.current_cell["text"] += data

    def handle_endtag(self, tag):
        if tag == "td" and self.in_td:
            self.current_row.append(self.current_cell)
            self.in_td = False
            self.current_cell = None
        elif tag == "tr" and self.in_tr:
            if self.current_row:
                self.rows.append(self.current_row)
            self.in_tr = False
        elif tag == "table" and self.in_table:
            self.in_table = False

def fetch_latest_gold_prices(user_agent: str = "SalaryTracker/1.0") -> dict:
    ctx = _ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = _ssl.CERT_NONE

    page_url = "https://goldbullioneg.com/%D8%A3%D8%B3%D8%B9%D8%A7%D8%B1-%D8%A7%D9%84%D8%B0%D9%87%D8%A8/"
    req = _ur.Request(page_url, headers={"User-Agent": user_agent})
    with _ur.urlopen(req, timeout=15, context=ctx) as resp:
        page_html = resp.read().decode("utf-8", errors="ignore")

    parser = GoldTableParser()
    parser.feed(page_html)

    if not parser.rows or len(parser.rows) < 8:
        raise ValueError("Unable to parse complete gold price table from goldbullioneg.com")

    prices_egp = {}
    usd_to_egp = None
    usd_per_oz = None

    for row in parser.rows:
        if len(row) < 3:
            continue
        label = (row[0].get("text") or "").strip()
        buy_val = (row[1].get("data_val") or row[1].get("text") or "").strip()
        sell_val = (row[2].get("data_val") or row[2].get("text") or "").strip()

        if not buy_val or not sell_val:
            continue

        try:
            buy_num = float(str(buy_val).replace(",", ""))
            sell_num = float(str(sell_val).replace(",", ""))
        except ValueError:
            continue

        karat_match = re.search(r"عيار\s*([0-9]{1,2})", label)
        if karat_match:
            carat = int(karat_match.group(1))
            prices_egp[carat] = {"buy": buy_num, "sell": sell_num}
            continue

        label_lower = label.lower()
        if "دولار" in label_lower:
            usd_to_egp = sell_num
            continue

        if "أونصة" in label_lower or "ounce" in label_lower:
            usd_per_oz = sell_num

    if not all(carat in prices_egp for carat in (24, 22, 21, 18)):
        raise ValueError("Missing required karat prices from goldbullioneg.com")

    if usd_to_egp is None:
        raise ValueError("Could not find USD/EGP rate on goldbullioneg.com")

    if usd_per_oz is None:
        raise ValueError("Could not find USD/oz spot price on goldbullioneg.com")

    return {
        "prices_egp": prices_egp,
        "usd_to_egp": usd_to_egp,
        "usd_per_oz": usd_per_oz,
    }
