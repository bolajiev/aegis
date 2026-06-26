"""News digest — DuckDuckGo + CoinGecko news API for Mantle and crypto news."""
import asyncio
import html
import logging
import re
from datetime import datetime, timezone

import httpx

from skills.base import SkillResult, register

logger = logging.getLogger(__name__)

_DDG_URL = "https://duckduckgo.com/html/"
_CG_NEWS_URL = "https://api.coingecko.com/api/v3/news"
_TIMEOUT = 12.0


async def _ddg_search(query: str, max_results: int = 6) -> list[dict]:
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; AegisBot/1.0)",
        "Accept": "text/html",
    }
    results = []
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
            r = await client.post(_DDG_URL, data={"q": query}, headers=headers)
            r.raise_for_status()
            text = r.text

        blocks = re.findall(
            r'<a rel="nofollow" class="result__a" href="([^"]+)"[^>]*>(.*?)</a>.*?'
            r'<a class="result__snippet"[^>]*>(.*?)</a>',
            text, re.DOTALL
        )
        for url, title, snippet in blocks[:max_results]:
            clean_title = re.sub(r"<[^>]+>", "", html.unescape(title)).strip()
            clean_snippet = re.sub(r"<[^>]+>", "", html.unescape(snippet)).strip()
            if clean_title:
                results.append({"title": clean_title, "url": url, "snippet": clean_snippet})
    except Exception as exc:
        logger.warning("DDG search failed: %s", exc)
    return results


async def _coingecko_news(keyword: str = "mantle", max_results: int = 5) -> list[dict]:
    """CoinGecko public news endpoint — no API key required."""
    results = []
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.get(_CG_NEWS_URL, params={"per_page": 50})
            r.raise_for_status()
            data = r.json()

        articles = data if isinstance(data, list) else data.get("data", data.get("news", []))
        kw = keyword.lower()
        for a in articles:
            title = (a.get("title") or a.get("headline") or "").lower()
            desc  = (a.get("description") or a.get("snippet") or "").lower()
            if kw in title or kw in desc or "mantle" in title or "mnt" in title:
                results.append({
                    "title": a.get("title") or a.get("headline"),
                    "url":   a.get("url") or a.get("link") or "",
                    "snippet": a.get("description") or a.get("snippet") or "",
                    "source": "CoinGecko News",
                })
            if len(results) >= max_results:
                break
    except Exception as exc:
        logger.debug("CoinGecko news failed: %s", exc)
    return results


class NewsSkill:
    name = "news"

    async def run(self, query: str) -> SkillResult:
        q = query.strip() or "Mantle crypto news 2026"
        if "mantle" not in q.lower() and "mnt" not in q.lower():
            q = f"Mantle {q}"

        # Run both sources in parallel
        ddg_q = f"{q} site:theblock.co OR site:coindesk.com OR site:decrypt.co OR site:cointelegraph.com OR site:mantle.xyz"
        ddg_task = _ddg_search(ddg_q, max_results=6)
        cg_task  = _coingecko_news(keyword="mantle", max_results=5)

        ddg_results, cg_results = await asyncio.gather(ddg_task, cg_task)

        # Merge, deduplicate by URL
        seen_urls: set[str] = set()
        combined = []
        for item in ddg_results + cg_results:
            u = item.get("url", "")
            if u and u not in seen_urls:
                seen_urls.add(u)
                combined.append(item)

        # Fallback: plain DDG if both failed
        if not combined:
            combined = await _ddg_search(q)

        sources_used = []
        has_ddg = any(not item.get("source") for item in combined)
        has_cg  = any(item.get("source") == "CoinGecko News" for item in combined)
        if has_ddg:
            sources_used.append("DuckDuckGo")
        if has_cg:
            sources_used.append("CoinGecko News")

        return SkillResult(
            skill=self.name,
            source=" + ".join(sources_used) if sources_used else "DuckDuckGo",
            source_url="https://www.coingecko.com/en/news" if has_cg else "",
            fetched_at=datetime.now(timezone.utc),
            data={
                "query": q,
                "results": combined[:10],
                "count": len(combined),
            },
        )


register(NewsSkill())
