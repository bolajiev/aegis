"""Async DefiLlama API client."""
import httpx

from clients._retry import get_json

_BASE = "https://api.llama.fi"
_TIMEOUT = 15.0


async def get_chain_tvl_history(chain: str = "Mantle") -> list[dict]:
    """Returns [{date: int, tvl: float}, ...] sorted oldest→newest."""
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        return await get_json(client, f"{_BASE}/v2/historicalChainTvl/{chain}")


async def get_chain_current_tvl(chain: str = "Mantle") -> float:
    """Returns the current TVL for a chain in USD."""
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        chains = await get_json(client, f"{_BASE}/v2/chains")
    entry = next((c for c in chains if c.get("name") == chain), None)
    if entry is None:
        raise ValueError(f"Chain {chain!r} not found in DefiLlama")
    return float(entry["tvl"])


async def get_protocols() -> list[dict]:
    """Returns the full protocols list from DefiLlama."""
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        return await get_json(client, f"{_BASE}/protocols")


async def get_dex_overview(chain: str = "Mantle") -> dict:
    """DEX volume summary for a chain: total24h, total7d, change_1d, change_7d."""
    params = {"excludeTotalDataChart": "true", "excludeTotalDataChartBreakdown": "true"}
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        d = await get_json(client, f"{_BASE}/overview/dexs/{chain}", params=params)
    return {
        "total_24h_usd": d.get("total24h"),
        "total_7d_usd": d.get("total7d"),
        "change_1d_pct": d.get("change_1d"),
        "change_7d_pct": d.get("change_7d"),
    }


async def get_fees_overview(chain: str = "Mantle") -> dict:
    """Protocol fee summary for a chain: total24h, total7d, top earners."""
    params = {"excludeTotalDataChart": "true", "excludeTotalDataChartBreakdown": "true"}
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        d = await get_json(client, f"{_BASE}/overview/fees/{chain}", params=params)
    top = sorted(
        [p for p in d.get("protocols", []) if p.get("total24h")],
        key=lambda p: p["total24h"],
        reverse=True,
    )[:5]
    return {
        "total_24h_usd": d.get("total24h"),
        "total_7d_usd": d.get("total7d"),
        "change_1d_pct": d.get("change_1d"),
        "top_earners": [{"name": p["name"], "fees_24h": p["total24h"]} for p in top],
    }
