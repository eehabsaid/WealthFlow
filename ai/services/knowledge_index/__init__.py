"""Code-aware knowledge index for the AI investigator.

Structural index of the whole repository (Python AST, Django models/routes/migrations, JavaScript via Acorn or a pure-Python
scanner, templates, CSS, locale files, docs), kept in sync by content hash, with hybrid retrieval and trace tools.
Public API: refresh / status (indexer), search (module), relations, flow, diagnose, verify. Source only: no user data is ever indexed.
"""

from ai.services.knowledge_index.config import INDEX_VERSION
from ai.services.knowledge_index.indexer import refresh, status

__all__ = ["INDEX_VERSION", "refresh", "status"]   # submodules (search, relations, flow, ...) are imported by name; none is shadowed here
