"""Tokenized equities on Mantle — xStocks prices from CoinGecko."""
import asyncio
import logging
from datetime import datetime, timezone

from clients.coingecko import get_prices, XSTOCK_IDS
from skills.base import SkillResult, register

logger = logging.getLogger(__name__)


class MantleEquitySkill:
    name = "mantle-equity"

    async def run(self, query: str) -> SkillResult:
        try:
            ids = list(XSTOCK_IDS.values())
            raw = await get_prices(ids)

            stocks = []
            for ticker, coin_id in XSTOCK_IDS.items():
                entry = raw.get(coin_id, {})
                price = entry.get("usd")
                if price is None:
                    continue
                stocks.append({
                    "ticker": ticker,
                    "coin_id": coin_id,
                    "price_usd": price,
                    "change_24h_pct": entry.get("usd_24h_change"),
                    "market_cap_usd": entry.get("usd_market_cap"),
                    "volume_24h_usd": entry.get("usd_24h_vol"),
                })

            return SkillResult(
                skill=self.name,
                source="CoinGecko",
                fetched_at=datetime.now(timezone.utc),
                data={
                    "stocks": stocks,
                    "count": len(stocks),
                    "note": "xStocks are tokenized equities on Mantle powered by Infinex/Kraken xStocks",
                },
            )
        except Exception as exc:
            logger.exception("mantle-equity failed")
            return SkillResult.failure(self.name, "CoinGecko", str(exc))


register(MantleEquitySkill())
