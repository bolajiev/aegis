---
name: mantle-equity
version: 1.0.0
description: "Use when the user asks about tokenized stocks, xStocks, synthetic equities, or specific tickers like TSLAx, NVDAx, SPCXx, AAPLx, QQQx, GOOGLx, MSTRx, GLDx on Mantle."
---

## Overview
Fetches live prices for tokenized equities (xStocks) available on Mantle from CoinGecko. Returns current prices, 24h change, and market cap for each available xStock.

## When to use
- "What is the price of TSLAx?"
- "Show me xStocks on Mantle"
- "Tokenized Apple stock price"
- "What synthetic equities are on Mantle?"
- "NVDAx price"

## When NOT to use
- Real stock prices (not on Mantle)
- Crypto tokens (use crypto-price or mantle-token-prices)

## Workflow
1. Call CoinGecko simple/price for all known xStock coin IDs
2. Return price, 24h change, market cap per ticker

## Output Format
```json
{
  "stocks": [
    {"ticker": "TSLAX", "price_usd": 182.50, "change_24h_pct": 1.2, "market_cap_usd": 8500000},
    {"ticker": "NVDAX", "price_usd": 124.30, "change_24h_pct": -0.8}
  ],
  "count": 8
}
```

## Guardrails
- These track the real stock price but are crypto tokens on Mantle
- Always note they are tokenized versions, not direct stock ownership
- If CoinGecko is unavailable, return ok=False

## References
- https://xstocks.com
- https://www.coingecko.com/en/categories/xstocks
