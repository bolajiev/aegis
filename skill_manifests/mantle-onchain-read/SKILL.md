---
name: mantle-onchain-read
version: 1.0.0
description: "Use when a question asks for live Mantle network stats (gas price, block height, block utilization) or the MNT native token balance of a specific wallet address."
---

# Mantle Onchain Read

## Overview

Query the Mantle RPC endpoint for live network state: current gas price, latest block number and utilization, and optionally the MNT native balance for an address extracted from the query. Optionally supplements with mantlescan stats (MNT circulating supply, USD price) when `MANTLESCAN_API_KEY` is configured.

## Data Sources

- Mantle JSON-RPC (`https://rpc.mantle.xyz` by default, configurable via `MANTLE_RPC_URL`)
  - `eth_gasPrice` — current gas price
  - `eth_getBlockByNumber("latest", false)` — block number, gas used/limit, timestamp, tx count, base fee
  - `eth_getBalance(address, "latest")` — MNT balance (if address in query)
- mantlescan Etherscan v2 API (optional, requires `MANTLESCAN_API_KEY`)
  - `module=stats&action=ethsupply` — MNT circulating supply
  - `module=stats&action=ethprice` — MNT/USD price from scanner

Cite as `(Mantle RPC, YYYY-MM-DD)`.

## Workflow

1. Run `eth_gasPrice`, `eth_getBlockByNumber("latest", false)`, and `get_scan_stats()` concurrently via `asyncio.gather`.
2. If the RPC calls fail, return `ok=False` immediately.
3. Compute `block_gas_used_pct = gas_used / gas_limit * 100`.
4. Convert `baseFeePerGas` from wei to Gwei.
5. Scan the query text for an Ethereum address (`0x[0-9a-fA-F]{40}`). If found, fetch `eth_getBalance` and add to `data`.
6. If `get_scan_stats()` succeeds, append `mnt_circulating_supply` and `mnt_price_usd_scan` to `data`.
7. Return the `SkillResult`.

## Guardrails

- Never log or expose `AGENT_PRIVATE_KEY` or `MANTLESCAN_API_KEY` in error messages or skill output.
- If `get_scan_stats()` fails (no API key or API error), degrade gracefully — return the RPC data without scanner fields.
- Do not interpret gas price as a recommendation to transact.
- Balance values are in MNT (native token), not USD. Do not convert unless a price source is available.

## Output Format

```
skill:       mantle-onchain-read
source:      Mantle RPC (rpc.mantle.xyz) [+ mantlescan]
fetched_at:  <UTC ISO-8601>
ok:          true | false
data:
  block_number:               <int>
  block_timestamp_utc:        <ISO-8601>
  tx_count_latest_block:      <int>
  gas_price_gwei:             <float>
  base_fee_gwei:              <float>
  block_gas_used_pct:         <float | null>
  mnt_circulating_supply:     <int | absent>
  mnt_price_usd_scan:         <float | absent>
  queried_address:            <str | absent>
  mnt_balance:                <float | absent>
```

## References

- Mantle RPC: https://rpc.mantle.xyz
- Mantlescan API: https://docs.mantlescan.xyz
