"""Errors the service raises; the HTTP layer maps `code` to a status."""

from __future__ import annotations


class ServiceError(RuntimeError):
    def __init__(self, message: str, code: str = "bad_request"):
        super().__init__(message)
        self.code = code


class Busy(ServiceError):
    def __init__(self, message: str = "another task is running; stop it or wait"):
        super().__init__(message, "busy")
