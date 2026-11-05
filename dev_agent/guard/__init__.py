from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Decision:
    action: str          # "allow" | "ask" | "deny"
    reason: str = ""


ALLOW = Decision("allow")


def deny(reason: str) -> Decision:
    return Decision("deny", reason)


def ask(reason: str) -> Decision:
    return Decision("ask", reason)
