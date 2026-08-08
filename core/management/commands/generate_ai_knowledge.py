"""
Django Management Command to regenerate AI System Knowledge files from Django model metadata.
Usage: python manage.py generate_ai_knowledge
"""

from django.core.management.base import BaseCommand
from core.services.ai.knowledge_generator import KnowledgeGenerator


class Command(BaseCommand):
    help = "Auto-generates WealthFlow AI database schema documentation and updates knowledge manifest metadata."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting AI System Knowledge generation..."))
        result = KnowledgeGenerator.generate_all()
        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully generated AI database schema knowledge!\n"
                f"- Models introspected: {result['models_count']}\n"
                f"- Schema path: {result['schema_path']}\n"
                f"- Timestamp: {result['generated_at']}"
            )
        )
