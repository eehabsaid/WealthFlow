"""Where the chat domain (core/services/ai/domains.py) is applied to a model answer: after the model wrote it, before it is saved."""

from __future__ import annotations

from core.services.ai.domain_scope import guard_answer


def guard_text(domain: str, content: str, question: str, evidence: str) -> str:
    """`content` after the domain rules (out-of-scope token, invented future rows, invented figures in the App domain)."""
    return guard_answer(domain, content, question, evidence) if content else content


def guard_result(domain: str, result, question: str, hint: str = "") -> None:
    """The same for an Investigation: the evidence is what its tools returned (the answer is never judged against itself)."""
    if result.content:
        evidence = "\n".join([hint, *[text for _, _, text in result.results]])
        result.content = guard_text(domain, result.content, question, evidence)
