---
name: news-digest
version: 1.0.0
description: "Use when a question asks about recent Mantle ecosystem activity, MNT token performance, DEX trading volume, protocol fees, or a general 'what's happening on Mantle' pulse check."
---

# News Digest

## Overview

Aggregate live on-chain signals from multiple sources to produce a Mantle ecosystem pulse: MNT token price and performance, DEX trading volume, protocol fees, and TVL trend. Answers "what's happening on Mantle" without requiring a news API — the on-chain signals tell the story.

## Data Sources

- **CoinGecko** `GET /coins/mantle` — MNT price, market cap, 24h/7d change, volume, Telegram community size
- **DefiLlama** `GET /overview/dexs/Mantle` — DEX 24h and 7d volume, change
- **DefiLlama** `GET /overview/fees/Mantle` — protocol 24h and 7d fees, top fee earners
- **DefiLlama** `GET /v2/historicalChainTvl/Mantle` — TVL time series for 1d/7d/30d delta computation

All four sources are fetched in parallel. Partial failures degrade gracefully — the skill remains `ok=True` as long as at least one source returns data.

Cite as `(DefiLlama + CoinGecko, YYYY-MM-DD)`.

## Workflow

1. Launch all four fetches concurrently with `asyncio.gather(return_exceptions=True)`.
2. For each result, check `isinstance(result, Exception)`. Log but do not raise partial failures.
3. If all four sources fail, return `ok=False`.
4. Build the data dict from whichever sources succeeded.
5. For TVL history, compute 1d, 7d, 30d deltas from the last entry vs entries at `[-2]`, `[-8]`, `[-31]`.
6. Populate `partial_errors` list if any source failed.
7. Return the `SkillResult`.

## Guardrails

- Never fabricate MNT price, volume, or TVL figures. If CoinGecko is unavailable, omit `mnt_token`.
- Do not claim to have access to blog posts, press releases, or social media — this skill reflects on-chain signals only.
- If DEX volume data is missing, say so explicitly rather than implying it is zero.
- Cite with the UTC fetch date to make clear the data is a snapshot.

## Output Format

```
skill:       news-digest
source:      DefiLlama (TVL/fees/volume) + CoinGecko (MNT)
fetched_at:  <UTC ISO-8601>
ok:          true | false
data:
  mnt_token:
    price_usd:           <float>
    market_cap_usd:      <float>
    volume_24h_usd:      <float>
    change_24h_pct:      <float>
    change_7d_pct:       <float>
    market_cap_rank:     <int>
    telegram_users:      <int>
  dex_volume:
    total_24h_usd:       <float | null>
    total_7d_usd:        <float | null>
    change_1d_pct:       <float | null>
    change_7d_pct:       <float | null>
  protocol_fees:
    total_24h_usd:       <float | null>
    total_7d_usd:        <float | null>
    top_earners:
      - name:            <str>
        fees_24h:        <float>
  chain_tvl:
    current_usd:         <int>
    change_1d_pct:       <float | null>
    change_7d_pct:       <float | null>
    change_30d_pct:      <float | null>
  partial_errors:        <list[str] | absent>
```

## References

- DefiLlama API docs: https://defillama.com/docs/api
- CoinGecko API docs: https://www.coingecko.com/api/documentation
