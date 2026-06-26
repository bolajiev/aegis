"""In-memory TTL cache for skill results. Prevents redundant API calls."""
import time
from typing import Any

_cache: dict[str, tuple[Any, float]] = {}

TTLS: dict[str, int] = {
    "crypto-price":         300,
    "mantle-token-prices":  300,
    "mantle-chain":          60,
    "mantle-defi":          300,
    "mantle-rwa-tvl":       900,
    "mantle-equity":        300,
    "mantle-identity":      300,
    "mantle-portfolio":      60,
    "mantle-defi-markets":  300,
    "mantle-risk":         1800,
    "news":                1800,
    "web-search":          3600,
    "fetch-url":           3600,
}


def get(key: str) -> Any | None:
    entry = _cache.get(key)
    if entry and time.time() < entry[1]:
        return entry[0]
    _cache.pop(key, None)
    return None


def set(key: str, value: Any, skill: str = "") -> None:
    ttl = TTLS.get(skill, 600)
    _cache[key] = (value, time.time() + ttl)


def make_key(skill: str, query: str) -> str:
    return f"{skill}:{query[:80]}"
