"""
Aegis — Mantle Research Agent
Telegram bot (aiogram 3.x, Bot API 10.1)

Message flow:
  1. User sends message
  2. Bot replies with ⏳ Thinking… immediately
  3. Task submitted to async worker queue
  4. Worker runs ReAct pipeline
  5. Worker deletes thinking bubble, sends chart(s), sends response
"""
import asyncio
import hashlib
import logging
import re
import time as _time

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.types import (
    BotCommand, BufferedInputFile, CallbackQuery,
    InlineKeyboardButton, InlineKeyboardMarkup,
    InputRichMessage, Message,
)

from config import settings
from pipeline.router import handle as pipeline_handle
from middleware.rate_limit import check as rate_check
from middleware.logger import log_request, log_response
from memory.session import get_history, add_exchange
from memory.user import get_context_summary, update as user_mem_update, load as user_mem_load
from task_queue.worker import submit, run_worker
from scheduler.tasks import parse_schedule, schedule, pop_due, pending_count

# Last rich response per user: (query, html)  — for /export
_last_response: dict[int, tuple[str, str]] = {}

# Callback store: cb_key -> {action, query, intent, user_id}
_cb_store: dict[str, dict] = {}

# Register all skills
import skills  # noqa: F401

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

router = Router()

_MAX_HTML = 4096
_MAX_RICH = 32768

# ---------------------------------------------------------------------------
# Static content
# ---------------------------------------------------------------------------

_START_HTML = """\
<b>Aegis — Mantle Research Agent</b>

I answer onchain finance questions with <b>live, sourced data</b> from DefiLlama, CoinGecko, Mantle RPC, and the web.

<b>Try asking:</b>
• What is Mantle's RWA TVL?
• MNT price
• How does Mantle compare to Base and Arbitrum?
• Best yield on Mantle right now
• Is Lendle safe?
• What xStocks are on Mantle?
• Latest Mantle news
• Check wallet 0x...

Just ask naturally — no commands needed."""

_HELP_HTML = """\
<b>Aegis — Capabilities</b>

<b>Mantle Skills</b>
• <b>RWA TVL</b> — Ondo, Midas, Maple, OpenEden live TVL
• <b>DeFi Snapshot</b> — Merchant Moe, Agni, Aave, Lendle
• <b>DeFi Markets</b> — Aave V3 lending rates + top LP pools
• <b>Token Prices</b> — MNT, mETH, WMNT, USDT via mantle-cli
• <b>xStocks</b> — TSLAx, NVDAx, SPCXx, AAPLx prices
• <b>Chain Compare</b> — Mantle vs Base vs Arbitrum TVL + RWA
• <b>Portfolio</b> — Wallet balances + Aave positions
• <b>Risk Eval</b> — Protocol safety score + audit history
• <b>Chain Stats</b> — Gas price, block, chain health
• <b>Identity</b> — Aegis's ERC-8004 onchain agent identity

<b>Research Tools</b>
• Price charts — auto with every price query
• Web search — news, announcements, narratives
• URL reader — reads full article content
• Cross-chain compare — Mantle vs peers

<b>Commands</b>
/start — Introduction
/help — This page
/export — Save last response as Markdown file"""


# ---------------------------------------------------------------------------
# Send helpers
# ---------------------------------------------------------------------------

def _chunk(text: str, limit: int = _MAX_HTML) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunks, buf = [], ""
    for line in text.split("\n"):
        if len(buf) + len(line) + 1 > limit and buf:
            chunks.append(buf.strip())
            buf = line
        else:
            buf += ("\n" if buf else "") + line
    if buf.strip():
        chunks.append(buf.strip())
    return chunks or [text[:limit]]


async def _send(chat_id: int, html_body: str, bot: Bot, reply_to: int | None = None) -> None:
    """
    Try: send_rich_message (Bot API 10.1)
    Fallback 1: send_message(parse_mode="HTML")
    Fallback 2: strip tags, plain text
    """
    limit = _MAX_RICH if len(html_body) > _MAX_HTML else _MAX_HTML
    for chunk in _chunk(html_body, limit):
        reply_params = {"message_id": reply_to} if reply_to else None
        try:
            kwargs: dict = {"chat_id": chat_id, "rich_message": InputRichMessage(html=chunk)}
            if reply_params:
                kwargs["reply_parameters"] = reply_params
            await bot.send_rich_message(**kwargs)
            reply_to = None
        except Exception as e1:
            logger.debug("rich send failed (%s) — trying HTML", e1)
            try:
                kwargs2: dict = {"chat_id": chat_id, "text": chunk[:_MAX_HTML], "parse_mode": "HTML"}
                if reply_params:
                    kwargs2["reply_parameters"] = reply_params
                await bot.send_message(**kwargs2)
                reply_to = None
            except Exception as e2:
                logger.debug("HTML send failed (%s) — plain text", e2)
                plain = re.sub(r"<[^>]+>", "", chunk)[:_MAX_HTML]
                await bot.send_message(chat_id, plain)
                reply_to = None


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    # Static content: send_message with parse_mode="HTML" — newlines are preserved
    await message.bot.send_message(message.chat.id, _START_HTML, parse_mode="HTML")


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.bot.send_message(message.chat.id, _HELP_HTML, parse_mode="HTML")


def _html_to_md(html_text: str) -> str:
    """Convert Aegis's rich HTML back to clean Markdown."""
    md = re.sub(r"<h2>(.*?)</h2>", r"## \1\n", html_text, flags=re.DOTALL)
    md = re.sub(r"<h3>(.*?)</h3>", r"### \1\n", md, flags=re.DOTALL)
    md = re.sub(r"<b>(.*?)</b>", r"**\1**", md, flags=re.DOTALL)
    md = re.sub(r"<i>(.*?)</i>", r"*\1*", md, flags=re.DOTALL)
    md = re.sub(r"<li>(.*?)</li>", r"- \1\n", md, flags=re.DOTALL)
    md = re.sub(r"<ul>|</ul>", "", md)
    md = re.sub(r"<p>(.*?)</p>", r"\1\n\n", md, flags=re.DOTALL)
    md = re.sub(r'<a href="([^"]*)">([^<]*)</a>', r"[\2](\1)", md)
    md = re.sub(r"<blockquote>(.*?)</blockquote>", r"> \1\n", md, flags=re.DOTALL)
    md = re.sub(r"<[^>]+>", "", md)
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md.strip()


def _filename_slug(query: str) -> str:
    """Turn a query into a safe filename slug, max 40 chars."""
    slug = re.sub(r"[^\w\s-]", "", query.lower())
    slug = re.sub(r"[\s_]+", "_", slug).strip("_")[:40]
    return slug or "research"


@router.message(Command("export"))
async def cmd_export(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else 0
    stored = _last_response.get(user_id)
    if not stored:
        await message.reply("No recent response to export yet — ask me something first.")
        return
    query, raw_html = stored
    md = _html_to_md(raw_html)
    slug = _filename_slug(query)
    ts = int(_time.time())
    filename = f"aegis_{slug}_{ts}.md"
    buf = BufferedInputFile(md.encode(), filename=filename)
    await message.bot.send_document(message.chat.id, buf, caption=f"Research: {query[:80]}")


@router.message(Command("history"))
async def cmd_history(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else 0
    profile = user_mem_load(user_id)
    researched = profile.get("researched", [])
    if not researched:
        await message.bot.send_message(
            message.chat.id,
            "No research history yet — ask me something!",
            parse_mode="HTML",
        )
        return
    lines = [
        f"• {r['topic'][:55]} <i>({r.get('ts','?')})</i>"
        for r in reversed(researched[-12:])
    ]
    watchlist = profile.get("watchlist", [])
    watch_line = f"\n\n<b>Watching:</b> {', '.join(watchlist[-8:])}" if watchlist else ""
    text = "<b>Your Research History</b>\n\n" + "\n".join(lines) + watch_line
    await message.bot.send_message(message.chat.id, text, parse_mode="HTML")


# ---------------------------------------------------------------------------
# Inline keyboard builders
# ---------------------------------------------------------------------------

def _make_keyboard(query: str, user_id: int, intent: str) -> InlineKeyboardMarkup:
    """Action buttons appended to every non-chat response."""
    h = hashlib.md5(f"{user_id}:{query}:{_time.time():.0f}".encode()).hexdigest()[:10]

    def _btn(label: str, action: str) -> InlineKeyboardButton:
        key = f"{action}:{h}"
        _cb_store[key] = {"action": action, "query": query, "intent": intent, "user_id": user_id}
        return InlineKeyboardButton(text=label, callback_data=key)

    refresh = _btn("🔄 Refresh", "refresh")
    deep    = _btn("🔎 Deep Dive", "deep")
    chart   = _btn("📊 Chart", "chart")
    export  = _btn("📤 Export", "export")

    if intent == "price":
        rows = [[refresh, chart, export]]
    elif intent in ("audit", "risk"):
        rows = [[refresh, export]]
    elif intent == "chat":
        return None  # no buttons on chat
    else:
        rows = [[refresh, deep], [chart, export]]

    return InlineKeyboardMarkup(inline_keyboard=rows)


# ---------------------------------------------------------------------------
# Callback handler (button taps)
# ---------------------------------------------------------------------------

@router.callback_query()
async def on_callback(cb: CallbackQuery) -> None:
    key = cb.data or ""
    stored = _cb_store.get(key)
    if not stored:
        await cb.answer("Button expired — ask again.", show_alert=False)
        return

    action   = stored["action"]
    query    = stored["query"]
    intent   = stored["intent"]
    user_id  = stored["user_id"]
    chat_id  = cb.message.chat.id
    bot      = cb.bot

    await cb.answer()  # dismiss loading spinner

    if action == "export":
        stored_resp = _last_response.get(user_id)
        if stored_resp:
            q, html = stored_resp
            md = _html_to_md(html)
            slug = _filename_slug(q)
            buf = BufferedInputFile(md.encode(), filename=f"aegis_{slug}_{int(_time.time())}.md")
            await bot.send_document(chat_id, buf, caption=f"Research: {q[:80]}")
        return

    if action == "chart":
        # Extract a token from the stored query and render a chart
        tok_m = re.search(r"\b(MNT|BTC|ETH|SOL|mETH|WMNT)\b", query, re.I)
        coin = tok_m.group(1).lower() if tok_m else "mantle"
        await bot.send_chat_action(chat_id, "upload_photo")
        try:
            from formatters.chart import render
            png, caption = await render(coin, 7)
            await bot.send_photo(chat_id, BufferedInputFile(png, "chart.png"), caption=caption)
        except Exception as e:
            await bot.send_message(chat_id, f"Chart unavailable: {e}")
        return

    # refresh or deep — re-run the pipeline
    override = 6 if action == "deep" else None
    think_msg = await bot.send_message(chat_id, "⏳ Researching…")

    async def _rerun():
        history = get_history(user_id)
        ctx = get_context_summary(user_id)
        try:
            reply, lane, results, charts, ivalue = await pipeline_handle(
                query, user_id=user_id, history=history,
                user_context=ctx, override_iterations=override,
            )
        except Exception:
            reply = "<p><b>Something went wrong.</b></p>"
            results, charts, ivalue = [], [], intent

        try:
            await bot.delete_message(chat_id, think_msg.message_id)
        except Exception:
            pass

        for png_bytes, caption in charts:
            try:
                await bot.send_photo(chat_id, BufferedInputFile(png_bytes, "chart.png"), caption=caption)
            except Exception:
                pass

        kb = _make_keyboard(query, user_id, ivalue)
        await _send_with_kb(chat_id, reply, bot, kb)
        _last_response[user_id] = (query, reply)
        plain = re.sub(r"<[^>]+>", "", reply)[:400]
        add_exchange(user_id, query, plain)
        user_mem_update(user_id, query, ivalue)

    asyncio.create_task(_rerun())


# ---------------------------------------------------------------------------
# Send helper with optional inline keyboard
# ---------------------------------------------------------------------------

async def _send_with_kb(
    chat_id: int,
    html_body: str,
    bot: Bot,
    keyboard: InlineKeyboardMarkup | None = None,
    reply_to: int | None = None,
) -> None:
    """Send last chunk with keyboard attached; earlier chunks have no keyboard."""
    chunks = _chunk(html_body, _MAX_HTML)
    for i, chunk in enumerate(chunks):
        is_last = (i == len(chunks) - 1)
        kb = keyboard if is_last else None
        reply_params = {"message_id": reply_to} if (reply_to and i == 0) else None
        try:
            kwargs: dict = {"chat_id": chat_id, "rich_message": InputRichMessage(html=chunk)}
            if kb:
                kwargs["reply_markup"] = kb
            if reply_params:
                kwargs["reply_parameters"] = reply_params
            await bot.send_rich_message(**kwargs)
        except Exception:
            try:
                kwargs2: dict = {"chat_id": chat_id, "text": chunk[:_MAX_HTML], "parse_mode": "HTML"}
                if kb:
                    kwargs2["reply_markup"] = kb
                if reply_params:
                    kwargs2["reply_parameters"] = reply_params
                await bot.send_message(**kwargs2)
            except Exception:
                plain = re.sub(r"<[^>]+>", "", chunk)[:_MAX_HTML]
                await bot.send_message(chat_id, plain, reply_markup=kb if is_last else None)


# ---------------------------------------------------------------------------
# Main message handler
# ---------------------------------------------------------------------------

@router.message()
async def on_message(message: Message) -> None:
    if not message.text:
        return

    user_id = message.from_user.id if message.from_user else 0
    query = message.text.strip()

    if not rate_check(user_id):
        await message.reply("⏳ Slow down a bit — max 10 requests per minute.")
        return

    # ── Scheduled request detection ───────────────────────────────────────
    parsed = parse_schedule(query)
    if parsed:
        delay_seconds, clean_query = parsed
        if delay_seconds < 10:
            await message.reply("Minimum delay is 10 seconds.")
            return
        if pending_count(user_id) >= 5:
            await message.reply("You already have 5 scheduled requests pending.")
            return
        schedule(
            user_id=user_id, chat_id=message.chat.id,
            query=clean_query, delay_seconds=delay_seconds,
            reply_to=message.message_id,
        )
        mins, secs = delay_seconds // 60, delay_seconds % 60
        when = f"{mins}m {secs}s" if mins else f"{secs}s"
        await message.reply(
            f"⏰ Scheduled — I'll send you <b>{clean_query}</b> in {when}.",
            parse_mode="HTML",
        )
        return
    # ─────────────────────────────────────────────────────────────────────

    # Typing indicator — shows animated dots while we spin up
    try:
        await message.bot.send_chat_action(message.chat.id, "typing")
    except Exception:
        pass

    thinking = None
    try:
        thinking = await message.bot.send_message(
            message.chat.id, "⏳ Thinking…",
            reply_parameters={"message_id": message.message_id},
        )
    except Exception:
        pass

    thinking_id = thinking.message_id if thinking else None
    bot      = message.bot
    chat_id  = message.chat.id
    msg_id   = message.message_id
    start    = log_request(user_id, query, "auto")

    async def update_thinking(labels: list[str]) -> None:
        if not thinking_id:
            return
        lines = ["⏳ Researching…", ""] + [f"  {lbl}" for lbl in labels]
        try:
            await bot.edit_message_text(
                chat_id=chat_id, message_id=thinking_id,
                text="\n".join(lines),
            )
        except Exception:
            pass

    async def process():
        history = get_history(user_id)
        ctx     = get_context_summary(user_id)
        try:
            reply, lane, results, charts, intent_val = await pipeline_handle(
                query, user_id=user_id, history=history,
                progress_cb=update_thinking, user_context=ctx,
            )
        except Exception:
            logger.exception("Pipeline error for query: %.80r", query)
            reply = "<p><b>Something went wrong.</b> Please try again in a moment.</p>"
            results, charts, intent_val = [], [], "chat"

        # Delete thinking bubble
        if thinking_id:
            try:
                await bot.delete_message(chat_id, thinking_id)
            except Exception:
                pass

        # Send charts first
        for png_bytes, caption in charts:
            try:
                await bot.send_photo(
                    chat_id, BufferedInputFile(png_bytes, "chart.png"),
                    caption=caption,
                    reply_parameters={"message_id": msg_id},
                )
            except Exception:
                logger.warning("Chart send failed")

        # Build keyboard (None for chat/greetings)
        kb = _make_keyboard(query, user_id, intent_val)
        await _send_with_kb(chat_id, reply, bot, kb, reply_to=msg_id)

        # Persist
        _last_response[user_id] = (query, reply)
        plain_reply = re.sub(r"<[^>]+>", "", reply)[:400]
        add_exchange(user_id, query, plain_reply)
        user_mem_update(user_id, query, intent_val)
        log_response(user_id, start, [r.skill for r in results], "auto")

    submitted = await submit(user_id, process)
    if not submitted:
        if thinking_id:
            try:
                await bot.delete_message(chat_id, thinking_id)
            except Exception:
                pass
        await message.reply("⏳ Still working on your previous request — please wait.")


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

async def _run_scheduled(bot: Bot, task) -> None:
    """Execute a scheduled task and send the result to the user."""
    history = get_history(task.user_id)
    ctx     = get_context_summary(task.user_id)
    start   = log_request(task.user_id, task.query, "scheduled")
    try:
        reply, lane, results, charts, intent_val = await pipeline_handle(
            task.query, user_id=task.user_id, history=history, user_context=ctx,
        )
    except Exception:
        logger.exception("Scheduled pipeline error: %.80r", task.query)
        reply, results, charts, intent_val = (
            "<p><b>Something went wrong with your scheduled request.</b></p>",
            [], [], "chat",
        )

    header = f"<b>⏰ Scheduled: {task.query[:60]}</b>\n\n"
    for png_bytes, caption in charts:
        try:
            await bot.send_photo(
                task.chat_id, BufferedInputFile(png_bytes, "chart.png"), caption=caption,
            )
        except Exception:
            pass

    kb = _make_keyboard(task.query, task.user_id, intent_val)
    await _send_with_kb(task.chat_id, header + reply, bot, kb, reply_to=task.reply_to)

    plain = re.sub(r"<[^>]+>", "", reply)[:400]
    add_exchange(task.user_id, task.query, plain)
    user_mem_update(task.user_id, task.query, intent_val)
    log_response(task.user_id, start, [r.skill for r in results], "scheduled")
    _last_response[task.user_id] = (task.query, reply)


async def _scheduler_loop(bot: Bot) -> None:
    """Check for due scheduled tasks every 15 seconds."""
    while True:
        await asyncio.sleep(15)
        for task in pop_due():
            asyncio.create_task(_run_scheduled(bot, task))


async def main() -> None:
    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode="HTML"),
    )
    dp = Dispatcher()
    dp.include_router(router)

    await bot.set_my_commands([
        BotCommand(command="start",   description="Introduction"),
        BotCommand(command="help",    description="Capabilities"),
        BotCommand(command="history", description="Your research history"),
        BotCommand(command="export",  description="Save last response as Markdown file"),
    ])

    # Start background tasks
    asyncio.create_task(run_worker())
    asyncio.create_task(_scheduler_loop(bot))

    logger.info("Aegis starting…")
    await dp.start_polling(bot, allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    asyncio.run(main())
