"""Protocol risk evaluator — TVL stability + audit search for Mantle protocols."""
import asyncio
import logging
from datetime import datetime, timezone

from clients.defillama import get_protocols
from skills.base import SkillResult, register

logger = logging.getLogger(__name__)

_KNOWN_AUDITORS = [
    "certik", "quantstamp", "trail of bits", "consensys diligence",
    "peckshield", "sherlock", "code4rena", "halborn", "spearbit",
    "immunefi", "zellic", "cyfrin", "openzeppelin",
]


def _risk_score(tvl: float, change_1d: float | None, change_7d: float | None, age_days: int) -> dict:
    score = 50  # neutral start

    if tvl > 100_000_000:
        score += 20
    elif tvl > 10_000_000:
        score += 10
    elif tvl < 1_000_000:
        score -= 20

    if change_1d is not None:
        if abs(change_1d) > 30:
            score -= 25
        elif abs(change_1d) > 10:
            score -= 10

    if change_7d is not None:
        if change_7d < -40:
            score -= 20
        elif change_7d < -20:
            score -= 10

    if age_days > 365:
        score += 15
    elif age_days < 30:
        score -= 15

    score = max(0, min(100, score))
    level = "LOW" if score >= 70 else ("MEDIUM" if score >= 40 else "HIGH")
    return {"score": score, "level": level}


class MantleRiskSkill:
    name = "mantle-risk"

    async def run(self, query: str) -> SkillResult:
        protocol_name = query.strip().lower()
        try:
            protocols = await get_protocols()
            match = None
            for p in protocols:
                if (
                    protocol_name in (p.get("name") or "").lower()
                    or protocol_name in (p.get("slug") or "").lower()
                ):
                    chains = {c.lower() for c in (p.get("chains") or [])}
                    if "mantle" in chains or not chains:
                        match = p
                        break

            if not match:
                return SkillResult.failure(
                    self.name,
                    "DefiLlama",
                    f"Protocol '{protocol_name}' not found on Mantle in DefiLlama",
                )

            chain_tvls = match.get("chainTvls") or {}
            mantle_tvl = float(chain_tvls.get("Mantle") or match.get("tvl") or 0)
            change_1d = match.get("change_1d")
            change_7d = match.get("change_7d")
            created_at = match.get("listedAt")
            age_days = 0
            if created_at:
                from datetime import datetime, timezone
                now_ts = datetime.now(timezone.utc).timestamp()
                age_days = int((now_ts - created_at) / 86400)

            risk = _risk_score(mantle_tvl, change_1d, change_7d, age_days)

            flags = []
            if mantle_tvl < 1_000_000:
                flags.append("Low TVL — limited liquidity depth")
            if change_1d and abs(change_1d) > 20:
                flags.append(f"High 1d TVL volatility ({change_1d:+.1f}%)")
            if change_7d and change_7d < -20:
                flags.append(f"Significant 7d TVL decline ({change_7d:+.1f}%)")
            if age_days and age_days < 30:
                flags.append("Protocol is new (< 30 days old)")

            audits = match.get("audits")
            audit_links = match.get("audit_links") or []

            return SkillResult(
                skill=self.name,
                source="DefiLlama",
                fetched_at=datetime.now(timezone.utc),
                data={
                    "protocol": match.get("name"),
                    "slug": match.get("slug"),
                    "category": match.get("category"),
                    "mantle_tvl_usd": mantle_tvl,
                    "global_tvl_usd": match.get("tvl"),
                    "change_1d_pct": change_1d,
                    "change_7d_pct": change_7d,
                    "age_days": age_days,
                    "risk": risk,
                    "risk_flags": flags,
                    "audits": audits,
                    "audit_links": audit_links,
                    "url": match.get("url"),
                    "twitter": match.get("twitter"),
                },
            )
        except Exception as exc:
            logger.exception("mantle-risk failed")
            return SkillResult.failure(self.name, "DefiLlama", str(exc))


register(MantleRiskSkill())
