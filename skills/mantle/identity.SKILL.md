---
name: mantle-identity
version: 1.0.0
description: "Use when the user asks about Aegis's onchain identity, ERC-8004 registration, agent NFT, or who/what Aegis is onchain."
---

## Overview
Queries the ERC-8004 IdentityRegistry contract on Mantle mainnet (`0x8004A169FB4a3325136EB29fA0ceB6D2e539a432`) to check if Aegis has a registered agent identity. Returns registration status, token count, and explorer link.

## When to use
- "What is your onchain identity?"
- "Are you registered on Mantle?"
- "Show me your ERC-8004 token"
- "What is Aegis's agent identity?"

## When NOT to use
- General Mantle chain stats (use mantle-chain)
- Wallet balance for a user address (use mantle-portfolio)

## Workflow
1. Derive agent address from AGENT_PRIVATE_KEY
2. Call `balanceOf(agentAddress)` on the IdentityRegistry
3. Return registration status and token details

## Output Format
```json
{
  "registered": true,
  "agent_address": "0x...",
  "registry": "0x8004A169FB4a3325136EB29fA0ceB6D2e539a432",
  "token_count": 1,
  "erc_standard": "ERC-8004",
  "chain": "Mantle Mainnet (chain ID 5000)"
}
```

## Guardrails
- Never log or expose AGENT_PRIVATE_KEY in any output
- If key is not set, return registered=false with a note
- Registry address: `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432` (verified on Mantle mainnet)

## References
- https://mantlescan.xyz/address/0x8004A169FB4a3325136EB29fA0ceB6D2e539a432
- ERC-8004 agent identity standard
