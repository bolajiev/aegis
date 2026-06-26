# How Aegis Works

Aegis is a ReAct-loop research agent. Every answer is grounded in live data fetched seconds before you read it — nothing comes from the model's training memory.

![Aegis workflow diagram](workflow.svg)

---

## Step by step

### 1. Message arrives
You send a message in Telegram. The middleware layer checks your rate limit (10 req/min), parses any scheduled delay ("tell me in 5 minutes"), and sends a typing indicator immediately so you know something is happening.

### 2. Intent classification
A rule-based classifier reads your message and assigns one of 12 intents in under 1ms — with no LLM call and no API cost:

| Intent | Example trigger | Max depth |
|---|---|---|
| CHAT | "hi", "gm", "thanks" | 1 — direct reply, no tools |
| PRICE | "MNT price", "what's ETH worth" | 2 |
| CHART | "show me a chart", "7d graph" | 2 |
| RWA | "tokenized bonds", "Ondo TVL" | 3 |
| DEFI | "Mantle TVL", "best yield" | 3 |
| NEWS | "latest Mantle news" | 3 |
| RESEARCH | "deep dive", "explain how mETH works" | 4 |
| AUDIT | "is Merchant Moe safe", "red flags" | 6 |
| WALLET | `0x…` address detected | 3 |
| COMPARE | "vs", "compare", "how does Mantle stack up" | 4 |
| EQUITY | "TSLAx", "xStocks" | 2 |
| IDENTITY | "who are you", "ERC-8004" | 2 |

**CHAT** returns immediately with zero API calls. All other intents enter the ReAct loop.

### 3. The ReAct Loop (Reason + Act)

The core of Aegis. The model thinks, calls tools, observes real data, and repeats.

```
Iteration 1   tool_choice = REQUIRED
              ↳ Model MUST call at least one skill.
                It cannot answer from training data.

Iterations 2–N  tool_choice = AUTO
              ↳ Model chains tools, cross-references sources,
                or stops when it has enough data.

Final iteration  synthesis prompt injected
              ↳ "Write your final response using only the
                 tool data above. No extrapolation."
```

As each tool fires, the ⏳ Thinking message is edited live:
```
⏳ Researching…

  📋 Checking Mantle RWA TVL
  ⚖️ Comparing chains
  🌐 Searching the web
```

### 4. Skills layer

14 skills run in parallel via `asyncio.gather`. Each one returns a typed `SkillResult` with `source`, `source_url`, `data`, `fetched_at`, and `ok` fields. The `source_url` points to the exact data page — not a homepage.

| Skill | Data source |
|---|---|
| `mantle-rwa-tvl` | DefiLlama /protocols |
| `mantle-defi` | DefiLlama /protocols |
| `mantle-defi-markets` | mantle-cli + DefiLlama |
| `mantle-token-prices` | mantle-cli + CoinGecko |
| `mantle-equity` | CoinGecko (xStocks) |
| `mantle-chain` | Mantle RPC + mantle-cli |
| `mantle-portfolio` | Mantle RPC + mantle-cli |
| `mantle-risk` | DefiLlama + web search |
| `mantle-identity` | Mantle RPC (ERC-8004) |
| `cross-chain-compare` | DefiLlama /v2/chains |
| `crypto-price` | CoinGecko |
| `news` | DuckDuckGo + CoinGecko News |
| `web-search` | DuckDuckGo |
| `fetch-url` | HTTP + content extraction |

### 5. Response formatter

The model's markdown output is converted to Telegram-native rich HTML:

```
## Section    →  <h2>Section</h2>
### Sub        →  <h3>Sub</h3>
**bold**       →  <b>bold</b>
- item         →  <ul><li>item</li></ul>
paragraph      →  <p>paragraph</p>
```

A sources block is appended — each source is a tappable link to the exact page the data came from. A data confidence score shows the percentage of skill calls that succeeded.

### 6. Telegram delivery

- **Price queries** → chart image sent first (`sendPhoto`), text response below
- **Research responses** → rich HTML message (Bot API 10.1)
- **Every response** → inline buttons: `[🔄 Refresh]` `[🔎 Deep Dive]` `[📊 Chart]` `[📤 Export]`

---

## Two rules that never break

**1. Greetings never trigger research.**
`hi`, `gm`, `thanks`, and similar messages return CHAT — zero API calls, zero tool calls, instant.

**2. The model cannot answer from training data.**
`tool_choice = required` on iteration 1 forces a live skill call before any synthesis. If a skill fails, the response says "Data unavailable" — it never invents numbers.

---

## Memory

**Session** — last 20 exchanges per user, 4-hour TTL. Enables natural follow-ups ("what about its TVL" → Aegis knows the context).

**Long-term (SQLite)** — persists across sessions. Tracks watchlist, last 30 research queries, and a risk profile derived from query patterns. Injected as a compact context string on every call:
```
[User context: Watching: MNT, TSLAx | Recent research: Mantle RWA, xStocks | Risk: moderate]
```

**Scheduler** — queries like "tell me MNT price in 5 minutes" are stored and fired by a 15-second poll loop.

---

## Running it yourself

```bash
git clone https://github.com/bolajiev/aegis
cd aegis
pip install -r requirements.txt
cp .env.example .env   # fill in TELEGRAM_BOT_TOKEN + QWEN_API_KEY
python3 bot.py
```

See [README.md](../README.md) for the full environment variable reference.
