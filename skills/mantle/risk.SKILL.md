---
name: mantle-risk
version: 1.0.0
description: "Use when the user asks whether a Mantle protocol is safe, if it's been audited, if it's a rug pull risk, or requests a risk assessment / security review of a specific Mantle protocol."
---

## Overview
Evaluates protocol risk using TVL stability, TVL trends, protocol age, and available audit information from DefiLlama. Produces a risk score (0–100) and risk level (LOW/MEDIUM/HIGH) with specific flags.

## When to use
- "Is Merchant Moe safe?"
- "Risk assessment for Agni Finance"
- "Was Lendle audited?"
- "Is this a rug pull?"
- "Security review of [protocol name]"

## When NOT to use
- Generic DeFi TVL data (use mantle-defi)
- Token prices (use mantle-token-prices)
- This is NOT a contract audit — it uses on-chain TVL signals, not code review

## Workflow
1. Search DefiLlama protocols for the named protocol on Mantle
2. Extract TVL, 1d/7d change, age (listedAt), audit links
3. Score risk based on: TVL size, TVL volatility, protocol age
4. Flag specific risks
5. Return risk score + flags + audit info

## Output Format
```json
{
  "protocol": "Agni Finance",
  "mantle_tvl_usd": 28000000,
  "change_1d_pct": 0.5,
  "change_7d_pct": -2.1,
  "risk": {"score": 72, "level": "LOW"},
  "risk_flags": [],
  "audits": "2",
  "audit_links": ["https://..."]
}
```

## Guardrails
- This is TVL-based risk assessment, not a smart contract audit
- Always note that risk score is data-driven, not a security guarantee
- If protocol not found on DefiLlama, say so — do not invent data

## References
- https://defillama.com/protocols
- https://defillama.com/protocol/agni-finance
