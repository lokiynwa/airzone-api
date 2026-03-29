from copy import deepcopy
from dataclasses import dataclass
from threading import Lock
from time import monotonic
from typing import Generic, TypeVar

ValueT = TypeVar("ValueT")


@dataclass
class CacheEntry(Generic[ValueT]):
    expires_at: float
    value: ValueT


class TTLMemoryCache(Generic[ValueT]):
    def __init__(self, *, ttl_seconds: float) -> None:
        self.ttl_seconds = ttl_seconds
        self._entries: dict[str, CacheEntry[ValueT]] = {}
        self._lock = Lock()

    def get(self, key: str) -> ValueT | None:
        with self._lock:
            entry = self._entries.get(key)
            now = monotonic()
            if not entry:
                return None
            if entry.expires_at <= now:
                self._entries.pop(key, None)
                return None
            return deepcopy(entry.value)

    def set(self, key: str, value: ValueT) -> None:
        with self._lock:
            self._entries[key] = CacheEntry(
                expires_at=monotonic() + self.ttl_seconds,
                value=deepcopy(value),
            )

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

