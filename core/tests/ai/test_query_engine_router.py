"""Query-engine router: time parsing, slot filling, registry, and the paraphrase corpus (>=30 per capability)."""

from datetime import date

from django.test import SimpleTestCase

from core.services.ai.query_engine import get_capabilities, route
from core.services.ai.query_engine.lexicon import norm
from core.services.ai.query_engine.timespec import parse_time

from .qe_paraphrases import CORPUS, FALL_THROUGH

TODAY = date(2026, 9, 29)
EXPECTED = {"expenses", "salary", "balance", "certificates", "fixed_assets", "gold_price", "exchange_rates", "gold_holdings"}


def months(q):
    return [f"{y}-{m:02d}" for y, m in parse_time(norm(q), TODAY).months]


class TimeParsingTests(SimpleTestCase):
    def test_ranges_and_lists(self):
        want = ["2026-06", "2026-07", "2026-08", "2026-09"]
        for q in ("Jun to Sept 2026", "from June to September 2026", "between June and September 2026", "2026-06 to 2026-09",
                  "Jun 2026\nJul 2026\nAug 2026\nSept 2026", "مصروفات من يونيو حتى سبتمبر 2026"):
            self.assertEqual(months(q), want, q)

    def test_year_wrap_relative_and_single(self):
        self.assertEqual(months("Nov to Feb 2026"), ["2025-11", "2025-12", "2026-01", "2026-02"])
        self.assertEqual(months("last month"), ["2026-08"])
        self.assertEqual(months("last 3 months"), ["2026-07", "2026-08", "2026-09"])
        self.assertEqual(len(months("expenses in 2026")), 12)
        self.assertEqual(months("Sept-2026"), ["2026-09"])
        self.assertEqual(months("ما هو راتبي في يناير 2026"), ["2026-01"])
        self.assertEqual(months("مصروفات اخر ٣ شهور"), ["2026-07", "2026-08", "2026-09"])

    def test_may_verb_is_not_a_month_and_latest_today(self):
        self.assertEqual(months("how may I spend less"), [])
        spec = parse_time(norm("gold price today"), TODAY)
        self.assertEqual((spec.kind, spec.today), ("latest", True))


class RegistryTests(SimpleTestCase):
    def test_capabilities_declared_by_providers(self):
        caps = get_capabilities()
        self.assertEqual({c.key for c in caps}, EXPECTED)
        for c in caps:
            self.assertTrue(c.metrics and c.default_metric in c.metric_names(), c.key)
            self.assertTrue(callable(c.executor))

    def test_capability_registry_lists_engine_entries(self):
        from core.services.ai.capability_registry import CapabilityRegistry

        names = [c["name"] for c in CapabilityRegistry.autodiscover()]
        self.assertTrue(any(n.startswith("Instant answer: Gold price") for n in names))


class SlotTests(SimpleTestCase):
    def slots(self, q):
        r = route(q, today=TODAY)
        return r, r.request

    def test_gold_slots(self):
        r, req = self.slots("what is the gold price today for 24k?")
        self.assertEqual((r.status, req.capability, req.filters.get("karat")), ("ready", "gold_price", "24"))
        _, req = self.slots("21k gold buy price")
        self.assertEqual((req.filters["karat"], req.filters["side"]), ("21", "buy"))
        _, req = self.slots("سعر شراء الذهب عيار 18")
        self.assertEqual((req.filters["karat"], req.filters["side"]), ("18", "buy"))

    def test_expense_slots(self):
        _, req = self.slots("expenses by category for Jun to Sept 2026")
        self.assertEqual((req.group_by, len(req.periods)), ("category", 4))
        _, req = self.slots("show the last 5 expenses")
        self.assertEqual((req.metric, req.n), ("latest", 5))
        _, req = self.slots("my last expense")
        self.assertEqual((req.metric, req.n), ("latest", 1))

    def test_fx_currency_slot(self):
        _, req = self.slots("USD sell rate")
        self.assertEqual((req.filters["currencies"], req.filters["side"]), (["USD"], "sell"))

    def test_status_reasons(self):
        self.assertEqual(route("why did my expenses grow in Aug 2026", today=TODAY).status, "analytic")
        self.assertEqual(route("expenses", today=TODAY).status, "incomplete")
        self.assertEqual(route("gold price in March 2025", today=TODAY).status, "unsupported_time")
        self.assertEqual(route("add an expense of 50", today=TODAY).status, "blocked")
        self.assertEqual(route("x" * 700, today=TODAY).status, "none")


class FollowUpTests(SimpleTestCase):
    """A short follow-up inherits the topic of the previous user question (the real log: gold price -> "and how much i hold?")."""

    def test_real_conversation_gold_price_then_holdings(self):
        self.assertEqual(route("and how much i hold?", today=TODAY).status, "none")  # alone it means nothing
        r = route("and how much i hold?", today=TODAY, previous="what is the gold price today for 24k?")
        self.assertEqual((r.status, r.capability), ("ready", "gold_holdings"))
        self.assertIn("follow_up_of:gold_price", r.reason)

    def test_follow_up_inherits_period_for_period_capabilities(self):
        r = route("and my salary?", today=TODAY, previous="total expenses for Sept 2026")
        self.assertEqual((r.status, r.capability, r.request.periods), ("ready", "salary", [(2026, 9)]))
        self.assertEqual(route("and my salary?", today=TODAY).status, "incomplete")  # no previous question: nothing to inherit
        r = route("what about last month?", today=TODAY, previous="salary for Sept 2026")
        self.assertEqual((r.status, r.capability, r.request.periods), ("ready", "salary", [(2026, 8)]))

    def test_follow_up_never_invents_a_topic(self):
        for prev in ("what is the gold price today for 24k?", "total expenses for Sept 2026"):
            for q in ("and thanks?", "ok", "and how are you?", "so what is the meaning of life?"):
                self.assertNotEqual(route(q, today=TODAY, previous=prev).status, "ready", (prev, q))
        self.assertEqual(route("and how much i hold?", today=TODAY, previous="hello").status, "none")
        self.assertEqual(route("and how much i hold?", today=TODAY, previous="").status, "none")
        long_q = "and " + "very " * 12 + "long question about nothing in particular"
        self.assertEqual(route(long_q, today=TODAY, previous="gold price today").status, "none")


class ParaphraseTests(SimpleTestCase):
    def test_at_least_30_phrasings_per_capability(self):
        self.assertEqual(set(CORPUS), EXPECTED)
        for cap, qs in CORPUS.items():
            self.assertGreaterEqual(len(set(qs)), 30, cap)

    def test_every_paraphrase_routes_to_its_capability(self):
        for cap, qs in CORPUS.items():
            for q in qs:
                with self.subTest(cap=cap, q=q):
                    r = route(q, today=TODAY)
                    self.assertEqual((r.status, r.capability), ("ready", cap), r.summary())

    def test_advice_why_compare_and_actions_fall_through(self):
        for q in FALL_THROUGH:
            with self.subTest(q=q):
                self.assertNotEqual(route(q, today=TODAY).status, "ready")
