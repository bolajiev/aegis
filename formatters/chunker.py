"""Split rich HTML at block boundaries to stay within Telegram limits."""
import re

MAX_RICH = 32768   # Bot API 10.1 rich message limit
MAX_HTML = 4096    # sendMessage HTML limit

_BLOCK_TAGS = re.compile(r"(?=<(?:h[1-6]|p|ul|ol|table|blockquote)[\s>])", re.IGNORECASE)


def _split_at_blocks(text: str, limit: int) -> list[str]:
    if len(text) <= limit:
        return [text]

    candidates = [m.start() for m in _BLOCK_TAGS.finditer(text)]
    chunks = []
    start = 0
    while start < len(text):
        end = start + limit
        if end >= len(text):
            chunks.append(text[start:])
            break
        # Find last block boundary before limit
        split = next((p for p in reversed(candidates) if start < p < end), None)
        if split:
            chunks.append(text[start:split])
            start = split
        else:
            # Hard split at newline
            nl = text.rfind("\n", start, end)
            split = nl if nl > start else end
            chunks.append(text[start:split])
            start = split
    return [c.strip() for c in chunks if c.strip()]


def chunk_rich(text: str) -> list[str]:
    return _split_at_blocks(text, MAX_RICH)


def chunk_html(text: str) -> list[str]:
    return _split_at_blocks(text, MAX_HTML)
