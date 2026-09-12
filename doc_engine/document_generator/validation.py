"""ValidationMixin: loads and validates manifest/metadata inputs, builds
the DocumentationModel, and loads i18n translations for the run. See this
package's __init__.py for the sibling list and composition conventions."""
import os
import json
import logging

from ..config import METADATA_FILE
from ..models import DocumentationModel

logger = logging.getLogger(__name__)


class ValidationMixin:
    def _load_metadata(self):
        try:
            with open(METADATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return None

    def _validate_inputs(self):
        self.manifest = self.manifest_provider.load()
        self.content = self.content_provider.load()
        self.metadata = self._load_metadata()
        
        if not self.manifest:
            self.validation_errors.append("Fatal: manifest.json missing")
        if not self.metadata:
            self.validation_errors.append("Fatal: capture_metadata.json missing")
            
        if self.validation_errors:
            logger.error("Generation stopped due to fatal errors.")
            return False
            
        self.doc_model = DocumentationModel(self.manifest, self.content)
        self.validation_warnings.extend(self.doc_model.validation_warnings)
        
        # Load Translations
        self.translations = {}
        self.reverse_en = {}
        
        # Try metadata first, fallback to first page, default to 'en'
        lang = "en"
        if self.metadata and self.metadata.get("language"):
            lang = self.metadata.get("language")
        elif self.manifest and self.manifest.get("pages") and len(self.manifest["pages"]) > 0:
            lang = self.manifest["pages"][0].get("language", "en")
            
        lang = lang.lower()
        if lang == 'ar':
            lang = 'ar'
            
        i18n_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "i18n")
        
        # Load English for reverse lookup (to translate hardcoded English strings)
        en_path = os.path.join(i18n_dir, "en.json")
        try:
            if os.path.exists(en_path):
                with open(en_path, "r", encoding="utf-8") as f:
                    en_data = json.load(f)
                    self.reverse_en = {v.strip(): k for k, v in en_data.items() if isinstance(v, str)}
        except Exception as e:
            logger.warning(f"Could not load English translations for reverse lookup: {e}")

        i18n_path = os.path.join(i18n_dir, f"{lang}.json")
        try:
            if os.path.exists(i18n_path):
                with open(i18n_path, "r", encoding="utf-8") as f:
                    self.translations = json.load(f)
            else:
                self.validation_warnings.append(f"Translation file missing for language: {lang}")
        except Exception as e:
            logger.warning(f"Could not load translations for {lang}: {e}")
            
        return True

