# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false, reportRedeclaration=false, reportAssignmentType=false
import json
from pathlib import Path
from django.conf import settings
from core.models import EmailTemplate
from core.authentication.emails import EMAIL_TEMPLATE_DEFINITIONS

class EmailTemplateService:
    locale_dir = Path(settings.BASE_DIR) / "static" / "i18n"

    @classmethod
    def _load_locale(cls, lang: str) -> dict:
        """Load the locale JSON file for the given language, returning an empty dict on failure."""
        path = cls.locale_dir / f"{lang}.json"
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    @classmethod
    def _available_languages(cls) -> list[str]:
        """Return the sorted list of languages available as JSON locale files."""
        return sorted(path.stem for path in cls.locale_dir.glob("*.json"))

    @classmethod
    def ensure_defaults(cls) -> None:
        """Populate missing per-language translations for all defined email templates from locale files."""
        languages = cls._available_languages()
        locale_map = {lang: cls._load_locale(lang) for lang in languages}
        for definition in EMAIL_TEMPLATE_DEFINITIONS:
            template, _ = EmailTemplate.objects.get_or_create(key=definition["key"])
            subject_translations = dict(template.subject_translations or {})
            body_translations = dict(template.body_translations or {})
            description_translations = dict(template.description_translations or {})
            changed = False
            for lang in languages:
                lang_dict = locale_map.get(lang, {})
                subject_value = lang_dict.get(definition["subject_key"], "")
                body_value = lang_dict.get(definition["body_key"], "")
                description_value = lang_dict.get(definition["description_key"], "")
                if subject_value and not subject_translations.get(lang):
                    subject_translations[lang] = subject_value
                    changed = True
                if body_value and not body_translations.get(lang):
                    body_translations[lang] = body_value
                    changed = True
                if description_value and not description_translations.get(lang):
                    description_translations[lang] = description_value
                    changed = True
            if changed:
                template.subject_translations = subject_translations
                template.body_translations = body_translations
                template.description_translations = description_translations
                template.save(update_fields=[
                    "subject_translations",
                    "body_translations",
                    "description_translations",
                    "updated_at",
                ])

    @classmethod
    def list_templates(cls, lang: str) -> list[dict]:
        """Ensure defaults exist and return all email templates as dicts for the given language."""
        cls.ensure_defaults()
        return [item.to_dict(lang) for item in EmailTemplate.objects.all()]

    @classmethod
    def update_template(cls, template: EmailTemplate, lang: str, subject: str, body: str) -> EmailTemplate:
        """Set the subject and body translations for the given language and save the template."""
        cls.ensure_defaults()
        subjects = dict(template.subject_translations or {})
        bodies = dict(template.body_translations or {})
        subjects[lang] = subject
        bodies[lang] = body
        template.subject_translations = subjects
        template.body_translations = bodies
        template.save(update_fields=["subject_translations", "body_translations", "updated_at"])
        return template

    @classmethod
    def render_preview(cls, subject: str, body: str, context: dict) -> dict:
        """Render a preview of the subject and body by replacing placeholders using the context."""
        from core.services.shared.auth_workflow_service import AuthWorkflowService
        return {
            "subject": AuthWorkflowService.replace_placeholders(subject, context),
            "body": AuthWorkflowService.replace_placeholders(body, context),
        }
