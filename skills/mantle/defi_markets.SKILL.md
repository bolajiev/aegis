---
name: mantle-defi-markets
version: 1.0.0
description: "Use when the user asks about specific Aave V3 lending rates/APY on Mantle, top liquidity pools, LP yields, or wants to know the best yield opportunities on Mantle."
---

## Overview
Fetches live Aave V3 lending market data (supply APY, borrow APY, utilization) and top LP pools by TVL on Mantle using `mantle-cli`. Covers Merchant Moe, Agni Finance, and Fluxion pools.

## When to use
- "What are the Aave V3 rates on Mantle?"
- "Best yield on Mantle right now"
- "Top liquidity pools on Mantle"
- "USDT supply rate on Aave Mantle"
- "Where can I earn yield on Mantle?"

## When NOT to use
- Overall DeFi TVL breakdown (use mantle-defi)
- Specific token price (use mantle-token-prices)
- Portfolio/wallet positions (use mantle-portfolio)

## Workflow
1. Call `mantle-cli aave markets --json` for lending market data
2. Call `mantle-cli lp top-pools --sort-by tvl --limit 10 --json` for pool data
3. Return both datasets

## Output Format
```json
{
  "aave_v3": {
    "markets": [
      {"asset": "USDT", "supply_apy": 3.2, "borrow_apy": 4.8, "utilization": 0.78}
    ]
  },
  "top_lp_pools": [
    {"protocol": "Merchant Moe", "pair": "MNT/USDT", "tvl": 12500000, "apy": 18.4}
  ]
}
```

## Guardrails
- Rates change frequently — always note the fetched_at timestamp
- Aave V3 Pool address on Mantle: `0x458F293454fE0d67EC0655f3672301301DD51422`
- Never invent APY or TVL figures

## References
- mantle-cli: `npx @mantleio/mantle-cli aave markets --json`
- Aave V3 Mantle: https://app.aave.com/?marketName=proto_mantle_v3
- Merchant Moe: https://merchantmoe.com
