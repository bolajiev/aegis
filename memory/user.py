"""
Long-term cross-session user memory — SQLite backed.
Tracks watchlist, research history, risk profile across sessions.
"""
from __future__ import annotations
import json
import sqlite3
import time
from pathlib import Path

_DB = Path(__file__).parent.parent / "user_memory.db"
_DEFAULT: dict = {
    "watchlist":        [],   # tokens / protocols user mentions
    "researched":       [],   # [{topic, intent, ts}]
    "risk_profile":     None, # "conservative" | "moderate" | "degen"
    "preferred_chains": [],
    "last_active":      None,
}

# Intents that hint at risk tolerance
_DEGEN_INTENTS   = {"audit", "defi", "compare"}
_CAREFUL_INTENTS = {"rwa", "equity", "news"}


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(_DB, check_same_thread=False)
    c.execute("""
        CREATE TABLE IF NOT EXISTS profiles (
            user_id   INTEGER PRIMARY KEY,
            profile   TEXT    NOT NULL,
            updated   REAL    NOT NULL
        )
    """)
    c.commit()
    return c


def load(user_id: int) -> dict:
    with _conn() as c:
        row = c.execute("SELECT profile FROM profiles WHERE user_id=?", (user_id,)).fetchone()
    if not row:
        return dict(_DEFAULT)
    try:
        return json.loads(row[0])
    except Exception:
        return dict(_DEFAULT)


def save(user_id: int, profile: dict) -> None:
    with _conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO profiles (user_id, profile, updated) VALUES (?,?,?)",
            (user_id, json.dumps(profile), time.time()),
        )


def update(user_id: int, query: str, intent: str) -> None:
    profile = load(user_id)

    # Append to research history, keep last 30
    profile["researched"].append({
        "topic":  query[:80],
        "intent": intent,
        "ts":     time.strftime("%Y-%m-%d", time.gmtime()),
    })
    profile["researched"] = profile["researched"][-30:]

    # Extract watchlist tokens from query
    import re
    tokens = re.findall(r"\b(MNT|mETH|WMNT|BTC|ETH|SOL|USDT|USDC|TSLAx|NVDAx|AAPLx|SPCXx)\b", query, re.I)
    for t in tokens:
        t_up = t.upper()
        if t_up not in profile["watchlist"]:
            profile["watchlist"].append(t_up)
    profile["watchlist"] = profile["watchlist"][-20:]

    # Derive risk profile from intent mix
    intents = [r["intent"] for r in profile["researched"][-10:]]
    degen_count   = sum(1 for i in intents if i in _DEGEN_INTENTS)
    careful_count = sum(1 for i in intents if i in _CAREFUL_INTENTS)
    if degen_count > careful_count + 2:
        profile["risk_profile"] = "degen"
    elif careful_count > degen_count:
        profile["risk_profile"] = "conservative"
    else:
        profile["risk_profile"] = "moderate"

    profile["last_active"] = time.strftime("%Y-%m-%d", time.gmtime())
    save(user_id, profile)


def get_context_summary(user_id: int) -> str:
    """Compact string injected into agent prompt — tells AEGIS what it knows about this user."""
    profile = load(user_id)

    parts = []
    if profile["watchlist"]:
        parts.append(f"Watching: {', '.join(profile['watchlist'][-5:])}")

    if profile["researched"]:
        recent = [r["topic"][:40] for r in profile["researched"][-3:]]
        parts.append(f"Recent research: {', '.join(recent)}")

    if profile["risk_profile"]:
        parts.append(f"Risk profile: {profile['risk_profile']}")

    return " | ".join(parts) if parts else ""
