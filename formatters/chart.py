"""Chart renderer — price and TVL charts via matplotlib."""
import io
import logging
from datetime import datetime, timezone

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from clients.coingecko import get_price_chart, search_coin, get_mnt_info
from clients.defillama import get_chain_tvl_history

logger = logging.getLogger(__name__)

_KNOWN: dict[str, str] = {
    "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana",
    "BNB": "binancecoin", "MNT": "mantle", "MATIC": "matic-network",
    "ARB": "arbitrum", "OP": "optimism",
}

_CHART_STYLE = {
    "figure.facecolor": "#1a1a2e",
    "axes.facecolor":   "#16213e",
    "axes.edgecolor":   "#0f3460",
    "xtick.color":      "#e0e0e0",
    "ytick.color":      "#e0e0e0",
    "axes.labelcolor":  "#e0e0e0",
    "text.color":       "#e0e0e0",
    "grid.color":       "#0f3460",
    "grid.linestyle":   "--",
    "grid.alpha":        0.5,
}


async def render(coin: str, days: int = 7) -> tuple[bytes, str]:
    """
    Render a price or TVL chart.
    coin = "mantle_tvl" → chain TVL chart
    coin = any ticker/name → price chart
    Returns (png_bytes, caption).
    """
    coin_lower = coin.lower().strip()

    if coin_lower in ("mantle_tvl", "mantle tvl", "tvl"):
        return await _tvl_chart(days)

    coin_id = _KNOWN.get(coin.upper()) or _KNOWN.get(coin_lower)
    if not coin_id:
        try:
            coin_id = await search_coin(coin)
        except Exception:
            pass
    if not coin_id:
        raise ValueError(f"Unknown coin: {coin!r}")

    return await _price_chart(coin_id, coin.upper(), days)


async def _price_chart(coin_id: str, label: str, days: int) -> tuple[bytes, str]:
    data = await get_price_chart(coin_id, days)
    if not data:
        raise ValueError("No chart data returned")

    times = [datetime.fromtimestamp(ts / 1000, tz=timezone.utc) for ts, _ in data]
    prices = [p for _, p in data]

    color = "#00d4aa" if prices[-1] >= prices[0] else "#ff4d6d"

    with plt.style.context(_CHART_STYLE):
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(times, prices, color=color, linewidth=2)
        ax.fill_between(times, prices, min(prices), alpha=0.15, color=color)
        ax.set_title(f"{label} — {days}d Price", fontsize=14, pad=12)
        ax.set_ylabel("USD", fontsize=11)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.gcf().autofmt_xdate()
        ax.grid(True)

        pct = ((prices[-1] - prices[0]) / prices[0] * 100) if prices[0] else 0
        arrow = "▲" if pct >= 0 else "▼"
        caption = (
            f"📈 {label} {days}d Chart · "
            f"${prices[-1]:,.4f}" if prices[-1] < 1 else f"${prices[-1]:,.2f}"
        )
        caption = f"📈 {label} {days}d · ${prices[-1]:,.2f} ({arrow}{abs(pct):.1f}%)"

        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=130, bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        return buf.read(), caption


async def _tvl_chart(days: int) -> tuple[bytes, str]:
    history = await get_chain_tvl_history("Mantle")
    if not history:
        raise ValueError("No TVL history returned")

    # Trim to requested window
    cutoff = datetime.now(timezone.utc).timestamp() - days * 86400
    data = [(e["date"], e["tvl"]) for e in history if e["date"] >= cutoff]
    if not data:
        data = [(e["date"], e["tvl"]) for e in history[-days:]]

    times = [datetime.fromtimestamp(ts, tz=timezone.utc) for ts, _ in data]
    tvls = [v / 1e6 for _, v in data]  # millions

    color = "#7b61ff"
    with plt.style.context(_CHART_STYLE):
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(times, tvls, color=color, linewidth=2)
        ax.fill_between(times, tvls, min(tvls), alpha=0.15, color=color)
        ax.set_title(f"Mantle TVL — {days}d", fontsize=14, pad=12)
        ax.set_ylabel("TVL ($ millions)", fontsize=11)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.gcf().autofmt_xdate()
        ax.grid(True)

        caption = f"📊 Mantle TVL {days}d · ${tvls[-1]:.1f}M"

        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=130, bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        return buf.read(), caption
