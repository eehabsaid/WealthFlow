"""python manage.py ai_setup [--check]: prepare a host project for the AI app (idempotent).

1. checks INSTALLED_APPS, URLs, settings and third-party packages and tells what is missing,
2. creates coding_agent/ (runtime data outside the package) from ai/coding_agent_template/ when it is absent,
The AI default prompts and settings are created on first use; nothing else needs seeding.
Run `python manage.py migrate` first. Nothing outside ai/ is read except the files listed in ai/INSTALL.md.
"""
import importlib
import shutil
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.urls import Resolver404, resolve

REQUIRED = {"requests": "requests", "cryptography": "cryptography"}
OPTIONAL = {"openpyxl": "Excel exports", "reportlab": "PDF exports", "docx": "Word exports (python-docx)",
            "pypdf": "reading PDFs", "PIL": "images (Pillow)", "playwright": "browser tools / documentation screenshots"}
TEMPLATE = Path(__file__).resolve().parents[2] / "coding_agent_template"


class Command(BaseCommand):
    help = "Check the host project's AI wiring and create the coding_agent/ runtime folder."

    def add_arguments(self, parser):
        parser.add_argument("--check", action="store_true", help="only report, create nothing")

    def handle(self, *args, **opts):
        problems = self._check()
        if not opts["check"]:
            self._init_runtime()
        for p in problems:
            self.stdout.write(self.style.WARNING("  - " + p))
        self.stdout.write(self.style.ERROR("AI setup needs attention.") if problems else self.style.SUCCESS("AI setup OK."))

    def _check(self) -> list[str]:
        out = []
        if "ai" not in {c.label for c in __import__("django.apps", fromlist=["apps"]).apps.get_app_configs()}:
            out.append('add "ai" to INSTALLED_APPS')
        try:
            resolve("/api/settings/ai/")
        except Resolver404:
            out.append('add path("", include("ai.urls")) to the root urls.py')
        if not getattr(settings, "AI_PACKS", None):
            self.stdout.write("  (no AI_PACKS: generic features only)")
        for mod, why in REQUIRED.items():
            if not self._has(mod):
                out.append(f"pip install {why} (required)")
        for mod, why in OPTIONAL.items():
            if not self._has(mod):
                self.stdout.write(f"  (optional, missing: {mod} - {why})")
        return out

    @staticmethod
    def _has(mod) -> bool:
        try:
            importlib.import_module(mod)
            return True
        except ImportError:
            return False

    def _init_runtime(self):
        from ai.services.coding import AGENT_DIR
        if AGENT_DIR.exists():
            self.stdout.write(f"  coding_agent/ already there: {AGENT_DIR}")
            return
        shutil.copytree(TEMPLATE, AGENT_DIR)
        self.stdout.write(self.style.SUCCESS(f"  created {AGENT_DIR}"))
