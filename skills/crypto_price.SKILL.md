---
name: crypto-price
version: 1.0.0
description: "Use when the user asks about the price, market cap, or 24h change of any cryptocurrency by name or ticker — BTC, ETH, SOL, BNB, or any other coin. Also use for MNT price."
---

## Overview
Fetches live price, 24h change, market cap, and volume for any cryptocurrency from CoinGecko. Maps common tickers (BTC, ETH, etc.) to CoinGecko IDs automatically. Falls back to search for unknown tickers.

## When to use
- "Bitcoin price"
- "How much is ETH?"
- "SOL 24h change"
- "MNT market cap"
- Any crypto price question

## When NOT to use
- Mantle-specific token prices (try mantle-token-prices first for MNT/mETH/WMNT)
- xStocks (use mantle-equity)
- DeFi TVL (use mantle-defi)

## Workflow
1. Normalize query to ticker/name
2. Look up CoinGecko ID from known map or search endpoint
3. Fetch price, 24h change, market cap, volume

## Output Format
```json
{
  "coin": "BTC",
  "coin_id": "bitcoin",
  "price_usd": 68420.00,
  "change_24h_pct": 1.8,
  "market_cap_usd": 1340000000000,
  "volume_24h_usd": 28000000000
}
```

## Guardrails
- Never invent prices — return ok=False if CoinGecko fails
- If coin not found by ticker, try searching by name

## References
- https://api.coingecko.com/api/v3/simple/price
