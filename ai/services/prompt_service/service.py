"""
AIPromptService: composes the validation, query, and mutation mixins into
the single service-layer class used by AI Workspace Prompt Library views.
"""

from ai.services.prompt_service.validation_mixin import PromptValidationMixin
from ai.services.prompt_service.query_mixin import PromptQueryMixin
from ai.services.prompt_service.mutation_mixin import PromptMutationMixin


class AIPromptService(PromptValidationMixin, PromptQueryMixin, PromptMutationMixin):
    """
    Service layer providing business logic for AI Workspace Prompt Library.
    """
    pass
