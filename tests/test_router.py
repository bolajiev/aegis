"""Router and intent classifier tests."""
import pytest
from pipeline.intent import classify, Intent


def test_price_intent():
    assert classify("what's the BTC price") == Intent.PRICE
    assert classify("how much is ETH") == Intent.PRICE
    assert classify("MNT worth?") == Intent.PRICE


def test_chart_intent():
    assert classify("show me a chart for MNT 7d") == Intent.CHART


def test_rwa_intent():
    assert classify("what's Mantle RWA TVL?") == Intent.RWA
    assert classify("tell me about Ondo on Mantle") == Intent.RWA
    assert classify("tokenized bonds on Mantle") == Intent.RWA


def test_equity_intent():
    assert classify("TSLAx price") == Intent.EQUITY
    assert classify("what xStocks are on Mantle") == Intent.EQUITY


def test_news_intent():
    assert classify("latest Mantle news") == Intent.NEWS
    assert classify("what's happening with Mantle this week") == Intent.NEWS


def test_audit_intent():
    assert classify("is Merchant Moe safe?") == Intent.AUDIT
    assert classify("risk assessment for Agni Finance") == Intent.AUDIT


def test_wallet_intent():
    assert classify("check balance of 0x1234567890abcdef1234567890abcdef12345678") == Intent.WALLET


def test_defi_intent():
    assert classify("Mantle DeFi TVL") == Intent.DEFI
    assert classify("best yield on Mantle") == Intent.DEFI


def test_chat_intent():
    assert classify("hi") == Intent.CHAT
    assert classify("hey") == Intent.CHAT
    assert classify("thanks") == Intent.CHAT


def test_research_intent():
    assert classify("explain how mETH works") == Intent.RESEARCH
    assert classify("deep dive into Mantle ecosystem") == Intent.RESEARCH


def test_compare_intent():
    assert classify("compare Agni vs Merchant Moe") == Intent.COMPARE
    assert classify("Agni Finance versus FusionX") == Intent.COMPARE


def test_identity_intent():
    assert classify("what is your onchain identity?") == Intent.IDENTITY
    assert classify("ERC-8004 agent registration") == Intent.IDENTITY


@pytest.mark.asyncio
async def test_router_classifies_and_calls_agent():
    """Router should classify intent and call agent.run with correct params."""
    import skills  # registers skills
    from unittest.mock import AsyncMock, patch
    from pipeline.router import handle

    with patch("pipeline.agent.run", new_callable=AsyncMock) as mock_agent:
        mock_agent.return_value = ("<p>response</p>", [], [])
        reply, lane, results, charts, _intent = await handle("what's MNT price", user_id=42)

    assert mock_agent.called
    call_kwargs = mock_agent.call_args.kwargs
    # Price intent → max_iterations=2
    assert call_kwargs.get("max_iterations") == 2
    assert call_kwargs.get("response_type") == "photo_then_html"
    assert reply == "<p>response</p>"


@pytest.mark.asyncio
async def test_router_research_intent():
    import skills
    from unittest.mock import AsyncMock, patch
    from pipeline.router import handle

    with patch("pipeline.agent.run", new_callable=AsyncMock) as mock_agent:
        mock_agent.return_value = ("<p>research</p>", [], [])
        reply, lane, results, charts, _intent = await handle("deep dive on Agni Finance", user_id=1)

    call_kwargs = mock_agent.call_args.kwargs
    assert call_kwargs.get("max_iterations") == 4
    assert call_kwargs.get("response_type") == "rich"
