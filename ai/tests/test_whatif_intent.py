"""Intent-recognition tests: natural-language what-if questions in all four
supported languages must activate the what_if_simulator advisor service, while
unrelated questions must not."""

from __future__ import annotations

from django.test import SimpleTestCase

from ai.services.context_builder_service.service import ContextBuilderService


class WhatIfIntentTest(SimpleTestCase):
    def test_natural_language_what_if_questions_activate_the_service(self):
        svc = ContextBuilderService()
        questions = {
            "en": "What happens if my salary increases by 15%?",
            "en2": "If I save another 2,500 every month, when will I reach my goal?",
            "ar": "لو زادت مصروفاتي 2000 كل شهر، هل أستطيع الادخار؟",
            "fr": "Si mon salaire augmente de 15 %, que se passe-t-il ?",
            "de": "Was passiert, wenn mein Gehalt um 15 % steigt?",
        }
        for q in questions.values():
            self.assertIn("what_if_simulator", svc.determine_relevant_services(q), q)

    def test_unrelated_question_does_not_activate_what_if(self):
        svc = ContextBuilderService()
        self.assertNotIn("what_if_simulator", svc.determine_relevant_services("list my daily expenses"))
