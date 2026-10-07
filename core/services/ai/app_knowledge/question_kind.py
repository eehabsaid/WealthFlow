"""Is this a how / where / should question about using the app (vs a lookup of the user's numbers)?
Deterministic and cheap (runs on every chat turn, after the query engine declined the question)."""

from __future__ import annotations

import re

_FLAGS = re.I
_PATTERNS = tuple(re.compile(p, _FLAGS) for p in (
    r"\b(where|how)\b.{0,70}\b(record|enter|add|log|track|put|store|register|save|book|count|treat|categori[sz]e|classif\w*|do i|should i|can i)\b",
    r"\bshould (i|we)\b",
    r"\bwhich (one|page|tab|place|section|screen|option)\b.{0,40}\b(use|record|enter|add|put|go)\b",
    r"\b(in|under|as|on)\s+(the\s+|an?\s+)?[\w\s]{2,24}?,?\s+or\s+(in|under|as|on)\b",
    r"\b(what('s| is) the (right|best|correct|proper) (way|place)|is it (right|ok|okay|better)|would it be)\b",
    r"\bif i (bought|buy|sold|sell|paid|pay|received|get|got|lent|borrowed)\b",
    r"(أين|اين|كيف)\s.{0,60}(أسجل|اسجل|أضيف|اضيف|أدخل|ادخل|أحتسب|احتسب)",
    r"هل (يجب|ينبغي|الأفضل)",
    # French
    r"\b(où|comment)\b.{0,70}\b(enregistr\w*|saisir|ajouter|noter|comptabilis\w*|classer|mettre|ranger|dois-je|devrais-je|puis-je|dois je|puis je)\b",
    r"\b(dois|devrais)[- ]je\b",
    r"\bsi j['’](ai|achète|vends|paie|reçois)\b.{0,40}\b(acheté|vendu|payé|reçu|achète|vends|paie|reçois)\b",
    r"\best-ce (mieux|correct|bien) de\b",
    # German
    r"\b(wo|wie)\b.{0,70}\b(erfass\w*|eintrag\w*|buch\w*|verbuch\w*|hinzufüg\w*|speicher\w*|einordn\w*|kategorisier\w*|soll ich|muss ich|kann ich)\b",
    r"\bsoll(te)? ich\b",
    r"\bwenn ich\b.{0,50}\b(gekauft|verkauft|bezahlt|erhalten|kaufe|verkaufe|bezahle)\b",
))
_ACTION_START = re.compile(
    r"^\s*(please\s+|s'il vous plaît\s+|bitte\s+)?(add|create|delete|remove|update|edit|transfer|pay|change"
    r"|ajoute|crée|supprime|modifie|virer|paie|füge|erstelle|lösche|ändere|überweise|zahle)\b",
    _FLAGS,
)


def is_workflow_question(text: str) -> bool:
    text = (text or "").strip()
    if not text or len(text) > 500 or _ACTION_START.search(text):
        return False
    return any(p.search(text) for p in _PATTERNS)
