"""Intent classifier — routes queries to the right response type and iteration limit."""
from __future__ import annotations
import re
from enum import Enum


class Intent(str, Enum):
    CHAT      = "chat"
    PRICE     = "price"
    CHART     = "chart"
    RWA       = "rwa"
    RESEARCH  = "research"
    NEWS      = "news"
    AUDIT     = "audit"
    WALLET    = "wallet"
    DEFI      = "defi"
    COMPARE   = "compare"
    EQUITY    = "equity"
    IDENTITY  = "identity"


# Intent → (max_iterations, response_type)
INTENT_CONFIG: dict[Intent, tuple[int, str]] = {
    Intent.CHAT:     (1,  "html"),
    Intent.PRICE:    (2,  "photo_then_html"),
    Intent.CHART:    (2,  "photo"),
    Intent.RWA:      (3,  "rich"),
    Intent.RESEARCH: (4,  "rich"),
    Intent.NEWS:     (3,  "rich"),
    Intent.AUDIT:    (6,  "rich"),
    Intent.WALLET:   (3,  "html"),
    Intent.DEFI:     (3,  "rich"),
    Intent.COMPARE:  (4,  "rich"),
    Intent.EQUITY:   (2,  "rich"),
    Intent.IDENTITY: (2,  "html"),
}

_GREETINGS = frozenset({
    "hi", "hey", "hello", "gm", "gn", "yo", "sup", "hiya",
    "thanks", "thank you", "thx", "ty", "thank", "thank u",
    "ok", "okay", "bye", "lol", "haha", "lmao",
    "cool", "nice", "great", "awesome", "good", "ok cool",
    "got it", "perfect", "sounds good", "makes sense", "noted",
})

_PRICE_RX = re.compile(
    r"\b(?:price|worth|cost|how much|value|trading at|rate)\b"
    r"|\$\w+|\b(?:usd|usdt|usdc)\b"
    r"|\b(?:btc|eth|sol|bnb|mnt|avax|matic|arb|op|ada|xrp|doge|shib|link|uni)\b",
    re.I,
)
_CHART_RX = re.compile(
    r"\b(?:chart|graph|plot|visuali[sz]e|show me|candle|1[hHdDwW]|7d|30d|trend)\b", re.I
)
_RWA_RX = re.compile(
    r"\b(?:rwa|real.?world|tokenized?\s+(?:bond|treasury|equity|stock|real|asset)|"
    r"tokenized\s+bonds?|tokenized\s+treasur|"
    r"ondo|midas|maple|openeden|backed|mountain\s+protocol|mif4|syrup|institutional)\b", re.I
)
_EQUITY_RX = re.compile(
    r"\b(?:xstock|xstocks|tslax|nvdax|spcxx|aaplx|qqqx|googlx|mstrx|gldx|tokenized\s+stock"
    r"|synthetic\s+equit|stock\s+token)\b", re.I
)
_DEFI_RX = re.compile(
    r"\b(?:tvl|defi|protocol|yield|apy|apr|liquidity|pool|dex|swap|lend|borrow"
    r"|merchant\s+moe|agni|lendle|aave|pendle|fusionx|bybit|init.capital)\b", re.I
)
_AUDIT_RX = re.compile(
    r"\b(?:safe|rug|audit|risk|security|exploit|hack|vulnerabil|scam|legit|trust|red\s+flag)\b", re.I
)
_NEWS_RX = re.compile(
    r"\b(?:news|latest|update|announcement|what.?s\s+(?:new|happening)|recent|today|this\s+week"
    r"|launch(?:ed)?|release|partnership)\b", re.I
)
_WALLET_RX = re.compile(r"0x[a-fA-F0-9]{38,}", re.I)
_COMPARE_RX = re.compile(r"\b(?:compar|vs\.?|versus|better|differ|between)\b", re.I)
_IDENTITY_RX = re.compile(
    r"\b(?:identity|erc.?8004|who\s+are\s+you|onchain\s+agent|your\s+(?:address|wallet|agent)\b"
    r"|registered|agent\s+nft)\b", re.I
)
_RESEARCH_RX = re.compile(
    r"\b(?:research|analyz|explain|tell\s+me\s+about|deep\s+dive|how\s+does|what\s+is"
    r"|overview|summar|report|breakdown)\b", re.I
)


def classify(text: str) -> Intent:
    """Rule-based intent classifier. Fast, no LLM needed."""
    t = text.strip()
    lower = t.lower().strip("!?.,")

    # Check structural signals first — these override the chat gate
    has_signal = (
        _NEWS_RX.search(t) or _PRICE_RX.search(t) or _DEFI_RX.search(t)
        or _RWA_RX.search(t) or _AUDIT_RX.search(t) or _EQUITY_RX.search(t)
        or _COMPARE_RX.search(t) or _RESEARCH_RX.search(t) or _WALLET_RX.search(t)
        or _IDENTITY_RX.search(t) or _CHART_RX.search(t)
    )

    # Smalltalk / greetings — only if no signals detected
    if not has_signal:
        if lower in _GREETINGS or (
            len(lower.split()) <= 3
            and not any(c.isdigit() for c in lower)
            and "?" not in lower
        ):
            return Intent.CHAT

    # Wallet address present → wallet intent
    if _WALLET_RX.search(t):
        return Intent.WALLET

    # Identity
    if _IDENTITY_RX.search(t):
        return Intent.IDENTITY

    # Explicit chart request
    if _CHART_RX.search(t) and not _DEFI_RX.search(t):
        return Intent.CHART

    # RWA — high priority, before research (e.g. "tell me about Ondo")
    if _RWA_RX.search(t):
        return Intent.RWA

    # News — must come before DeFi (e.g. "latest Mantle news")
    if _NEWS_RX.search(t):
        return Intent.NEWS

    # Audit / security
    if _AUDIT_RX.search(t):
        return Intent.AUDIT

    # Research keywords override DeFi when explicit (e.g. "deep dive on Agni")
    if _RESEARCH_RX.search(t) and not _COMPARE_RX.search(t):
        return Intent.RESEARCH

    # xStocks
    if _EQUITY_RX.search(t):
        return Intent.EQUITY

    # Price (simple)
    if _PRICE_RX.search(t) and not _COMPARE_RX.search(t) and not _DEFI_RX.search(t):
        return Intent.PRICE

    # Compare
    if _COMPARE_RX.search(t):
        return Intent.COMPARE

    # DeFi TVL / yield
    if _DEFI_RX.search(t):
        return Intent.DEFI

    # Default — general research
    return Intent.RESEARCH


# Legacy Lane enum kept for router backward compat
class Lane(str, Enum):
    SMALLTALK = "SMALLTALK"
    LOOKUP    = "LOOKUP"
    RESEARCH  = "RESEARCH"


async def classify_intent(text: str) -> Lane:
    intent = classify(text)
    if intent == Intent.CHAT:
        return Lane.SMALLTALK
    return Lane.RESEARCH
