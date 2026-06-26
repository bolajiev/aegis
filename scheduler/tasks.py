"""
Lightweight in-process scheduler for delayed bot responses.
Supports: "tell me MNT price in 5 minutes", "check TVL in 2 hours"
"""
from __future__ import annotations
import re
import time
from dataclasses import dataclass, field


_TIME_RX = re.compile(
    r"\b(?:in|after)\s+(\d+(?:\.\d+)?)\s*(minute|min|hour|hr|second|sec)s?\b",
    re.I,
)

# Phrases to strip when extracting the real query
_SCHEDULE_STRIP = re.compile(
    r"\b(?:tell me|remind me|check|show me|send me|give me|update me on)\b",
    re.I,
)


@dataclass
class ScheduledTask:
    user_id: int
    chat_id: int
    query: str          # the actual query to run when due
    execute_at: float   # unix timestamp
    reply_to: int | None = None


_pending: list[ScheduledTask] = []


def parse_schedule(text: str) -> tuple[int, str] | None:
    """
    If text contains a delay expression, return (delay_seconds, clean_query).
    Returns None if no delay found.
    """
    m = _TIME_RX.search(text)
    if not m:
        return None

    amount = float(m.group(1))
    unit = m.group(2).lower()
    if unit in ("hour", "hr"):
        seconds = int(amount * 3600)
    elif unit in ("minute", "min"):
        seconds = int(amount * 60)
    else:
        seconds = int(amount)

    # Strip the time expression and schedule filler words
    clean = _TIME_RX.sub("", text)
    clean = _SCHEDULE_STRIP.sub("", clean)
    # Strip trailing punctuation and connectors
    clean = re.sub(r"\b(me|on|about|the|for)\b", " ", clean, flags=re.I)
    clean = re.sub(r"\s{2,}", " ", clean).strip(" .,?!")

    if len(clean) < 3:
        clean = text  # fallback to original if stripping left nothing

    return seconds, clean


def schedule(
    user_id: int,
    chat_id: int,
    query: str,
    delay_seconds: int,
    reply_to: int | None = None,
) -> None:
    _pending.append(ScheduledTask(
        user_id=user_id,
        chat_id=chat_id,
        query=query,
        execute_at=time.time() + delay_seconds,
        reply_to=reply_to,
    ))


def pop_due() -> list[ScheduledTask]:
    """Return and remove all tasks whose execute_at has passed."""
    now = time.time()
    due = [t for t in _pending if t.execute_at <= now]
    for t in due:
        _pending.remove(t)
    return due


def pending_count(user_id: int) -> int:
    return sum(1 for t in _pending if t.user_id == user_id)
