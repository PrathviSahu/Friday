"""telegram_bot.py — Remote phone access to FRIDAY via Telegram (v3).

Turn FRIDAY from a Mac-only desk assistant into an always-available personal
AI reachable from your phone anywhere.

Run it with:
    python -m services.telegram_bot   (from backend/)

Requires in backend/.env:
    TELEGRAM_BOT_TOKEN=...   (create a bot via @BotFather)
    TELEGRAM_OWNER_ID=...    (your numeric Telegram user id — only this user
                              may talk to the bot; everyone else gets denied)
"""

import asyncio
import logging
import os

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("friday_telegram")

try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
    _PTB_AVAILABLE = True
except ImportError:
    _PTB_AVAILABLE = False
    logger.warning("python-telegram-bot not installed — Telegram interface disabled.")


def _owner_id() -> int:
    try:
        return int(os.getenv("TELEGRAM_OWNER_ID", "0") or 0)
    except ValueError:
        return 0


def _is_owner(update: Update) -> bool:
    owner = _owner_id()
    if not owner:
        return False
    user = update.effective_user
    return bool(user) and user.id == owner


def _deny() -> str:
    return "⛔ Access denied. This bot belongs to Prem only."


async def _require_owner(update: Update) -> bool:
    if _is_owner(update):
        return True
    if update.effective_message:
        await update.effective_message.reply_text(_deny())
    return False


# ── Command handlers ───────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_owner(update):
        return
    _register_owner_device(update)
    await update.effective_message.reply_text(
        "⚡ Hey Prem! F.R.I.D.A.Y. here.\n"
        "I'm reachable from anywhere now. Try /help to see what I can do.\n"
        "This chat is now a trusted Presence device — approval prompts with\n"
        "✅/❌ buttons will land here."
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_owner(update):
        return
    await update.effective_message.reply_text(
        "📋 Commands:\n"
        "/time — current time\n"
        "/weather — live weather\n"
        "/tasks — pending tasks\n"
        "/market — quick market overview\n"
        "/spotify — what's playing\n"
        "/analyze SYMBOL — real technical analysis\n"
        "/help — this list\n\n"
        "Or just message me in plain language — I use the same brain as the desktop."
    )


async def cmd_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_owner(update):
        return
    from services.function_engine import dispatch
    await update.effective_message.reply_text(dispatch("get_time", {}))


async def cmd_weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_owner(update):
        return
    from services.function_engine import dispatch
    await update.effective_message.reply_text(dispatch("get_weather", {}))


async def cmd_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_owner(update):
        return
    from services.function_engine import dispatch
    await update.effective_message.reply_text(dispatch("get_todos", {}))


async def cmd_spotify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_owner(update):
        return
    from services.function_engine import dispatch
    await update.effective_message.reply_text(dispatch("get_spotify_info", {}))


async def cmd_market(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_owner(update):
        return
    await update.effective_message.reply_text(await asyncio.to_thread(_market_overview))


def _market_overview() -> str:
    """Fetch last prices for the default watchlist essentials."""
    from services.chart_data import fetch_ohlcv
    symbols = [("FX:EURUSD", "EURUSD"), ("OANDA:XAUUSD", "GOLD"),
               ("OANDA:NAS100USD", "NASDAQ"), ("BINANCE:BTCUSDT", "BTC"),
               ("CAPITALCOM:DXY", "DXY")]
    lines = ["📈 Quick Market Overview:"]
    for tv_sym, label in symbols:
        try:
            data = fetch_ohlcv(tv_sym, "5")
            candles = data.get("candles", [])
            if candles:
                lines.append(f"• {label}: {candles[-1]['close']:,.4f}")
            else:
                lines.append(f"• {label}: n/a")
        except Exception as err:
            logger.warning(f"[Telegram /market] {tv_sym}: {err}")
            lines.append(f"• {label}: n/a")
    return "\n".join(lines)


async def cmd_analyze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_owner(update):
        return
    args = context.args
    symbol = args[0].strip().upper() if args else "FX:EURUSD"
    interval = args[1].strip() if len(args) > 1 else "15"
    await update.effective_message.reply_text(
        f"🔍 Analyzing {symbol} ({interval})…"
    )
    from services.technical_analysis import analyze_symbol
    result = await asyncio.to_thread(analyze_symbol, symbol, interval)
    await update.effective_message.reply_text(result.get("summary") or result.get("error", "Analysis failed."))


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Free-form text → the same brain_v2 function-calling engine as the desktop."""
    if not await _require_owner(update):
        return
    text = (update.effective_message.text or "").strip()
    if not text:
        return
    try:
        from services.brain_v2 import respond_v2
        result = await asyncio.to_thread(respond_v2, text, True, True)
        reply = result.get("reply") or "Done."
        await update.effective_message.reply_text(reply)
    except Exception as err:
        logger.error(f"[Telegram message] {err}")
        await update.effective_message.reply_text("Sorry Prem, I hit an error processing that.")


# ── Cross-Device Presence (Phase 2.5) ─────────────────────────────────────────

_APP = None   # running Application, captured in post_init
_LOOP = None  # its asyncio loop (for cross-thread sends from FastAPI handlers)


def _register_owner_device(update: Update) -> None:
    """/start from the owner registers this chat as a trusted presence device."""
    try:
        from services import presence
        chat_id = str(update.effective_chat.id)
        presence.register_device("telegram", chat_id, "Prem (Telegram)")
    except Exception as err:
        logger.warning(f"[Presence] device registration failed: {err}")


def _approval_keyboard(approval_token: str) -> "InlineKeyboardMarkup":
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Approve", callback_data=f"pr:{approval_token}:approve"),
        InlineKeyboardButton("❌ Deny",    callback_data=f"pr:{approval_token}:deny"),
    ]])


async def _send_approval_async(chat_id: str, record: dict) -> None:
    text = (f"🛡️ *FRIDAY needs approval*\n\n{record['description']}\n\n"
            f"Capability: `{record['capability']}` — expires in 5 minutes.")
    await _APP.bot.send_message(
        chat_id=chat_id, text=text, parse_mode="Markdown",
        reply_markup=_approval_keyboard(record["approval_token"]))


def _telegram_sender(chat_id: str, record: dict) -> None:
    """SYNC hook handed to services.presence.TELEGRAM_SENDER — schedules the
    async send onto the bot's own loop (presence is called from FastAPI threads)."""
    if _APP is None or _LOOP is None:
        raise RuntimeError("telegram bot loop not ready")
    asyncio.run_coroutine_threadsafe(_send_approval_async(chat_id, record), _LOOP)


def parse_presence_callback(data: str) -> tuple[str, str] | None:
    """'pr:<token>:approve|deny' → (token, decision); anything else → None."""
    parts = (data or "").split(":")
    if len(parts) == 3 and parts[0] == "pr" and parts[1] and parts[2] in {"approve", "deny"}:
        return parts[1], parts[2]
    return None


async def on_presence_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Resolve an inline ✅/❌ tap — same Permission Center one-time approval."""
    query = update.callback_query
    if not query or not query.from_user or query.from_user.id != _owner_id():
        return
    parsed = parse_presence_callback(query.data)
    if not parsed:
        return
    token, decision = parsed
    from services import presence
    result = await asyncio.to_thread(presence.resolve_decision, token, decision)
    if result.get("status") != "ok":
        await query.answer(result.get("message", "Expired."), show_alert=True)
        return
    icon = "✅" if decision == "approve" else "❌"
    await query.answer(f"{icon} {result.get('message', decision)}")
    try:
        await query.edit_message_text(f"{icon} {result.get('message', '')}")
    except Exception:
        pass  # stale message — answer already acknowledged


# ── Builder ────────────────────────────────────────────────────────────────────

def build_application() -> "Application":
    """Construct the bot Application (raises if python-telegram-bot missing)."""
    global _APP
    if not _PTB_AVAILABLE:
        raise RuntimeError("python-telegram-bot is not installed (pip install -r requirements.txt)")
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token or token == "your_key_here":
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set in backend/.env")
    if not _owner_id():
        logger.warning("TELEGRAM_OWNER_ID not set — the bot will deny everyone.")

    async def _capture(application: "Application") -> None:
        global _LOOP
        _LOOP = asyncio.get_running_loop()
        from services import presence
        presence.TELEGRAM_SENDER = _telegram_sender

    builder = Application.builder().token(token)
    try:
        builder = builder.post_init(_capture)   # PTB ≥ 20
    except AttributeError:
        logger.warning("[Presence] telegram lib lacks post_init — push approvals disabled")
    app = builder.build()
    _APP = app
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("time", cmd_time))
    app.add_handler(CommandHandler("weather", cmd_weather))
    app.add_handler(CommandHandler("tasks", cmd_tasks))
    app.add_handler(CommandHandler("market", cmd_market))
    app.add_handler(CommandHandler("spotify", cmd_spotify))
    app.add_handler(CommandHandler("analyze", cmd_analyze))
    app.add_handler(CallbackQueryHandler(on_presence_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
    return app


def run_bot() -> None:
    """Blocking entrypoint: builds the app and polls for updates."""
    try:
        app = build_application()
    except RuntimeError as err:
        logger.error(err)
        return
    logger.info("⚡ FRIDAY Telegram bot started — polling for updates…")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    run_bot()
