from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Decision:
    action: str          # "allow" | "ask" | "deny"
    reason: str = ""
    kind: str = ""      # why an `ask`: "unlisted" = a harmless command that is merely not on the allow list (the owner can switch this approval off)


ALLOW = Decision("allow")


def deny(reason: str) -> Decision:
    return Decision("deny", reason)


def ask(reason: str, kind: str = "") -> Decision:
    return Decision("ask", reason, kind)
