"""Lightweight HTTP retry helper for rate-limit and server errors."""
import asyncio
import logging

import httpx

logger = logging.getLogger(__name__)

_RETRY_STATUSES = {429, 500, 502, 503, 504}
_BACKOFF = [1.0, 2.5, 5.0]  # seconds between attempts (3 retries max)


async def get_json(client: httpx.AsyncClient, url: str, **kwargs) -> object:
    """GET *url* with retry on rate-limit and transient server errors.

    Returns parsed JSON. Raises on non-retryable errors or after all retries exhausted.
    """
    last_exc: Exception | None = None
    for attempt, delay in enumerate([0.0] + _BACKOFF):
        if delay:
            await asyncio.sleep(delay)
        try:
            r = await client.get(url, **kwargs)
            if r.status_code in _RETRY_STATUSES:
                logger.warning("HTTP %s from %s (attempt %d)", r.status_code, url, attempt + 1)
                last_exc = httpx.HTTPStatusError(
                    f"HTTP {r.status_code}", request=r.request, response=r
                )
                continue
            r.raise_for_status()
            return r.json()
        except (httpx.TimeoutException, httpx.ConnectError) as exc:
            logger.warning("Network error on %s (attempt %d): %s", url, attempt + 1, exc)
            last_exc = exc
    raise last_exc  # type: ignore[misc]
