"""
AST-based Codebase Structural Indexer for AI architecture reasoning.
Builds structured architectural knowledge of models, services, views, serializers, and utilities
WITHOUT executing code, modifying files, or dumping raw source code.

CRITICAL CONSTRAINT: 100% READ-ONLY. Zero write/save/delete calls.
"""

from __future__ import annotations

import ast
import os
import time
from typing import Any
from django.conf import settings

_CODEBASE_INDEX_CACHE: dict[str, Any] = {}
_CACHE_TTL_SECONDS = 600.0


class CodebaseIndexer:
    """
    Scans Python source files in core/ and builds a structured, searchable architectural index.
    """

    @classmethod
    def get_index(
        self,
        search_term: str = "",
        module_type: str = "",
        class_name: str = "",
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        now = time.time()
        cached_time = _CODEBASE_INDEX_CACHE.get("timestamp", 0)

        if not force_refresh and (now - cached_time < _CACHE_TTL_SECONDS) and "index" in _CODEBASE_INDEX_CACHE:
            items = _CODEBASE_INDEX_CACHE["index"]
        else:
            items = self._scan_core_codebase()
            _CODEBASE_INDEX_CACHE["timestamp"] = now
            _CODEBASE_INDEX_CACHE["index"] = items

        # Filter items
        filtered = items
        term = str(search_term or "").strip().lower()
        m_type = str(module_type or "").strip().lower()
        c_name = str(class_name or "").strip().lower()

        if m_type:
            filtered = [i for i in filtered if i.get("module_type", "").lower() == m_type]

        if c_name:
            filtered = [i for i in filtered if c_name in i.get("class_name", "").lower()]

        if term:
            matched = []
            for i in filtered:
                match_txt = (
                    f"{i.get('class_name', '')} {i.get('location', '')} "
                    f"{i.get('docstring', '')} {' '.join(i.get('methods', []))} "
                    f"{' '.join(i.get('dependencies', []))}"
                ).lower()
                if term in match_txt:
                    matched.append(i)
            filtered = matched

        return {
            "total_indexed_classes": len(items),
            "matching_results_count": len(filtered),
            "search_term": term,
            "module_type_filter": m_type,
            "class_name_filter": c_name,
            "architecture_index": filtered[:50],  # Return top 50 matches
        }

    @classmethod
    def _scan_core_codebase(cls) -> list[dict[str, Any]]:
        core_dir = os.path.join(settings.BASE_DIR, "core")
        indexed: list[dict[str, Any]] = []

        if not os.path.exists(core_dir):
            return indexed

        for root, _, files in os.walk(core_dir):
            for file in files:
                if not file.endswith(".py") or file.startswith("test"):
                    continue

                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, settings.BASE_DIR).replace("\\", "/")

                m_type = "utility"
                if "/services/" in rel_path:
                    m_type = "service"
                elif "/views/" in rel_path:
                    m_type = "view"
                elif "models" in rel_path:
                    m_type = "model"
                elif "serializers" in rel_path:
                    m_type = "serializer"
                elif "/integrations/" in rel_path:
                    m_type = "integration"

                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                        source_code = f.read()

                    tree = ast.parse(source_code, filename=rel_path)
                    file_imports = cls._extract_imports(tree)

                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            class_doc = ast.get_docstring(node) or ""
                            bases = [b.id for b in node.bases if isinstance(b, ast.Name)]
                            methods = [
                                m.name for m in node.body
                                if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))
                            ]

                            indexed.append({
                                "class_name": node.name,
                                "module_type": m_type,
                                "location": rel_path,
                                "base_classes": bases,
                                "docstring": class_doc.strip().split("\n")[0] if class_doc else "",
                                "full_docstring": class_doc.strip()[:300] if class_doc else "",
                                "methods": methods,
                                "dependencies": file_imports,
                            })
                except Exception:
                    pass

        return indexed

    @staticmethod
    def _extract_imports(tree: ast.AST) -> list[str]:
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
        return sorted(list(set(imports)))[:15]
