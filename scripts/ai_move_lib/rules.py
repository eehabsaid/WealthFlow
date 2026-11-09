"""Declarative move rules: (old repo-relative path, new repo-relative path).

Directories move with all their contents. Dotted module names are derived
from the paths. Edit only this table to change what moves where.
"""

MODEL_FILES = ["ai_attachment", "ai_chat_block", "ai_conversation", "ai_feedback",
               "ai_knowledge", "ai_memory", "ai_message", "ai_prompt"]

RULES = (
    [("core/services/ai", "ai/services")]
    + [(f"core/models/{m}.py", f"ai/models/{m}.py") for m in MODEL_FILES]
    + [
        ("core/views/ai_chat", "ai/views/ai_chat"),
        ("core/views/ai_chat_views.py", "ai/views/ai_chat_views.py"),
        ("core/views/ai_prompt_views.py", "ai/views/ai_prompt_views.py"),
        ("core/views/ai_platform_views", "ai/views/ai_platform"),
        ("core/views/ai_speech", "ai/views/ai_speech"),
        ("core/views/exports_ai_features.py", "ai/views/exports.py"),
        ("core/views/settings/ai", "ai/views/settings"),
        ("core/urls/ai_platform_urls.py", "ai/urls_platform.py"),
        ("core/integrations/ai_provider", "ai/integrations/ai_provider"),
        ("core/integrations/claude_provider", "ai/integrations/claude_provider"),
        ("core/integrations/gemini_provider", "ai/integrations/gemini_provider"),
        ("core/integrations/openai_provider", "ai/integrations/openai_provider"),
        ("core/integrations/azure_openai_provider", "ai/integrations/azure_openai_provider"),
        ("ai_training", "ai/training"),
        ("ai_knowledge", "ai/knowledge"),
        ("doc_engine", "ai/doc_engine"),
        ("dev_agent", "ai/dev_agent"),
        ("static/js/ai", "ai/static/ai/js"),
        ("static/css/ai", "ai/static/ai/css"),
        ("templates/partials/scripts/04_ai.html", "ai/templates/ai/scripts.html"),
    ]
)

# Test directories/files are classified by classify_tests.py (generic vs finance).
TEST_ROOT_OLD = "core/tests/ai"
TEST_ROOT_GENERIC = "ai/tests"
TEST_ROOT_FINANCE = "core/tests/ai_pack"

# String rewrites that are not path/dotted derived: (regex, replacement, why).
EXTRA_STRING_RULES = [
    (r"\{% static 'css/ai/", "{% static 'ai/css/", "template static css"),
    (r"\{% static 'js/ai/", "{% static 'ai/js/", "template static js"),
    (r"(?<![\w/])css/ai/", "ai/css/", "static css path string"),
    (r"(?<![\w/])js/ai/", "ai/js/", "static js path string"),
    (r"partials/scripts/04_ai\.html", "ai/scripts.html", "template name"),
]

# Old names that legitimately remain (logger names, DB table names, prose).
ALLOWED_OLD_STRINGS = ["core.ai.pipeline", "core_ai"]

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv",
             ".pytest_cache", "staticfiles", "htmlcov"}
SKIP_FILES = {"db.sqlite3"}
TEXT_EXT = {".py", ".js", ".ts", ".json", ".html", ".css", ".md", ".txt", ".ini",
            ".cfg", ".toml", ".yml", ".yaml", ".bat", ".ps1", ".sh", ".cjs", ".mjs"}
