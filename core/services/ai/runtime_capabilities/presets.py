"""Turns raw hardware + Ollama introspection + a live timing benchmark into a
concrete, explained ai_context_size / ai_max_tokens / ai_timeout / ai_keep_alive
recommendation. Every recommended value is either MEASURED (from the live
benchmark or /api/show) or a clearly-labeled conservative fallback — never a
silent guess. Each field's "basis" says which.
"""

from __future__ import annotations

# Conservative context-size ceiling by total system RAM, used when the model's
# own max context (from /api/show) isn't known, or as an extra safety cap on
# top of it — WealthFlow targets a single local Ollama instance sharing RAM
# with everything else running on the machine (integrated/shared GPU is the
# documented real case), so this deliberately leaves headroom rather than
# maximizing context.
_RAM_CONTEXT_TIERS = ((8, 2048), (16, 4096), (32, 8192))
_DEFAULT_CONTEXT_CAP = 16384
_MIN_CONTEXT = 1024

# Acceptable worst-case wall-clock generation time used to size ai_max_tokens
# from a MEASURED decode rate. Kept modest since real hardware seen so far
# (see core/migrations/0020_lower_ai_max_tokens_cap.py) decodes at ~1-2 tok/s.
_TARGET_GENERATION_SECONDS = 90
_MAX_TOKENS_FLOOR = 128
_MAX_TOKENS_CEILING = 2048

# Safety multiplier applied to the measured prompt-eval + decode time estimate
# when recommending the HTTP request timeout, so a slightly-slower-than-probed
# real answer doesn't get cut off.
_TIMEOUT_SAFETY_MARGIN = 1.5
_TIMEOUT_FLOOR = 30
_TIMEOUT_CEILING = 600


def _ram_context_cap(total_ram_gb: float | None) -> int:
    if total_ram_gb is None:
        return _DEFAULT_CONTEXT_CAP
    for ram_limit, cap in _RAM_CONTEXT_TIERS:
        if total_ram_gb <= ram_limit:
            return cap
    return _DEFAULT_CONTEXT_CAP


def recommend_config(
    current: dict,
    model_info: dict | None,
    hardware: dict,
    benchmark: dict | None,
) -> dict:
    """current: today's {ai_context_size, ai_max_tokens, ai_timeout, ai_keep_alive}.
    Returns {recommended: {...}, notes: [...]} — never mutates/persists anything;
    the settings page applies it explicitly via the existing save flow."""
    notes: list[str] = []
    recommended: dict = {}

    # --- context size ---
    ram_cap = _ram_context_cap(hardware.get("total_ram_gb"))
    model_max = (model_info or {}).get("max_context_length")
    if model_max:
        context_size = max(_MIN_CONTEXT, min(int(model_max), ram_cap))
        notes.append(
            f"ai_context_size: model reports max_context_length={model_max}, "
            f"capped to {ram_cap} for this machine's RAM -> {context_size}."
        )
    else:
        context_size = max(_MIN_CONTEXT, min(int(current.get("ai_context_size", ram_cap)), ram_cap))
        notes.append(
            f"ai_context_size: model's real max context unknown (model not pulled or "
            f"/api/show unreachable) — capped current/default value to this machine's "
            f"RAM tier -> {context_size}."
        )
    recommended["ai_context_size"] = context_size

    # --- max tokens (from a MEASURED decode rate, not a guess) ---
    decode_rate = (benchmark or {}).get("decode_tok_per_sec")
    if decode_rate:
        max_tokens = max(_MAX_TOKENS_FLOOR, min(_MAX_TOKENS_CEILING, int(decode_rate * _TARGET_GENERATION_SECONDS)))
        notes.append(
            f"ai_max_tokens: measured decode rate {decode_rate} tok/s on this hardware "
            f"right now -> capped to ~{_TARGET_GENERATION_SECONDS}s worst case -> {max_tokens}."
        )
    else:
        max_tokens = int(current.get("ai_max_tokens", _MAX_TOKENS_FLOOR))
        notes.append("ai_max_tokens: could not measure decode rate (benchmark failed) — left unchanged.")
    recommended["ai_max_tokens"] = max_tokens

    # --- request timeout (from MEASURED prompt-eval + decode rates) ---
    prompt_rate = (benchmark or {}).get("prompt_tok_per_sec")
    if decode_rate and prompt_rate:
        prompt_eval_estimate = context_size / prompt_rate
        decode_estimate = max_tokens / decode_rate
        timeout = int(max(_TIMEOUT_FLOOR, min(_TIMEOUT_CEILING,
                                              (prompt_eval_estimate + decode_estimate) * _TIMEOUT_SAFETY_MARGIN)))
        notes.append(
            f"ai_timeout: measured {prompt_rate} tok/s prompt-eval + {decode_rate} tok/s decode, "
            f"worst case for context_size={context_size}/max_tokens={max_tokens} "
            f"with {_TIMEOUT_SAFETY_MARGIN}x margin -> {timeout}s."
        )
    else:
        timeout = int(current.get("ai_timeout", _TIMEOUT_FLOOR))
        notes.append("ai_timeout: could not measure prompt-eval/decode rates — left unchanged.")
    recommended["ai_timeout"] = timeout

    # --- keep_alive ---
    has_headroom = (hardware.get("total_ram_gb") or 0) > 16 or hardware.get("gpu_vram_gb")
    if has_headroom:
        keep_alive = "30m"
        notes.append("ai_keep_alive: hardware has headroom (>16GB RAM or a dedicated GPU) -> 30m, avoid reload cost.")
    else:
        keep_alive = "5m"
        notes.append("ai_keep_alive: limited/shared memory -> 5m, free it between chats.")
    recommended["ai_keep_alive"] = keep_alive

    return {"recommended": recommended, "notes": notes}
