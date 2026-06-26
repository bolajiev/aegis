"""Router — classifies intent, runs agent with correct iteration budget."""
from __future__ import annotations
import logging
from collections.abc import Awaitable, Callable

from pipeline.intent import Intent, Lane, classify, classify_intent, INTENT_CONFIG
from pipeline import agent
from skills.base import SkillResult

logger = logging.getLogger(__name__)


async def handle(
    text: str,
    user_id: int = 0,
    history: list[dict] | None = None,
    progress_cb: Callable[[list[str]], Awaitable[None]] | None = None,
    user_context: str = "",
    override_iterations: int | None = None,
) -> tuple[str, Lane, list[SkillResult], list[tuple[bytes, str]], str]:
    """
    Returns (html_reply, lane, skill_results, charts, intent_value).
    Intent drives max_iterations and response_type passed to the agent.
    """
    intent = classify(text)
    config = INTENT_CONFIG.get(intent, (4, "rich"))
    max_iterations, response_type = config
    if override_iterations is not None:
        max_iterations = override_iterations

    logger.info("intent=%s iterations=%d type=%s", intent, max_iterations, response_type)

    reply, results, charts = await agent.run(
        text,
        history=history or [],
        max_iterations=max_iterations,
        response_type=response_type,
        intent=intent.value,
        progress_cb=progress_cb,
        user_context=user_context,
    )

    lane = Lane.SMALLTALK if intent == Intent.CHAT else Lane.RESEARCH
    return reply, lane, results, charts, intent.value


# Stubs kept so old test imports don't crash
_LOOKUP_KEYWORDS: list = []
def _pick_lookup_skill(text: str): return None
def _pick_skill_or_skills(text: str) -> list: return []
