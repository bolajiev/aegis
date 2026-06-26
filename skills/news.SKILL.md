---
name: news
version: 1.0.0
description: "Use when the user asks for recent news, latest updates, announcements, or what's happening with Mantle or any crypto project. Searches crypto news sources via DuckDuckGo."
---

## Overview
Searches DuckDuckGo for recent news from major crypto publications (The Block, CoinDesk, Decrypt, CoinTelegraph, Mantle.xyz). Returns titles, URLs, and snippets for the most recent results.

## When to use
- "Latest Mantle news"
- "What happened with Mantle this week?"
- "Recent DeFi announcements"
- "Mantle ecosystem updates"
- Any question about recent events

## When NOT to use
- Price data (use crypto-price or mantle-token-prices)
- Historical TVL data (use mantle-defi)
- Reading a specific URL (use fetch-url)

## Workflow
1. Build query with "Mantle" prefix if not already present
2. Search crypto news sites via DuckDuckGo
3. If domain-restricted search yields < 3 results, retry without site filter

## Output Format
```json
{
  "query": "Mantle ecosystem news 2026",
  "results": [
    {"title": "Mantle...", "url": "https://...", "snippet": "..."}
  ],
  "count": 8
}
```

## Guardrails
- Results are web snippets, not verified data — model must cite specific sources
- Don't quote snippets as facts — recommend reading full articles via fetch-url

## References
- DuckDuckGo HTML search (no API key needed)
