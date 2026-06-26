"""Async CoinGecko API client (free tier)."""
import httpx
from config import settings

from clients._retry import get_json

_BASE = "https://api.coingecko.com/api/v3"
_TIMEOUT = 15.0

# Map of human-readable ticker → CoinGecko coin ID
# Verified 2026-06-22 via /search endpoint
XSTOCK_IDS: dict[str, str] = {
    "SPCXX":  "spacex-xstocks",
    "TSLAX":  "tesla-xstock",
    "NVDAX":  "nvidia-xstock",
    "SPYX":   "sp500-xstock",
    "AAPLX":  "apple-xstock",
    "QQQX":   "nasdaq-xstock",
    "MSTRX":  "microstrategy-xstock",
    "GOOGLX": "alphabet-xstock",
    "GLDX":   "gold-xstock",
}


def _headers() -> dict:
    if settings.coingecko_api_key:
        return {"x-cg-demo-api-key": settings.coingecko_api_key}
    return {}


async def get_mnt_info() -> dict:
    """
    Returns MNT token market data from CoinGecko.
    Fields: price_usd, market_cap_usd, volume_24h_usd, price_change_24h_pct,
            telegram_users, last_updated.
    """
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        d = await get_json(
            client,
            f"{_BASE}/coins/mantle",
            params={
                "localization": "false",
                "tickers": "false",
                "community_data": "true",
                "developer_data": "false",
                "sparkline": "false",
            },
            headers=_headers(),
        )
    md = d.get("market_data", {})
    return {
        "price_usd": md.get("current_price", {}).get("usd"),
        "market_cap_usd": md.get("market_cap", {}).get("usd"),
        "volume_24h_usd": md.get("total_volume", {}).get("usd"),
        "price_change_24h_pct": md.get("price_change_percentage_24h"),
        "price_change_7d_pct": md.get("price_change_percentage_7d"),
        "market_cap_rank": d.get("market_cap_rank"),
        "telegram_users": d.get("community_data", {}).get("telegram_channel_user_count"),
        "last_updated": d.get("last_updated"),
    }


async def get_prices(coin_ids: list[str]) -> dict:
    """
    Returns {coin_id: {usd: float, usd_24h_change: float, last_updated_at: int}}.
    Missing ids are simply absent from the result.
    """
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        return await get_json(
            client,
            f"{_BASE}/simple/price",
            params={
                "ids": ",".join(coin_ids),
                "vs_currencies": "usd",
                "include_24hr_change": "true",
                "include_last_updated_at": "true",
                "include_market_cap": "true",
                "include_24hr_vol": "true",
            },
            headers=_headers(),
        )


async def search_coin(query: str) -> str | None:
    """Returns the top CoinGecko coin ID for a search query, or None."""
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        data = await get_json(client, f"{_BASE}/search", params={"query": query}, headers=_headers())
    coins = data.get("coins", [])
    if not coins:
        return None
    return coins[0]["id"]


async def get_price_chart(coin_id: str, days: int = 30) -> list[tuple[float, float]]:
    """Returns [(timestamp_ms, price_usd), ...] for the last *days* days."""
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        data = await get_json(
            client,
            f"{_BASE}/coins/{coin_id}/market_chart",
            params={"vs_currency": "usd", "days": str(days)},
            headers=_headers(),
        )
    return [(ts, price) for ts, price in data.get("prices", [])]
