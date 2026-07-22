import os
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from doc_engine.config import MANIFEST_FILE, METADATA_FILE, STATUS_FILE, CANCEL_FILE, RUNTIME_DIR

class DocumentationMetadataService:
    """
    Manages manifest generation, metadata tracking, and status file updates for screenshot capture.
    Centralizes runtime artifact tracking across all Playwright backends.
    """
    def __init__(self, language: str = 'en', theme: str = 'dark', device: Optional[str] = None):
        self.language = language
        self.theme = theme
        self.device = device or 'desktop'

        self.start_time = datetime.now()
        self.start_time_iso = self.start_time.isoformat()
        
        self.screenshots_count = 0
        self.current_progress = 0
        self.total_items: Optional[int] = None
        self.failed_pages: List[Dict[str, str]] = []

        self.manifest = {
            "schema_version": 1,
            "application": "WealthFlow",
            "version": "1.0",
            "generated_at": datetime.now().isoformat(),
            "pages": []
        }

    def check_cancelled(self) -> bool:
        """Checks if cancellation has been requested via .cancel_capture flag file."""
        return os.path.exists(CANCEL_FILE)

    def record_screenshot(self, context_dict: Dict[str, Any], filename: str) -> None:
        """Appends a screenshot entry to the in-memory manifest data structure."""
        page_entry = {
            "page_id": context_dict.get("page_id"),
            "page_title": context_dict.get("page_title"),
            "route": context_dict.get("route"),
            "tab_id": context_dict.get("tab_id"),
            "tab_order": context_dict.get("tab_order", 0),
            "nested_tab_id": context_dict.get("nested_tab_id"),
            "nested_tab_order": context_dict.get("nested_tab_order", 0),
            "modal_id": context_dict.get("modal_id"),
            "modal_order": context_dict.get("modal_order", 0),
            "language": self.language,
            "theme": self.theme,
            "device": self.device,
            "is_admin": context_dict.get("is_admin", False),
            "filename": f"{filename}.png",
            "screenshot_path": f"screenshots/{filename}.png",
            "capture_timestamp": datetime.now().isoformat()
        }
        self.manifest["pages"].append(page_entry)
        self.screenshots_count += 1

    def update_status(self, status: str, page_name: str = '', tab_name: str = '', error: str = '') -> None:
        """Writes current capture execution status to runtime/status.json."""
        now = datetime.now()
        elapsed = int((now - self.start_time).total_seconds())

        finished_at = ""
        if status in ("finished", "cancelled", "COMPLETED", "FAILED"):
            finished_at = now.isoformat()

        data = {
            "status": status,
            "page": page_name,
            "tab": tab_name,
            "language": self.language,
            "theme": self.theme,
            "device": self.device,
            "progress": self.current_progress,
            "total": self.total_items,
            "screenshots_count": self.screenshots_count,
            "started_at": self.start_time_iso,
            "finished_at": finished_at,
            "elapsed_seconds": elapsed,
            "error": error,
            "failed_pages": self.failed_pages
        }

        os.makedirs(RUNTIME_DIR, exist_ok=True)
        with open(STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def save_manifest_and_metadata(self) -> None:
        """Writes manifest.json and capture_metadata.json to runtime directory."""
        os.makedirs(RUNTIME_DIR, exist_ok=True)

        with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
            json.dump(self.manifest, f, indent=2, ensure_ascii=False)

        unique_pages = len(set(p["page_id"] for p in self.manifest["pages"] if p.get("page_id")))

        metadata = {
            "schema_version": 1,
            "wealthflow_version": self.manifest.get("version", "1.0"),
            "capture_timestamp": datetime.now().isoformat(),
            "language": self.language,
            "theme": self.theme,
            "device": self.device,
            "screenshots": self.screenshots_count,
            "pages": unique_pages,
            "status": "Completed"
        }

        with open(METADATA_FILE, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

# Backward compatibility alias
ManifestService = DocumentationMetadataService
