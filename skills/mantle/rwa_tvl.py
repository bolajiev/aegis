"""Mantle RWA TVL — tokenized bonds, treasuries, institutional assets."""
import logging
from datetime import datetime, timezone

from clients.defillama import get_protocols
from skills.base import SkillResult, register

logger = logging.getLogger(__name__)

_RWA_SLUGS = {
    "ondo-finance":  "Ondo",
    "midas":         "Midas",
    "maple-finance": "Maple",
    "syrup":         "Syrup (Maple)",
    "mif4":          "MIF4",
    "openeden":      "OpenEden",
    "backed-finance": "Backed Finance",
    "mountainprotocol": "Mountain Protocol",
}


class MantleRwaTvlSkill:
    name = "mantle-rwa-tvl"

    async def run(self, query: str) -> SkillResult:
        try:
            protocols = await get_protocols()
            mantle_rwa = []
            total_tvl = 0.0
            for p in protocols:
                chains = {c.lower() for c in (p.get("chains") or [])}
                if "mantle" not in chains:
                    continue
                slug = p.get("slug", "").lower()
                cat = (p.get("category") or "").lower()
                is_rwa = (
                    "rwa" in cat
                    or "real world" in cat
                    or any(s in slug for s in _RWA_SLUGS)
                )
                if not is_rwa:
                    continue
                chain_tvls = p.get("chainTvls") or {}
                mantle_tvl = chain_tvls.get("Mantle", 0.0)
                label = _RWA_SLUGS.get(slug) or p.get("name", slug)
                mantle_rwa.append({
                    "name": label,
                    "slug": slug,
                    "tvl_usd": mantle_tvl,
                    "change_1d": p.get("change_1d"),
                    "change_7d": p.get("change_7d"),
                    "category": p.get("category"),
                })
                total_tvl += mantle_tvl

            mantle_rwa.sort(key=lambda x: x["tvl_usd"], reverse=True)
            # Build DefiLlama URL for top protocol for easy reference
            top_slug = mantle_rwa[0]["slug"] if mantle_rwa else ""
            top_url = f"https://defillama.com/protocol/{top_slug}" if top_slug else "https://defillama.com/chain/Mantle"
            return SkillResult(
                skill=self.name,
                source="DefiLlama",
                source_url=top_url,
                fetched_at=datetime.now(timezone.utc),
                data={
                    "total_rwa_tvl_usd": total_tvl,
                    "protocols": mantle_rwa,
                    "count": len(mantle_rwa),
                },
            )
        except Exception as exc:
            logger.exception("mantle-rwa-tvl failed")
            return SkillResult.failure(self.name, "DefiLlama", str(exc))


register(MantleRwaTvlSkill())
