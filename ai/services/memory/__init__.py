"""Cross-chat memory for the AI: notes the model writes for itself, an index in every new chat's prompt, and a read_memory tool."""

from ai.services.memory.index import build_memory_block, build_memory_block_for_ui
from ai.services.memory.scheduler import schedule_memory_update
from ai.services.memory.store import apply_edits, list_notes
from ai.services.memory.writer import update_memory

__all__ = ["build_memory_block", "build_memory_block_for_ui", "schedule_memory_update", "apply_edits", "list_notes", "update_memory"]
