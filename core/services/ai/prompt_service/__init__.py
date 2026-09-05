"""Umbrella re-export for the AI Prompt Library service, so both
core/services/ai/__init__.py and any other file can keep doing
`from core.services.ai.prompt_service import AIPromptService` unchanged,
without needing to know this moved from a flat
core/services/ai/prompt_service.py into this package.

ORGANIZING PRINCIPLE: mixin composition by concern for the single
AIPromptService class — validation, read queries, and write mutations.

STRUCTURE / CONVENTION:
  - validation_mixin.py   PromptValidationMixin — validate_prompt_data().
  - query_mixin.py        PromptQueryMixin — get_prompts(),
                           get_prompt_by_id(), get_categories().
  - mutation_mixin.py     PromptMutationMixin — create_prompt(),
                           update_prompt(), delete_prompt(),
                           toggle_favorite(), record_usage(),
                           duplicate_prompt(). Mutation methods call
                           validate_prompt_data() via a local import of
                           the composed AIPromptService (this package),
                           not a direct mixin reference, since these are
                           staticmethods invoked as `AIPromptService.x()`.
  - service.py            AIPromptService — composes the three mixins.
  - If any file here grows past ~200 lines, split it by concern into
    more files in this same folder.
  - Always update this __init__.py's imports/__all__ to match.
"""

from core.services.ai.prompt_service.service import AIPromptService

__all__ = ["AIPromptService"]
