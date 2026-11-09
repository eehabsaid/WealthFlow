"""TranslationMixin: single-key and title lookups against the loaded
translation dict (populated by ValidationMixin._validate_inputs). See this
package's __init__.py for the sibling list and composition conventions."""
import logging

logger = logging.getLogger(__name__)


class TranslationMixin:
    def _t(self, key):
        if not hasattr(self, 'translations'):
            return key
        if key not in self.translations:
            logger.warning(f"Missing translation key: {key}")
            if f"Missing translation key: {key}" not in self.validation_warnings:
                self.validation_warnings.append(f"Missing translation key: {key}")
            return key
        return self.translations[key]

    def _t_title(self, text):
        if not text:
            return text
        text_strip = text.strip()
        # Direct key lookup
        if text_strip in self.translations:
            return self.translations[text_strip]
        # Reverse English lookup
        key = self.reverse_en.get(text_strip)
        if key and key in self.translations:
            return self.translations[key]
        return text

