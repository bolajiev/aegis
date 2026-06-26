"""
Aegis ReAct agent — Reason + Act loop.

Flow per query:
  1. Classify intent (caller sets max_iterations + response_type)
  2. First call: tool_choice="required" (model MUST get live data)
  3. Execute all tool calls in parallel via asyncio.gather
  4. Feed observations back; model reasons and calls more tools or answers
  5. On last iteration: inject "write your final answer now" message
  6. Format response based on response_type (html / rich / photo_then_html)

Returns (html_reply, skill_results, charts).
"""
from __future__ import annotations

import asyncio
import html as _html_lib
import json
import logging
import re
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone

from openai import AsyncOpenAI

from config import settings
from skills.base import SkillResult, get_skill

_TOOL_LABELS: dict[str, str] = {
    "get_mantle_rwa_tvl":      "📋 Checking Mantle RWA TVL",
    "get_mantle_defi":         "📊 Pulling DeFi protocol data",
    "get_mantle_token_prices": "💰 Fetching token prices",
    "get_price_chart":         "📈 Rendering price chart",
    "get_crypto_price":        "💱 Looking up price",
    "get_mantle_chain":        "⛓️ Reading chain stats",
    "get_mantle_portfolio":    "👛 Scanning wallet",
    "get_mantle_risk":         "🔍 Running risk check",
    "get_mantle_defi_markets": "🏦 Checking Aave markets",
    "search_web":              "🌐 Searching the web",
    "fetch_url":               "📄 Reading article",
    "get_tokenized_equities":  "📈 Fetching xStocks prices",
    "get_agent_identity":      "🪪 Checking agent identity",
    "compare_chains":          "⚖️ Comparing chains",
}

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_mantle_rwa_tvl",
            "description": (
                "Fetch live RWA TVL on Mantle: Ondo, Midas, MIF4, OpenEden, Maple, Backed Finance. "
                "Use for tokenized bonds, treasuries, RWAs, institutional DeFi on Mantle."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_mantle_defi",
            "description": (
                "Live DeFi protocol TVLs on Mantle: Merchant Moe, Agni Finance, Aave V3, "
                "Lendle, Pendle, FusionX, Init Capital, Bybit DeFi. DEX volume + fees. "
                "Use for DeFi TVL, protocol comparison, DEX activity on Mantle."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_mantle_defi_markets",
            "description": (
                "Live Aave V3 lending rates on Mantle (supply APY, borrow APY, utilization) "
                "and top LP pools by TVL (Merchant Moe, Agni, Fluxion). "
                "Use for: yield, APY, lending rates, best LP opportunities on Mantle."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_mantle_token_prices",
            "description": (
                "Live prices for Mantle-native tokens: MNT, WMNT, mETH, USDT, USDC, WETH, FBTC. "
                "Uses official mantle-cli with CoinGecko fallback. "
                "Use for MNT price, mETH price, or any Mantle ecosystem token."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "tokens": {
                        "type": "string",
                        "description": "Comma-separated token symbols, e.g. 'MNT,mETH,USDT'",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_tokenized_equities",
            "description": (
                "Live prices for tokenized stocks (xStocks) on Mantle: "
                "SPCXx (SpaceX), TSLAx, NVDAx, AAPLx, QQQx, GOOGLx, MSTRx, GLDx. "
                "Use for xStocks, tokenized shares, synthetic equities on Mantle."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_crypto_price",
            "description": (
                "Live price, 24h change, market cap for any cryptocurrency (non-Mantle tokens). "
                "Use for BTC, ETH, SOL, BNB, ARB, OP, AVAX, MATIC, or any coin by name/ticker."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "coin": {
                        "type": "string",
                        "description": "Coin name or ticker, e.g. 'bitcoin', 'BTC', 'ethereum'",
                    }
                },
                "required": ["coin"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_mantle_chain",
            "description": (
                "Live Mantle chain stats: gas price (MNT), block height, chain health. "
                "Also fetches MNT balance for a specific wallet address. "
                "Use for gas, block, chain health, or 'check balance of 0x...' queries. "
                "MNT is the gas token on Mantle (chain ID 5000)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "address": {
                        "type": "string",
                        "description": "Wallet address (0x...) for balance lookup (optional)",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_mantle_portfolio",
            "description": (
                "Full wallet portfolio on Mantle for a given 0x address: "
                "native MNT balance, ERC-20 token balances (USDT, USDC, WETH, mETH), "
                "and Aave V3 lending/borrowing positions."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "address": {
                        "type": "string",
                        "description": "Wallet address (0x...)",
                    }
                },
                "required": ["address"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_mantle_risk",
            "description": (
                "Risk assessment for a Mantle protocol: TVL stability, audit history, "
                "risk score (0-100), and risk flags. "
                "Use when user asks if a protocol is safe, risky, or has been audited."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "protocol": {
                        "type": "string",
                        "description": "Protocol name or slug, e.g. 'merchant-moe', 'agni finance'",
                    }
                },
                "required": ["protocol"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_agent_identity",
            "description": (
                "Look up Aegis's ERC-8004 onchain agent identity on Mantle. "
                "Use for questions about Aegis's identity, onchain registration, agent NFT."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_chains",
            "description": (
                "Compare TVL and RWA metrics across EVM chains: Mantle vs Base, Arbitrum, Optimism, "
                "Polygon, Ethereum. Use for 'compare', 'vs', 'how does Mantle stack up', "
                "'cross-chain', 'which chain has more RWA' type questions."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_price_chart",
            "description": (
                "Render a price or TVL chart as an image. "
                "Call for price queries (7d default) — chart ALWAYS accompanies price data. "
                "Also call when user explicitly asks for a chart, graph, or trend."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "coin": {
                        "type": "string",
                        "description": "Coin ticker/name, or 'mantle_tvl' for chain TVL chart",
                    },
                    "days": {
                        "type": "number",
                        "description": "Days of history. Default 7.",
                    },
                },
                "required": ["coin"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": (
                "Search the web for recent news, announcements, protocol info, and current events. "
                "Use for: Mantle news, protocol research, DeFi narratives, anything needing web sources."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query — be specific, include year for recency",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_url",
            "description": (
                "Fetch and read full content of a specific URL. "
                "Use after search_web to read a specific article or documentation in depth."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "Full URL starting with https://",
                    }
                },
                "required": ["url"],
            },
        },
    },
]

_TOOL_TO_SKILL: dict[str, str] = {
    "get_mantle_rwa_tvl":      "mantle-rwa-tvl",
    "get_mantle_defi":         "mantle-defi",
    "get_mantle_defi_markets": "mantle-defi-markets",
    "get_mantle_token_prices": "mantle-token-prices",
    "get_tokenized_equities":  "mantle-equity",
    "get_crypto_price":        "crypto-price",
    "get_mantle_chain":        "mantle-chain",
    "get_mantle_portfolio":    "mantle-portfolio",
    "get_mantle_risk":         "mantle-risk",
    "get_agent_identity":      "mantle-identity",
    "search_web":              "web-search",
    "fetch_url":               "fetch-url",
    "compare_chains":          "cross-chain-compare",
}

_SMALLTALK = frozenset({
    "hi", "hey", "hello", "gm", "gn", "yo", "sup", "hiya",
    "thanks", "thank you", "thx", "ty", "thank", "thank u",
    "ok", "okay", "bye", "lol", "haha", "lmao",
    "cool", "nice", "great", "awesome", "good", "got it",
    "perfect", "sounds good", "makes sense", "noted",
})


def _get_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=settings.qwen_api_key,
        base_url=settings.qwen_base_url,
    )


def _system_prompt() -> str:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"""\
=================================================================
SYSTEM — AEGIS WEB3 RESEARCH AGENT
=================================================================

IDENTITY
--------
You are AEGIS, an autonomous Web3 research agent specializing in the
Mantle ecosystem and broader onchain finance. Today is {today}.

You are sharp, direct, and knowledgeable — not a template machine.
You talk to people like a person. Casual question → casual answer.
Deep query → structured report. Read the room.

You do NOT guess. You do NOT hallucinate onchain data.
If data is unavailable: "Data unavailable — [reason]."

CRITICAL — DATA FRESHNESS AND ACCURACY
-----------------------------------------
NEVER use training-data prices, TVL, APY rates, or market stats.
You MUST call tools for ALL numbers. Your training data is outdated.
Always cite numbers from tool results — never invent or extrapolate.

SPECIFIC FORBIDDEN BEHAVIORS:
• Never state a specific APY/rate (e.g. "5.32% APY") unless a tool returned it
• Never state 7d change percentages unless a tool returned them
• Never name specific vault features or launches unless a tool confirmed them
• If you want to mention something but don't have tool data for it, say "reportedly" or omit it
• "Also worth knowing" bullets must ONLY contain facts from tool results

YOUR CAPABILITIES
-----------------
• Live token prices + auto price charts on every price query
• Mantle DeFi TVL analysis (DefiLlama)
• RWA / tokenized asset analysis
• xStocks (tokenized equities) on Mantle
• Wallet portfolio + Aave V3 positions
• Protocol risk assessment
• Mantle chain stats (gas, blocks) via mantle-cli
• ERC-8004 agent identity
• Web research and news synthesis
• URL reading for deep article analysis
• Cross-source verification

CONVERSATION STYLE
------------------
CASUAL → match their energy:
  "yo what's MNT at" → "MNT sitting at $0.87, down 2.3% today. Chart 👇"

FOLLOW-UP → use context from history:
  "what about TVL" → reference Mantle and whatever they asked before

DEEP QUERY → full structured response with sections

CONFUSED → ask ONE clarifying question, conversationally

DO NOT default to full report format for every message. It gets annoying.

PROACTIVE INTEL
---------------
After every substantive response, add "Also worth knowing" with 1–3
genuinely relevant related intel the user didn't ask for but probably needs.
Keep it brief. Only add if actually relevant.

PRICE QUERIES — CHART IS AUTOMATIC
-------------------------------------
When user asks about price:
→ ALWAYS call get_price_chart alongside the price tool (7d default)
→ Chart goes first, then text summary
→ ONLY skip chart if user explicitly says "no chart" or "just the price"

RESPONSE FORMAT RULES
----------------------
STRICT OUTPUT RULES — read carefully:
• NO HTML tags — never write <b>, <i>, <p>, <h2>, etc.
• NO markdown image embeds — never write ![alt](url) or ![](url)
• NO markdown links — never write [text](url)
• NO raw JSON or code fences

USE THIS MARKDOWN STRUCTURE — the system converts it to rich formatting:

## Section Header        ← becomes <h2> (large heading)
### Sub-header           ← becomes <h3> (medium heading)
**bold text**            ← becomes bold
- bullet item            ← becomes list item (use - not •)

TEMPLATES BY QUERY TYPE:

PRICE query:
**[TOKEN] — $[price]** ([change]% 24h)
[2-3 sentence analysis of what the price means, direction, context]

**Also worth knowing:**
- [related intel 1]
- [related intel 2]

RESEARCH / DEEP DIVE:
## [Topic Title]
[1-2 sentence overview]

### Key Numbers
- **[Metric]:** [value]
- **[Metric]:** [value]

### Analysis
[3-5 sentences of actual analysis — take a position, explain why]

### Risk Flags
- [flag 1]
- [flag 2]

### Also Worth Knowing
- [proactive intel 1]
- [proactive intel 2]

### Bottom Line
[1 sentence verdict — the single most important thing the user should know]

NEWS:
## What Happened This Week
### [Story Title]
[2-3 sentence summary with onchain verification]

### [Story Title]
[summary]

COMPARE (cross-chain):
## [Chain A] vs [Chain B] — [Topic]

### TVL Comparison
- **[Chain]:** $[tvl] ([7d change])
- **[Chain]:** $[tvl] ([7d change])

### RWA Breakdown
- **[Chain]:** $[rwa_tvl] ([rwa_share]% of total)
- **[Chain]:** $[rwa_tvl] ([rwa_share]% of total)

### What This Means
[2-3 sentence analysis — who's winning and why it matters for investors]

### Bottom Line
[1 sentence verdict]

RISK / AUDIT:
## Risk Assessment: [Protocol]
**Verdict: [LOW / MEDIUM / HIGH RISK]**
[explanation of verdict]

### Evidence
- **TVL:** [value] ([trend])
- **Audits:** [yes/no, auditor names]
- **Age:** [days old]

### Red Flags
- [flag if any]

### Bottom Line
[1 sentence verdict — is it safe to use right now?]

MANTLE FACTS (always current)
------------------------------
• Mantle chain ID: 5000
• Gas token: MNT (not ETH)
• mETH: Mantle's staked ETH product
• Key protocols: Merchant Moe (DEX), Agni (DEX), Aave V3 (lending),
  Lendle (lending), Pendle (yield), FusionX (DEX), Init Capital
• RWA leaders: Ondo, Midas, Maple/Syrup, MIF4, OpenEden
• xStocks: TSLAx, NVDAx, SPCXx, AAPLx, QQQx, GOOGLx, MSTRx, GLDx
• Explorer: mantlescan.xyz
• Bridge: app.mantle.xyz/bridge

TOOL SELECTION GUIDE
---------------------
• MNT / Mantle token price → get_mantle_token_prices
• Any other crypto price → get_crypto_price
• Price query of any kind → ALSO call get_price_chart
• Mantle DeFi TVL / protocol list → get_mantle_defi
• Aave rates / LP yields → get_mantle_defi_markets
• RWA / tokenized bonds → get_mantle_rwa_tvl
• xStocks → get_tokenized_equities
• Chain stats / gas / wallet MNT balance → get_mantle_chain
• Full wallet portfolio → get_mantle_portfolio
• Protocol safety / audit → get_mantle_risk
• Aegis identity → get_agent_identity
• News / current events → search_web
• Cross-chain compare / "vs" / "how does Mantle stack up" → compare_chains + get_mantle_rwa_tvl
• Read full article → fetch_url (after search_web)
• Cross-reference: call 2+ tools when possible for critical data
================================================================="""


# ---------------------------------------------------------------------------
# Tool executor
# ---------------------------------------------------------------------------

async def _execute_tool(
    tool_name: str,
    args: dict,
    original_query: str,
) -> tuple[SkillResult, bytes | None]:
    """Execute one tool. Returns (SkillResult, optional chart PNG)."""

    # Chart — handled separately
    if tool_name == "get_price_chart":
        coin = args.get("coin", "").strip() or "bitcoin"
        days = int(args.get("days") or 7)
        try:
            from formatters.chart import render
            png, caption = await render(coin, days)
            return SkillResult(
                skill="price-chart",
                source="CoinGecko / DefiLlama",
                data={"coin": coin, "days": days, "caption": caption},
            ), png
        except Exception as exc:
            return SkillResult.failure("price-chart", "CoinGecko", str(exc)), None

    skill_name = _TOOL_TO_SKILL.get(tool_name)
    if not skill_name:
        return SkillResult.failure(tool_name, "internal", f"Unknown tool: {tool_name}"), None

    skill = get_skill(skill_name)
    if not skill:
        return SkillResult.failure(tool_name, "internal", f"Skill not registered: {skill_name}"), None

    # Pick the best argument for the skill's query param
    query = (
        args.get("address")
        or args.get("protocol")
        or args.get("coin")
        or args.get("tokens")
        or args.get("query")
        or args.get("url")
        or original_query
    )
    try:
        result = await skill.run(query)
        return result, None
    except Exception as exc:
        return SkillResult.failure(skill_name, "internal", str(exc)), None


def _tool_result_content(sr: SkillResult) -> str:
    if not sr.ok:
        return json.dumps({"error": sr.error or "unavailable", "skill": sr.skill})
    data = {k: v for k, v in sr.data.items() if "png" not in k.lower()}
    return json.dumps({
        "skill": sr.skill,
        "source": sr.source,
        "fetched_at": sr.fetched_at.isoformat(),
        "data": data,
    }, default=str)


def _confidence(results: list[SkillResult]) -> str:
    if not results:
        return ""
    ok = [r for r in results if r.ok]
    sources = len({r.source for r in ok})
    pct = int(len(ok) / len(results) * 100) if results else 0
    # ✅ if all tools succeeded (regardless of source count)
    # ⚠️ if partial failure or only 1 source for a multi-source query
    if pct >= 90 and not [r for r in results if not r.ok]:
        icon = "✅"
    elif pct >= 60:
        icon = "⚠️"
    else:
        icon = "❌"
    failed = [r.skill for r in results if not r.ok]
    note = f" · unverified on: {', '.join(failed)}" if failed else ""
    label = f"{icon} {pct}% data confidence · {sources} source{'s' if sources != 1 else ''}{note}"
    return f"<blockquote>{_html_lib.escape(label)}</blockquote>"


def _sources_block(results: list[SkillResult]) -> str:
    seen: set[str] = set()
    lines = []
    for r in results:
        if not r.ok:
            continue
        ts = r.fetched_at.strftime("%H:%M UTC")

        # Web search / news: link to each real article, not a generic search engine
        if r.skill in ("web-search", "news") and isinstance(r.data.get("results"), list):
            for item in r.data["results"][:3]:
                item_url = item.get("url", "")
                title = (item.get("title") or item_url)[:55]
                key = f"article:{item_url}"
                if item_url and key not in seen:
                    seen.add(key)
                    lines.append(f'<a href="{_html_lib.escape(item_url)}">{_html_lib.escape(title)}</a>')
            continue

        if r.source in seen:
            continue
        seen.add(r.source)

        # Use exact source_url from the skill (set to the real data page) — no guessing
        url = r.source_url or (r.data.get("url") if r.skill == "fetch-url" else None)
        label = _html_lib.escape(r.source)
        if url:
            lines.append(f'<a href="{_html_lib.escape(url)}">{label}</a> · {ts}')
        else:
            lines.append(f"{label} · {ts}")

    if not lines:
        return ""
    # Two blank lines between each source so they're easy to tap separately
    inner = "\n\n".join(lines)
    return f"<blockquote>📌 Sources\n\n{inner}</blockquote>"


def _inline(text: str) -> str:
    """Escape then apply inline markdown → HTML (bold, italic, code)."""
    text = _html_lib.escape(text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\*([^*]+)\*",     r"<i>\1</i>", text)
    text = re.sub(r"`([^`]+)`",       r"<code>\1</code>", text)
    return text


def _md_to_html(text: str) -> str:
    """
    Convert model's structured markdown to Telegram rich HTML.
    Handles: ## h2, ### h3, - lists, **bold**, *italic*, `code`, paragraphs.
    """
    # Sanitise first — strip bad stuff
    text = re.sub(r"```[^`]*```", "", text, flags=re.DOTALL)
    text = re.sub(r"!\[.*?\]\([^)]*\)", "", text)          # strip ![](url)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)   # strip [text](url) → text
    text = re.sub(r"<[^>]+>", "", text)                     # strip raw HTML from model

    lines = text.split("\n")
    parts: list[str] = []
    list_items: list[str] = []

    def flush_list():
        if list_items:
            parts.append("<ul>" + "".join(f"<li>{item}</li>" for item in list_items) + "</ul>")
            list_items.clear()

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("## "):
            flush_list()
            parts.append(f"<h2>{_inline(stripped[3:])}</h2>")

        elif stripped.startswith("### "):
            flush_list()
            parts.append(f"<h3>{_inline(stripped[4:])}</h3>")

        elif stripped.startswith("- ") or stripped.startswith("* "):
            list_items.append(_inline(stripped[2:]))

        elif stripped == "":
            flush_list()
            # blank line = paragraph break, don't add empty element

        else:
            flush_list()
            parts.append(f"<p>{_inline(stripped)}</p>")

    flush_list()
    return "\n".join(p for p in parts if p)


def _build_response(prose: str, results: list[SkillResult], response_type: str) -> str:
    """Convert model output to rich HTML, append sources and confidence."""
    body = _md_to_html(prose)
    parts = [body] if body else ["<p>Data retrieved.</p>"]

    sources = _sources_block(results)
    confidence = _confidence(results)

    if sources:
        parts.append(sources)
    if confidence:
        parts.append(confidence)

    return "\n".join(p for p in parts if p)


# ---------------------------------------------------------------------------
# Main ReAct loop
# ---------------------------------------------------------------------------

async def run(
    query: str,
    history: list[dict] | None = None,
    max_iterations: int = 4,
    response_type: str = "rich",
    intent: str = "",
    progress_cb: Callable[[str], Awaitable[None]] | None = None,
    user_context: str = "",
) -> tuple[str, list[SkillResult], list[tuple[bytes, str]]]:
    """
    ReAct agent loop.
    Returns (html_reply, all_skill_results, charts_list).
    """
    client = _get_client()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Build messages — inject conversation history + long-term user context
    messages: list[dict] = [{"role": "system", "content": _system_prompt()}]
    if history:
        messages.extend(history[-10:])

    # Prepend user context so model can personalise (only if non-empty)
    user_query = query
    if user_context:
        user_query = f"[User context: {user_context}]\n\n{query}"
    messages.append({"role": "user", "content": user_query})

    # Skip tool loop for chat/greetings — trust intent classifier OR pattern match
    stripped = query.strip().lower().rstrip("!.,?")
    is_chat = (
        intent == "chat"
        or stripped in _SMALLTALK
        or (len(stripped.split()) <= 4 and not any(c.isdigit() for c in stripped)
            and "?" not in stripped and stripped in _SMALLTALK)
    )
    if is_chat:
        try:
            resp = await client.chat.completions.create(
                model=settings.synth_model,
                messages=messages,
                max_tokens=250,
                temperature=0.7,
            )
            prose = (resp.choices[0].message.content or "").strip()
            return f"<p>{_html_lib.escape(prose)}</p>", [], []
        except Exception:
            return "<p>Hey! What can I help you with?</p>", [], []

    all_results: list[SkillResult] = []
    all_charts: list[tuple[bytes, str]] = []
    final_prose = ""

    for iteration in range(max_iterations):
        is_first = iteration == 0

        try:
            response = await client.chat.completions.create(
                model=settings.synth_model,
                messages=messages,
                tools=TOOLS,
                tool_choice="required" if is_first else "auto",
                max_tokens=600,
                temperature=0.1,
            )
        except Exception:
            logger.exception("Agent loop iteration %d failed", iteration)
            break

        choice = response.choices[0]
        tool_calls = choice.message.tool_calls or []

        if not tool_calls:
            final_prose = (choice.message.content or "").strip()
            logger.info("Agent finished at iteration %d", iteration + 1)
            break

        # Append assistant tool-calling message
        messages.append(choice.message)

        tool_names = [tc.function.name for tc in tool_calls]
        logger.info("Iteration %d — tools: %s", iteration + 1, tool_names)

        # Notify the bot which tools are running so it can update the thinking message
        if progress_cb:
            labels = [_TOOL_LABELS.get(n, f"🔧 {n}") for n in tool_names]
            try:
                await progress_cb(labels)
            except Exception:
                pass

        # Execute all tool calls in this round in parallel
        round_results = list(await asyncio.gather(*[
            _execute_tool(
                tc.function.name,
                json.loads(tc.function.arguments or "{}"),
                query,
            )
            for tc in tool_calls
        ]))

        round_skill_results = [r for r, _ in round_results]
        round_charts = [(png, r.data.get("caption", "")) for r, png in round_results if png]

        all_results.extend(round_skill_results)
        all_charts.extend(round_charts)

        for tc, sr in zip(tool_calls, round_skill_results):
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": _tool_result_content(sr),
            })

        if iteration == max_iterations - 1:
            messages.append({
                "role": "user",
                "content": (
                    f"Today is {today}. You have all the data. "
                    "Write your final response now using the RESPONSE FORMAT RULES from your system prompt. "
                    "Use ## for main sections, ### for sub-sections, - for bullet lists, **bold** for key numbers. "
                    "No HTML tags, no JSON, no image markdown. Structure it clearly."
                ),
            })
            try:
                final_resp = await client.chat.completions.create(
                    model=settings.synth_model,
                    messages=messages,
                    max_tokens=800,
                    temperature=0.2,
                )
                final_prose = (final_resp.choices[0].message.content or "").strip()
            except Exception:
                logger.exception("Final synthesis failed")
            break

    if not final_prose:
        final_prose = "I retrieved the data but couldn't produce a summary. Please try again."

    # Reject if model hallucinated JSON or code fences
    if final_prose.startswith("{") or final_prose.startswith("[") or "```" in final_prose:
        logger.warning("Model returned structured output — stripping")
        final_prose = re.sub(r"```[^`]*```", "", final_prose, flags=re.DOTALL).strip()
        if not final_prose:
            final_prose = "Data retrieved. Please ask a more specific question."

    html_reply = _build_response(final_prose, all_results, response_type)
    return html_reply, all_results, all_charts
