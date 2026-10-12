"""Detects answers where the model gives up ("I don't have access / the data / a tool for that") in en/ar/fr/de.

Capability refusals always count: with this toolbox they are never true. "I couldn't find X" only counts when nothing
was investigated yet, because after real tool calls a negative finding is a legitimate answer.
"""

from __future__ import annotations

import re

_CAPABILITY = (
    r"i (?:do not|don't|dont) have (?:access|the (?:tools?|ability|data|information|permission)|enough (?:information|data|context)|"
    r"any (?:tools?|access|data)|a (?:tool|way))",
    r"i (?:can ?not|can't|cant) (?:access|see|view|read|check|look|retrieve|browse|query)",
    r"i(?:'m| am) (?:not able|unable) to (?:access|see|view|read|check|look|retrieve|browse|query)",
    r"(?:no|without) (?:direct )?access to (?:your|the) (?:data|app|application|code|database|files)",
    r"(?:not|n't) (?:have|got) (?:the )?(?:necessary |required |enough )?(?:tools?|access|permissions?|capabilit)",
    r"as an ai(?: language model)?,? i",
    r"beyond my (?:capabilities|scope|access)",
    r"لا (?:أملك|املك|أستطيع|استطيع|يمكنني|أقدر|اقدر) (?:الوصول|الاطلاع|الإطلاع|عرض|قراءة|معرفة|الحصول)",
    r"(?:ليس|ليست) لدي (?:وصول|صلاحية|أدوات|اداة|أداة|بيانات|معلومات كافية|إمكانية)",
    r"لا (?:تتوفر|توجد|يتوفر) لدي",
    r"ليس بإمكاني|لا أستطيع الوصول|غير قادر على الوصول",
    r"je n[' ]ai pas (?:accès|acces|les outils|d'outil|assez d'informations|suffisamment|les données|la possibilité)",
    r"je ne (?:peux|puis) pas (?:accéder|acceder|consulter|voir|lire|vérifier|verifier)",
    r"je ne dispose pas (?:des|de|d')",
    r"je ne suis pas en mesure (?:de|d')",
    r"ich habe (?:keinen|keine) (?:zugriff|zugang|werkzeuge|tools|möglichkeit|informationen|daten)",
    r"ich kann (?:nicht|leider nicht) (?:auf|zugreifen|einsehen|lesen|prüfen|nachsehen)",
    r"ich verfüge (?:nicht|leider nicht) über",
    r"ich bin (?:nicht in der lage|leider nicht in der lage|außerstande)",
)
_NOT_FOUND = (
    r"(?:i )?(?:could ?n[o']?t|can ?not|can't|did not|didn't|was unable to|am unable to) (?:find|locate|determine|answer|identify)",
    r"(?:there is |there's )?no (?:information|data|record|details) (?:available|provided|found)",
    r"(?:not enough|insufficient) (?:information|data|context)",
    r"لم (?:أتمكن|اتمكن|أجد|اجد|أستطع|استطع)",
    r"لا (?:توجد|يوجد) (?:معلومات|بيانات) (?:كافية|متاحة)",
    r"je n'ai pas (?:trouvé|pu)",
    r"ich konnte (?:nicht|keine)",
)
_CAP = re.compile("|".join(_CAPABILITY), re.IGNORECASE)
_NF = re.compile("|".join(_NOT_FOUND), re.IGNORECASE)
_LEAD = 400   # a refusal is announced at the start; deep inside a long, sourced answer the phrase is just prose


def is_refusal(text: str, investigated: bool = False, extra_markers: tuple = ()) -> bool:
    body = (text or "").strip()
    if not body:
        return True
    if any(m and m in body for m in extra_markers):
        return True
    head = body[:_LEAD]
    if _CAP.search(head):
        return True
    return (not investigated) and bool(_NF.search(head)) and len(body) < 700
