"""Query engine in French and German: every capability routes from fr/de phrasings (>=14 per capability per language),
English / Arabic behaviour is guarded against regression, and the label tables match the English ones exactly.
End-to-end answers live in test_query_engine_fr_de_chat.py."""

import string
from datetime import date

from django.test import SimpleTestCase

from core.services.ai.query_engine import labels, labels_de, labels_fr, route
from core.services.ai.query_engine import lexicon_fr_de as lexicon
from core.services.ai.query_engine.lexicon import language, norm

from .qe_paraphrases import CORPUS, FALL_THROUGH
from .qe_paraphrases_fr_de import DE, FALL_THROUGH_DE, FALL_THROUGH_FR, FR

TODAY = date(2026, 9, 29)
EXPECTED = {"expenses", "salary", "balance", "certificates", "fixed_assets", "gold_price", "exchange_rates", "gold_holdings", "budgets", "recurring"}
CORPORA = (("fr", FR, FALL_THROUGH_FR), ("de", DE, FALL_THROUGH_DE))


def months(q, lang):
    return [f"{y}-{m:02d}" for y, m in route(q, today=TODAY).time.months]


class FrDeParaphraseTests(SimpleTestCase):
    def test_every_capability_has_at_least_15_phrasings_per_language(self):
        for lang, corpus, _ in CORPORA:
            self.assertEqual(set(corpus), EXPECTED, lang)
            for cap, qs in corpus.items():
                self.assertGreaterEqual(len(set(qs)), 14, f"{lang}/{cap}")

    def test_every_paraphrase_routes_to_its_capability_and_language(self):
        for lang, corpus, _ in CORPORA:
            for cap, qs in corpus.items():
                for q in qs:
                    with self.subTest(lang=lang, cap=cap, q=q):
                        r = route(q, today=TODAY)
                        self.assertEqual((r.status, r.capability, r.lang), ("ready", cap, lang), r.summary())

    def test_advice_why_compare_actions_and_small_talk_fall_through(self):
        for _, _, fall in CORPORA:
            for q in fall:
                with self.subTest(q=q):
                    self.assertNotEqual(route(q, today=TODAY).status, "ready")

    def test_actions_are_blocked_in_both_languages(self):
        for q in ("Ajoute une dépense de 50 pour le déjeuner", "Supprime ma dernière dépense", "Füge eine Ausgabe von 50 hinzu", "Lösche meine letzte Ausgabe"):
            self.assertEqual(route(q, today=TODAY).status, "blocked", q)


class LanguageDetectionTests(SimpleTestCase):
    def test_english_and_arabic_phrasings_are_never_reclassified(self):
        for qs in list(CORPUS.values()) + [FALL_THROUGH]:
            for q in qs:
                want = "ar" if any("\u0600" <= c <= "\u06ff" for c in q) else "en"
                self.assertEqual(language(q), want, q)

    def test_short_real_phrases_are_detected(self):
        for q, want in (("Mon or", "fr"), ("Mes primes", "fr"), ("Cours de l'or", "fr"), ("Meine Zertifikate", "de"), ("Mein Gold", "de"),
                        ("Wechselkurs Euro", "de"), ("my gold", "en"), ("gold price", "en"), ("karat 21 price", "en"), ("", "en")):
            self.assertEqual(language(q), want, q)


class RewriteTests(SimpleTestCase):
    def rewrite(self, q, lang):
        return lexicon.to_english(lexicon.fold(norm(q)), lang)

    def test_fold_strips_latin_accents_but_not_arabic(self):
        self.assertEqual(lexicon.fold("Février Café Größe ça"), "Fevrier Cafe Grosse ca")
        self.assertEqual(lexicon.fold("راتبي"), "راتبي")

    def test_all_twelve_months_in_both_languages(self):
        fr = "janvier février mars avril mai juin juillet août septembre octobre novembre décembre".split()
        de = "Januar Februar März April Mai Juni Juli August September Oktober November Dezember".split()
        for names in (fr, de):
            lang = "fr" if names is fr else "de"
            for i, name in enumerate(names, 1):
                self.assertEqual(months(f"dépenses {name} 2026" if lang == "fr" else f"Ausgaben {name} 2026", lang), [f"2026-{i:02d}"], name)

    def test_relative_periods_and_ranges(self):
        self.assertEqual(months("Dépenses le mois dernier", "fr"), ["2026-08"])
        self.assertEqual(months("Dépenses ce mois-ci", "fr"), ["2026-09"])
        self.assertEqual(months("Dépenses ces 3 derniers mois", "fr"), ["2026-07", "2026-08", "2026-09"])
        self.assertEqual(len(months("Dépenses de l'année dernière", "fr")), 12)
        self.assertEqual(months("Dépenses de juin à septembre 2026", "fr"), ["2026-06", "2026-07", "2026-08", "2026-09"])
        self.assertEqual(months("Ausgaben letzten Monat", "de"), ["2026-08"])
        self.assertEqual(months("Ausgaben diesen Monat", "de"), ["2026-09"])
        self.assertEqual(months("Ausgaben in den letzten 3 Monaten", "de"), ["2026-07", "2026-08", "2026-09"])
        self.assertEqual(len(months("Ausgaben im letzten Jahr", "de")), 12)
        self.assertEqual(months("Ausgaben von Juni bis September 2026", "de"), ["2026-06", "2026-07", "2026-08", "2026-09"])
        self.assertEqual(months("Ausgaben zwischen Juni und August 2026", "de"), ["2026-06", "2026-07", "2026-08"])

    def test_latest_n_and_slots(self):
        for q in ("Quelles sont mes 5 dernières dépenses ?", "Meine letzten 5 Ausgaben"):
            req = route(q, today=TODAY).request
            self.assertEqual((req.metric, req.n), ("latest", 5), q)
        for q in ("Ma dernière dépense", "Meine letzte Ausgabe"):
            req = route(q, today=TODAY).request
            self.assertEqual((req.metric, req.n), ("latest", 1), q)
        self.assertEqual(route("Dépenses par catégorie en septembre 2026", today=TODAY).request.group_by, "category")
        self.assertEqual(route("Ausgaben nach Kategorie im September 2026", today=TODAY).request.group_by, "category")
        req = route("Prix d'achat de l'or 18 carats", today=TODAY).request
        self.assertEqual((req.filters["karat"], req.filters["side"]), ("18", "buy"))
        req = route("Verkaufspreis Gold 24 Karat", today=TODAY).request
        self.assertEqual((req.filters["karat"], req.filters["side"]), ("24", "sell"))

    def test_the_month_word_may_is_not_confused_with_the_verb(self):
        self.assertEqual(months("Mes dépenses en mai 2026", "fr"), ["2026-05"])
        self.assertEqual(months("Meine Ausgaben im Mai 2026", "de"), ["2026-05"])


class EntityMatchingTests(SimpleTestCase):
    """The user's own category names are matched against the accent-folded ORIGINAL text, never the translation."""

    def test_accented_category_names_match_in_both_languages(self):
        lookup = lambda: ["Café", "Électricité", "Lebensmittel", "Food"]  # noqa: E731
        cases = (("Dépenses en café en septembre 2026", "Café"), ("Dépenses électricité août 2026", "Électricité"),
                 ("Ausgaben für Lebensmittel im September 2026", "Lebensmittel"), ("expenses Food Sept 2026", "Food"))
        for q, want in cases:
            self.assertEqual(route(q, category_lookup=lookup, today=TODAY).request.filters.get("category"), want, q)

    def test_a_category_that_is_also_a_vocabulary_word_still_matches_as_a_name(self):
        lookup = lambda: ["Transport", "Factures"]  # noqa: E731   ("factures" is also the word for bills)
        r = route("Dépenses Factures septembre 2026", category_lookup=lookup, today=TODAY)
        self.assertEqual((r.capability, r.request.filters.get("category")), ("expenses", "Factures"))
        r = route("Ausgaben Rechnungen September 2026", category_lookup=lambda: ["Rechnungen"], today=TODAY)
        self.assertEqual((r.capability, r.request.filters.get("category")), ("expenses", "Rechnungen"))


class FollowUpTests(SimpleTestCase):
    def test_french_and_german_follow_ups_inherit_topic_and_period(self):
        r = route("Et mon salaire ?", today=TODAY, previous="Total des dépenses pour septembre 2026")
        self.assertEqual((r.status, r.capability, r.request.periods), ("ready", "salary", [(2026, 9)]))
        r = route("Und mein Gehalt?", today=TODAY, previous="Meine Ausgaben im September 2026")
        self.assertEqual((r.status, r.capability, r.request.periods), ("ready", "salary", [(2026, 9)]))
        r = route("Et le mois dernier ?", today=TODAY, previous="Mon salaire en septembre 2026")
        self.assertEqual((r.status, r.capability, r.request.periods), ("ready", "salary", [(2026, 8)]))

    def test_a_follow_up_never_invents_a_topic(self):
        for q, prev in (("Et merci ?", "Prix de l'or aujourd'hui"), ("Und danke?", "Goldpreis heute"), ("Ok", "Mes dépenses de septembre 2026")):
            self.assertNotEqual(route(q, today=TODAY, previous=prev).status, "ready", q)


class LabelTableTests(SimpleTestCase):
    @staticmethod
    def fields(text):
        return {f for _, f, _, _ in string.Formatter().parse(text) if f}

    def test_fr_and_de_have_exactly_the_english_keys_and_placeholders(self):
        for name, table in (("ar", labels._AR), ("fr", labels_fr.TABLE), ("de", labels_de.TABLE)):
            self.assertEqual(set(table), set(labels._EN), name)
            for key, text in labels._EN.items():
                self.assertEqual(self.fields(table[key]), self.fields(text), f"{name}.{key}")

    def test_every_answer_text_is_actually_translated(self):
        for name, table in (("fr", labels_fr.TABLE), ("de", labels_de.TABLE)):
            same = sorted(k for k in labels._EN if table[k] == labels._EN[k])
            self.assertLess(len(same), 12, f"{name}: untranslated {same}")      # only cognate column headers may match English
            self.assertTrue(all(k.startswith(("col_", "total_of", "head_tx", "sal_part")) for k in same), f"{name}: {same}")
        for k in ("exp_total", "sal_month", "bal_total", "cert_none", "gold_none", "fx_none", "bud_none", "rec_none"):
            self.assertNotEqual(labels_de.TABLE[k], labels._EN[k], k)
            self.assertNotEqual(labels_fr.TABLE[k], labels._EN[k], k)

    def test_month_labels_and_range_labels(self):
        self.assertEqual(labels.month_label("fr", 2026, 8), "août 2026")
        self.assertEqual(labels.month_label("de", 2026, 3), "März 2026")
        self.assertEqual(labels.month_label("fr", 2026, 9, abbr=True), "sept. 2026")
        self.assertEqual(labels.range_label("de", [(2026, 6), (2026, 7), (2026, 8)]), "Juni 2026 – Aug. 2026")
        self.assertEqual(labels.month_label("en", 2026, 9), "September 2026")
        self.assertEqual(labels.t("de", "grand"), "Gesamtsumme")
        self.assertEqual(labels.t("it", "grand"), "Grand Total")   # unknown language -> English, never a KeyError

    def test_month_tables_are_complete(self):
        for mod in (labels_fr, labels_de):
            self.assertEqual((len(mod.MONTHS), len(mod.MONTHS_ABBR)), (12, 12))
