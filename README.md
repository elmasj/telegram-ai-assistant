# Personal AI Assistant — Telegram Bot

A personal AI assistant that lives in Telegram, built entirely using **Claude Code** by Anthropic. This is my first real-world use case of Claude Code, and it was built through a natural conversation — no manual coding required.

## What it does

- 🔍 **Research** — search the web and read articles on any topic
- 📧 **Gmail** — read, send, search and organise your emails
- 📝 **Notes** — save and retrieve research notes with tags
- ⏰ **Scheduled tasks** — e.g. "send me the world cup results at 9am tomorrow"
- ⚡ **Power outages** — check planned power outages in Macedonia (Elektrodistribucija) by region
- 👥 **User management** — owner-only access control, add/remove users from chat
- 🔄 **Self-restart** — `/restart` command to restart the bot without losing data

## Built with Claude Code

This project was built entirely through [Claude Code](https://claude.ai/code) — Anthropic's AI coding assistant. Every file, feature, and fix was written by Claude through a natural conversation. This is my first real-world use case of Claude Code, going from idea to working product in a single session.

## Tech stack

- [Claude Sonnet 4.6](https://anthropic.com) — AI brain (tool use & reasoning)
- [python-telegram-bot](https://python-telegram-bot.org/) — Telegram interface
- [Tavily](https://tavily.com) — web search API
- [Gmail API](https://developers.google.com/gmail/api) — email integration
- [APScheduler](https://apscheduler.readthedocs.io/) — scheduled tasks
- SQLite — conversation memory, notes & user management

## Setup

See [SETUP.md](SETUP.md) for full setup instructions including Telegram, Gmail, and API keys.

## Commands

| Command | Description |
|---|---|
| `/start` | Show welcome message |
| `/inbox` | Show Gmail inbox |
| `/notes` | List saved notes |
| `/tasks` | List scheduled tasks |
| `/outages` | Today's power outages (all Macedonia) |
| `/outages Скопје` | Outages filtered by region |
| `/adduser <id>` | Add a user (owner only) |
| `/removeuser <id>` | Remove a user (owner only) |
| `/users` | List allowed users (owner only) |
| `/clear` | Reset conversation memory |
| `/restart` | Restart the bot |

## Usage examples

```
"What are the latest AI agent frameworks in 2026?"
"Search my inbox for emails from Google"
"Send an email to x@gmail.com about the meeting"
"Remember that Tavily has a 1000 req/month free tier"
"Send me the world cup results tomorrow at 9am"
"Are there any power cuts in Скопје tomorrow?"
```

## Project structure

```
├── bot.py              # Telegram bot entry point
├── src/
│   ├── agent.py        # Claude tool-use loop
│   ├── memory.py       # Per-user conversation history
│   ├── scheduler.py    # Scheduled task engine
│   ├── users.py        # User access management
│   └── tools/
│       ├── search.py   # Web search + URL reader
│       ├── gmail.py    # Gmail integration
│       ├── notes.py    # Notes storage
│       └── outages.py  # Power outage checker (Elektrodistribucija MK)
├── requirements.txt
├── .env.example
└── SETUP.md
```
