"""Per-user rate limiting. Max 10 requests per 60-second window."""
import time
from collections import defaultdict

_windows: dict[int, list[float]] = defaultdict(list)
MAX_PER_MINUTE = 10
WINDOW = 60.0


def check(user_id: int) -> bool:
    """Returns True if request is allowed, False if rate limited."""
    now = time.time()
    _windows[user_id] = [t for t in _windows[user_id] if now - t < WINDOW]
    if len(_windows[user_id]) >= MAX_PER_MINUTE:
        return False
    _windows[user_id].append(now)
    return True


def remaining(user_id: int) -> int:
    now = time.time()
    recent = [t for t in _windows[user_id] if now - t < WINDOW]
    return max(0, MAX_PER_MINUTE - len(recent))
