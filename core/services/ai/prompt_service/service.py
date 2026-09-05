"""
AIPromptService: composes the validation, query, and mutation mixins into
the single service-layer class used by AI Workspace Prompt Library views.
"""

from core.services.ai.prompt_service.validation_mixin import PromptValidationMixin
from core.services.ai.prompt_service.query_mixin import PromptQueryMixin
from core.services.ai.prompt_service.mutation_mixin import PromptMutationMixin


class AIPromptService(PromptValidationMixin, PromptQueryMixin, PromptMutationMixin):
    """
    Service layer providing business logic for AI Workspace Prompt Library.
    """
    pass
