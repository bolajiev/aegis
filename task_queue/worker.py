"""
Async worker queue. Bot submits tasks immediately so the handler returns fast,
worker picks them up and delivers responses when ready.
"""
import asyncio
import logging
from typing import Awaitable, Callable

logger = logging.getLogger(__name__)

_queue: asyncio.Queue = asyncio.Queue(maxsize=200)
_active: dict[int, bool] = {}


async def submit(user_id: int, task: Callable[[], Awaitable[None]]) -> bool:
    """
    Submit a task for a user.
    Returns False if user already has a task in flight (prevents duplicate requests).
    """
    if _active.get(user_id):
        return False
    _active[user_id] = True
    await _queue.put((user_id, task))
    return True


async def run_worker() -> None:
    """Run the worker loop forever. Call once at bot startup via asyncio.create_task()."""
    logger.info("Worker started")
    while True:
        user_id, task = await _queue.get()
        try:
            await task()
        except Exception:
            logger.exception("Worker task failed for user %s", user_id)
        finally:
            _active.pop(user_id, None)
            _queue.task_done()
