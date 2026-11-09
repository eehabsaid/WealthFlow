"""French / German query-side normalisation for the app-knowledge retrieval.

The knowledge chunks (docstrings, page descriptions, data-flow facts) are English. tokenize() splits on every
non-ASCII-letter, so "dépenses" became "d" + "pense" and "Vermögenswerte" lost its umlaut: FR/DE questions matched
nothing. fold() removes accents/umlauts first; foreign_terms() maps everyday FR/DE words (after light suffix
stripping) to the English words the app's own text uses. Query side only - never answers, no LLM, no extra calls.
"""

from __future__ import annotations

import re
import unicodedata

_LATIN_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)
_ASSET = ("asset",)
_PURCHASE_ASSET = ("asset", "purchase")

_FR = {
    "depense": ("expense",), "frais": ("fee", "expense"), "achat": ("purchase", "price"), "achete": ("purchase", "price"),
    "acheter": ("purchase", "price"), "paye": ("payment",), "payer": ("payment",), "paiement": ("payment",),
    "prix": ("price",), "cout": ("cost", "price"), "actif": _ASSET, "immobilisation": _ASSET, "bien": ("asset",),
    "voiture": ("vehicle", "asset"), "vehicule": ("vehicle", "asset"), "immeuble": ("real", "estate", "asset"),
    "appartement": ("real", "estate", "asset"), "maison": ("real", "estate", "asset"), "banque": ("bank",),
    "compte": ("bank", "account"), "solde": ("balance",), "espece": ("cash",), "liquide": ("cash",),
    "salaire": ("salary",), "certificat": ("certificate",), "interet": ("interest",),
    "carte": ("card",), "credit": ("credit",), "enregistrer": ("record",), "saisir": ("record", "add"),
    "ajouter": ("add", "record"), "noter": ("record",), "comptabiliser": ("record", "count"), "vendre": ("sale", "sell"),
    "vente": ("sale", "sell"), "vendu": ("sale", "sell"), "budget": ("budget",), "virement": ("transfer",),
    "patrimoine": ("net", "worth"), "renovation": ("renovation",), "travaux": ("renovation",),
    "meuble": ("furniture",), "mobilier": ("furniture",), "ordinateur": _PURCHASE_ASSET, "portable": _PURCHASE_ASSET,
    "telephone": _PURCHASE_ASSET
}
_DE = {
    "ausgabe": ("expense",), "kosten": ("cost", "price"), "gebuhr": ("fee",), "kauf": ("purchase", "price"),
    "kaufen": ("purchase", "price"), "gekauft": ("purchase", "price"), "bezahlt": ("payment",), "zahlung": ("payment",),
    "bezahlen": ("payment",), "preis": ("price",), "vermogenswert": _ASSET, "anlagegut": _ASSET,
    "anlagevermogen": _ASSET, "anlage": ("asset",), "fahrzeug": ("vehicle", "asset"),
    "immobilie": ("real", "estate", "asset"), "wohnung": ("real", "estate", "asset"), "haus": ("real", "estate", "asset"),
    "bank": ("bank",), "konto": ("bank", "account"), "kontostand": ("balance",), "saldo": ("balance",),
    "bargeld": ("cash",), "gold": ("gold",), "gehalt": ("salary",), "zertifikat": ("certificate",),
    "zins": ("interest",), "zinsen": ("interest",), "karte": ("card",), "kreditkarte": ("credit", "card"),
    "erfassen": ("record",), "eintragen": ("record", "add"), "buchen": ("record",), "verbuchen": ("record",),
    "hinzufugen": ("add", "record"), "verkaufen": ("sale", "sell"), "verkauf": ("sale", "sell"),
    "verkauft": ("sale", "sell"), "budget": ("budget",), "uberweisung": ("transfer",), "nettovermogen": ("net", "worth"),
    "renovierung": ("renovation",), "sanierung": ("renovation",), "mobel": ("furniture",),
    "handy": _PURCHASE_ASSET, "telefon": _PURCHASE_ASSET,
}
_TERMS = {**_DE, **_FR}
_PLURALIZE = frozenset({"expense", "asset", "fee", "payment"})
_DE_COMPOUND_KEYS = tuple(k for k in _DE if len(k) >= 4)  # Kaufpreis = kauf + preis, Nettovermögen, Nettovermögen...
_SUFFIXES = ("ements", "ement", "ations", "ation", "es", "en", "er", "e", "s", "x", "n")


def fold(text: str) -> str:
    """Lower-case Latin text without accents/umlauts (ß -> ss). Arabic and other scripts are left untouched."""
    text = (text or "").replace("ß", "ss").replace("ẞ", "SS")
    out = []
    for ch in unicodedata.normalize("NFKD", text):
        if unicodedata.category(ch) == "Mn" and out and out[-1].isascii():
            continue
        out.append(ch)
    return "".join(out).lower()


def foreign_terms(query: str) -> set[str]:
    """English app words for the French/German words in `query` (empty set for English-only questions)."""
    found: set[str] = set()
    for word in _LATIN_WORD.findall(fold(query)):
        candidates = [word] + [word[: -len(s)] for s in _SUFFIXES if word.endswith(s) and len(word) - len(s) >= 3]
        for cand in candidates:
            if cand in _TERMS:
                found.update(_TERMS[cand])
                break
        else:
            if len(word) >= 8:
                for key in _DE_COMPOUND_KEYS:
                    if key in word:
                        found.update(_DE[key])
    # English questions yield both "expense" and "expenses" (tokenize keeps the plural); the knowledge text uses both.
    return found | {w + "s" for w in found if w in _PLURALIZE}
