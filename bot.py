"""Telegram → Notion 想法捕获 bot（无状态定时轮询版）。"""
from __future__ import annotations

import os
import re

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
