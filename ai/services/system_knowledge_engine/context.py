"""
Token-budgeted assembly of selected system knowledge sections into a context string.

BUG FIX (see conversation history / CHANGES.diff): the previous version only
enforced `max_chars` "if a block was already added" (`and context_blocks`),
so a single oversized first section — e.g. the auto-generated DB schema
reference, which can run 30k+ chars for a database with many models —
was always injected in FULL regardless of token_limit. That alone blew
past the entire downstream ContextBuilderService budget before any real
financial data was even considered, silently zeroing out the actual
"FINANCIAL CONTEXT DATA" section on every chat turn.

Fix: if the first (highest-priority) section alone exceeds the remaining
budget, truncate its content to fit instead of injecting it whole.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List

HEADER = "\n\n=== SYSTEM KNOWLEDGE & DOMAIN MANIFEST ==="


def _format_block(title: str, content: str) -> str:
    return f"\n\n--- [{title.upper()}] ---\n{content}"


def build_context_string(
    relevant_sections: List[Dict[str, Any]],
    load_section_content: Callable[[str], str],
    token_limit: int = 1500,
) -> str:
    if not relevant_sections:
        return ""

    context_blocks: list[str] = []
    current_chars = len(HEADER)
    max_chars = token_limit * 4

    for sec in relevant_sections:
        content = load_section_content(sec.get("file", ""))
        if not content:
            continue

        title = str(sec.get("title", ""))
        block = _format_block(title, content)
        remaining = max_chars - current_chars

        if len(block) <= remaining:
            context_blocks.append(block)
            current_chars += len(block)
            continue

        if not context_blocks:
            # First section alone exceeds the budget — truncate rather than
            # injecting it whole and starving every other section of any
            # budget at all.
            title_line_len = len(_format_block(title, ""))
            keep_chars = max(remaining - title_line_len - 40, 0)
            if keep_chars > 0:
                truncated = content[:keep_chars] + "\n[...truncated: section exceeds context budget...]"
                context_blocks.append(_format_block(title, truncated))
                current_chars += len(context_blocks[-1])

        # Budget reached — stop adding further sections either way.
        break

    if not context_blocks:
        return ""

    return HEADER + "".join(context_blocks)
