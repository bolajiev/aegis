"""Web search via DuckDuckGo — open-ended research queries."""
import html
import logging
import re
from datetime import datetime, timezone

import httpx

from skills.base import SkillResult, register

logger = logging.getLogger(__name__)

_DDG_URL = "https://duckduckgo.com/html/"
_TIMEOUT = 12.0


class WebSearchSkill:
    name = "web-search"

    async def run(self, query: str) -> SkillResult:
        if not query.strip():
            return SkillResult.failure(self.name, "DuckDuckGo", "Empty search query")

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (compatible; AegisBot/1.0)",
                "Accept": "text/html",
            }
            async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
                r = await client.post(_DDG_URL, data={"q": query}, headers=headers)
                r.raise_for_status()
                text = r.text

            blocks = re.findall(
                r'<a rel="nofollow" class="result__a" href="([^"]+)"[^>]*>(.*?)</a>.*?'
                r'<a class="result__snippet"[^>]*>(.*?)</a>',
                text, re.DOTALL
            )

            results = []
            for url, title, snippet in blocks[:10]:
                clean_title = re.sub(r"<[^>]+>", "", html.unescape(title)).strip()
                clean_snippet = re.sub(r"<[^>]+>", "", html.unescape(snippet)).strip()
                if clean_title:
                    results.append({"title": clean_title, "url": url, "snippet": clean_snippet})

            return SkillResult(
                skill=self.name,
                source="DuckDuckGo",
                fetched_at=datetime.now(timezone.utc),
                data={"query": query, "results": results, "count": len(results)},
            )
        except Exception as exc:
            logger.exception("web-search failed for %r", query)
            return SkillResult.failure(self.name, "DuckDuckGo", str(exc))


register(WebSearchSkill())
