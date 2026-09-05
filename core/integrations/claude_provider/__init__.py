"""
claude_provider package
========================
Split from the former `claude_provider.py` module (200-line refactor).

Sibling files:
- constants.py          CLAUDE_DEFAULT_MODELS fallback list.
- config_mixin.py        ClaudeConfigMixin — from_settings(), get_config_schema(),
                         capabilities property.
- request_mixin.py       ClaudeRequestMixin — _convert_tools(), generate().
- connection_mixin.py    ClaudeConnectionMixin — check_connection(),
                         list_models(), check_model_available().
- provider.py            ClaudeProvider — composes the mixins above.

`make_json_http_request` is re-exported here (not just imported where used)
so `unittest.mock.patch("core.integrations.claude_provider.make_json_http_request")`
keeps working post-split — request_mixin.py and connection_mixin.py call it
via this package's namespace rather than a direct name-bound import.

Update this docstring whenever a sibling file is added, removed, or its
responsibility changes.
"""

from __future__ import annotations

from core.integrations.claude_provider.provider import ClaudeProvider
from core.integrations.provider_utils import make_json_http_request

__all__ = ["ClaudeProvider", "make_json_http_request"]
