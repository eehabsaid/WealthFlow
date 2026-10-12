"""German -> canonical English routing tokens (see lexicon_fr_de.py). Patterns are written against accent-FOLDED, lowercase
text (ä->a, ö->o, ü->u, ß->ss). PHRASES run first, in order; WORDS is one final pass."""

ACCENTS = "äöüß"
DOMAIN_WORDS = frozenset({
    "ausgaben", "ausgabe", "kontostand", "kontostande", "saldo", "salden", "gehalt", "gehalter", "zertifikat", "zertifikate",
    "anlagevermogen", "wechselkurs", "wechselkurse", "goldpreis", "goldkurs", "konto", "konten", "monat", "monate", "jahr", "jahre",
    "bargeld", "kosten", "rechnungen", "wieviel", "ausgegeben", "guthaben", "dauerauftrage", "festgeld", "zinsen",
    "januar", "februar", "marz", "juni", "juli", "oktober", "dezember", "letzten", "letzte", "goldbestand", "vermogenswerte",
})
POSSESSIVES = frozenset({"mein", "meine", "meiner", "meinen", "meinem", "meines", "dein", "deine", "unser", "unsere"})
EXTRA_DOMAIN = frozenset({"festgeld", "festgelder", "termineinlage", "termineinlagen", "wiederkehrende", "wiederkehrenden", "wiederkehrend",
                          "zahlungen", "geplante", "geplanten", "mittelkurs", "devisenkurse", "devisenkurs", "goldpreise", "goldkurs",
                          "kostet", "aktive", "aktiven", "aktives", "unze", "gramm", "goldbestande", "goldbesitz", "goldunze"})
ENGLISH_CLASH = frozenset({"auto", "limit", "top", "august", "april", "november", "september", "villa", "bonus", "trend"})
FUNCTION_WORDS = frozenset({"der", "die", "das", "dem", "ein", "eine", "einen", "mein", "meine", "meiner", "meinen", "ist", "sind", "wie",
                            "viel", "viele", "welche", "welcher", "fur", "im", "und", "von", "mit", "ich", "habe", "mir", "wann", "nach",
                            "pro", "bis", "zwischen", "dieses", "diesen", "diesem", "auf"})
_M = "januar|februar|marz|april|mai|juni|juli|august|september|oktober|november|dezember|jan|feb|mrz|apr|jun|jul|aug|sep|sept|okt|nov|dez"
_START = r"^\s*(?:bitte )?"

PHRASES = [
    # actions (must start the sentence)
    (_START + r"(?:fuge|fuege|fugen)\b", " add "), (_START + r"(?:erstelle|erstellen|lege|anlegen)\b", " create "),
    (_START + r"(?:losche|loschen|entferne|entfernen)\b", " delete "), (_START + r"(?:andere|andern|bearbeite|bearbeiten)\b", " update "),
    (_START + r"(?:uberweise|uberweisen)\b", " transfer "), (_START + r"(?:zahle|bezahle|zahlen|bezahlen)\b", " pay "),
    (_START + r"(?:erfasse|erfassen|buche|trage)\b", " record "), (_START + r"(?:setze|setzen)\b", " set "),
    # how much / how many
    (r"\bwie ?viele\b", " how many "), (r"\bwie ?viel geld\b", " how much money "), (r"\bwie ?viel gold\b", " how much gold "),
    (r"\bwie ?viel (?:habe|hab|besitze) ich\b(?! .{0,40}(?:ausgegeben|bezahlt|gezahlt|verdient|gekauft))", " how much do i have "),
    (r"\bwie ?viel (?:kostet|kosten) (?:ein|eine|einen|1)? ?", " how much is one "), (r"\bwas (?:kostet|kosten) (?:ein|eine|einen|1)? ?", " how much is one "),
    (r"\bwie ?viel\b", " how much "),
    (r"\b(?:habe|hab) ich\b(?! .{0,40}(?:ausgegeben|bezahlt|gezahlt|verdient|gekauft))", " do i have "), (r"\b(?:besitze|halte) ich\b", " i own "),
    (r"\b(?:habe|hab) ich\b", " i "),
    # ranges and relative periods
    (rf"\b(?:bis|bis zum|bis einschliesslich)\s+(?=(?:{_M})\b)", " to "),
    (r"\b(?:die |in den |den )?(?:letzten|vergangenen|letzte) (\d{1,2}) monat(?:e|en)?\b", r" last \1 months "),
    (r"\b(?:in |im |den )?(?:diesen|diesem|dieser|aktuellen|laufenden) monat\b", " this month "),
    (r"\b(?:im |den |in )?(?:letzten|vorigen|vergangenen|letzter) monat\b|\b(?:im )?vormonat\b", " last month "),
    (r"\b(?:in )?(?:diesem|dieses|laufenden|aktuellen) jahr\b", " this year "),
    (r"\b(?:im |in )?(?:letztes|letzten|vergangenes|vergangenen|vorigen) jahr\b|\b(?:im )?vorjahr\b", " last year "),
    (r"\b(?:letzten|letzte|letzter|neuesten|neueste) (\d{1,3})\b", r" last \1 "), (r"\b(?:heute|jetzt)\b", " today "),
    (r"\b(?:derzeit|momentan|aktuell(?:e[rsmn]?)?)\b", " current "),
    # dimensions
    (r"\b(?:jahrlich\w*|pro jahr|nach jahr(?:en)?|jedes jahr)\b", " per year "), (r"\b(?:monatlich\w*|pro monat|jeden monat|nach monat(?:en)?)\b", " per month "),
    (r"\b(?:taglich\w*|pro tag|jeden tag|nach tag(?:en)?)\b", " per day "), (r"\b(?:nach|pro|je) kategorie\w*", " by category "),
    (r"\b(?:nach|pro|je) wahrung\w*", " by currency "), (r"\b(?:nach|pro|je) (?:art|typ)\b", " by type "),
    (r"\b(?:nach|pro|je) (?:bank|konto)\b", " by account "), (r"\b(?:nach|pro|je) (?:firma|unternehmen|arbeitgeber)\b", " by company "),
    # domain phrases
    (r"\bgold(?:preis|kurs)e?n?\b", " gold price "), (r"\bgoldbestand\w*|\bgoldbesitz\b", " gold holdings "), (r"\bgoldunze\b", " gold ounce "),
    (r"\b(?:wechsel|devisen)kurse?\b", " exchange rate "), (r"\bumrechnungskurs\w*", " conversion rate "), (r"\bmittelkurs\b", " mid rate "),
    (r"\bpfund sterling\b|\bbritische[sn]? pfund\b", " sterling "), (r"\bagyptische[sn]? pfund\b", " egp "),
    (r"\bschweizer franken\b", " chf "), (r"\b(?:festgeld\w*|termineinlage\w*)\b", " fixed deposit "),
    (r"\bwiederkehrende?\w*|\bregelmassige?\w*", " recurring "), (r"\bdauerauftrag\b|\bdauerauftrage\b", " standing orders "),
    (r"\b(?:anstehende|bevorstehende|kommende|fallige)\s+(?:rechnungen|zahlungen)\b", " upcoming bills "),
    (r"\bgehaltsabrechnung\w*|\blohnabrechnung\w*", " payslip "), (r"\blauft\b(?=.{0,30}\bab\b)|\bablauf\b", " matures "),
    (r"\bgeplante[nrsm]? zahlungen\b", " scheduled payments "),
    (r"\bsollte ich\b|\bsoll ich\b", " should i "), (r"\bwie kann ich\b|\bwie konnte ich\b", " how can i "),
    (r"\b(?:zeig|zeige|zeigen)(?: mir)?\b", " show "), (r"\bwas ist mit\b|\bund was ist mit\b", " what about "),
]

WORDS = {
    # compounds (German glues words together; the router sees the English parts)
    "gesamtausgaben": "total expenses", "gesamtkosten": "total expenses", "gesamtsaldo": "total balance", "gesamtguthaben": "total balance",
    "gesamtkapital": "total principal", "gesamtzinsen": "total interest", "gesamtgehalt": "total salary", "gesamtwert": "total value",
    "monatsausgaben": "monthly expenses", "tagesausgaben": "daily expenses", "jahresausgaben": "yearly expenses",
    "monatsgehalt": "monthly salary", "jahresgehalt": "yearly salary", "falligkeitsdaten": "maturity dates", "dollarkurs": "dollar rate",
    "eurokurs": "euro rate", "kaufkurs": "buy rate", "verkaufskurs": "sell rate", "budgetstatus": "budget status", "essensbudget": "food budget",
    "ausgabenlimit": "spending limit", "ausgabenlimits": "spending limits", "nahe": "close to", "verbleibendes": "remaining",
    "aktive": "active", "aktiven": "active", "aktives": "active", "zahlungen": "payments", "zahlung": "payment", "kostet": "costs",
    "verpflichtungen": "commitments", "ubersicht": "summary",
    # months
    "januar": "january", "februar": "february", "marz": "march", "april": "april", "mai": "may", "juni": "june", "juli": "july",
    "august": "august", "september": "september", "oktober": "october", "november": "november", "dezember": "december",
    "mrz": "mar", "okt": "oct", "dez": "dec",
    # expenses
    "ausgaben": "expenses", "ausgabe": "expense", "ausgegeben": "spent", "kosten": "expenses", "einkaufe": "purchases", "einkauf": "purchase",
    "buchungen": "transactions", "buchung": "transaction", "transaktionen": "transactions", "umsatze": "transactions",
    "rechnungen": "bills", "rechnung": "bill",
    # balance
    "kontostand": "balance", "kontostande": "balances", "saldo": "balance", "salden": "balances", "guthaben": "balance",
    "konto": "account", "konten": "accounts", "bankkonto": "bank account", "bankkonten": "bank accounts", "bargeld": "cash",
    "liquide": "liquid", "liquiditat": "liquid", "ersparnisse": "savings", "erspartes": "savings", "geldborse": "wallet",
    "portemonnaie": "wallet",
    # salary
    "gehalt": "salary", "gehalter": "salaries", "lohn": "wages", "lohne": "wages", "bonus": "bonus", "boni": "bonuses",
    "pramie": "bonus", "pramien": "bonuses", "brutto": "gross", "erwartet": "expected", "erwartete": "expected", "erwartetes": "expected",
    # certificates
    "zertifikat": "certificate", "zertifikate": "certificates", "sparzertifikat": "certificate", "sparzertifikate": "certificates",
    "einlage": "deposit", "einlagen": "deposits", "zins": "interest", "zinsen": "interest", "zinszahlung": "interest payment",
    "zinszahlungen": "interest payment", "nachste": "next", "nachsten": "next", "nachster": "next", "nachstes": "next", "wann": "when",
    "falligkeit": "maturity", "fallig": "maturity",
    # budgets / recurring
    "uberschritten": "exceeded", "uberschreitung": "exceeded", "uberzogen": "exceeded", "knapp": "close to", "verbleibend": "remaining",
    "verbleibende": "remaining", "ubrig": "left", "limit": "spending limit", "abonnement": "subscription", "abonnements": "subscriptions",
    "abo": "subscription", "abos": "subscriptions", "lastschrift": "direct debit", "lastschriften": "direct debits",
    # assets
    "anlagevermogen": "fixed assets", "anlagegut": "fixed asset", "anlageguter": "fixed assets", "vermogenswerte": "assets",
    "immobilien": "real estate", "immobilie": "property", "grundstuck": "land", "grundstucke": "land", "fahrzeug": "vehicle",
    "fahrzeuge": "vehicles", "auto": "car", "autos": "cars", "wohnung": "apartment", "wohnungen": "apartments", "haus": "property",
    "hauser": "properties", "villa": "villa",
    # gold / market
    "preis": "price", "kurs": "rate", "kurse": "rates", "unze": "ounce", "unzen": "ounce", "gramm": "gram", "kauf": "buy", "kaufen": "buy",
    "ankauf": "buy", "kaufpreis": "buy price", "verkauf": "sell", "verkaufen": "sell", "verkaufspreis": "sell price", "mittel": "mid",
    # metrics
    "gesamt": "total", "gesamte": "total", "gesamtsumme": "total", "insgesamt": "total", "summe": "total", "durchschnitt": "average",
    "durchschnittlich": "average", "durchschnittliche": "average", "grosste": "biggest", "grossten": "biggest", "hochste": "biggest",
    "hochsten": "biggest", "teuerste": "biggest", "teuersten": "biggest", "top": "top", "liste": "list", "auflisten": "list",
    "anzeigen": "show", "alle": "all", "alles": "all", "details": "details", "detail": "details", "detailliert": "detailed",
    "aufgeschlusselt": "breakdown", "tabelle": "table", "letzte": "last", "letzten": "last", "letzter": "last", "letztes": "last",
    "neueste": "latest", "neuesten": "latest", "aufteilung": "allocation", "verteilung": "allocation",
    # analytic
    "vergleich": "compare", "vergleiche": "compare", "vergleichen": "compare", "trend": "trend", "warum": "why", "weshalb": "why",
    "prognose": "forecast", "vorhersage": "forecast", "wachstum": "growth", "erklare": "explain", "erklaren": "explain",
    "erklarung": "explain", "grund": "reason", "rat": "advice", "empfehlung": "recommend", "empfehle": "recommend",
    "empfehlen": "recommend", "vorschlag": "suggest", "vorschlage": "suggest", "analyse": "analyze", "analysiere": "analyze",
    "verbessern": "improve", "sparen": "save", "reduzieren": "reduce", "senken": "reduce", "szenario": "scenario",
    "simulation": "simulate", "simulieren": "simulate",
    # grammar
    "mein": "my", "meine": "my", "meiner": "my", "meinen": "my", "meinem": "my", "ist": "is", "sind": "are", "der": "the", "die": "the",
    "das": "the", "den": "the", "dem": "the", "des": "the", "ein": "one", "eine": "one", "einen": "one", "und": "and", "von": "from",
    "bis": "to", "zwischen": "between", "im": "in", "fur": "for", "ich": "i", "mir": "me", "mich": "me", "welche": "which",
    "welcher": "which", "was": "what", "wie": "how", "viel": "much", "viele": "many", "wo": "where", "seit": "since", "vor": "before",
    "nach": "after", "dieses": "this", "diesen": "this", "diesem": "this",
}
