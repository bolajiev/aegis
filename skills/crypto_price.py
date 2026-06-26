"""General crypto price skill — any coin via CoinGecko."""
import logging
from datetime import datetime, timezone

from clients.coingecko import get_prices, search_coin, get_mnt_info
from skills.base import SkillResult, register

logger = logging.getLogger(__name__)

_KNOWN: dict[str, str] = {
    "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana",
    "BNB": "binancecoin", "XRP": "ripple", "ADA": "cardano",
    "AVAX": "avalanche-2", "MATIC": "matic-network", "LINK": "chainlink",
    "DOT": "polkadot", "UNI": "uniswap", "LTC": "litecoin",
    "DOGE": "dogecoin", "SHIB": "shiba-inu", "ARB": "arbitrum",
    "OP": "optimism", "MNT": "mantle", "USDT": "tether", "USDC": "usd-coin",
}


class CryptoPriceSkill:
    name = "crypto-price"

    async def run(self, query: str) -> SkillResult:
        q = query.strip().upper()

        # MNT has richer data from dedicated endpoint
        if q in ("MNT", "MANTLE"):
            try:
                data = await get_mnt_info()
                return SkillResult(
                    skill=self.name,
                    source="CoinGecko",
                    fetched_at=datetime.now(timezone.utc),
                    data={"coin": "MNT", "coin_id": "mantle", **data},
                )
            except Exception as exc:
                return SkillResult.failure(self.name, "CoinGecko", str(exc))

        # Look up coin ID
        coin_id = _KNOWN.get(q)
        if not coin_id:
            try:
                coin_id = await search_coin(query.strip())
            except Exception:
                pass

        if not coin_id:
            return SkillResult.failure(self.name, "CoinGecko", f"Coin not found: {query!r}")

        try:
            raw = await get_prices([coin_id])
            entry = raw.get(coin_id, {})
            return SkillResult(
                skill=self.name,
                source="CoinGecko",
                source_url=f"https://www.coingecko.com/en/coins/{coin_id}",
                fetched_at=datetime.now(timezone.utc),
                data={
                    "coin": q,
                    "coin_id": coin_id,
                    "price_usd": entry.get("usd"),
                    "change_24h_pct": entry.get("usd_24h_change"),
                    "market_cap_usd": entry.get("usd_market_cap"),
                    "volume_24h_usd": entry.get("usd_24h_vol"),
                },
            )
        except Exception as exc:
            logger.exception("crypto-price failed for %s", query)
            return SkillResult.failure(self.name, "CoinGecko", str(exc))


register(CryptoPriceSkill())
