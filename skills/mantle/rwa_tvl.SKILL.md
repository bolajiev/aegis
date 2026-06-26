---
name: mantle-rwa-tvl
version: 1.0.0
description: "Use when the user asks about RWA TVL, tokenized bonds, tokenized treasuries, Ondo, Midas, Maple, syrupUSDT, MIF4, OpenEden, real world assets, or institutional DeFi on Mantle."
---

## Overview
Fetches live RWA (real-world asset) protocol TVLs on the Mantle chain from DefiLlama. Returns a breakdown of each RWA protocol's TVL, 24h/7d changes, and the combined total.

## When to use
- "What is Mantle's RWA TVL?"
- "How much is locked in tokenized bonds on Mantle?"
- "Tell me about Ondo on Mantle"
- "Mantle institutional DeFi"
- "RWA protocols on Mantle"

## When NOT to use
- Generic DeFi TVL questions (use mantle-defi instead)
- Token prices (use mantle-token-prices or crypto-price)

## Workflow
1. Fetch all protocols from DefiLlama `/protocols`
2. Filter to protocols deployed on Mantle chain
3. Filter to RWA category (by slug or category field)
4. Sum TVLs and return breakdown

## Output Format
```json
{
  "total_rwa_tvl_usd": 412000000,
  "protocols": [
    {"name": "Ondo", "tvl_usd": 280000000, "change_1d": 0.4, "change_7d": 2.1},
    {"name": "Midas", "tvl_usd": 82000000, "change_1d": -0.2, "change_7d": 1.5}
  ],
  "count": 5
}
```

## Guardrails
- Never invent protocol names or TVL figures
- If DefiLlama is unavailable, return ok=False with error message
- Cite DefiLlama as source with fetched_at timestamp

## References
- https://defillama.com/chain/Mantle
- https://defillama.com/protocols/rwa
