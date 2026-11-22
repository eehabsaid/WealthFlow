"""Block ownership and budget fitting helpers for the context builder."""

from __future__ import annotations





def _owner_of(block: str, sources: list[str]) -> str:
    """Source of a business-data block: its header is '### <Provider>_<part> Payload Data:' (see summarize_payload)."""
    head = block.split("\n", 1)[0].lower().replace(" ", "_")
    return next((s for s in sorted(sources, key=len, reverse=True) if s.lower() in head), "")


def _fit_blocks(high: list[str], low: list[str], budget: int, owner: dict[int, str]) -> tuple[list[str], set[str]]:
    """Choose the blocks that fit `budget`. Every source gets its most important block considered before any source gets a
    second one (round robin), so one data-heavy topic (e.g. expenses) can no longer starve another matched source
    (e.g. the wealth forecast). A block that does not fit is skipped, not a reason to stop. Order of the chosen blocks is
    kept as assembled (priority order). Returns (blocks, sources that made it in)."""
    chosen: set[int] = set()
    used = 0

    def take(pool: list[str]) -> None:
        nonlocal used
        queues: dict[str, list[str]] = {}
        for blk in pool:
            queues.setdefault(owner.get(id(blk), ""), []).append(blk)
        while any(queues.values()):
            for key in list(queues):
                while queues[key]:
                    blk = queues[key].pop(0)
                    if used + len(blk) <= budget:
                        chosen.add(id(blk))
                        used += len(blk)
                        break          # one block per source per round
    take(high)
    take(low)
    ordered = [b for b in (*high, *low) if id(b) in chosen]
    return ordered, {owner.get(id(b), "") for b in ordered}
