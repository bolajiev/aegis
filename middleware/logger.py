"""Structured request/response logger."""
import logging
import time

logger = logging.getLogger("esu.requests")


def log_request(user_id: int, query: str, intent: str) -> float:
    start = time.time()
    logger.info("REQ user=%s intent=%s query=%.80r", user_id, intent, query)
    return start


def log_response(user_id: int, start: float, tools_called: list[str], response_type: str) -> None:
    elapsed = int((time.time() - start) * 1000)
    logger.info("RES user=%s tools=%s type=%s elapsed=%dms",
                user_id, tools_called, response_type, elapsed)
