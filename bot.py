"""Telegram → Notion 想法捕获 bot（无状态定时轮询版）。

列名不写死：每次运行读一遍数据库结构，按属性「类型」认列（标题=唯一 title 列，
状态=单选列，分类=多选列，链接=URL 列）。中英文库、随便改列名都能用，不用配环境
变量。原来的环境变量降级为「可选的手动指定」，仅在自动认错时兜底。
"""
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

# 都可选：不设 -> 按类型自动探测；设了 -> 手动指定，覆盖探测。
IDEA_TITLE_PROPERTY = os.getenv("IDEA_TITLE_PROPERTY")
IDEA_STATUS_PROPERTY = os.getenv("IDEA_STATUS_PROPERTY")
IDEA_CATEGORY_PROPERTY = os.getenv("IDEA_CATEGORY_PROPERTY")
IDEA_URL_PROPERTY = os.getenv("IDEA_URL_PROPERTY")
DEFAULT_STATUS = os.getenv("IDEA_DEFAULT_STATUS")  # 不设 -> 取状态列第一个选项
DEFAULT_CATEGORY = os.getenv("IDEA_DEFAULT_CATEGORY")  # 不设 -> 留空，事后自己标
MAX_TITLE_LENGTH = int(os.getenv("IDEA_MAX_TITLE_LENGTH", "60"))

# 同类型多列时按名字关键词猜；命中不了就跳过那一列，绝不乱写。
STATUS_HINTS = ("status", "state", "状态", "狀態", "进度", "進度", "阶段", "階段")
CATEGORY_HINTS = ("category", "categories", "tag", "tags", "分类", "分類", "类别", "類別", "标签", "標籤", "类型", "類型")
URL_HINTS = ("url", "link", "链接", "連結", "网址", "網址", "地址")

URL_RE = re.compile(r"https?://[^\s]+")


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


def extract_url(text: str) -> str | None:
    """消息里第一个 http(s) 链接，没有则 None。"""
    match = URL_RE.search(text)
    return match.group(0) if match else None


def _pick_by_type(schema: dict, wanted_type: str, hints: tuple, override: str | None) -> str | None:
    """在 schema 里认出某类型的列。override 若存在于 schema 则优先；否则按类型探测：
    唯一一列直接用；多列按名字关键词命中；命中不了返回 None（跳过，不乱猜）。"""
    if override and override in schema:
        return override
    candidates = [name for name, prop in schema.items() if prop.get("type") == wanted_type]
    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) > 1:
        for name in candidates:
            low = name.lower()
            if any(hint in low for hint in hints):
                return name
        return None
    return None


def resolve_columns(schema: dict) -> dict:
    """读 Notion 数据库结构，按类型认列，返回一份解析结果。纯函数，离线可测。"""
    title_prop = _pick_by_type(schema, "title", (), IDEA_TITLE_PROPERTY)
    if title_prop is None:  # 每个库都有唯一 title 列，兜底防御
        title_prop = next((n for n, p in schema.items() if p.get("type") == "title"), None)

    status_prop = _pick_by_type(schema, "select", STATUS_HINTS, IDEA_STATUS_PROPERTY)
    category_prop = _pick_by_type(schema, "multi_select", CATEGORY_HINTS, IDEA_CATEGORY_PROPERTY)
    url_prop = _pick_by_type(schema, "url", URL_HINTS, IDEA_URL_PROPERTY)

    if DEFAULT_STATUS:
        status_value = DEFAULT_STATUS
    elif status_prop:
        options = schema[status_prop].get("select", {}).get("options", [])
        status_value = options[0]["name"] if options else None
    else:
        status_value = None

    return {
        "title_prop": title_prop,
        "status_prop": status_prop,
        "status_value": status_value,
        "category_prop": category_prop,
        "category_value": DEFAULT_CATEGORY,  # 默认 None -> 留空
        "url_prop": url_prop,
    }


def build_page_properties(resolved: dict, raw_text: str, url: str | None = None) -> dict:
    """按认到的列拼 Notion 页面属性。认不到的列不出现在 payload 里。"""
    properties = {
        resolved["title_prop"]: {"title": [{"text": {"content": summarize_title(raw_text)}}]},
    }
    if resolved["status_prop"] and resolved["status_value"]:
        properties[resolved["status_prop"]] = {"select": {"name": resolved["status_value"]}}
    if resolved["category_prop"] and resolved["category_value"]:
        properties[resolved["category_prop"]] = {"multi_select": [{"name": resolved["category_value"]}]}
    if url and resolved["url_prop"]:
        properties[resolved["url_prop"]] = {"url": url}
    return properties


notion = Client(auth=NOTION_TOKEN) if NOTION_TOKEN else None

_resolved_cache: dict | None = None


def reset_schema_cache() -> None:
    global _resolved_cache
    _resolved_cache = None


def get_resolved_columns() -> dict:
    """每次运行只读一遍结构并缓存，后续消息复用。"""
    global _resolved_cache
    if _resolved_cache is None:
        schema = notion.databases.retrieve(database_id=IDEA_DATABASE_ID)["properties"]
        _resolved_cache = resolve_columns(schema)
    return _resolved_cache


def create_idea_page(raw_text: str) -> dict:
    resolved = get_resolved_columns()
    properties = build_page_properties(resolved, raw_text, url=extract_url(raw_text))
    response = notion.pages.create(
        parent={"database_id": IDEA_DATABASE_ID},
        properties=properties,
        children=build_body_blocks(raw_text),
    )
    return {
        "url": response["url"],
        "title": summarize_title(raw_text),
        "status": resolved["status_value"] if resolved["status_prop"] else None,
    }


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
        result = create_idea_page(text)
    except Exception as exc:  # 失败也要回一句，让用户可手动补发
        return f"存入失败：{exc}"
    lines = ["已存入想法库", f"标题：{result['title']}"]
    if result.get("status"):  # 认不到状态列就不显示，避免「状态：None」噪音
        lines.append(f"状态：{result['status']}")
    lines.append(f"链接：{result['url']}")
    return "\n".join(lines)


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
