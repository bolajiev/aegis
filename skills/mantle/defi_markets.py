"""Mantle DeFi markets — Aave V3 lending rates + top pools via mantle-cli + DefiLlama."""
import asyncio
import logging
from datetime import datetime, timezone

from clients.mcp_cli import call as mcp_call
from clients.defillama import get_protocols
from skills.base import SkillResult, register

logger = logging.getLogger(__name__)

_DEX_SLUGS = {
    "merchant-moe", "agni-finance", "agni", "fusionx-v3", "butter-exchange",
    "cleo-exchange", "izumi-finance", "fluxion",
}


async def _top_pools_from_defillama() -> list[dict]:
    """Get top DEX pools on Mantle from DefiLlama protocol list."""
    try:
        protocols = await get_protocols()
        pools = []
        for p in protocols:
            chains = {c.lower() for c in (p.get("chains") or [])}
            if "mantle" not in chains:
                continue
            slug = (p.get("slug") or "").lower()
            cat = (p.get("category") or "").lower()
            if cat not in ("dexes", "dex") and slug not in _DEX_SLUGS:
                continue
            chain_tvls = p.get("chainTvls") or {}
            tvl = float(chain_tvls.get("Mantle") or 0)
            if tvl < 100_000:
                continue
            pools.append({
                "name": p.get("name", slug),
                "tvl_usd": tvl,
                "change_1d": p.get("change_1d"),
                "change_7d": p.get("change_7d"),
                "url": p.get("url"),
            })
        return sorted(pools, key=lambda x: x["tvl_usd"], reverse=True)[:10]
    except Exception as exc:
        logger.warning("DefiLlama pool fallback failed: %s", exc)
        return []


class MantleDefiMarketsSkill:
    name = "mantle-defi-markets"

    async def run(self, query: str) -> SkillResult:
        try:
            aave_task  = mcp_call(["aave", "markets"])
            pools_task = _top_pools_from_defillama()

            aave_data, pools = await asyncio.gather(aave_task, pools_task)

            result: dict = {}

            if aave_data:
                markets = (
                    aave_data if isinstance(aave_data, list)
                    else aave_data.get("markets", []) if isinstance(aave_data, dict)
                    else []
                )
                result["aave_v3"] = {
                    "markets": markets[:20],
                    "pool_address": "0x458F293454fE0d67EC0655f3672301301DD51422",
                }

            if pools:
                result["top_dex_pools"] = pools

            if not result:
                return SkillResult.failure(
                    self.name,
                    "mantle-cli / DefiLlama",
                    "No DeFi market data available",
                )

            return SkillResult(
                skill=self.name,
                source="mantle-cli / DefiLlama",
                source_url="https://app.aave.com/?marketName=proto_mantle_v3",
                fetched_at=datetime.now(timezone.utc),
                data=result,
            )
        except Exception as exc:
            logger.exception("mantle-defi-markets failed")
            return SkillResult.failure(self.name, "mantle-cli", str(exc))


register(MantleDefiMarketsSkill())
