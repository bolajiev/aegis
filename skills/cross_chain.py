"""Cross-chain TVL comparison — Mantle vs peers via DefiLlama /v2/chains."""
import asyncio
import logging
from datetime import datetime, timezone

import httpx

from skills.base import SkillResult, register

logger = logging.getLogger(__name__)

_BASE = "https://api.llama.fi"
_TIMEOUT = 15.0

# Chains to compare; canonical DefiLlama names
_COMPARE_CHAINS = ["Mantle", "Base", "Arbitrum", "Optimism", "Polygon", "Ethereum"]

# RWA category keywords for protocol filtering
_RWA_CATS = {"rwa", "real world assets", "real-world assets", "treasury"}


async def _get_all_chains() -> list[dict]:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        r = await client.get(f"{_BASE}/v2/chains")
        r.raise_for_status()
        return r.json()


async def _get_rwa_tvl_by_chain() -> dict[str, float]:
    """Return {chain_name: rwa_tvl} for chains in _COMPARE_CHAINS."""
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        r = await client.get(f"{_BASE}/protocols")
        r.raise_for_status()
        protocols = r.json()

    rwa_by_chain: dict[str, float] = {}
    for p in protocols:
        cat = (p.get("category") or "").lower()
        if not any(k in cat for k in _RWA_CATS):
            continue
        chain_tvls = p.get("chainTvls") or {}
        for chain, tvl in chain_tvls.items():
            if chain in _COMPARE_CHAINS:
                rwa_by_chain[chain] = rwa_by_chain.get(chain, 0.0) + float(tvl or 0)
    return rwa_by_chain


class CrossChainCompareSkill:
    name = "cross-chain-compare"

    async def run(self, query: str) -> SkillResult:
        try:
            chains_data, rwa_by_chain = await asyncio.gather(
                _get_all_chains(),
                _get_rwa_tvl_by_chain(),
            )

            # Index by name
            chain_index: dict[str, dict] = {}
            for c in chains_data:
                name = c.get("name", "")
                if name in _COMPARE_CHAINS:
                    chain_index[name] = c

            rows = []
            for chain_name in _COMPARE_CHAINS:
                c = chain_index.get(chain_name, {})
                tvl = float(c.get("tvl") or 0)
                rwa = rwa_by_chain.get(chain_name, 0.0)
                rows.append({
                    "chain": chain_name,
                    "total_tvl_usd": tvl,
                    "rwa_tvl_usd": rwa,
                    "rwa_share_pct": round(rwa / tvl * 100, 1) if tvl else 0,
                    "change_1d_pct": c.get("change_1d"),
                    "change_7d_pct": c.get("change_7d"),
                })

            # Sort by total TVL descending
            rows.sort(key=lambda x: x["total_tvl_usd"], reverse=True)

            # Mantle-specific rank
            mantle_rank = next(
                (i + 1 for i, r in enumerate(rows) if r["chain"] == "Mantle"), None
            )

            return SkillResult(
                skill=self.name,
                source="DefiLlama",
                source_url="https://defillama.com/chains",
                fetched_at=datetime.now(timezone.utc),
                data={
                    "chains": rows,
                    "mantle_rank": mantle_rank,
                    "chains_compared": len(rows),
                },
            )
        except Exception as exc:
            logger.exception("cross-chain-compare failed")
            return SkillResult.failure(self.name, "DefiLlama", str(exc))


register(CrossChainCompareSkill())
