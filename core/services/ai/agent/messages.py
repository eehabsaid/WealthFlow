"""The two notes Agent mode adds to an answer, in the language the user wrote in (en/ar/fr/de)."""

from __future__ import annotations

STOPPED = {
    "en": "Stopped at your request.",
    "ar": "تم الإيقاف بناءً على طلبك.",
    "fr": "Arrêté à votre demande.",
    "de": "Auf Ihren Wunsch gestoppt.",
}
NO_TOOLS = {
    "en": "Note: this model did not use any tools, so this answer is not backed by a lookup in your data. Agent mode works best with a tool-calling model (for example qwen3 or llama3.1); change the model in Settings > AI Advisor.",
    "ar": "ملاحظة: لم يستخدم هذا النموذج أي أداة، لذلك هذه الإجابة غير مدعومة ببحث في بياناتك. يعمل وضع الوكيل بشكل أفضل مع نموذج يدعم الأدوات (مثل qwen3 أو llama3.1)؛ غيّر النموذج من الإعدادات > مستشار الذكاء الاصطناعي.",
    "fr": "Remarque : ce modèle n'a utilisé aucun outil, cette réponse n'est donc pas appuyée par une recherche dans vos données. Le mode Agent fonctionne mieux avec un modèle capable d'appeler des outils (par exemple qwen3 ou llama3.1) ; changez de modèle dans Paramètres > Conseiller IA.",
    "de": "Hinweis: Dieses Modell hat keine Werkzeuge benutzt, daher stützt sich diese Antwort nicht auf eine Abfrage Ihrer Daten. Der Agent-Modus funktioniert am besten mit einem Modell, das Werkzeuge aufrufen kann (z. B. qwen3 oder llama3.1); ändern Sie das Modell unter Einstellungen > KI-Berater.",
}


def note(table: dict, text: str) -> str:
    from core.services.ai.query_engine.lexicon import language

    return table.get(language(text), table["en"])
