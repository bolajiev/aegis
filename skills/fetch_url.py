"""URL fetcher — reads full article/page content for the agent."""
import logging
import re
from datetime import datetime, timezone

import httpx

from skills.base import SkillResult, register

logger = logging.getLogger(__name__)

_TIMEOUT = 20.0
_MAX_CHARS = 12000


def _extract_text(html_content: str) -> str:
    """Strip HTML tags and compress whitespace."""
    text = re.sub(r"<script[^>]*>.*?</script>", " ", html_content, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s{3,}", "\n\n", text)
    return text.strip()[:_MAX_CHARS]


class FetchUrlSkill:
    name = "fetch-url"

    async def run(self, query: str) -> SkillResult:
        url = query.strip()
        if not url.startswith("http"):
            return SkillResult.failure(self.name, "HTTP", f"Invalid URL: {url!r}")

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (compatible; AegisBot/1.0)",
                "Accept": "text/html,application/xhtml+xml",
            }
            async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
                r = await client.get(url, headers=headers)
                r.raise_for_status()
                content = r.text

            text = _extract_text(content)
            return SkillResult(
                skill=self.name,
                source=url,
                fetched_at=datetime.now(timezone.utc),
                data={"url": url, "content": text, "char_count": len(text)},
            )
        except httpx.HTTPStatusError as exc:
            return SkillResult.failure(self.name, url, f"HTTP {exc.response.status_code}")
        except Exception as exc:
            logger.warning("fetch-url failed for %s: %s", url, exc)
            return SkillResult.failure(self.name, url, str(exc))


register(FetchUrlSkill())
