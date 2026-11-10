"""Re-export: the implementation now lives in ai.integrations.http (ai/ owns it so it can be copied alone)."""
from ai.integrations.http import make_json_http_request  # noqa: F401

__all__ = ["make_json_http_request"]
