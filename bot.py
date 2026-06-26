"""
Telegram bot entry point.
Run with: python bot.py
"""

import logging
import os
from dotenv import load_dotenv
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ChatAction, ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler

load_dotenv()

from src import agent, memory, scheduler

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

ALLOWED_USER_IDS: set[int] = set()


def _is_allowed(user_id: int) -> bool:
    return not ALLOWED_USER_IDS or user_id in ALLOWED_USER_IDS


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hi! I'm your personal AI assistant.\n\n"
        "I can help you with:\n"
        "• 🔍 *Research* — search the web, read articles\n"
        "• 📧 *Gmail* — read, send, and organise your emails\n"
        "• 📝 *Notes* — save and retrieve information\n"
        "• ⏰ *Scheduled tasks* — e.g. 'send me world cup results at 9am'\n\n"
        "Just talk to me naturally. Commands:\n"
        "/clear — reset conversation\n"
        "/notes — list saved notes\n"
        "/inbox — show Gmail inbox\n"
        "/tasks — list scheduled tasks",
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_clear(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    memory.clear(update.effective_user.id)
    await update.message.reply_text("Conversation cleared. Fresh start! 🧹")


async def cmd_inbox(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_allowed(update.effective_user.id):
        return
    await update.message.reply_chat_action(ChatAction.TYPING)
    user_id = update.effective_user.id
    history = memory.load(user_id)
    reply, history = agent.chat(history, "Show me my Gmail inbox — list the latest 10 emails.", user_id=user_id)
    memory.save(user_id, history)
    await _send_long(update, reply)


async def cmd_notes(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_allowed(update.effective_user.id):
        return
    await update.message.reply_chat_action(ChatAction.TYPING)
    user_id = update.effective_user.id
    history = memory.load(user_id)
    reply, history = agent.chat(history, "List all my saved notes.", user_id=user_id)
    memory.save(user_id, history)
    await _send_long(update, reply)


async def cmd_tasks(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_allowed(update.effective_user.id):
        return
    tasks = scheduler.list_tasks(update.effective_user.id)
    if not tasks:
        await update.message.reply_text("No scheduled tasks.")
        return
    lines = [f"⏰ *Scheduled Tasks*"]
    for t in tasks:
        lines.append(f"• ID {t['id']} — {t['run_at'][:16]}: {t['prompt'][:60]}")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_allowed(update.effective_user.id):
        await update.message.reply_text("Sorry, you're not authorised to use this bot.")
        return

    user_text = update.message.text.strip()
    if not user_text:
        return

    await update.message.reply_chat_action(ChatAction.TYPING)

    user_id = update.effective_user.id
    history = memory.load(user_id)
    try:
        reply, history = agent.chat(history, user_text, user_id=user_id)
        memory.save(user_id, history)
    except Exception as e:
        logger.exception("Agent error")
        reply = f"Something went wrong: {e}"

    await _send_long(update, reply)


async def _send_long(update: Update, text: str):
    if not text:
        text = "_(no response)_"
    chunk_size = 4000
    for i in range(0, len(text), chunk_size):
        chunk = text[i : i + chunk_size]
        try:
            await update.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN)
        except Exception:
            await update.message.reply_text(chunk)


def main():
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    app = ApplicationBuilder().token(token).build()

    # Wire up scheduler with a send function that uses the bot
    async def send_to_user(chat_id: int, text: str):
        chunk_size = 4000
        for i in range(0, len(text), chunk_size):
            chunk = text[i : i + chunk_size]
            try:
                await app.bot.send_message(chat_id=chat_id, text=chunk, parse_mode=ParseMode.MARKDOWN)
            except Exception:
                await app.bot.send_message(chat_id=chat_id, text=chunk)

    apscheduler = AsyncIOScheduler()

    async def post_init(application):
        scheduler.init(apscheduler, send_to_user)
        apscheduler.start()

    app.post_init = post_init

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("clear", cmd_clear))
    app.add_handler(CommandHandler("inbox", cmd_inbox))
    app.add_handler(CommandHandler("notes", cmd_notes))
    app.add_handler(CommandHandler("tasks", cmd_tasks))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot is running...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
