"""Skill unit tests — verify registration, output shapes, and fallback behavior."""
import asyncio
import pytest
from unittest.mock import AsyncMock, patch

import skills  # registers all skills

from skills.base import get_skill, SkillResult


def test_all_skills_registered():
    expected = [
        "mantle-rwa-tvl", "mantle-defi", "mantle-defi-markets",
        "mantle-token-prices", "mantle-equity", "mantle-chain",
        "mantle-portfolio", "mantle-risk", "mantle-identity",
        "crypto-price", "news", "web-search", "fetch-url",
    ]
    for name in expected:
        assert get_skill(name) is not None, f"Skill not registered: {name}"


def test_skill_result_failure():
    r = SkillResult.failure("test", "src", "boom")
    assert r.ok is False
    assert r.error == "boom"
    assert r.skill == "test"
    assert r.source == "src"


@pytest.mark.asyncio
async def test_crypto_price_skill_mnt():
    skill = get_skill("crypto-price")
    # Patch at skills.crypto_price since it imports get_mnt_info at module level
    with patch("skills.crypto_price.get_mnt_info", new_callable=AsyncMock) as m:
        m.return_value = {
            "price_usd": 0.87,
            "market_cap_usd": 890_000_000,
            "price_change_24h_pct": -2.3,
        }
        result = await skill.run("MNT")
    assert result.ok
    assert result.data["price_usd"] == 0.87
    assert result.source == "CoinGecko"


@pytest.mark.asyncio
async def test_crypto_price_skill_btc():
    skill = get_skill("crypto-price")
    with patch("skills.crypto_price.get_prices", new_callable=AsyncMock) as m:
        m.return_value = {"bitcoin": {"usd": 68000, "usd_24h_change": 1.5, "usd_market_cap": 1_340_000_000_000}}
        result = await skill.run("BTC")
    assert result.ok
    assert result.data["price_usd"] == 68000


@pytest.mark.asyncio
async def test_rwa_tvl_skill():
    skill = get_skill("mantle-rwa-tvl")
    protocols = [
        {"name": "Ondo Finance", "slug": "ondo-finance", "category": "RWA", "chains": ["Mantle"],
         "chainTvls": {"Mantle": 280_000_000}, "change_1d": 0.4, "change_7d": 2.1},
        {"name": "Midas", "slug": "midas", "category": "RWA", "chains": ["Mantle"],
         "chainTvls": {"Mantle": 82_000_000}, "change_1d": -0.2, "change_7d": 1.5},
        {"name": "Unrelated DEX", "slug": "some-dex", "category": "Dexes", "chains": ["Ethereum"],
         "chainTvls": {}, "change_1d": 0, "change_7d": 0},
    ]
    with patch("clients.defillama.get_protocols", new_callable=AsyncMock) as m:
        m.return_value = protocols
        result = await skill.run("RWA")
    assert result.ok
    assert result.data["count"] >= 2
    assert result.data["total_rwa_tvl_usd"] > 0


@pytest.mark.asyncio
async def test_equity_skill():
    skill = get_skill("mantle-equity")
    with patch("clients.coingecko.get_prices", new_callable=AsyncMock) as m:
        m.return_value = {
            "tesla-xstock": {"usd": 182.5, "usd_24h_change": 1.2, "usd_market_cap": 8_500_000},
        }
        result = await skill.run("xStocks")
    assert result.ok


@pytest.mark.asyncio
async def test_chain_skill_fallback():
    skill = get_skill("mantle-chain")
    with patch("clients.mcp_cli.call", new_callable=AsyncMock) as mc, \
         patch("clients.mantle.get_gas_price_gwei", new_callable=AsyncMock) as mg, \
         patch("clients.mantle.get_latest_block", new_callable=AsyncMock) as mb:
        mc.return_value = None  # CLI unavailable
        mg.return_value = 0.02
        mb.return_value = {"number": 71234567, "tx_count": 42, "base_fee_gwei": 0.001}
        result = await skill.run("chain stats")
    assert result.ok
    assert result.data["chain_id"] == 5000


@pytest.mark.asyncio
async def test_portfolio_skill_no_address():
    skill = get_skill("mantle-portfolio")
    result = await skill.run("what's in my wallet?")
    assert not result.ok
    assert "0x" in result.error.lower() or "address" in result.error.lower()


@pytest.mark.asyncio
async def test_fetch_url_invalid():
    skill = get_skill("fetch-url")
    result = await skill.run("not a url")
    assert not result.ok


@pytest.mark.asyncio
async def test_web_search_empty():
    skill = get_skill("web-search")
    result = await skill.run("")
    assert not result.ok
