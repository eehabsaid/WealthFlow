"""Hand-specified glue applied after the mechanical move (assertive, idempotent)."""
import ast
import os

from . import rules

PKG_DOC = '"""%s"""\n'


def _write(root, rel, text):
    p = os.path.join(root, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    if not os.path.exists(p):
        with open(p, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)


def _sub(root, rel, old, new, count=1):
    p = os.path.join(root, rel)
    with open(p, encoding="utf-8", newline="") as fh:
        s = fh.read()
    if old not in s:
        raise RuntimeError(f"scaffold anchor not found in {rel}: {old[:60]!r}")
    with open(p, "w", encoding="utf-8", newline="") as fh:
        fh.write(s.replace(old, new, count))


def _add_db_tables(root):
    for m in rules.MODEL_FILES:
        rel = f"ai/models/{m}.py"
        p = os.path.join(root, rel)
        with open(p, encoding="utf-8", newline="") as fh:
            src = fh.read()
        lines = src.split("\n")
        tree = ast.parse(src)
        ins = []
        for c in tree.body:
            if isinstance(c, ast.ClassDef):
                for b in c.body:
                    if isinstance(b, ast.ClassDef) and b.name == "Meta":
                        if any("db_table" in ast.dump(x) for x in b.body):
                            continue
                        ins.append((b.lineno, f'db_table = "core_{c.name.lower()}"'))
        for lineno, text in sorted(ins, reverse=True):
            lines.insert(lineno, "        " + text)
        with open(p, "w", encoding="utf-8", newline="") as fh:
            fh.write("\n".join(lines))


def apply(root):
    _write(root, "ai/__init__.py", PKG_DOC % "Self-contained AI app (chat, agents, knowledge, training, docs).")
    _write(root, "ai/integrations/__init__.py", PKG_DOC % "AI provider clients (Ollama, Claude, Gemini, OpenAI, Azure).")
    _write(root, "ai/views/__init__.py", PKG_DOC % "AI views: chat, platform, speech, settings.")
    imports = "\n".join(f"from .{m} import *  # noqa: F401,F403" for m in rules.MODEL_FILES)
    _write(root, "ai/models/__init__.py", PKG_DOC % "The AI models (tables keep their core_ai* names)." + imports + "\n")
    _write(root, "ai/apps.py", (
        "from django.apps import AppConfig\n\n\nclass AIConfig(AppConfig):\n"
        "    name = \"ai\"\n    label = \"ai\"\n\n"
        "    def ready(self) -> None:\n"
        "        \"\"\"Autodiscover AI context providers and capabilities at startup.\"\"\"\n"
        "        try:\n"
        "            from ai.services.providers.registry import autodiscover_providers\n"
        "            from ai.services.capability_registry import CapabilityRegistry\n\n"
        "            autodiscover_providers()\n            CapabilityRegistry.autodiscover()\n"
        "        except Exception:\n            pass\n"))
    _add_db_tables(root)
    _sub(root, "ai/training/apps.py", 'name = "ai_training"', 'name = "ai.training"\n    label = "ai_training"')
    _sub(root, "wealthflow/settings.py", '    "ai_training",\n', '    "ai",\n    "ai.training",\n')
