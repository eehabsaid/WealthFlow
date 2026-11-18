"""Manage the code knowledge index (separate SQLite file, source only).

  python manage.py knowledge_index status     health: version, counts, files that differ from disk
  python manage.py knowledge_index update     incremental refresh (hash based; renames/deletes handled)
  python manage.py knowledge_index rebuild    drop and rebuild everything
  python manage.py knowledge_index embed      embed symbols with the configured ai_embed_model (needs Ollama; optional)
"""

import json

from django.core.management.base import BaseCommand

from ai.services.knowledge_index import indexer, store, vectors


class Command(BaseCommand):
    help = "Build, refresh, inspect or rebuild the AI code knowledge index."

    def add_arguments(self, parser):
        parser.add_argument("action", choices=["status", "update", "rebuild", "embed"])
        parser.add_argument("--limit", type=int, default=500, help="symbols to embed per run (embed only)")

    def handle(self, *args, **options):
        action = options["action"]
        if action == "status":
            result = indexer.status()
        elif action in ("update", "rebuild"):
            result = indexer.refresh(full=action == "rebuild")
        else:
            conn = store.connect()
            try:
                result = vectors.embed_pending(conn, options["limit"])
            finally:
                conn.close()
        self.stdout.write(json.dumps(result, indent=2, default=str))
