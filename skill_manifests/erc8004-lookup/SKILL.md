---
name: erc8004-lookup
version: 1.0.0
description: "Use when a question asks about ERC-8004 agent identity, Aegis's onchain token ID, the AgentIdentity registry, or registered AI agent metadata on Mantle mainnet."
---

# ERC-8004 Agent Identity Lookup

## Overview

Query the ERC-8004 AgentIdentity registry on Mantle mainnet to look up agent metadata and token ownership. This is the skill that answers "does Aegis have an onchain identity?" by reading the EIP-721 registry directly. It also serves as a general lookup for any registered agent token.

## Data Sources

- **AgentIdentity Registry**: proxy at `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432`, Mantle mainnet (chain ID 5000)
- **ABI functions** (verified from deployed bytecode 2026-06-22):
  - `totalSupply() → uint256` — number of registered agents
  - `ownerOf(uint256) → address` — token owner
  - `tokenURI(uint256) → string` — metadata URI (external URL or `data:application/json;base64,...`)
  - ERC-721 `Transfer` event topic: `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef`
- **Deployment block**: 91,334,370

Cite as `(Mantle RPC / AgentIdentity ERC-8004, YYYY-MM-DD)`.

## Workflow

1. Determine lookup target from the query:
   - If a token ID is present (pattern `(?:token|agent|id|#)\s*(\d{1,6})`), look up that specific token.
   - If "esu" is mentioned or no target is specified, look up Aegis's registered token ID by scanning Transfer events.
   - If a wallet address is present (`0x[0-9a-fA-F]{40}`), find tokens owned by that address.
2. Call `totalSupply()` to verify the registry has at least one entry.
3. For token lookups: call `ownerOf(tokenId)` and `tokenURI(tokenId)`.
4. For address lookups: scan Transfer events from `DEPLOY_BLOCK` to latest in chunks of 10,000 blocks; filter mints (`from = 0x0`) to the target address.
5. Decode `tokenURI`:
   - If it starts with `data:application/json;base64,`, base64-decode and parse as JSON.
   - If it starts with `data:application/json`, gzip-decompress if needed, then parse as JSON.
   - If it starts with `https://` or `ipfs://`, return the URI as-is (external fetch not performed).
6. Return `ok=True` with the structured data. If the token does not exist or the registry call reverts, return `ok=False`.

## Guardrails

- Never log or expose `AGENT_PRIVATE_KEY` in any error message.
- Do not attempt `eth_getLogs` spanning more than 10,000 blocks per call; iterate in chunks.
- The `0xf2c298be` selector is the `register(string)` function — for reads only `ownerOf`, `tokenURI`, and `totalSupply` are needed; do not call `register`.
- If `tokenURI` returns a URL, do not fetch it — return the URL so the synthesis layer can describe it.
- This skill is read-only; it never constructs or submits transactions.

## Output Format

```
skill:       erc8004-lookup
source:      Mantle RPC / AgentIdentity ERC-8004 (0x8004A169...)
fetched_at:  <UTC ISO-8601>
ok:          true | false
data:
  registry_address:    0x8004A169FB4a3325136EB29fA0ceB6D2e539a432
  total_supply:        <int>
  token_id:            <int | null>
  owner_address:       <str | null>
  metadata_uri:        <str | null>
  metadata:            <dict | null>   # decoded JSON if data URI
  error:               <str | null>
```

## References

- ERC-8004 spec: https://eips.ethereum.org/EIPS/eip-8004
- AgentIdentity contract: https://mantlescan.xyz/address/0x8004A169FB4a3325136EB29fA0ceB6D2e539a432
