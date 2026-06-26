---
name: fetch-url
version: 1.0.0
description: "Use when you have a specific URL to read in full — typically after web-search returns a relevant result and you need the complete article content, documentation, or protocol information."
---

## Overview
Fetches a URL via HTTP, strips HTML tags, and returns up to 12,000 characters of readable text. Ideal for reading articles, docs, blog posts, and protocol pages.

## When to use
- After web-search returns a useful-looking URL
- "Read this: https://..."
- "What does this article say: [url]"
- Fetching documentation pages for deeper research

## When NOT to use
- General searches (use web-search instead)
- PDFs (may not render correctly)
- Pages requiring authentication/login

## Workflow
1. Validate URL starts with http/https
2. GET request with browser User-Agent and follow redirects
3. Strip scripts, styles, HTML tags
4. Return first 12,000 characters of readable text

## Output Format
```json
{
  "url": "https://...",
  "content": "Article text here...",
  "char_count": 8432
}
```

## Guardrails
- Content is extracted text, may not include images/tables perfectly
- If HTTP error, return ok=False with status code
- Max 12,000 characters to avoid context overload

## References
- Direct HTTP fetch, no external API
