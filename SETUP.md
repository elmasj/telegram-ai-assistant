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
GMAIL_CREDENTIALS_PATH=credentials.json
GMAIL_TOKEN_PATH=data/gmail_token.json
```

## 3. Telegram Bot Token

1. Open Telegram → search **@BotFather**
2. Send `/newbot`
3. Follow prompts → copy the token into `.env`

## 4. Anthropic API Key

1. Go to https://console.anthropic.com
2. Create an API key → paste into `.env`

## 5. Tavily API Key (free web search)

1. Go to https://tavily.com → sign up (free tier available)
2. Copy your API key → paste into `.env`

## 6. Gmail Setup

### Step A — Google Cloud Project

1. Go to https://console.cloud.google.com
2. Create a new project (e.g. "Personal Assistant")
3. Go to **APIs & Services → Library**
4. Search **"Gmail API"** → Enable it

### Step B — OAuth Credentials

1. Go to **APIs & Services → Credentials**
2. Click **Create Credentials → OAuth client ID**
3. Application type: **Desktop app**
4. Download the JSON → rename to `credentials.json`
5. Place `credentials.json` in the project root

### Step C — OAuth Consent Screen

1. Go to **Google Auth Platform → Audience**
2. Set to **External**, fill in app name & your email
3. Under **Test users** → Add your Gmail address

### Step D — First run (authenticate)

Run the bot, then type `/inbox` in Telegram.
A browser window will open asking you to sign in to Gmail.
After approval, a token is saved to `data/gmail_token.json` automatically.

## 7. Run the bot

```bash
python bot.py
```

Then open Telegram, find your bot, and send `/start`.

---

## Access Control

By default only the owner can use the bot. The owner ID is set in `src/users.py`:

```python
OWNER_ID = your_telegram_user_id
```

To find your Telegram user ID, message [@userinfobot](https://t.me/userinfobot) on Telegram.

To add other users from the bot chat:
```
/adduser 123456789 John
```

---

## Power Outages (Macedonia only)

The bot connects directly to the Elektrodistribucija MK API to check planned outages.
No extra setup required — just use:

```
/outages              → today's outages across all Macedonia
/outages Скопје       → filtered by region
```

Or ask naturally: *"Are there any power cuts in Скопје tomorrow?"*

Supported regions: Скопје, Тетово, Охрид, Битола, Прилеп, Велес, Куманово, Штип, Струмица, Гостивар, Кичево, Струга, Кавадарци, Гевгелија, Кочани, Делчево, Кратово

---

## What you can say

- `"Search for the latest news on AI agents"`
- `"What's in my inbox?"`
- `"Send an email to x@gmail.com about the meeting tomorrow"`
- `"Remember that Tavily has a 1000 req/month free tier"`
- `"Show me my notes tagged research"`
- `"Summarise this article: https://..."`
- `"Send me world cup results at 9am tomorrow"`
- `"Are there any power cuts in Скопје this week?"`
