"""
Telegram bot for capturing free-form ideas into a Notion database.

Workflow:
1. Send any thought to the Telegram bot.
2. The bot creates a new Notion page in the ideas database.
3. The page title is derived from the first sentence / line.
4. The original message is saved under "Raw Capture" in the page body.
"""

from __future__ import annotations

import os
import re

from dotenv import load_dotenv
from notion_client import Client
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
IDEA_DATABASE_ID = os.getenv("IDEA_NOTION_DATABASE_ID") or os.getenv("NOTION_DATABASE_ID")
IDEA_TITLE_PROPERTY = os.getenv("IDEA_TITLE_PROPERTY", "Idea")
IDEA_STATUS_PROPERTY = os.getenv("IDEA_STATUS_PROPERTY", "Status")
IDEA_CATEGORY_PROPERTY = os.getenv("IDEA_CATEGORY_PROPERTY", "Category")
DEFAULT_STATUS = os.getenv("IDEA_DEFAULT_STATUS", "Raw")
DEFAULT_CATEGORY = os.getenv("IDEA_DEFAULT_CATEGORY", "Random")
MAX_TITLE_LENGTH = int(os.getenv("IDEA_MAX_TITLE_LENGTH", "60"))

for key, value in [
    ("TELEGRAM_BOT_TOKEN", TELEGRAM_TOKEN),
    ("NOTION_TOKEN", NOTION_TOKEN),
    ("IDEA_NOTION_DATABASE_ID or NOTION_DATABASE_ID", IDEA_DATABASE_ID),
]:
    if not value:
        raise SystemExit(f"ERROR: {key} must be set in .env")

notion = Client(auth=NOTION_TOKEN)


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def summarize_title(text: str, max_length: int = MAX_TITLE_LENGTH) -> str:
    """Use the first line / sentence as a lightweight title."""
    cleaned = text.strip()
    if not cleaned:
        return "Untitled idea"

    first_line = next((line.strip() for line in cleaned.splitlines() if line.strip()), cleaned)
    parts = re.split(r"[。！？!?；;\n]+", first_line, maxsplit=1)
    candidate = normalize_whitespace(parts[0]) or normalize_whitespace(first_line)

    if len(candidate) <= max_length:
        return candidate

    shortened = candidate[: max_length - 1].rstrip()
    return f"{shortened}…"


def build_body_blocks(raw_text: str) -> list[dict]:
    return [
        {
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "Raw Capture"}}]
            },
        },
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {"content": "把你当下想到的话原样丢进来，不用整理。"},
                    }
                ],
            },
        },
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": raw_text.strip()}}],
            },
        },
        {
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "Next Step"}}]
            },
        },
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": "如果这个想法值得继续，写一个最小的下一步动作。"
                        },
                    }
                ],
            },
        },
        {
            "object": "block",
            "type": "heading_2",
            "heading_2": {"rich_text": [{"type": "text", "text": {"content": "Notes"}}]},
        },
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {"content": "补充背景、判断、延伸方向。"},
                    }
                ],
            },
        },
    ]


def create_idea_page(raw_text: str) -> str:
    title = summarize_title(raw_text)
    properties = {
        IDEA_TITLE_PROPERTY: {"title": [{"text": {"content": title}}]},
        IDEA_STATUS_PROPERTY: {"select": {"name": DEFAULT_STATUS}},
        IDEA_CATEGORY_PROPERTY: {"multi_select": [{"name": DEFAULT_CATEGORY}]},
    }

    response = notion.pages.create(
        parent={"database_id": IDEA_DATABASE_ID},
        properties=properties,
        children=build_body_blocks(raw_text),
    )
    return response["url"]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "直接把任何想法发给我。我会把它存进 Notion，并自动生成标题和页面结构。"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if not text:
        await update.message.reply_text("发一段文字就行，我会把它作为一条想法存进 Notion。")
        return

    try:
        page_url = create_idea_page(text)
    except Exception as exc:
        await update.message.reply_text(f"存入失败：{exc}")
        return

    title = summarize_title(text)
    await update.message.reply_text(
        f"已存入想法库\n标题：{title}\n状态：{DEFAULT_STATUS}\n链接：{page_url}"
    )


def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Idea bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
