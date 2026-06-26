---
name: web-search
version: 1.0.0
description: "Use when the user asks for information that requires searching the web: research questions, protocol analysis, competitor comparisons, or anything needing recent web content beyond onchain data."
---

## Overview
Performs DuckDuckGo web searches and returns up to 10 results with titles, URLs, and snippets. No API key required. Use for open-ended research where the answer isn't in onchain data.

## When to use
- "Research Agni Finance"
- "How does mETH work?"
- "Mantle vs Optimism comparison"
- "What is ERC-8004?"
- Any research question needing web sources

## When NOT to use
- Crypto news specifically (use news skill for Mantle news)
- Reading one specific URL (use fetch-url)
- Onchain data (use dedicated Mantle skills)

## Workflow
1. Send query to DuckDuckGo HTML endpoint
2. Parse up to 10 result blocks
3. Return title, URL, snippet for each

## Output Format
```json
{
  "query": "Agni Finance Mantle DEX",
  "results": [
    {"title": "Agni Finance...", "url": "https://...", "snippet": "..."}
  ],
  "count": 8
}
```

## Guardrails
- Results are web snippets — model must synthesize, not blindly quote
- Recommend fetch-url for any result needing deeper reading

## References
- DuckDuckGo HTML endpoint (no API key)
