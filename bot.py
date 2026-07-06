"""
Telegram bot entry point.
Run with: python bot.py
"""

import logging
import os
import sys

# Force UTF-8 for all I/O so Macedonian/Cyrillic characters don't crash on Windows
if sys.stdout.encoding != "utf-8":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
from dotenv import load_dotenv
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ChatAction, ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler

load_dotenv()

from src import agent, memory, scheduler, users

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

def _is_allowed(user_id: int) -> bool:
    return users.is_allowed(user_id)


def _is_owner(user_id: int) -> bool:
    return user_id == users.OWNER_ID


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


async def cmd_logs(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_owner(update.effective_user.id):
        return
    # Optional: /logs <user_id> to filter by user
    target_id = int(ctx.args[0]) if ctx.args else None
    logs = memory.get_user_logs(user_id=target_id, limit=20)
    if not logs:
        await update.message.reply_text("No activity logged yet.")
        return
    lines = [f"📋 *Recent activity{'  for ' + str(target_id) if target_id else ''}:*\n"]
    for entry in logs:
        ts = entry["timestamp"][:16].replace("T", " ")
        lines.append(f"`{ts}` [{entry['user_id']}]: {entry['message']}")
    await _send_long(update, "\n".join(lines))


async def cmd_adduser(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_owner(update.effective_user.id):
        await update.message.reply_text("Only the owner can add users.")
        return
    args = ctx.args
    if not args:
        await update.message.reply_text("Usage: /adduser <telegram_user_id> [note]")
        return
    try:
        uid = int(args[0])
        note = " ".join(args[1:]) if len(args) > 1 else ""
        result = users.add_user(uid, update.effective_user.id, note)
        await update.message.reply_text(f"✅ {result}")
    except ValueError:
        await update.message.reply_text("User ID must be a number.")


async def cmd_removeuser(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_owner(update.effective_user.id):
        await update.message.reply_text("Only the owner can remove users.")
        return
    args = ctx.args
    if not args:
        await update.message.reply_text("Usage: /removeuser <telegram_user_id>")
        return
    try:
        uid = int(args[0])
        result = users.remove_user(uid)
        await update.message.reply_text(f"✅ {result}")
    except ValueError:
        await update.message.reply_text("User ID must be a number.")


async def cmd_users(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_owner(update.effective_user.id):
        return
    user_list = users.list_users()
    if not user_list:
        await update.message.reply_text("No extra users added yet. You're the only one with access.")
        return
    lines = ["*Allowed Users:*", f"• `{users.OWNER_ID}` — owner (you)"]
    for u in user_list:
        note = f" — {u['note']}" if u['note'] else ""
        lines.append(f"• `{u['user_id']}`{note}")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


async def cmd_outages(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_allowed(update.effective_user.id):
        return
    region = " ".join(ctx.args) if ctx.args else None
    await update.message.reply_chat_action(ChatAction.TYPING)
    from src.tools import outages as outages_tool
    from datetime import date
    results = outages_tool.get_outages(region=region, for_date=date.today().isoformat())
    reply = outages_tool.format_outages(results)
    await _send_long(update, reply)


async def cmd_restart(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_allowed(update.effective_user.id):
        return
    await update.message.reply_text("Restarting... I'll be back in a few seconds. 🔄")
    await ctx.application.updater.stop()
    await ctx.application.stop()
    os.execv(sys.executable, [sys.executable] + sys.argv)


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

    user_id = update.effective_user.id
    user_text = update.message.text.strip()
    if not user_text:
        return

    memory.log_message(user_id, user_text)
    await update.message.reply_chat_action(ChatAction.TYPING)
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
    app.add_handler(CommandHandler("restart", cmd_restart))
    app.add_handler(CommandHandler("outages", cmd_outages))
    app.add_handler(CommandHandler("logs", cmd_logs))
    app.add_handler(CommandHandler("adduser", cmd_adduser))
    app.add_handler(CommandHandler("removeuser", cmd_removeuser))
    app.add_handler(CommandHandler("users", cmd_users))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot is running...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
