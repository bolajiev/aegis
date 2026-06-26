---
name: general-crypto-price
version: 1.0.0
description: "Use when a question asks for the current price, 24h change, market cap, or trading volume of any cryptocurrency: Bitcoin (BTC), Ethereum (ETH), Solana (SOL), BNB, and all other coins not covered by Mantle-specific skills."
---

# General Crypto Price

## Overview

Fetch real-time price, 24h percentage change, market cap, and 24h trading volume for any cryptocurrency listed on CoinGecko. Uses a curated alias map for the top 30 coins (instant lookup) and falls back to CoinGecko's `/search` endpoint for unknown symbols. Returns `ok=False` if the coin cannot be identified — never fabricates a price.

## Data Sources

- `GET https://api.coingecko.com/api/v3/simple/price` — price, 24h change, market cap, volume
- `GET https://api.coingecko.com/api/v3/search?query={text}` — coin ID resolution for unknown symbols

Cite as `(CoinGecko, YYYY-MM-DD)`.

## Workflow

1. Extract the coin name or symbol from the query (strip noise words: "price", "of", "current", "today", etc.).
2. Check the curated alias map (`btc→bitcoin`, `eth→ethereum`, `sol→solana`, `mnt→mantle`, etc.).
3. If not in the alias map, call `/search` and take the top result's `id`.
4. Call `/simple/price` with `include_24hr_change`, `include_market_cap`, `include_24hr_vol`.
5. If the coin ID is not in the response, return `ok=False` — do not fabricate.

## Guardrails

- **Never invent a price.** If CoinGecko returns no data for an ID, return `ok=False` with a clear error.
- Mantle-specific tokens (RWA protocols, xStocks) are handled by dedicated skills — this skill is a general fallback.
- MNT is in the alias map but the `news-digest` skill provides richer Mantle context; route accordingly.
- Cite with the UTC fetch date on every answer.

## Output Format

```
skill:       general-crypto-price
source:      CoinGecko /simple/price
fetched_at:  <UTC ISO-8601>
ok:          true | false
error:       <str | null>
data:
  coin_id:          <str>
  price_usd:        <float>
  change_24h_pct:   <float>
  market_cap_usd:   <float>
  volume_24h_usd:   <float>
```

## References

- CoinGecko API docs: https://www.coingecko.com/api/documentation
