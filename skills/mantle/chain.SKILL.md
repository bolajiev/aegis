---
name: mantle-chain
version: 1.0.0
description: "Use when the user asks about Mantle chain stats: gas price, block height, chain health, TPS, or MNT native balance for a specific wallet address."
---

## Overview
Queries live Mantle chain metrics via `mantle-cli chain status` (with fallback to direct RPC). Also handles wallet balance lookups when a 0x address is provided.

## When to use
- "What is the gas price on Mantle?"
- "What block is Mantle on?"
- "Is Mantle healthy?"
- "Check balance of 0x1234..."
- "Mantle chain stats"

## When NOT to use
- Token balances (ERC-20) — use mantle-portfolio
- Token prices — use mantle-token-prices
- Protocol TVL — use mantle-defi

## Workflow
1. Call `mantle-cli chain status --json` and `mantle-cli chain info --json` in parallel
2. If CLI fails, fall back to direct RPC (`eth_gasPrice`, `eth_getBlockByNumber`)
3. If query contains 0x address, also fetch MNT balance
4. Return unified data object

## Output Format
```json
{
  "chain": "Mantle",
  "chain_id": 5000,
  "block_number": 71234567,
  "gas_price_gwei": 0.02,
  "native_token": "MNT",
  "wallet_balance": {"address": "0x...", "mnt_balance": 14.5}
}
```

## Guardrails
- MNT is the gas token on Mantle (not ETH)
- Chain ID is 5000 for Mantle Mainnet
- Never fabricate block numbers or gas prices

## References
- https://rpc.mantle.xyz
- https://mantlescan.xyz
- mantle-cli: `npx @mantleio/mantle-cli chain status --json`
