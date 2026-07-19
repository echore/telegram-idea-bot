# Telegram Idea Bot

This project is a standalone Telegram-to-Notion idea capture bot.

## What it does

Send any free-form idea to a Telegram bot. The bot creates a new page in a Notion ideas database.

For each message:

1. It uses the first line or first sentence as the page title.
2. It creates a new page in the ideas database.
3. It sets the default database properties:
   - `Status = Raw`
   - `Category = Random`
4. It writes the original message into the page body under:
   - `Raw Capture`
   - `Next Step`
   - `Notes`

## Files

- `idea_bot.py`: main bot entrypoint
- `requirements.txt`: Python dependencies
- `runtime.txt`: pinned Python runtime for deployment
- `.env.example`: environment variable template
- `.gitignore`: local ignore rules
- `README.md`: setup and deployment overview
- `NOTES.md`: handoff notes
- `IMPLEMENTATION_GUIDE.md`: design and implementation details

## Required environment variables

- `TELEGRAM_BOT_TOKEN`
- `NOTION_TOKEN`
- `IDEA_NOTION_DATABASE_ID`

Optional variables are already shown in `.env.example`.

## Local setup

1. Copy `.env.example` to `.env`.
2. Fill in the required environment variables.
3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Run the bot:

```bash
python idea_bot.py
```

## Railway deployment

This bot is intended to run as a long-lived Railway service.

Use these settings:

- Start command: `python idea_bot.py`
- Python runtime: from `runtime.txt`
- Variables: set `TELEGRAM_BOT_TOKEN`, `NOTION_TOKEN`, and `IDEA_NOTION_DATABASE_ID` in Railway

## Safety note

Do not commit `.env`.
Do not paste tokens or secrets into chat logs.
Do not hardcode real database IDs or API credentials into public config files.
