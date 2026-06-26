---
name: mantle-token-prices
version: 1.0.0
description: "Use when the user asks about Mantle-native token prices: MNT, WMNT, mETH, USDT, USDC, WETH, FBTC, or any token deployed on Mantle. Uses official mantle-cli for live prices."
---

## Overview
Fetches live token prices from the official mantle-cli (`mantle_getTokenPrices` MCP tool), with CoinGecko fallback for unmapped tokens. Returns price, 24h change, and market cap where available.

## When to use
- "MNT price"
- "What is mETH worth?"
- "WMNT price"
- "How much is USDT on Mantle?"
- Any Mantle-native token price question

## When NOT to use
- Non-Mantle tokens (use crypto-price instead)
- xStocks (use mantle-equity)

## Workflow
1. Try `mantle-cli token prices --tokens MNT,... --json`
2. For tokens not found in CLI, fallback to CoinGecko by coin ID
3. MNT uses dedicated `get_mnt_info()` for full market data

## Output Format
```json
{
  "prices": {
    "MNT":  {"price_usd": 0.87, "change_24h_pct": -1.2, "market_cap_usd": 890000000},
    "mETH": {"price_usd": 3840.00, "change_24h_pct": 0.8}
  },
  "tokens": ["MNT", "mETH", "USDT"]
}
```

## Guardrails
- MNT is the native gas token on Mantle (chain ID 5000)
- mETH is Mantle's staked ETH product
- Never invent prices — return ok=False if all sources fail

## References
- mantle-cli: `npx @mantleio/mantle-cli token prices --tokens MNT --json`
- https://www.coingecko.com/en/coins/mantle
