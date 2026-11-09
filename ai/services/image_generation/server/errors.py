"""Errors of the managed image server (kept apart so providers can convert them without an import cycle)."""


class ServerError(Exception):
    """Startup / lifecycle failure with a short, user-safe message (includes the tail of the server's own log when it helps)."""
