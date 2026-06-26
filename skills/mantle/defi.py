"""Mantle DeFi protocol snapshot — TVL, volume, fees per protocol."""
import asyncio
import logging
from datetime import datetime, timezone

from clients.defillama import get_protocols, get_dex_overview, get_fees_overview
from skills.base import SkillResult, register

logger = logging.getLogger(__name__)

_TRACKED = {
    "merchant-moe", "agni-finance", "agni", "aave-v3", "lendle",
    "pendle", "bybit-defi", "init-capital", "cleo-exchange",
    "fusionx-v3", "izumi-finance", "butter-exchange",
}


class MantleDefiSkill:
    name = "mantle-defi"

    async def run(self, query: str) -> SkillResult:
        try:
            protocols_task = get_protocols()
            dex_task = get_dex_overview("Mantle")
            fees_task = get_fees_overview("Mantle")
            protocols, dex, fees = await asyncio.gather(
                protocols_task, dex_task, fees_task, return_exceptions=True
            )

            defi_list = []
            total_tvl = 0.0
            if isinstance(protocols, list):
                for p in protocols:
                    chains = {c.lower() for c in (p.get("chains") or [])}
                    if "mantle" not in chains:
                        continue
                    slug = p.get("slug", "").lower()
                    cat = (p.get("category") or "").lower()
                    if cat in ("rwa", "real world assets"):
                        continue
                    chain_tvls = p.get("chainTvls") or {}
                    mantle_tvl = float(chain_tvls.get("Mantle") or 0)
                    if mantle_tvl < 50_000:
                        continue
                    defi_list.append({
                        "name": p.get("name", slug),
                        "slug": slug,
                        "category": p.get("category"),
                        "tvl_usd": mantle_tvl,
                        "change_1d": p.get("change_1d"),
                        "change_7d": p.get("change_7d"),
                    })
                    total_tvl += mantle_tvl

            defi_list.sort(key=lambda x: x["tvl_usd"], reverse=True)

            return SkillResult(
                skill=self.name,
                source="DefiLlama",
                source_url="https://defillama.com/chain/Mantle",
                fetched_at=datetime.now(timezone.utc),
                data={
                    "total_defi_tvl_usd": total_tvl,
                    "protocols": defi_list[:15],
                    "dex": dex if not isinstance(dex, Exception) else None,
                    "fees": fees if not isinstance(fees, Exception) else None,
                },
            )
        except Exception as exc:
            logger.exception("mantle-defi failed")
            return SkillResult.failure(self.name, "DefiLlama", str(exc))


register(MantleDefiSkill())
