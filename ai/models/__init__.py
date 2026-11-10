"""The AI models (tables keep their core_ai* names)."""
from .ai_attachment import AIAttachment
from .ai_chat_block import AIChatBlock
from .ai_conversation import AIConversation
from .ai_feedback import AIAnswerFeedback
from .ai_knowledge import AIKnowledgeEntry
from .ai_memory import AIMemoryNote
from .ai_message import AIMessage
from .ai_setting import AISetting
from .ai_prompt import AIPrompt, AIPromptCategory

__all__ = ["AIAnswerFeedback", "AIAttachment", "AIChatBlock", "AIConversation", "AIKnowledgeEntry",
           "AIMemoryNote", "AIMessage", "AIPrompt", "AIPromptCategory", "AISetting"]
