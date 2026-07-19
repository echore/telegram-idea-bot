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


def test_handle_text_returns_error_string_on_failure(monkeypatch):
    def fake_create_idea_page(text):
        raise RuntimeError("boom")

    monkeypatch.setattr(bot, "create_idea_page", fake_create_idea_page)

    result = bot.handle_text("some idea")

    assert isinstance(result, str)
    assert result.startswith("存入失败：")


def test_handle_text_returns_success_message(monkeypatch):
    def fake_create_idea_page(text):
        return "https://notion.so/x"

    monkeypatch.setattr(bot, "create_idea_page", fake_create_idea_page)

    result = bot.handle_text("买菜")

    assert "已存入想法库" in result
    assert "https://notion.so/x" in result


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
