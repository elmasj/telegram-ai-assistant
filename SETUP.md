# Personal AI Assistant — Setup Guide

## 1. Install dependencies

```bash
cd "C:\Telegram Agent"
pip install -r requirements.txt
```

## 2. Create your .env file

Copy `.env.example` to `.env` and fill in the values:

```
TELEGRAM_BOT_TOKEN=...
ANTHROPIC_API_KEY=...
TAVILY_API_KEY=...
```

## 3. Telegram Bot Token

1. Open Telegram → search **@BotFather**
2. Send `/newbot`
3. Follow prompts → copy the token into `.env`

## 4. Tavily API Key (free web search)

1. Go to https://tavily.com → sign up
2. Copy your API key → paste into `.env`

## 5. Gmail Setup

### Step A — Google Cloud Project

1. Go to https://console.cloud.google.com
2. Create a new project (e.g. "Personal Assistant")
3. Go to **APIs & Services → Library**
4. Search "Gmail API" → Enable it

### Step B — OAuth Credentials

1. Go to **APIs & Services → Credentials**
2. Click **Create Credentials → OAuth client ID**
3. Application type: **Desktop app**
4. Download the JSON → rename to `credentials.json`
5. Place `credentials.json` in `C:\Telegram Agent\`

### Step C — OAuth Consent Screen

1. Go to **APIs & Services → OAuth consent screen**
2. Set to **External**, fill in app name & your email
3. Add your test Gmail as a **Test user**

### Step D — First run (authenticate)

Run the bot once — a browser window will open asking you to log in to Gmail.
After approval, a token is saved to `data/gmail_token.json` automatically.

## 6. Run the bot

```bash
python bot.py
```

Then open Telegram, find your bot, and send `/start`.

---

## What you can say

- "Search for the latest news on AI agents"
- "What's in my inbox?"
- "Read that email from John"
- "Send an email to x@gmail.com about the meeting tomorrow"
- "Remember that Tavily has a 1000 req/month free tier"
- "Show me my notes tagged research"
- "Summarise this article: https://..."
