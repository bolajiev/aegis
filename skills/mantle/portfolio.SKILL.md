---
name: mantle-portfolio
version: 1.0.0
description: "Use when the user provides a wallet address (0x...) and asks about their balance, holdings, portfolio, or Aave lending positions on Mantle."
---

## Overview
Fetches live wallet balances (native MNT + ERC-20 tokens) and Aave V3 lending positions for a given wallet address on Mantle, using `mantle-cli account` commands.

## When to use
- "What's in wallet 0x1234...?"
- "Check my balance on Mantle"
- "My portfolio on Mantle"
- "Do I have any Aave positions?"
- Any message containing a 0x wallet address

## When NOT to use
- No wallet address provided — explain that one is needed
- Chain stats without an address (use mantle-chain)

## Workflow
1. Extract 0x address from the query
2. In parallel: fetch native MNT balance, ERC-20 balances, Aave positions
3. Fallback to direct RPC for native balance if CLI fails
4. Return unified portfolio snapshot

## Output Format
```json
{
  "address": "0x...",
  "mnt_balance": 14.5,
  "token_balances": [{"symbol": "USDT", "balance": "1000.00"}],
  "aave_positions": {"supplied": [...], "borrowed": [...]},
  "explorer": "https://mantlescan.xyz/address/0x..."
}
```

## Guardrails
- Never fabricate balances
- If no 0x address in query, return error asking for one
- Token balances tracked: MNT, WMNT, USDT, USDC, WETH, mETH, FBTC

## References
- mantle-cli: `npx @mantleio/mantle-cli account balance <address> --json`
- https://mantlescan.xyz
