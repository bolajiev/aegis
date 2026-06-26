"""Mantle native token prices via mantle-cli, fallback to CoinGecko."""
import asyncio
import logging
from datetime import datetime, timezone

from clients.mcp_cli import call as mcp_call
from clients.coingecko import get_prices, search_coin, get_mnt_info
from skills.base import SkillResult, register

logger = logging.getLogger(__name__)

_DEFAULT_TOKENS = "MNT,WMNT,USDT,USDC,WETH,mETH"

_MANTLE_TO_COINGECKO: dict[str, str] = {
    "MNT":  "mantle",
    "WMNT": "wrapped-mantle",
    "mETH": "mantle-staked-ether",
    "USDT": "tether",
    "USDC": "usd-coin",
    "WETH": "weth",
    "FBTC": "fire-bitcoin",
    "COOK": "cook-finance",
}


class MantleTokenPricesSkill:
    name = "mantle-token-prices"

    async def run(self, query: str) -> SkillResult:
        q = query.strip().upper()
        tokens_requested = [t.strip() for t in q.split(",") if t.strip()] or _DEFAULT_TOKENS.split(",")

        prices: dict[str, dict] = {}
        cli_tokens = ",".join(tokens_requested)

        # Try mantle-cli first
        cli_data = await mcp_call(["token", "prices", "--tokens", cli_tokens])
        if cli_data and isinstance(cli_data, dict):
            for token, info in cli_data.items():
                if isinstance(info, dict):
                    prices[token.upper()] = {
                        "price_usd": info.get("price") or info.get("priceUSD"),
                        "change_24h_pct": info.get("change24h") or info.get("priceChange24h"),
                        "source": "mantle-cli",
                    }

        # CoinGecko fallback for missing tokens
        missing = [t for t in tokens_requested if t not in prices]
        if missing:
            cg_ids = [_MANTLE_TO_COINGECKO[t] for t in missing if t in _MANTLE_TO_COINGECKO]
            if "MNT" in missing:
                try:
                    mnt = await get_mnt_info()
                    prices["MNT"] = {
                        "price_usd": mnt.get("price_usd"),
                        "change_24h_pct": mnt.get("price_change_24h_pct"),
                        "change_7d_pct": mnt.get("price_change_7d_pct"),
                        "market_cap_usd": mnt.get("market_cap_usd"),
                        "volume_24h_usd": mnt.get("volume_24h_usd"),
                        "source": "CoinGecko",
                    }
                    missing = [t for t in missing if t != "MNT"]
                    if "MNT" in cg_ids:
                        cg_ids.remove("mantle")
                except Exception:
                    pass

            if cg_ids:
                try:
                    raw = await get_prices(cg_ids)
                    for tok in missing:
                        cid = _MANTLE_TO_COINGECKO.get(tok)
                        if cid and cid in raw:
                            prices[tok] = {
                                "price_usd": raw[cid].get("usd"),
                                "change_24h_pct": raw[cid].get("usd_24h_change"),
                                "market_cap_usd": raw[cid].get("usd_market_cap"),
                                "source": "CoinGecko",
                            }
                except Exception as exc:
                    logger.warning("CoinGecko fallback failed: %s", exc)

        # Link to CoinGecko MNT page if MNT was fetched, else CoinGecko home
        cg_url = "https://www.coingecko.com/en/coins/mantle" if "MNT" in prices else "https://www.coingecko.com"
        return SkillResult(
            skill=self.name,
            source="mantle-cli / CoinGecko",
            source_url=cg_url,
            fetched_at=datetime.now(timezone.utc),
            data={
                "prices": prices,
                "tokens": list(prices.keys()),
            },
        )


register(MantleTokenPricesSkill())
