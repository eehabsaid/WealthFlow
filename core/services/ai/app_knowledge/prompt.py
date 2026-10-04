"""Prompt for the how/where/should reasoning path. Small on purpose (CPU model, ~37 tok/s prefill):
instructions + a few knowledge chunks + a few approved examples + a tiny data slice + short history."""

from __future__ import annotations

from typing import Any, Sequence

MAX_CHUNKS, MAX_KNOWLEDGE_CHARS, HISTORY_MESSAGES, HISTORY_CHARS = 4, 2400, 4, 300
MIN_REL_SCORE = 0.4

INSTRUCTIONS = (
    "You are the WealthFlow assistant. Answer the user's how / where / should question about using the app.\n"
    "Use ONLY the APP KNOWLEDGE and the user's setup below; they describe what the app really does.\n"
    "Think it through: name the options the app offers, say what each one does to balances, expenses and "
    "net worth, then pick the best fit and say why. If the knowledge does not settle it, say what is uncertain "
    "and what to check, instead of guessing. Do not invent screens, fields or figures. "
    "At most 120 words, plain sentences, same language as the question."
)


def select_chunks(ranked: list[tuple[float, dict[str, Any]]]) -> list[tuple[float, dict[str, Any]]]:
    if not ranked:
        return []
    top, chosen, used = ranked[0][0], [], 0
    for score, chunk in ranked:
        if len(chosen) >= MAX_CHUNKS or score < MIN_REL_SCORE * top:
            break
        if used + len(chunk["text"]) > MAX_KNOWLEDGE_CHARS:
            continue
        chosen.append((score, chunk))
        used += len(chunk["text"])
    return chosen


def build_messages(question: str, chunks: list[dict[str, Any]], examples: list[dict[str, str]], data_slice: str,
                   history: Sequence[Any] = ()) -> list[dict[str, str]]:
    parts = [INSTRUCTIONS, "", "APP KNOWLEDGE:"]
    parts += [f"[{c['title']}] {c['text']}" for c in chunks] or ["(nothing relevant was found in the app documentation)"]
    if examples:
        parts += ["", "ANSWERS THE USER APPROVED FOR SIMILAR QUESTIONS (reuse the reasoning only if it fits this question):"]
        parts += [f"Q: {e['question']}\nA: {e['answer']}" for e in examples]
    if data_slice:
        parts += ["", data_slice]
    messages = [{"role": "system", "content": "\n".join(parts)}]
    for m in list(history)[-HISTORY_MESSAGES:]:
        if getattr(m, "role", "") in ("user", "assistant") and (m.content or "").strip():
            messages.append({"role": m.role, "content": m.content[:HISTORY_CHARS]})
    messages.append({"role": "user", "content": question})
    return messages
