"""Shared, safe parsing of JSON request bodies.

Malformed JSON must answer 400, never 500. Views call parse_json_body();
BadJsonError subclasses json.JSONDecodeError, so existing
``except (json.JSONDecodeError, ValueError)`` blocks keep working, and any
BadJsonError left uncaught is turned into a 400 by JsonBodyErrorMiddleware.
"""
import json

DEFAULT_MESSAGE = "Invalid JSON body"


class BadJsonError(json.JSONDecodeError):
    def __init__(self, message: str = DEFAULT_MESSAGE):
        super().__init__(message, "", 0)
        self.message = message

    def __str__(self):
        return self.message


def parse_json_body(request, *, allow_list: bool = False):
    """Return the request body parsed as a JSON object (or list if allowed).

    An empty body yields {}. Invalid UTF-8/JSON or a body of the wrong type
    raises BadJsonError.
    """
    raw = request.body
    if not raw or not raw.strip():
        return {}
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise BadJsonError() from None
    if isinstance(data, dict) or (allow_list and isinstance(data, list)):
        return data
    raise BadJsonError("JSON body must be an object")
