"""AI Agent mode: the chat model owns the tool loop from the start (like Continue's Agent mode in VS Code).

  settings.py      global sysadmin switches/limits/instructions + the per-user Ask/Agent choice
  instructions.py  the default, editable investigation instructions (the app's ".continue/rules")
  control.py       Stop flag + the live step list the chat polls
  sources.py       "Sources" built from the tool calls that really ran
  stage.py         the chat stage: agent mode answers the question before any instant/normal path
The loop itself is core/services/ai/investigation/loop.py (shared with the auto-escalation investigator).
"""

from .settings import agent_active, agent_enabled, get_chat_mode, set_chat_mode

__all__ = ["agent_active", "agent_enabled", "get_chat_mode", "set_chat_mode"]
