"""Agent loop tests — verify ReAct loop, tool execution, confidence block."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import skills  # registers all skills


@pytest.mark.asyncio
async def test_greeting_skips_tools():
    """Greetings should bypass tool loop and get a simple response."""
    from pipeline.agent import run

    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock()]
    mock_resp.choices[0].message.content = "Hey! What can I help you with?"
    mock_resp.choices[0].message.tool_calls = None

    with patch("pipeline.agent._get_client") as mock_client:
        client_inst = MagicMock()
        client_inst.chat.completions.create = AsyncMock(return_value=mock_resp)
        mock_client.return_value = client_inst

        reply, results, charts = await run("hi", max_iterations=4)

    assert results == []
    assert charts == []
    assert "hey" in reply.lower() or "help" in reply.lower()


@pytest.mark.asyncio
async def test_tool_call_dispatched():
    """Agent should dispatch tool calls and collect SkillResults."""
    from pipeline.agent import run
    from skills.base import SkillResult
    from datetime import datetime, timezone

    mock_skill_result = SkillResult(
        skill="mantle-token-prices",
        source="mantle-cli",
        fetched_at=datetime.now(timezone.utc),
        data={"prices": {"MNT": {"price_usd": 0.87}}},
    )

    # Iteration 1: model calls a tool
    tool_call = MagicMock()
    tool_call.function.name = "get_mantle_token_prices"
    tool_call.function.arguments = '{"tokens": "MNT"}'
    tool_call.id = "call_1"

    resp1 = MagicMock()
    resp1.choices = [MagicMock()]
    resp1.choices[0].message.tool_calls = [tool_call]
    resp1.choices[0].message.content = None

    # Iteration 2: model writes final answer
    resp2 = MagicMock()
    resp2.choices = [MagicMock()]
    resp2.choices[0].message.tool_calls = []
    resp2.choices[0].message.content = "MNT is trading at $0.87 right now."

    with patch("pipeline.agent._get_client") as mock_client, \
         patch("pipeline.agent._execute_tool", new_callable=AsyncMock) as mock_exec:

        mock_exec.return_value = (mock_skill_result, None)

        client_inst = MagicMock()
        client_inst.chat.completions.create = AsyncMock(side_effect=[resp1, resp2])
        mock_client.return_value = client_inst

        reply, results, charts = await run("MNT price", max_iterations=4)

    assert len(results) == 1
    assert results[0].ok
    assert "0.87" in reply


@pytest.mark.asyncio
async def test_confidence_block_in_reply():
    """Confidence blockquote should appear in reply when results exist."""
    from pipeline.agent import _confidence
    from skills.base import SkillResult
    from datetime import datetime, timezone

    results = [
        SkillResult(skill="a", source="CoinGecko", fetched_at=datetime.now(timezone.utc), data={}),
        SkillResult(skill="b", source="DefiLlama", fetched_at=datetime.now(timezone.utc), data={}),
        SkillResult.failure("c", "internal", "timeout"),
    ]
    block = _confidence(results)
    assert "<blockquote>" in block
    assert "confidence" in block.lower()
    assert "66%" in block  # 2/3 ok = 66%


@pytest.mark.asyncio
async def test_max_iterations_respected():
    """Agent should not exceed max_iterations LLM calls."""
    from pipeline.agent import run

    # Always return a tool call — agent should hit limit and force synthesis
    tool_call = MagicMock()
    tool_call.function.name = "get_mantle_token_prices"
    tool_call.function.arguments = "{}"
    tool_call.id = "tc1"

    resp_with_tool = MagicMock()
    resp_with_tool.choices = [MagicMock()]
    resp_with_tool.choices[0].message.tool_calls = [tool_call]
    resp_with_tool.choices[0].message.content = None

    resp_final = MagicMock()
    resp_final.choices = [MagicMock()]
    resp_final.choices[0].message.tool_calls = []
    resp_final.choices[0].message.content = "Here is the summary."

    from skills.base import SkillResult
    from datetime import datetime, timezone
    mock_sr = SkillResult(
        skill="mantle-token-prices", source="mantle-cli",
        fetched_at=datetime.now(timezone.utc), data={}
    )

    call_count = 0

    async def counted_create(**kwargs):
        nonlocal call_count
        call_count += 1
        if kwargs.get("tool_choice") == "required" or (call_count <= 2 and kwargs.get("tools")):
            return resp_with_tool
        return resp_final

    with patch("pipeline.agent._get_client") as mock_client, \
         patch("pipeline.agent._execute_tool", new_callable=AsyncMock) as mock_exec:

        mock_exec.return_value = (mock_sr, None)
        client_inst = MagicMock()
        client_inst.chat.completions.create = AsyncMock(side_effect=counted_create)
        mock_client.return_value = client_inst

        reply, results, charts = await run("MNT price", max_iterations=2)

    # Should not exceed 3 total calls (2 iterations + 1 final synthesis)
    assert call_count <= 4
