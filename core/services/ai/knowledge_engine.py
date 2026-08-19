"""
AI Knowledge Engine.

Manages distilled long-term domain knowledge entries (business rules, codebase architecture,
user preferences, app evolution facts) for AI system prompt context injection.
"""

from __future__ import annotations

import logging
from typing import Any
from core.models import AIKnowledgeEntry

logger = logging.getLogger(__name__)


class AIKnowledgeEngine:
    """
    Central engine for reading, storing, and summarizing distilled long-term knowledge entries.
    """

    @classmethod
    def get_active_knowledge_entries(cls, category: str | None = None) -> list[AIKnowledgeEntry]:
        qs = AIKnowledgeEntry.objects.filter(is_active=True)
        if category:
            qs = qs.filter(category=category)
        return list(qs.order_by("-updated_at"))

    @classmethod
    def record_knowledge_entry(
        cls,
        key: str,
        title: str,
        content: str,
        category: str = "business_rule",
        confidence: float = 1.0,
        source: str = "autonomous_learning",
    ) -> AIKnowledgeEntry:
        clean_key = str(key or "").strip().lower()
        entry, _created = AIKnowledgeEntry.objects.update_or_create(
            key=clean_key,
            defaults={
                "title": str(title or "").strip(),
                "content": str(content or "").strip(),
                "category": category,
                "confidence": confidence,
                "source": source,
                "is_active": True,
            },
        )
        return entry

    @classmethod
    def extract_knowledge_from_conversation(
        cls, user: Any, user_query: str, ai_response: str
    ) -> list[AIKnowledgeEntry]:
        """
        General-purpose learning pipeline.
        Extracts user preferences, behavioral directives, and module focus signals
        from every conversation turn and persists them as independent KB entries.
        """
        extracted = []
        q = (user_query or "").lower().strip()
        r = (ai_response or "").lower().strip()

        def record(key, title, content, category="user_preference", confidence=0.9):
            entry = cls.record_knowledge_entry(
                key=key,
                title=title,
                content=content,
                category=category,
                confidence=confidence,
                source="user_conversation",
            )
            extracted.append(entry)

        # ── 1. MODULE FOCUS SIGNALS ──────────────────────────────────────────
        # Each module has independent KB key so signals never overwrite each other.
        MODULE_SIGNALS = [
            # (kb_key, title, content, keywords_en, keywords_ar)
            ("focus_gold",          "Module Focus: Gold",               "User frequently queries Gold holdings and valuations.",
             ["gold", "karat", "21k", "18k", "24k", "spot price", "gram"],
             ["ذهب", "عيار", "أونصة"]),
            ("focus_certificates",  "Module Focus: Bank Certificates",  "User frequently queries Bank Certificates, yields, and maturity dates.",
             ["certificate", "cert", "maturity", "yield", "interest rate", "payout", "annual rate"],
             ["شهادة", "شهادات", "عائد", "فائدة"]),
            ("focus_balance",       "Module Focus: Cash & Bank Balances","User frequently queries liquid cash and bank account balances.",
             ["balance", "cash", "bank account", "liquid", "deposit", "account"],
             ["رصيد", "حساب", "نقدي", "سيولة"]),
            ("focus_salary",        "Module Focus: Salary & Income",     "User frequently queries salary, income, deductions, and per diems.",
             ["salary", "income", "payslip", "deduction", "per diem", "net pay", "gross"],
             ["راتب", "دخل", "خصم", "بدل", "صافي"]),
            ("focus_expenses",      "Module Focus: Expenses & Spending", "User frequently queries expenses, spending categories, and budgets.",
             ["expense", "spending", "budget", "cost", "category", "discretionary", "fixed cost"],
             ["مصروف", "مصاريف", "ميزانية", "إنفاق"]),
            ("focus_fixed_assets",  "Module Focus: Fixed Assets",        "User frequently queries real estate, vehicles, and other fixed assets.",
             ["real estate", "property", "vehicle", "car", "fixed asset", "valuation", "asset"],
             ["عقار", "سيارة", "أصول", "تقييم"]),
            ("focus_net_worth",     "Module Focus: Net Worth",           "User frequently queries overall net worth and wealth summary.",
             ["net worth", "total wealth", "wealth", "portfolio", "asset allocation"],
             ["ثروة", "صافي", "إجمالي"]),
            ("focus_cash_flow",     "Module Focus: Cash Flow",           "User frequently queries cash flow forecasts and monthly net income.",
             ["cash flow", "flow", "forecast", "monthly income", "savings rate", "net cash"],
             ["تدفق", "توقع", "شهري"]),
            ("focus_risk",          "Module Focus: Risk Analysis",       "User frequently queries risk analysis and concentration alerts.",
             ["risk", "concentration", "diversif", "volatility", "stress test"],
             ["مخاطر", "تركيز", "تنويع"]),
            ("focus_opportunity",   "Module Focus: Opportunity Detection","User frequently queries yield opportunities and idle cash alerts.",
             ["opportunity", "idle cash", "optimize", "return", "reinvest"],
             ["فرصة", "عائد", "تحسين"]),
            ("focus_performance",   "Module Focus: Performance",         "User frequently queries historical performance and returns.",
             ["performance", "historical", "gain", "loss", "return on"],
             ["أداء", "تاريخي", "ربح", "خسارة"]),
            ("focus_goal_planning", "Module Focus: Goal Planning",       "User frequently queries financial goals and savings targets.",
             ["goal", "target", "saving goal", "plan", "milestone"],
             ["هدف", "خطة", "توفير"]),
            ("focus_scenario",      "Module Focus: Scenario Planning",   "User frequently queries scenario and stress-test simulations.",
             ["scenario", "recession", "inflation", "crisis", "simulate", "what if"],
             ["سيناريو", "تضخم", "أزمة", "محاكاة"]),
            ("focus_wealth_growth", "Module Focus: Wealth Growth",       "User frequently queries long-term wealth growth projections.",
             ["growth", "projection", "compounding", "long term", "future wealth"],
             ["نمو", "مستقبل", "مركب"]),
            ("focus_exchange_rates","Module Focus: Exchange Rates",      "User frequently queries currency rates and FX conversions.",
             ["exchange rate", "usd", "eur", "sar", "currency", "forex", "convert"],
             ["سعر صرف", "دولار", "يورو", "ريال", "عملة"]),
        ]

        for kb_key, title, content, kw_en, kw_ar in MODULE_SIGNALS:
            if any(kw in q for kw in kw_en) or any(kw in q for kw in kw_ar):
                record(kb_key, title, content, confidence=0.85)

        # ── 2. RESPONSE FORMAT PREFERENCES ──────────────────────────────────
        if any(w in q for w in ["summary", "brief", "short", "quick", "tldr", "ملخص", "مختصر", "بإيجاز"]):
            record("pref_response_brief", "Response Style: Brief", "User prefers concise, summarized responses.")
        if any(w in q for w in ["detail", "breakdown", "full", "comprehensive", "deep dive", "تفصيل", "تفصيلي", "بالتفصيل"]):
            record("pref_response_detailed", "Response Style: Detailed", "User prefers detailed breakdowns with full data.")
        if any(w in q for w in ["table", "tabular", "grid", "جدول"]):
            record("pref_format_table", "Format: Tables", "User prefers tabular output for financial data.")
        if any(w in q for w in ["bullet", "list", "قائمة", "نقاط"]):
            record("pref_format_bullets", "Format: Bullets", "User prefers bullet-point formatted responses.")
        if any(w in q for w in ["chart", "graph", "visual", "رسم", "مخطط"]):
            record("pref_format_chart", "Format: Charts", "User prefers chart or visual representations.")

        # ── 3. CURRENCY / DISPLAY PREFERENCES ───────────────────────────────
        if any(w in q for w in ["in egp", "بالجنيه", "جنيه مصري", "egp only"]):
            record("pref_currency_egp", "Currency Preference: EGP", "User prefers all amounts displayed in EGP.", confidence=1.0)
        if any(w in q for w in ["in usd", "in dollars", "بالدولار", "usd only"]):
            record("pref_currency_usd", "Currency Preference: USD", "User prefers amounts displayed in USD.", confidence=1.0)

        # ── 4. LANGUAGE PREFERENCE ───────────────────────────────────────────
        total_chars = len(user_query or "")
        if total_chars > 0:
            arabic_chars = sum(1 for c in (user_query or "") if "\u0600" <= c <= "\u06ff")
            ratio = arabic_chars / total_chars
            if ratio >= 0.4:
                record("pref_language_arabic", "Language: Arabic", "User communicates in Arabic; AI should respond in Arabic.", confidence=1.0)
            elif ratio < 0.05 and total_chars > 10:
                record("pref_language_english", "Language: English", "User communicates in English; AI should respond in English.", confidence=0.95)

        # ── 5. EXPLICIT USER DIRECTIVES ─────────────────────────────────────
        # Captures verbatim any instruction-like statement from the user.
        directive_triggers_en = ["always", "never", "please always", "stop", "don't", "do not", "i want you to", "i need you to", "from now on", "make sure"]
        directive_triggers_ar = ["دائماً", "أبداً", "لا تفعل", "أريدك أن", "من الآن", "تأكد", "لا تعطيني", "أوقف"]
        if any(t in q for t in directive_triggers_en + directive_triggers_ar):
            directive_key = "directive_" + str(abs(hash(q[:80])))[:10]
            record(
                directive_key,
                "User Directive",
                f"User stated: \"{(user_query or '').strip()[:300]}\"",
                confidence=1.0,
            )

        # ── 6. POSITIVE FEEDBACK SIGNALS ────────────────────────────────────
        # When user confirms AI response quality, record what worked.
        positive_signals = ["perfect", "exactly", "great", "that's right", "correct", "good job", "ممتاز", "صح", "كده تمام", "برافو"]
        if any(s in q for s in positive_signals) and r:
            feedback_key = "feedback_positive_" + str(abs(hash(r[:60])))[:8]
            record(
                feedback_key,
                "Positive Feedback Signal",
                f"User confirmed satisfaction with a response about: \"{r[:150]}\"",
                category="app_evolution",
                confidence=0.7,
            )

        # ── 7. NEGATIVE FEEDBACK / CORRECTION SIGNALS ───────────────────────
        negative_signals = ["wrong", "incorrect", "not right", "that's not", "no that", "you're wrong", "خطأ", "غلط", "ده مش", "مش صح"]
        if any(s in q for s in negative_signals):
            correction_key = "correction_" + str(abs(hash(q[:80])))[:10]
            record(
                correction_key,
                "User Correction",
                f"User flagged incorrect response. Query: \"{(user_query or '').strip()[:200]}\"",
                category="app_evolution",
                confidence=1.0,
            )

        return extracted

    @classmethod
    def build_knowledge_context(cls, user: Any = None, query: str = "") -> str:
        """
        Formats system knowledge manifest and active database knowledge entries into concise system directives.
        """
        from core.services.ai.system_knowledge_engine import SystemKnowledgeEngine

        parts = []
        system_knowledge = SystemKnowledgeEngine.build_system_knowledge_context(query=query)
        if system_knowledge:
            parts.append(system_knowledge)

        entries = cls.get_active_knowledge_entries()
        if entries:
            lines = ["\n\nDYNAMIC USER & APPLICATION PREFERENCES:"]
            for entry in entries[:15]:  # Top 15 knowledge entries
                lines.append(f"- [{entry.category.upper()}] {entry.title}: {entry.content}")
            parts.append("\n".join(lines))

        return "".join(parts)

