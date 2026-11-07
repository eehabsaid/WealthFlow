"""Small request/response types shared by the routes."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


class HttpError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status, self.code = status, code


@dataclass
class Req:
    server: object
    method: str
    path: str
    match: re.Match
    query: dict
    body: dict | None
    headers: object

    @property
    def service(self):
        return self.server.service

    @property
    def project(self):
        return self.server.project

    @property
    def keys(self):
        return self.server.keys

    def need(self, name: str) -> str:
        value = self.query.get(name)
        if not value:
            raise HttpError(400, "bad_request", f"missing '{name}'")
        return value

    def field(self, name: str, kind=str):
        if not isinstance(self.body, dict) or not isinstance(self.body.get(name), kind):
            raise HttpError(400, "bad_request", f"'{name}' is required ({kind.__name__})")
        return self.body[name]


@dataclass
class Resp:
    body: object = None
    status: int = 200
    ctype: str = "application/json; charset=utf-8"
    headers: dict = field(default_factory=dict)


@dataclass
class Stream:
    """A long-lived response (server-sent events): `run(write)` writes until the client goes away."""
    run: object
