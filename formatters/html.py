"""HTML formatters for Telegram Bot API 10.1 rich messages and plain HTML."""
import html
import re
from datetime import datetime


def _esc(text) -> str:
    return html.escape(str(text))


def confidence_bar(score: int) -> str:
    score = max(0, min(100, score))
    filled = round(score / 10)
    return "█" * filled + "░" * (10 - filled)


def format_price(data: dict, coin: str = "") -> str:
    """Compact HTML for price responses. Chart is sent separately."""
    name = data.get("coin") or coin or "Token"
    price = data.get("price_usd")
    change_24h = data.get("change_24h_pct")
    mcap = data.get("market_cap_usd")
    vol = data.get("volume_24h_usd")
    change_7d = data.get("change_7d_pct")
    source = data.get("source", "CoinGecko")
    ts = data.get("last_updated") or datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    price_str = f"${price:,.4f}" if price and price < 1 else (f"${price:,.2f}" if price else "N/A")

    if change_24h is not None:
        arrow = "🟢" if change_24h >= 0 else "🔴"
        change_str = f"{arrow} <code>{change_24h:+.2f}%</code> 24h"
    else:
        change_str = ""

    parts = [f"<b>💰 {_esc(name.upper())}</b>  <code>{_esc(price_str)}</code>"]
    if change_str:
        extra = []
        if vol:
            extra.append(f"Vol <code>${vol/1e6:.1f}M</code>")
        if change_7d is not None:
            extra.append(f"7d <code>{change_7d:+.2f}%</code>")
        row = change_str
        if extra:
            row += " · " + " · ".join(extra)
        parts.append(row)
    if mcap:
        parts.append(f"MCap <code>${mcap/1e9:.2f}B</code>")

    parts.append(f"\n<i>🕐 {_esc(str(ts)[:16])} UTC · {_esc(source)}</i>")
    return "\n".join(parts)


def format_research(sections: dict) -> str:
    """Rich HTML for full research reports — uses h2/h3/table/ul for Bot API 10.1."""
    parts = []

    subject = sections.get("subject", "Research Report")
    ts = sections.get("timestamp", datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))
    parts.append(f"<h2>📊 {_esc(subject)}</h2>")
    parts.append(f"<p><i>{_esc(ts)} UTC · Live data</i></p>")

    verdict = sections.get("verdict")
    verdict_level = sections.get("verdict_level", "neutral")
    if verdict:
        icon = {"bullish": "🟢", "bearish": "🔴", "neutral": "⚪", "caution": "🟡"}.get(verdict_level, "⚪")
        parts.append(f"<h3>{icon} Verdict</h3>")
        parts.append(f"<p>{_esc(verdict)}</p>")

    stats = sections.get("stats")
    if stats and isinstance(stats, dict):
        parts.append("<h3>📈 Quick Stats</h3>")
        rows = "".join(
            f"<tr><td><b>{_esc(k)}</b></td><td>{_esc(str(v))}</td></tr>"
            for k, v in stats.items()
        )
        parts.append(f"<table><tbody>{rows}</tbody></table>")

    analysis = sections.get("analysis")
    if analysis:
        parts.append("<h3>🔍 Analysis</h3>")
        parts.append(f"<p>{_esc(analysis)}</p>")

    risks = sections.get("risks")
    if risks and isinstance(risks, list):
        parts.append("<h3>⚠️ Risk Flags</h3>")
        items = "".join(f"<li>{_esc(r.get('description', r) if isinstance(r, dict) else r)}</li>" for r in risks)
        parts.append(f"<ul>{items}</ul>")

    suggestions = sections.get("suggestions")
    if suggestions and isinstance(suggestions, list):
        parts.append("<h3>💡 Also Worth Knowing</h3>")
        items = "".join(f"<li>{_esc(s)}</li>" for s in suggestions)
        parts.append(f"<ul>{items}</ul>")

    confidence = sections.get("confidence")
    sources = sections.get("sources")
    if confidence is not None or sources:
        parts.append("<h3>📌 Sources &amp; Confidence</h3>")
        if confidence is not None:
            bar = confidence_bar(confidence)
            parts.append(f"<p><code>{bar}</code> {confidence}%</p>")
        if sources and isinstance(sources, list):
            links = " · ".join(
                f'<a href="{_esc(s["url"])}">{_esc(s["name"])}</a>'
                if isinstance(s, dict) and "url" in s
                else _esc(str(s))
                for s in sources
            )
            parts.append(f"<p>{links}</p>")

    return "\n".join(parts)


def format_conversational(text: str) -> str:
    """Minimal formatting for casual chat replies."""
    # Remove any code fences or markdown artifacts the model might emit
    text = re.sub(r"```[^`]*```", "", text, flags=re.DOTALL)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\*([^*]+)\*", r"<i>\1</i>", text)
    return f"<p>{text.strip()}</p>"
