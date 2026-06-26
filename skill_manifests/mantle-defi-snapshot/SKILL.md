---
name: mantle-defi-snapshot
version: 1.0.0
description: "Use when a question asks about DeFi activity on Mantle: DEX trading, lending, yield protocols, TVL for Merchant Moe, Agni Finance, Lendle, Fluxion, Aave V3, Uniswap, or Pendle on Mantle."
---

# Mantle DeFi Snapshot

## Overview

Fetch a live snapshot of DeFi protocols deployed on Mantle, sorted by TVL. Highlights Mantle-native protocols (Merchant Moe, Agni Finance, Lendle, Fluxion) alongside major cross-chain deployments (Aave V3, Uniswap V3, Pendle). Returns TVL, 1d/7d deltas, and protocol category for each.

## Data Sources

- `GET https://api.llama.fi/protocols` — filtered to `"Mantle" in chains` and `category in {Dexs, Lending, Yield, Liquid Staking, CDP, Derivatives}`

Cite as `(DefiLlama, YYYY-MM-DD)`.

## Workflow

1. Fetch all protocols from DefiLlama `/protocols`.
2. Filter: `"Mantle" in p["chains"]` AND `p["category"]` in the DeFi category set.
3. Sort descending by `tvl`. Keep top 10 by TVL.
4. Additionally include any Mantle-native protocols (`merchant moe`, `agni finance`, `fluxion network`, `lendle`) not already in the top 10, to ensure native ecosystem coverage.
5. Deduplicate, preserving original order.
6. Compute `total_defi_tvl_usd` as the sum of all Mantle DeFi protocols (not just displayed ones).
7. Return a `SkillResult`. On fetch error, return `ok=False`.

## Guardrails

- Do not include RWA protocols in this snapshot (use `mantle-rwa-tvl` for that).
- Never fabricate TVL or fee figures. If a protocol's TVL is `null`, report it as zero.
- The `native: true` flag marks Mantle-native protocols; use it to distinguish ecosystem-native from cross-chain deployments.
- Always cite DefiLlama with the UTC fetch date.

## Output Format

```
skill:       mantle-defi-snapshot
source:      DefiLlama /protocols (Mantle chain)
fetched_at:  <UTC ISO-8601>
ok:          true | false
data:
  total_defi_tvl_usd:  <int>
  protocol_count:      <int>
  protocols:
    - name:            <str>
      category:        <str>
      tvl_usd:         <int>
      change_1d_pct:   <float>
      change_7d_pct:   <float>
      native:          <bool>
```

## References

- DefiLlama API docs: https://defillama.com/docs/api
