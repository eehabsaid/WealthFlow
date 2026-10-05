"""Accumulates the token counts of every LLM call made for one chat request."""

from typing import Any


class TokenMeter:
    def __init__(self) -> None:
        self.prompt = 0
        self.completion = 0

    def add(self, result: Any) -> None:
        if not isinstance(result, dict):
            return
        for attr, key in (("prompt", "prompt_tokens"), ("completion", "completion_tokens")):
            val = result.get(key)
            if isinstance(val, (int, float)):
                setattr(self, attr, getattr(self, attr) + int(val))


class MeteredProvider:
    """Transparent proxy: forwards to the real provider and adds each generate() token count to `meter`."""

    def __init__(self, provider: Any, meter: TokenMeter):
        self._provider = provider
        self.meter = meter

    def __getattr__(self, name: str) -> Any:
        return getattr(self._provider, name)

    def generate(self, *args: Any, **kwargs: Any) -> Any:
        res = self._provider.generate(*args, **kwargs)
        self.meter.add(res)
        return res
