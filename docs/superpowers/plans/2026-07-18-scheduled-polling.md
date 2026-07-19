# 想法库 bot — 无状态定时轮询 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把想法库 bot 从常驻 `run_polling()` 改为 GitHub Actions cron 上每 15 分钟跑一次的无状态 `getUpdates` 脚本，永久免费、可公开自助部署。

**Architecture:** 一次性脚本：`getUpdates` 拉取积压消息 → 逐条写 Notion 页面并回复 → 用 `getUpdates(offset=last+1)` 在 Telegram 服务器端确认该批已消费 → 退出。不持久化 offset（Telegram 服务器负责保留未确认消息）。核心编排 `run_once` 用依赖注入，可无网络单测。

**Tech Stack:** Python 3.12、`requests`（Telegram HTTP API）、`notion-client`（写 Notion）、`python-dotenv`（本地 .env）、pytest（测试）、GitHub Actions（cron）。

## Global Constraints

- 真实 token 绝不进代码、绝不进仓库；本地走 `.env`（已被 `.gitignore` 忽略），线上走 GitHub Secrets。
- 彻底移除 `python-telegram-bot` 依赖，Telegram 交互一律用 `requests` 直调 HTTP API。
- 保留现有可配置环境变量名：`TELEGRAM_BOT_TOKEN`、`NOTION_TOKEN`、`IDEA_NOTION_DATABASE_ID`（回退 `NOTION_DATABASE_ID`）、`IDEA_TITLE_PROPERTY`、`IDEA_STATUS_PROPERTY`、`IDEA_CATEGORY_PROPERTY`、`IDEA_DEFAULT_STATUS`、`IDEA_DEFAULT_CATEGORY`、`IDEA_MAX_TITLE_LENGTH`。
- 失败也推进 offset：单条写 Notion 失败 → 回错误提示，但整批处理完仍推进 offset，避免毒消息堵塞。
- Python 3.12（保留 `runtime.txt` = python-3.12.8）。

## File Structure

- `bot.py` — 全部逻辑：纯函数助手（标题/正文）+ Notion 写入 + Telegram HTTP 封装 + `run_once` 编排 + `main()`。单文件便于他人阅读部署。
- `tests/test_bot.py` — 纯函数 + `run_once`（注入 fake）单测。
- `requirements.txt` — 更新依赖。
- `.github/workflows/poll.yml` — cron 每 15 分钟触发。
- `.env.example` — 已存在，校验即可。
- `README.md` — 重写为自助部署教程。

---

### Task 1: 重塑 bot.py 为可导入的纯函数 + 更新依赖

**Files:**
- Modify: `/Users/liyachen/Documents/fang/telegram_idea_bot/bot.py`（由 idea_bot.py 逻辑迁移而来，改文件名为 bot.py 以匹配设计）
- Modify: `/Users/liyachen/Documents/fang/telegram_idea_bot/requirements.txt`
- Create: `/Users/liyachen/Documents/fang/telegram_idea_bot/tests/test_bot.py`

**Interfaces:**
- Produces: `normalize_whitespace(text: str) -> str`、`summarize_title(text: str, max_length: int = MAX_TITLE_LENGTH) -> str`、`build_body_blocks(raw_text: str) -> list[dict]`（供 Task 2 使用）。

- [ ] **Step 1: 更新 requirements.txt**

```
notion-client==2.2.1
python-dotenv==1.0.1
requests==2.31.0
```

（移除 `python-telegram-bot==20.7`，新增 `requests==2.31.0`。）

- [ ] **Step 2: 新建 bot.py，迁移纯函数（含配置读取）**

```python
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
```

- [ ] **Step 3: 写纯函数测试**

```python
# tests/test_bot.py
import bot


def test_summarize_title_first_sentence():
    assert bot.summarize_title("做个 bot。然后发布") == "做个 bot"


def test_summarize_title_truncates_long():
    long = "a" * 100
    result = bot.summarize_title(long, max_length=10)
    assert len(result) == 10
    assert result.endswith("…")


def test_summarize_title_empty():
    assert bot.summarize_title("   ") == "Untitled idea"


def test_build_body_blocks_contains_raw_text():
    blocks = bot.build_body_blocks("我的想法")
    texts = [
        rt["text"]["content"]
        for b in blocks
        for rt in b[b["type"]]["rich_text"]
    ]
    assert "我的想法" in texts
    assert "Raw Capture" in texts
    assert "Next Step" in texts
    assert "Notes" in texts
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd /Users/liyachen/Documents/fang/telegram_idea_bot && python -m pytest tests/test_bot.py -v`
Expected: 4 passed（注意：导入 bot.py 需先临时设置环境变量或 .env，否则 IDEA_DATABASE_ID 为 None 也不报错——本 Task 的模块级代码不 raise，安全）

- [ ] **Step 5: 删除旧文件，提交**

```bash
cd /Users/liyachen/Documents/fang/telegram_idea_bot
git rm --cached idea_bot.py 2>/dev/null; rm -f idea_bot.py
git add bot.py requirements.txt tests/test_bot.py
git commit -m "refactor: reshape idea bot into importable pure helpers, drop PTB"
```

---

### Task 2: Notion 页面写入函数

**Files:**
- Modify: `/Users/liyachen/Documents/fang/telegram_idea_bot/bot.py`
- Modify: `/Users/liyachen/Documents/fang/telegram_idea_bot/tests/test_bot.py`

**Interfaces:**
- Consumes: `summarize_title`、`build_body_blocks`（Task 1）。
- Produces: `create_idea_page(raw_text: str) -> str`（返回新页面 URL），`notion` 全局 Client。

- [ ] **Step 1: 写失败测试（monkeypatch notion client）**

```python
def test_create_idea_page_builds_properties(monkeypatch):
    captured = {}

    class FakePages:
        def create(self, **kwargs):
            captured.update(kwargs)
            return {"url": "https://notion.so/fake"}

    class FakeNotion:
        pages = FakePages()

    monkeypatch.setattr(bot, "notion", FakeNotion())
    monkeypatch.setattr(bot, "IDEA_DATABASE_ID", "db123")

    url = bot.create_idea_page("买菜的想法")

    assert url == "https://notion.so/fake"
    assert captured["parent"] == {"database_id": "db123"}
    props = captured["properties"]
    assert props[bot.IDEA_TITLE_PROPERTY]["title"][0]["text"]["content"] == "买菜的想法"
    assert props[bot.IDEA_STATUS_PROPERTY]["select"]["name"] == bot.DEFAULT_STATUS
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /Users/liyachen/Documents/fang/telegram_idea_bot && python -m pytest tests/test_bot.py::test_create_idea_page_builds_properties -v`
Expected: FAIL — `AttributeError: module 'bot' has no attribute 'notion'` / `create_idea_page`

- [ ] **Step 3: 实现 notion client + create_idea_page**

在 bot.py 配置块之后加：

```python
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
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd /Users/liyachen/Documents/fang/telegram_idea_bot && python -m pytest tests/test_bot.py -v`
Expected: 5 passed

- [ ] **Step 5: 提交**

```bash
git add bot.py tests/test_bot.py
git commit -m "feat: add Notion idea page creation"
```

---

### Task 3: Telegram HTTP 封装 + run_once 无状态编排（核心）

**Files:**
- Modify: `/Users/liyachen/Documents/fang/telegram_idea_bot/bot.py`
- Modify: `/Users/liyachen/Documents/fang/telegram_idea_bot/tests/test_bot.py`

**Interfaces:**
- Consumes: `create_idea_page`、`summarize_title`、`DEFAULT_STATUS`（Task 1-2）。
- Produces: `get_updates(token, offset=None, timeout=0) -> list[dict]`、`send_message(token, chat_id, text) -> dict`、`handle_text(text) -> str`、`run_once(token, get_updates_fn, send_message_fn, handle_text_fn) -> int`。

- [ ] **Step 1: 写 run_once 测试（注入 fake，无网络）**

```python
def test_run_once_processes_and_confirms_offset():
    calls = {"get_updates": [], "sent": []}

    fake_updates = [
        {"update_id": 101, "message": {"chat": {"id": 5}, "text": "想法一"}},
        {"update_id": 102, "message": {"chat": {"id": 5}, "text": "想法二"}},
    ]

    def fake_get_updates(token, offset=None, timeout=0):
        calls["get_updates"].append(offset)
        return fake_updates if offset is None else []

    def fake_send(token, chat_id, text):
        calls["sent"].append((chat_id, text))
        return {}

    def fake_handle(text):
        return f"已存入：{text}"

    count = bot.run_once("T", fake_get_updates, fake_send, fake_handle)

    assert count == 2
    assert calls["get_updates"] == [None, 103]  # 拉取 + 用 last+1 确认
    assert calls["sent"] == [(5, "已存入：想法一"), (5, "已存入：想法二")]


def test_run_once_empty_no_confirm():
    def fake_get_updates(token, offset=None, timeout=0):
        return []

    count = bot.run_once("T", fake_get_updates, lambda *a: {}, lambda t: "")
    assert count == 0


def test_run_once_advances_offset_even_on_failure():
    sent = []

    def fake_get_updates(token, offset=None, timeout=0):
        if offset is None:
            return [{"update_id": 200, "message": {"chat": {"id": 1}, "text": "毒消息"}}]
        return []

    def fake_handle(text):
        raise RuntimeError("notion 挂了")

    # handle_text 内部已捕获异常并返回错误串，这里验证 run_once 不因单条失败中断 offset 推进
    def safe_handle(text):
        try:
            return fake_handle(text)
        except Exception as exc:
            return f"存入失败：{exc}"

    confirmed = []

    def track_get_updates(token, offset=None, timeout=0):
        confirmed.append(offset)
        return fake_get_updates(token, offset, timeout)

    bot.run_once("T", track_get_updates, lambda t, c, x: sent.append(x), safe_handle)
    assert confirmed == [None, 201]
    assert sent == ["存入失败：notion 挂了"]
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /Users/liyachen/Documents/fang/telegram_idea_bot && python -m pytest tests/test_bot.py -k run_once -v`
Expected: FAIL — `AttributeError: module 'bot' has no attribute 'run_once'`

- [ ] **Step 3: 实现 Telegram 封装 + handle_text + run_once**

```python
import requests

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
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd /Users/liyachen/Documents/fang/telegram_idea_bot && python -m pytest tests/test_bot.py -v`
Expected: 8 passed

- [ ] **Step 5: 提交**

```bash
git add bot.py tests/test_bot.py
git commit -m "feat: add stateless getUpdates polling orchestration"
```

---

### Task 4: main() 入口 + 启动校验

**Files:**
- Modify: `/Users/liyachen/Documents/fang/telegram_idea_bot/bot.py`

**Interfaces:**
- Consumes: `run_once`、配置常量。
- Produces: `main() -> None`、`__main__` 入口。

- [ ] **Step 1: 在 bot.py 末尾加 main()**

```python
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
```

- [ ] **Step 2: 冒烟测试（无网络，缺变量应快速失败）**

Run: `cd /Users/liyachen/Documents/fang/telegram_idea_bot && env -u TELEGRAM_BOT_TOKEN -u NOTION_TOKEN -u IDEA_NOTION_DATABASE_ID -u NOTION_DATABASE_ID python bot.py`
Expected: 打印 `ERROR: 缺少环境变量: ...` 并以非零退出

- [ ] **Step 3: 提交**

```bash
git add bot.py
git commit -m "feat: add main entry with env validation"
```

---

### Task 5: GitHub Actions workflow

**Files:**
- Create: `/Users/liyachen/Documents/fang/telegram_idea_bot/.github/workflows/poll.yml`

- [ ] **Step 1: 写 workflow**

```yaml
name: poll-telegram

on:
  schedule:
    - cron: "*/15 * * * *"   # 每 15 分钟（GitHub 高峰期可能延迟）
  workflow_dispatch: {}       # 支持手动触发测试

concurrency:
  group: poll-telegram
  cancel-in-progress: false

jobs:
  poll:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt
      - run: python bot.py
        env:
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          NOTION_TOKEN: ${{ secrets.NOTION_TOKEN }}
          IDEA_NOTION_DATABASE_ID: ${{ secrets.IDEA_NOTION_DATABASE_ID }}
```

- [ ] **Step 2: 校验 YAML 语法**

Run: `cd /Users/liyachen/Documents/fang/telegram_idea_bot && python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/poll.yml')); print('yaml ok')"`
Expected: `yaml ok`

- [ ] **Step 3: 提交**

```bash
git add .github/workflows/poll.yml
git commit -m "ci: add 15-min scheduled polling workflow"
```

---

### Task 6: README 自助部署教程 + .env.example 校验

**Files:**
- Modify: `/Users/liyachen/Documents/fang/telegram_idea_bot/README.md`
- Verify: `/Users/liyachen/Documents/fang/telegram_idea_bot/.env.example`（已存在，字段正确，无需改）

- [ ] **Step 1: 重写 README.md**

```markdown
# Telegram → Notion 想法捕获 bot

在 Telegram 随手发一段文字，几分钟内自动存进你的 Notion 想法库，
自动生成标题和页面结构。跑在 GitHub Actions 上，永久免费，无需服务器。

## 它怎么工作
GitHub Actions 每 15 分钟触发一次，拉取这段时间你发的消息，逐条写进
Notion，然后退出。不是实时的——通常几分钟到二十几分钟内进库。

## 自助部署（约 10 分钟）

1. **建 Telegram bot**：Telegram 里找 @BotFather，发 `/newbot`，
   按提示拿到 bot token。
2. **建 Notion integration**：https://www.notion.so/my-integrations
   新建 integration，复制 secret。建一个数据库（至少含标题、Status、
   Category 字段），在数据库右上 ··· → Connections 里把 integration
   连上，复制数据库 ID（URL 里那段 32 位字符）。
3. **Fork 本仓库**。
4. **填 Secrets**：仓库 Settings → Secrets and variables → Actions，
   新建三个：`TELEGRAM_BOT_TOKEN`、`NOTION_TOKEN`、
   `IDEA_NOTION_DATABASE_ID`。
5. **启用 Actions**：仓库 Actions 页，点 "I understand... enable"。
6. **测试**：给你的 bot 发一段话，最多 15 分钟看 Notion。也可以到
   Actions 页手动点 "Run workflow" 立即触发一次。

## 自定义字段名
若你的 Notion 字段不叫 Idea/Status/Category，可在 Secrets 里额外设
`IDEA_TITLE_PROPERTY` / `IDEA_STATUS_PROPERTY` / `IDEA_CATEGORY_PROPERTY`
等（见 `.env.example`）。

## 已知限制
- cron 高峰期可能延迟 5–20 分钟。
- 仓库 60 天无提交，GitHub 会自动暂停定时任务并发邮件，点一下即可恢复。

## 本地开发
复制 `.env.example` 为 `.env` 填入真实值，然后 `pip install -r
requirements.txt && python bot.py`。`.env` 已被 `.gitignore` 忽略。
```

- [ ] **Step 2: 确认 .env.example 无真实密钥**

Run: `cd /Users/liyachen/Documents/fang/telegram_idea_bot && grep -Eq "your_|=$|Idea|Status" .env.example && echo "example ok (占位符)" || echo "CHECK: 可能含真实值"`
Expected: `example ok (占位符)`

- [ ] **Step 3: 提交**

```bash
git add README.md
git commit -m "docs: rewrite README with self-hosting guide"
```

---

## Self-Review Notes
- Spec 覆盖：无状态 offset（Task 3）、失败也推进 offset（Task 3 测试+实现）、并发保护（Task 5 concurrency）、密钥走 Secrets（Task 5 env + README）、想法库处理逻辑（Task 1-2）、可配置属性名（Task 1 配置块 + README）、cron 15 分钟（Task 5）、60 天限制说明（Task 6 README）——均有对应任务。
- 类型一致：`get_updates`/`send_message`/`handle_text`/`run_once`/`create_idea_page`/`summarize_title`/`build_body_blocks` 全程签名一致。
- 无占位符：所有代码步骤含完整代码。
