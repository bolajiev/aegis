"""Per-user conversation history. In-memory, 4-hour TTL, last 20 exchanges."""
import time
from collections import defaultdict, deque

_store: dict[int, deque] = defaultdict(lambda: deque(maxlen=40))
_timestamps: dict[int, float] = {}
SESSION_TTL = 4 * 3600


def get_history(user_id: int) -> list[dict]:
    _expire_if_stale(user_id)
    return list(_store[user_id])


def add_exchange(user_id: int, user_msg: str, assistant_msg: str) -> None:
    _store[user_id].append({"role": "user", "content": user_msg})
    _store[user_id].append({"role": "assistant", "content": assistant_msg})
    _timestamps[user_id] = time.time()


def clear(user_id: int) -> None:
    _store.pop(user_id, None)
    _timestamps.pop(user_id, None)


def _expire_if_stale(user_id: int) -> None:
    ts = _timestamps.get(user_id, 0)
    if time.time() - ts > SESSION_TTL:
        _store.pop(user_id, None)
        _timestamps.pop(user_id, None)
