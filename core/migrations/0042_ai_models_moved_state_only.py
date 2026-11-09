"""State-only removal of the 9 AI models from app core (they now live in app ai).

HAND-WRITTEN on purpose (approved exception): a generated migration would DROP the core_ai* tables.
No table is touched (the only database step removes empty duplicate ContentType rows).
Never regenerate or edit this file.
"""
from django.db import migrations

from ai.migrations_support import relabel_forward

# Children first, so no model is deleted while another still points at it.
_ORDER = ["AIAnswerFeedback", "AIAttachment", "AIChatBlock", "AIMessage", "AIMemoryNote",
          "AIConversation", "AIPrompt", "AIPromptCategory", "AIKnowledgeEntry"]


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0041_monthly_income_adjustment"),
        ("ai", "0001_initial"),
    ]
    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[migrations.DeleteModel(name=n) for n in _ORDER],
            # Only removes empty duplicate ContentType rows left by a partial migrate; no table is touched.
            database_operations=[migrations.RunPython(relabel_forward, migrations.RunPython.noop)],
        ),
    ]
