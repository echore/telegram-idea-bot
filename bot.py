"""Telegram → Notion 想法捕获 bot（无状态定时轮询版）。"""
from __future__ import annotations

import os
import re

import requests
from dotenv import load_dotenv
from notion_client import Client

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


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def summarize_title(text: str, max_length: int = MAX_TITLE_LENGTH) -> str:
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
    def para(content: str) -> dict:
        return {
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": content}}]},
        }

    def heading(content: str) -> dict:
        return {
            "object": "block",
            "type": "heading_2",
            "heading_2": {"rich_text": [{"type": "text", "text": {"content": content}}]},
        }

    return [
        heading("Raw Capture"),
        para("把你当下想到的话原样丢进来，不用整理。"),
        para(raw_text.strip()),
        heading("Next Step"),
        para("如果这个想法值得继续，写一个最小的下一步动作。"),
        heading("Notes"),
        para("补充背景、判断、延伸方向。"),
    ]


notion = Client(auth=NOTION_TOKEN) if NOTION_TOKEN else None


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


TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"


def get_updates(token, offset=None, timeout=0):
    params = {"timeout": timeout, "allowed_updates": '["message"]'}
    if offset is not None:
        params["offset"] = offset
    resp = requests.get(TELEGRAM_API.format(token=token, method="getUpdates"), params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()["result"]


def send_message(token, chat_id, text):
    resp = requests.post(
        TELEGRAM_API.format(token=token, method="sendMessage"),
        json={"chat_id": chat_id, "text": text},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def handle_text(text: str) -> str:
    try:
        page_url = create_idea_page(text)
    except Exception as exc:  # 失败也要回一句，让用户可手动补发
        return f"存入失败：{exc}"
    return f"已存入想法库\n标题：{summarize_title(text)}\n状态：{DEFAULT_STATUS}\n链接：{page_url}"


def run_once(token, get_updates_fn=get_updates, send_message_fn=send_message, handle_text_fn=handle_text) -> int:
    updates = get_updates_fn(token, offset=None)
    if not updates:
        return 0
    last_update_id = None
    for update in updates:
        last_update_id = update["update_id"]
        message = update.get("message")
        if not message:
            continue
        chat_id = message["chat"]["id"]
        text = (message.get("text") or "").strip()
        if not text:
            send_message_fn(token, chat_id, "发一段文字就行，我会把它作为一条想法存进 Notion。")
            continue
        send_message_fn(token, chat_id, handle_text_fn(text))
    if last_update_id is not None:  # 确认该批已消费，失败与否都推进
        get_updates_fn(token, offset=last_update_id + 1)
    return len(updates)


def main():
    missing = [
        name
        for name, value in [
            ("TELEGRAM_BOT_TOKEN", TELEGRAM_TOKEN),
            ("NOTION_TOKEN", NOTION_TOKEN),
            ("IDEA_NOTION_DATABASE_ID or NOTION_DATABASE_ID", IDEA_DATABASE_ID),
        ]
        if not value
    ]
    if missing:
        raise SystemExit(f"ERROR: 缺少环境变量: {', '.join(missing)}")
    count = run_once(TELEGRAM_TOKEN)
    print(f"processed {count} update(s)")


if __name__ == "__main__":
    main()
