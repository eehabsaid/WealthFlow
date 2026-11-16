"""The context meter: how full the model's context is after a step, from numbers the agent really has. Pure functions, no I/O.

Used tokens = what the provider reported for the last call (prompt + reply). Some providers do not report a prompt count, and Ollama reports only the
newly evaluated tokens when its prompt cache is reused, which would understate a growing conversation. So when the reported prompt is missing or far
below the agent's own estimate (chars/4, the same number its trimming uses), the estimate is shown instead and `source` says so. Nothing is invented:
`reported` and `estimate` are both returned for the tooltip."""

from __future__ import annotations

WARN, CRITICAL = 0.80, 0.95   # of the usable limit (window - reserve); the agent starts trimming old steps at 100%
CACHE_DOUBT = 0.5             # a reported prompt below this share of the estimate is treated as cache-reduced


def snapshot(reported_in: int, reported_out: int, estimate: int, window: int, reserve: int) -> dict:
    """One meter reading. `estimate` is the agent's own token estimate of the whole conversation including the reply just received."""
    reported_in, reported_out, estimate = max(0, int(reported_in or 0)), max(0, int(reported_out or 0)), max(0, int(estimate or 0))
    window, reserve = max(1, int(window)), max(0, int(reserve))
    limit = max(1, window - reserve)
    reported = reported_in + reported_out
    from_provider = reported_in > 0 and reported >= estimate * CACHE_DOUBT
    used = reported if from_provider else estimate
    ratio = used / limit
    return {
        "used": used, "window": window, "reserve": reserve, "limit": limit,
        "percent": round(100 * used / window, 1),
        "remaining": max(0, window - used), "remaining_usable": max(0, limit - used),
        "level": "critical" if ratio >= CRITICAL else "warn" if ratio >= WARN else "ok",
        "source": "provider" if from_provider else "estimate",
        "reported": {"input_tokens": reported_in, "output_tokens": reported_out}, "estimate": estimate,
    }
