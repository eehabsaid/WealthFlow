from __future__ import annotations

import json
from datetime import date

from django.core.management.base import BaseCommand

from core.services.shared.automation_service import AutomationService


class Command(BaseCommand):
    help = "Run all automated WealthFlow jobs"

    def add_arguments(self, parser):
        parser.add_argument("--today", type=str, default="", help="Override automation date (YYYY-MM-DD)")

    def handle(self, *args, **options):
        today_value = options.get("today") or ""
        today = date.fromisoformat(today_value) if today_value else None
        results = AutomationService().run_all(today=today)
        self.stdout.write(json.dumps(results, ensure_ascii=False, indent=2, default=str))
