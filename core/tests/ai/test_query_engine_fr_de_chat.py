"""Query engine in French and German, end to end through the chat endpoint: every answer comes from code (ZERO LLM calls),
is written in the question's language, and never contains the other tenant's data."""

from unittest.mock import patch

from django.test import TestCase

from core.integrations.ai_provider import OllamaProvider

from . import qe_fixtures as fx

NO_LLM = patch.object(OllamaProvider, "generate", side_effect=AssertionError("LLM must not be called"))

# question -> substrings the answer must contain; each runs with the LLM forbidden and the other tenant's data present.
CHAT_CASES = [
    ("fr", "Quel est le prix de l'or 24 carats ?", ["Prix du gramme d'or 24 carats", "5,000.00 EGP", "4,950.00 EGP"]),
    ("fr", "Quel est le taux de change du dollar ?", ["1 USD = 50.2500 EGP", "achat 50.0000", "vente 50.5000"]),
    ("fr", "Total des dépenses pour septembre 2026", ["Total des dépenses pour septembre 2026", "1,000.00 EGP sur 1 transactions"]),
    ("fr", "Dépenses de juin à septembre 2026", ["**Total général**", "1,170.50 EGP"]),
    ("fr", "Dépenses par catégorie en juin 2026", ["Food", "150.50 EGP", "100.0%", "Catégorie"]),
    ("fr", "Quel a été mon salaire de janvier 2026 ?", ["87,643.86 EGP", "Salaire versé"]),
    ("fr", "Quel est mon solde ?", ["Solde total : 1,000.00 EGP"]),
    ("fr", "Mes certificats", ["1 certificat(s) actif(s)", "100,000.00 EGP"]),
    ("fr", "Quels sont mes actifs fixes ?", ["5,000,000.00 EGP", "sur 1 actif(s)"]),
    ("fr", "Ma dernière dépense", ["Rent", "1,000.00 EGP"]),
    ("de", "Goldpreis 24 Karat", ["Goldpreis pro Gramm 24 Karat", "5,000.00 EGP", "4,950.00 EGP"]),
    ("de", "Wie hoch ist der Wechselkurs des Dollars?", ["1 USD = 50.2500 EGP", "Kauf 50.0000", "Verkauf 50.5000"]),
    ("de", "Gesamtausgaben für September 2026", ["Gesamtausgaben für September 2026", "1,000.00 EGP in 1 Buchungen"]),
    ("de", "Meine Ausgaben von Juni bis September 2026", ["**Gesamtsumme**", "1,170.50 EGP"]),
    ("de", "Ausgaben nach Kategorie im Juni 2026", ["Food", "150.50 EGP", "100.0%", "Kategorie"]),
    ("de", "Wie hoch war mein Gehalt im Januar 2026?", ["87,643.86 EGP", "Gezahltes Gehalt"]),
    ("de", "Wie hoch ist mein Kontostand?", ["Gesamtsaldo: 1,000.00 EGP"]),
    ("de", "Meine Zertifikate", ["1 aktive(s) Zertifikat(e)", "100,000.00 EGP"]),
    ("de", "Meine Anlagegüter", ["5,000,000.00 EGP", "1 Gut/Gütern"]),
    ("de", "Meine letzte Ausgabe", ["Rent", "1,000.00 EGP"]),
]


class FrDeChatTests(TestCase):
    def setUp(self):
        fx.build(self)

    def test_answers_in_the_users_language_with_zero_llm_calls_and_no_leaks(self):
        for lang, q, needles in CHAT_CASES:
            with self.subTest(q=q), NO_LLM:
                data = fx.ask(self, q)
                text = data["message"]["content"]
                for n in needles:
                    self.assertIn(n, text)
                for secret in ("SECRET", "777,777", "111.00", "999,999", "9,999,999"):
                    self.assertNotIn(secret, text)
                call = data["message"]["tool_calls"][0]
                self.assertTrue(call["direct_answer"])
                self.assertEqual(call["arguments"]["request"]["lang"], lang)
                self.assertEqual(call["llm_calls"], 0)
