---
name: tokenized-equity-price
version: 1.0.0
description: "Use when a question asks for the price or 24h change of a tokenized equity xStock token: SPCXx (SpaceX), TSLAx (Tesla), NVDAx (NVIDIA), AAPLx (Apple), SPYx (S&P 500), QQQx (Nasdaq), MSTRx (MicroStrategy), GOOGLx (Alphabet), or GLDx (Gold)."
---

# Tokenized Equity Price

## Overview

Fetch real-time prices and 24h percentage changes for xStocks tokenized equity tokens listed on CoinGecko. If a ticker is not in the known map or CoinGecko returns no data, the skill returns `ok=False` — it never fabricates a price.

## Data Sources

- `GET https://api.coingecko.com/api/v3/simple/price` with `vs_currencies=usd&include_24hr_change=true&include_last_updated_at=true`
- CoinGecko coin IDs verified 2026-06-22:

| Ticker | CoinGecko ID |
|--------|-------------|
| SPCXX  | spacex-xstocks |
| TSLAX  | tesla-xstock |
| NVDAX  | nvidia-xstock |
| SPYX   | sp500-xstock |
| AAPLX  | apple-xstock |
| QQQX   | nasdaq-xstock |
| MSTRX  | microstrategy-xstock |
| GOOGLX | alphabet-xstock |
| GLDX   | gold-xstock |

## Workflow

1. Extract ticker symbols from the query using the pattern `\b[A-Za-z]{3,7}[Xx]\b` matched against the known ticker set.
2. If no tickers are found in the query, fetch all known tickers.
3. Map tickers to CoinGecko IDs. Any ticker not in the map is added to `unrecognised_tickers`.
4. Call `GET /simple/price` with all resolved coin IDs.
5. For each coin ID in the response, build a price entry. IDs absent from the response are added to `unavailable`.
6. If zero prices are returned for all requested IDs, return `ok=False` — do not fabricate prices.

## Guardrails

- **Never invent a price.** If CoinGecko does not return data for a ticker, report it as unavailable.
- Not all tokenized equities are on CoinGecko. For unlisted tickers, return `ok=False` with a clear error.
- xStock prices reflect the tokenized derivative, not a direct CEX or TradFi exchange quote; note this in synthesis.
- Cite as `(CoinGecko, YYYY-MM-DD)`.

## Output Format

```
skill:       tokenized-equity-price
source:      CoinGecko /api/v3/simple/price
fetched_at:  <UTC ISO-8601>
ok:          true | false
error:       <str | null>
data:
  prices:
    - ticker:          <str>
      coin_id:         <str>
      price_usd:       <float>
      change_24h_pct:  <float>
  unavailable:             <list[str] | absent>
  unrecognised_tickers:    <list[str] | absent>
```

## References

- CoinGecko API docs: https://www.coingecko.com/api/documentation
