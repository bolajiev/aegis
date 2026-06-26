---
name: mantle-rwa-tvl
version: 1.0.0
description: "Use when a question concerns Mantle's real-world asset (RWA) TVL, RWA protocol breakdown, or 1d/7d/30d TVL deltas for protocols such as Ondo, Midas, Mantle Index Four Fund, or Solv."
---

# Mantle RWA TVL

## Overview

Fetch live Mantle chain TVL and RWA-category protocol breakdown from DefiLlama. Returns total chain TVL, RWA sub-total, per-protocol TVL with 1d/7d deltas, and the percentage of chain TVL attributable to RWAs.

## Data Sources

- `GET https://api.llama.fi/v2/historicalChainTvl/Mantle` — time-series TVL used to compute deltas
- `GET https://api.llama.fi/protocols` — filtered to `chains contains "Mantle" AND category == "RWA"`

Both sources are fetched in parallel. Data is sourced from DefiLlama and should be cited as `(DefiLlama, YYYY-MM-DD)` in all answers.

## Workflow

1. Fetch historical chain TVL and full protocol list in parallel.
2. Compute current chain TVL from the last entry in the history array (`tvl` field, epoch `date`).
3. Compute 1d, 7d, and 30d deltas by comparing current TVL against entries at index `[-2]`, `[-8]`, `[-31]`.
4. Filter protocols: `"Mantle" in chains` AND `category == "RWA"`. Sort descending by `tvl`.
5. Sum filtered protocol TVLs to produce `rwa_total_usd`.
6. Return a `SkillResult` with `ok=True` and the structured data dict. On any fetch error, return `ok=False` with the error string — do not fabricate figures.

## Guardrails

- Never invent or extrapolate TVL figures. If the API returns an error or empty data, return `ok=False`.
- Do not include non-RWA protocols in the RWA total (check `category == "RWA"` strictly).
- The `change_1m` field from DefiLlama is often `null`; compute the 30d delta from history instead.
- Cite the source as `DefiLlama /v2/historicalChainTvl/Mantle + /protocols` with the UTC fetch date.

## Output Format

```
skill:         mantle-rwa-tvl
source:        DefiLlama /v2/historicalChainTvl/Mantle + /protocols
fetched_at:    <UTC ISO-8601>
ok:            true | false
data:
  chain_tvl_usd:            <int>
  chain_tvl_delta_1d_pct:   <float | null>
  chain_tvl_delta_7d_pct:   <float | null>
  chain_tvl_delta_30d_pct:  <float | null>
  rwa_total_usd:            <int>
  rwa_protocols:
    - name:           <str>
      tvl_usd:        <int>
      change_1d_pct:  <float>
      change_7d_pct:  <float>
```

## References

- DefiLlama API docs: https://defillama.com/docs/api
