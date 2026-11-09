"""The generated schema doc must still list the AI models after they moved from core to the ai app."""
from django.test import SimpleTestCase

from ai.services.knowledge_generator import KnowledgeGenerator


class SchemaIncludesAIModelsTests(SimpleTestCase):
    def test_ai_models_are_inspected(self):
        names = {spec["name"] for spec in KnowledgeGenerator.inspect_models()}
        for expected in ("AIConversation", "AIMessage", "AIPrompt", "AIAttachment", "AIChatBlock", "AIMemoryNote"):
            self.assertIn(expected, names)
