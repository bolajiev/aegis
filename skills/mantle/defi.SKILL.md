---
name: mantle-defi
version: 1.0.0
description: "Use when the user asks about DeFi TVL, liquidity, DEX volume, protocol comparison, lending rates, or the overall DeFi ecosystem on Mantle. Covers Merchant Moe, Agni Finance, Aave V3, Lendle, Pendle, FusionX, Init Capital."
---

## Overview
Fetches live DeFi protocol TVLs, DEX volume, and fee data on Mantle from DefiLlama. Excludes RWA protocols (covered by mantle-rwa-tvl). Returns top protocols sorted by TVL.

## When to use
- "What DeFi protocols are on Mantle?"
- "Compare Agni Finance vs Merchant Moe TVL"
- "Mantle DEX volume"
- "Mantle DeFi TVL"
- "Best yield on Mantle"
- "Lending protocols on Mantle"

## When NOT to use
- RWA/institutional assets (use mantle-rwa-tvl)
- Single token price (use mantle-token-prices or crypto-price)
- Detailed lending market rates (use mantle-defi-markets for Aave specifics)

## Workflow
1. Fetch all protocols from DefiLlama simultaneously with DEX + fees overview
2. Filter to Mantle chain, exclude RWA, exclude protocols with < $50K TVL
3. Sort by Mantle TVL descending, return top 15

## Output Format
```json
{
  "total_defi_tvl_usd": 380000000,
  "protocols": [
    {"name": "Merchant Moe", "category": "Dexes", "tvl_usd": 95000000, "change_1d": 1.2}
  ],
  "dex": {"total_24h_usd": 12000000, "change_1d_pct": -3.5},
  "fees": {"total_24h_usd": 45000}
}
```

## Guardrails
- Never fabricate TVL or volume figures
- If a protocol has no Mantle TVL, exclude it silently
- Cite DefiLlama as source

## References
- https://defillama.com/chain/Mantle
- https://defillama.com/dexs/Mantle
