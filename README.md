# Aegis — Mantle Research Agent

> Autonomous Web3 intelligence in your Telegram DMs. Ask anything about Mantle — live data, cited sources, structured answers.

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![aiogram](https://img.shields.io/badge/aiogram-3.29-2CA5E0?logo=telegram&logoColor=white)](https://aiogram.dev/)
[![Mantle](https://img.shields.io/badge/Mantle-mainnet-000000)](https://mantle.xyz/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## What it does

Aegis is a research agent that answers onchain-finance questions about the Mantle ecosystem with **live, sourced, cited data** — fetched in real time, never hallucinated.

- Token prices with automatic 7-day charts
- Mantle DeFi TVL and protocol analysis
- RWA / tokenized bond breakdown (Ondo, Midas, Maple, MIF4, OpenEden)
- xStocks — tokenized equities (TSLAx, NVDAx, AAPLx, SPCXx, QQQx and more)
- Cross-chain comparison (Mantle vs Base vs Arbitrum vs Optimism)
- Wallet portfolio and Aave V3 positions
- Protocol risk assessment
- Mantle chain stats (gas, blocks) via the official mantle-cli
- Web research and news synthesis (DuckDuckGo + CoinGecko News)
- ERC-8004 onchain agent identity
- Scheduled delayed queries ("check MNT price in 5 minutes")
- Cross-session memory (watchlist, research history, risk profile)

---

## Architecture

```
User message
    │
    ▼
Middleware ── rate limit (10/min) · scheduled delay parser · typing indicator
    │
    ▼
Intent Classifier ── 12 intents · rule-based · zero LLM cost
    │                CHAT · PRICE · CHART · RWA · RESEARCH · NEWS
    │                AUDIT · WALLET · DEFI · COMPARE · EQUITY · IDENTITY
    │
    ├── CHAT ──────────────────────→ 1 LLM call, no tools
    │
    └── RESEARCH / PRICE / AUDIT → ReAct Loop
              │
              │  Iteration 1: tool_choice = required (model MUST use live data)
              │  Iteration 2–N: tool_choice = auto  (chain or stop)
              │  Final: synthesis prompt injected
              │
              ▼
         Skills Layer  (14 skills · asyncio.gather · typed SkillResult)
              │
              ▼
         Response Formatter
              │  Markdown → Rich HTML  (##/### → <h2>/<h3> · ** → <b> · - → <ul>)
              │  Sources block — each skill sets source_url to the exact data page
              │  Data confidence score
              │
              ▼
         Telegram delivery
              📊 sendPhoto  (price chart, auto on every price query)
              📄 Rich message (Bot API 10.1)
              🔘 [🔄 Refresh] [🔎 Deep Dive] [📊 Chart] [📤 Export]
```

**Two rules that never break:**
1. Greetings (`hi`, `gm`, `thanks`, etc.) return CHAT — zero API calls, zero tool calls.
2. Raw JSON / tool output never reaches the user. Skills return typed `SkillResult` objects; the formatter emits prose only.

---

## Skills

| Skill | Data source | Returns |
|---|---|---|
| `mantle-rwa-tvl` | DefiLlama | RWA TVL by protocol on Mantle |
| `mantle-defi` | DefiLlama | DeFi TVL, DEX volume, fees |
| `mantle-defi-markets` | mantle-cli + DefiLlama | Aave V3 rates, top LP pools |
| `mantle-token-prices` | mantle-cli + CoinGecko | MNT, mETH, WMNT, USDT prices |
| `mantle-equity` | CoinGecko | TSLAx, NVDAx, AAPLx, SPCXx and more |
| `mantle-chain` | Mantle RPC + mantle-cli | Gas price, block height, chain status |
| `mantle-portfolio` | Mantle RPC + mantle-cli | Wallet balances, Aave positions |
| `mantle-risk` | DefiLlama + web search | TVL trend, audit history, risk score |
| `mantle-identity` | Mantle RPC | ERC-8004 agent identity lookup |
| `cross-chain-compare` | DefiLlama `/v2/chains` | TVL + RWA across 6 EVM chains |
| `crypto-price` | CoinGecko | Price, 24h change, market cap, volume |
| `news` | DuckDuckGo + CoinGecko News | Latest Mantle + Web3 news |
| `web-search` | DuckDuckGo | Open-ended research queries |
| `fetch-url` | HTTP + content extraction | Full article / document content |

SKILL.md manifests in `skill_manifests/<skill-id>/SKILL.md` follow the exact format of [mantle-xyz/mantle-skills](https://github.com/mantle-xyz/mantle-skills).

---

## Quick start

```bash
# 1. Clone and install
git clone https://github.com/<your-username>/aegis.git
cd aegis
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Fill in TELEGRAM_BOT_TOKEN and QWEN_API_KEY

# 3. Run
python3 bot.py

# 4. Test
pytest -q
```

### Environment variables

| Variable | Required | Description |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | ✅ | From @BotFather |
| `QWEN_API_KEY` | ✅ | Alibaba Cloud MaaS API key |
| `QWEN_BASE_URL` | — | Qwen endpoint (defaults to `ap-southeast-1`) |
| `MANTLE_RPC_URL` | — | Mantle mainnet RPC (defaults to `rpc.mantle.xyz`) |
| `COINGECKO_API_KEY` | — | Optional — raises free-tier rate limits |
| `MANTLESCAN_API_KEY` | — | Optional — enables scan stats |
| `AGENT_PRIVATE_KEY` | — | Used once for ERC-8004 registration |

---

## Models

| Role | Model | Why |
|---|---|---|
| Intent classification | `qwen-turbo` | Near-zero latency, cheap, accurate on 12 intents |
| Answer synthesis | `qwen-plus` | Higher reasoning quality for structured prose |

Both models run via the OpenAI-compatible Alibaba Cloud MaaS endpoint. Swap to Claude (`claude-haiku-4-5-20251001` / `claude-sonnet-4-6`) by changing two lines in `config.py`.

---

## ReAct Loop

The agent uses a **Reason + Act** loop — it thinks, calls tools, observes results, and repeats until confident.

- **Iteration 1:** `tool_choice = required` — the model is forced to call at least one tool. It cannot respond from training data.
- **Iterations 2–N:** `tool_choice = auto` — the model can chain tools, cross-reference sources, or stop when ready.
- **Final iteration:** synthesis prompt injected: *"Write your final response using only the tool data above."*
- **Live progress:** the ⏳ Thinking message is edited in real time as each tool fires.

Iteration depth by intent: `CHAT=1 · PRICE=2 · NEWS=3 · DEFI=3 · RWA=3 · RESEARCH=4 · AUDIT=6`

---

## Memory

**Session memory** — last 20 message exchanges per user, 4-hour TTL, in-process. Enables natural follow-ups.

**Long-term memory** — SQLite, persists across restarts. Per user:
- Watchlist (tokens and protocols mentioned)
- Research history (last 30 queries with dates)
- Risk profile (derived from query patterns: `conservative / moderate / degen`)

A compact context summary is injected into every agent call:
```
[User context: Watching: MNT, TSLAx | Recent research: Mantle RWA, xStocks | Risk: moderate]
```

---

## ERC-8004 Onchain Identity

Aegis is registered as an AI agent on Mantle mainnet via the [AgentIdentity ERC-8004 registry](https://mantlescan.xyz/address/0x8004A169FB4a3325136EB29fA0ceB6D2e539a432).

To register (one-time setup, requires a funded wallet):
```bash
AGENT_PRIVATE_KEY=0x... python3 register_agent.py
```

---

## Project structure

```
aegis/
├── bot.py                    # aiogram entry point, handlers, inline buttons
├── config.py                 # pydantic-settings config
├── register_agent.py         # one-time ERC-8004 registration
│
├── pipeline/
│   ├── intent.py             # 12-intent rule-based classifier
│   ├── router.py             # lane routing
│   └── agent.py              # ReAct loop, tool executor, response formatter
│
├── skills/
│   ├── base.py               # SkillResult (pydantic), Skill ABC, registry
│   ├── crypto_price.py
│   ├── cross_chain.py        # multi-chain TVL + RWA comparison
│   ├── news.py               # DuckDuckGo + CoinGecko News
│   ├── web_search.py
│   ├── fetch_url.py
│   └── mantle/
│       ├── rwa_tvl.py
│       ├── defi.py
│       ├── defi_markets.py
│       ├── token_prices.py
│       ├── equity.py
│       ├── chain.py
│       ├── portfolio.py
│       ├── risk.py
│       └── identity.py
│
├── clients/
│   ├── defillama.py
│   ├── coingecko.py
│   ├── llm.py                # Qwen chat wrapper
│   └── mantle.py             # RPC + mantlescan client
│
├── memory/
│   ├── user.py               # SQLite long-term user memory
│   └── cache.py              # In-process TTL cache
│
├── scheduler/
│   └── tasks.py              # Delayed query scheduler
│
├── middleware/
│   └── logger.py             # Request logging (never logs secrets)
│
├── skill_manifests/          # SKILL.md manifests (mantle-skills format)
│   ├── mantle-rwa-tvl/
│   ├── mantle-defi-snapshot/
│   ├── mantle-onchain-read/
│   ├── general-crypto-price/
│   ├── news-digest/
│   └── erc8004-lookup/
│
└── tests/                    # 28 tests — pytest -q
```

---

## Stack

- **Python 3.11+**, **aiogram 3.29** (Router/Dispatcher — not 2.x)
- **openai** SDK pointing at Alibaba Cloud MaaS (Qwen)
- **httpx** fully async with retry logic (3 attempts, exponential backoff for 429/5xx)
- **pydantic v2** + **pydantic-settings** — typed config and typed skill I/O across every layer
- **SQLite** — long-term user memory (no external database required)
- **web3.py** — ERC-8004 registry reads on Mantle mainnet

---

Built for the **Mantle Research Challenge — Track 2**.
