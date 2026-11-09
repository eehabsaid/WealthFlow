"""
Centralized, Thread-Safe In-Memory Cache Manager for AI Context Subsystem.
Manages per-key TTLs and invalidation strategies across UI structure, business data providers, codebase AST index, and capability registry.
CRITICAL CONSTRAINT: 100% READ-ONLY. Zero DB write calls.
"""

from __future__ import annotations

import threading
import time
from typing import Any


class AICacheManager:
    _instance: AICacheManager | None = None
    _lock = threading.Lock()

    def __new__(cls) -> AICacheManager:
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._store = {}
                cls._instance._store_lock = threading.Lock()
            return cls._instance

    def get(self, key: str) -> Any | None:
        clean_key = str(key or "").strip()
        with self._store_lock:
            entry = self._store.get(clean_key)
            if not entry:
                return None

            now = time.time()
            if entry["ttl"] > 0 and (now - entry["timestamp"] > entry["ttl"]):
                del self._store[clean_key]
                return None

            return entry["value"]

    def set(self, key: str, value: Any, ttl_seconds: float = 600.0) -> None:
        clean_key = str(key or "").strip()
        with self._store_lock:
            self._store[clean_key] = {
                "value": value,
                "timestamp": time.time(),
                "ttl": float(ttl_seconds),
            }

    def invalidate(self, key: str | None = None) -> None:
        with self._store_lock:
            if key is None:
                self._store.clear()
            else:
                clean_key = str(key).strip()
                self._store.pop(clean_key, None)

    def stats(self) -> dict[str, int]:
        with self._store_lock:
            return {
                "active_entries_count": len(self._store),
            }
