"""
Manifest & knowledge-file loading for the System Knowledge Engine.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from django.conf import settings

logger = logging.getLogger(__name__)

_KNOWLEDGE_CACHE: Dict[str, Any] = {}


def get_knowledge_dir() -> Path:
    base_dir = getattr(settings, "BASE_DIR", None)
    if base_dir:
        return Path(base_dir) / "ai_knowledge"
    return Path(__file__).resolve().parent.parent.parent.parent.parent / "ai_knowledge"


def get_version_metadata(knowledge_dir: Path | None = None) -> Dict[str, Any]:
    """Exposes manifest versioning metadata for diagnostics and cache validation."""
    try:
        knowledge_dir = knowledge_dir if knowledge_dir is not None else get_knowledge_dir()
        manifest_path = knowledge_dir / "MANIFEST.json"
        if not manifest_path.exists():
            return {"status": "missing", "knowledge_version": "0.0.0"}

        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {
                "status": "active",
                "manifest_version": data.get("manifest_version", "1.0.0"),
                "knowledge_version": data.get("knowledge_version", "1.0.0"),
                "schema_version": data.get("schema_version", "1.0.0"),
                "generated_at": data.get("generated_at", ""),
                "application_version": data.get("application_version", "1.0.0"),
            }
    except Exception as exc:
        logger.warning("Failed to read knowledge version metadata: %s", exc)
        return {"status": "error", "error": str(exc), "knowledge_version": "0.0.0"}


def load_manifest(force_refresh: bool = False, knowledge_dir: Path | None = None) -> List[Dict[str, Any]]:
    try:
        if not force_refresh and "manifest" in _KNOWLEDGE_CACHE:
            return _KNOWLEDGE_CACHE["manifest"]

        knowledge_dir = knowledge_dir if knowledge_dir is not None else get_knowledge_dir()
        manifest_path = knowledge_dir / "MANIFEST.json"

        if not manifest_path.exists():
            logger.warning("ai_knowledge/MANIFEST.json not found at %s", manifest_path)
            return []

        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            sections = data.get("sections", [])
            if isinstance(sections, list):
                _KNOWLEDGE_CACHE["manifest"] = sections
                return sections
            return []
    except Exception as exc:
        logger.error("Failed to load ai_knowledge/MANIFEST.json gracefully: %s", exc)
        return []


def load_section_content(file_name: str, force_refresh: bool = False, knowledge_dir: Path | None = None) -> str:
    try:
        if not file_name:
            return ""

        cache_key = f"content:{file_name}"
        if not force_refresh and cache_key in _KNOWLEDGE_CACHE:
            return _KNOWLEDGE_CACHE[cache_key]

        knowledge_dir = knowledge_dir if knowledge_dir is not None else get_knowledge_dir()
        file_path = knowledge_dir / file_name

        if not file_path.exists():
            logger.warning("Knowledge file %s not found at %s", file_name, file_path)
            return ""

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            _KNOWLEDGE_CACHE[cache_key] = content
            return content
    except Exception as exc:
        logger.error("Failed to read knowledge file %s gracefully: %s", file_name, exc)
        return ""


def clear_cache() -> None:
    _KNOWLEDGE_CACHE.clear()
