# Personal AI Assistant — Telegram Bot

A personal AI assistant that lives in Telegram, built entirely using **Claude Code** by Anthropic. This is my first real-world use case of Claude Code, and it was built through a natural conversation — no manual coding required.

## What it does

- 🔍 **Research** — search the web and read articles on any topic
- 📧 **Gmail** — read, send, search and organise your emails
- 📝 **Notes** — save and retrieve research notes with tags
- ⏰ **Scheduled tasks** — e.g. "send me the world cup results at 9am tomorrow"
- 💬 **Natural conversation** — just talk to it like a person

## Built with

- [Claude Sonnet 4.6](https://anthropic.com) — AI brain (tool use & reasoning)
- [python-telegram-bot](https://python-telegram-bot.org/) — Telegram interface
- [Tavily](https://tavily.com) — web search API
- [Gmail API](https://developers.google.com/gmail/api) — email integration
- [APScheduler](https://apscheduler.readthedocs.io/) — scheduled tasks
- SQLite — conversation memory & notes storage

## Built with Claude Code

This project was built entirely through [Claude Code](https://claude.ai/code) — Anthropic's AI coding assistant. Every file, feature, and fix was written by Claude through a natural conversation. This is my first real-world use case of Claude Code, going from idea to working product in a single session.

## Setup

See [SETUP.md](SETUP.md) for full setup instructions including Telegram, Gmail, and API keys.

## Project structure

```
├── bot.py              # Telegram bot entry point
├── src/
│   ├── agent.py        # Claude tool-use loop
│   ├── memory.py       # Per-user conversation history
│   ├── scheduler.py    # Scheduled task engine
│   └── tools/
│       ├── search.py   # Web search + URL reader
│       ├── gmail.py    # Gmail integration
│       └── notes.py    # Notes storage
├── requirements.txt
├── .env.example        # Environment variables template
└── SETUP.md            # Setup guide
```

## Usage examples

```
"What are the latest AI agent frameworks in 2026?"
"Search my inbox for emails from Google"
"Send an email to x@gmail.com about the meeting"
"Remember that Tavily has a 1000 req/month free tier"
"Send me the world cup results tomorrow at 9am"
```
