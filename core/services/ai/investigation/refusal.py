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
    # data-window / file give-ups: "only a capped window", "not in the provided data", "cannot generate or send a file"
    r"(?:i )?(?:can|could) only (?:see|access|view|read|use) (?:a |an |the )?(?:capped|limited|partial|truncated|small|recent)",
    r"(?:only|just) (?:see|have|access to|shows?) (?:a |the )?(?:capped|limited|partial|truncated|recent)? ?(?:window|subset|sample|portion|excerpt)",
    r"(?:does not|doesn't|do not|don't|did not|didn't) (?:contain|include|cover) (?:the |any |all |every |your )?(?:\w+ ){0,2}(?:data|entries|records|rows|information|figures|salar\w*|months?|years?|payload)",
    r"not (?:included|present|available|contained|listed|found) in (?:the |this )?(?:provided|supplied|given|current|available|payload|context|data)",
    r"(?:i )?(?:can ?not|can't|cant|am (?:not able|unable) to|unable to|not able to) (?:directly )?(?:generate|create|produce|build|export|send|attach|provide|make|write|deliver)(?: (?:or|and) \w+)? (?:an? |the |any )?(?:\.?(?:xlsx|xls|docx|pdf|csv|excel|word)\b|files?|spreadsheets?|documents?|downloads?|attachments?|exports?)",
    r"(?:i )?(?:can ?not|can't|cant|am (?:not able|unable) to|unable to) (?:directly )?(?:export|download|send|generate) (?:it|this|that|them|these|the (?:data|results?|table|list))",
    r"لا (?:أستطيع|استطيع|يمكنني|أقدر|اقدر|أملك|املك) (?:تصدير|إنشاء|انشاء|إرسال|ارسال|توليد|تحميل|إنتاج|انتاج|إعداد)",
    r"(?:يمكنني|أستطيع|استطيع) (?:فقط )?(?:رؤية|الاطلاع على|الوصول إلى|عرض) (?:نافذة|عدد محدود|جزء)",
    r"(?:لا|لم) (?:يحتوي|تحتوي|تتضمن|يتضمن|يشمل|تشمل) (?:على )?(?:البيانات|السجلات|المدخلات|الأشهر|معلومات)",
    r"(?:غير|ليست|ليس) (?:مدرج|مدرجة|متوفر|متوفرة|موجود|موجودة|مضمن|مضمنة) في (?:البيانات|السياق|المعطيات|الحمولة)",
    r"je ne (?:peux|puis) (?:pas )?(?:directement )?(?:générer|generer|créer|creer|exporter|envoyer|produire|fournir|joindre) (?:un |une |le |la |des |de )?(?:fichiers?|excel|xlsx|pdf|word|docx|csv|tableur|documents?|exports?|pièces? jointes?)",
    r"je (?:ne )?(?:vois|peux voir)(?: que| qu'|seulement|uniquement)? ?(?:une |la )?(?:fenêtre|partie|portion|sous-ensemble)",
    r"(?:ne contient|ne contiennent|ne comprend|n'inclut|n'inclus|ne figure|ne figurent) (?:pas|plus)? ?(?:dans|les données|de données|toutes|les mois|les entrées|les lignes)",
    r"(?:n'est|ne sont) pas (?:inclus|incluse|incluses|inclus|présent|présente|disponible|disponibles|fourni|fournie|fournis) dans (?:les |la |le )?(?:données|charge|contexte|payload|fournies?)",
    r"ich kann (?:nicht|leider nicht|keine?n?) (?:\S+ ){0,4}?(?:erstellen|generieren|exportieren|senden|erzeugen|bereitstellen|anhängen|liefern)",
    r"ich (?:sehe|kann nur) (?:nur )?(?:ein|einen|das) (?:begrenztes?|eingeschränktes?|teilweises?|gekürztes?) (?:fenster|ausschnitt|teilmenge)",
    r"(?:enthält|enthalten|umfasst|beinhaltet) (?:nicht|keine) (?:die |alle |sämtliche )?(?:daten|einträge|datensätze|monate|zeilen|informationen)",
    r"(?:nicht|nicht mehr) (?:in den|im|in der) (?:bereitgestellten|gelieferten|vorliegenden|übergebenen) (?:daten|kontext|payload|informationen)",
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
