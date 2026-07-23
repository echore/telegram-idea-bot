import bot


# ---------- helpers ----------

def make_schema(title="Idea", selects=None, multiselects=None, urls=None):
    """Build a fake Notion `properties` schema (name -> {type, ...})."""
    schema = {title: {"type": "title", "title": {}}}
    for name, options in (selects or {}).items():
        schema[name] = {"type": "select", "select": {"options": [{"name": o} for o in options]}}
    for name, options in (multiselects or {}).items():
        schema[name] = {"type": "multi_select", "multi_select": {"options": [{"name": o} for o in options]}}
    for name in (urls or []):
        schema[name] = {"type": "url", "url": {}}
    return schema


# ---------- title / body (unchanged behavior) ----------

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


# ---------- resolve_columns: detect by TYPE, not name ----------

def test_resolve_title_english_and_chinese(monkeypatch):
    monkeypatch.setattr(bot, "IDEA_TITLE_PROPERTY", None)
    assert bot.resolve_columns(make_schema(title="Idea"))["title_prop"] == "Idea"
    assert bot.resolve_columns(make_schema(title="想法"))["title_prop"] == "想法"


def test_resolve_status_single_select_uses_first_option(monkeypatch):
    monkeypatch.setattr(bot, "IDEA_STATUS_PROPERTY", None)
    monkeypatch.setattr(bot, "DEFAULT_STATUS", None)

    cn = bot.resolve_columns(make_schema(selects={"状态": ["待分析", "发展中"]}))
    assert cn["status_prop"] == "状态"
    assert cn["status_value"] == "待分析"

    en = bot.resolve_columns(make_schema(selects={"Status": ["To Review", "Developing"]}))
    assert en["status_prop"] == "Status"
    assert en["status_value"] == "To Review"


def test_resolve_category_single_multiselect(monkeypatch):
    monkeypatch.setattr(bot, "IDEA_CATEGORY_PROPERTY", None)
    resolved = bot.resolve_columns(make_schema(multiselects={"分类": ["产品", "生活"]}))
    assert resolved["category_prop"] == "分类"


def test_resolve_two_selects_picks_by_keyword(monkeypatch):
    monkeypatch.setattr(bot, "IDEA_STATUS_PROPERTY", None)
    monkeypatch.setattr(bot, "DEFAULT_STATUS", None)

    cn = bot.resolve_columns(make_schema(selects={"状态": ["待分析"], "优先级": ["高"]}))
    assert cn["status_prop"] == "状态"

    en = bot.resolve_columns(make_schema(selects={"Priority": ["High"], "Status": ["To Review"]}))
    assert en["status_prop"] == "Status"


def test_resolve_two_selects_no_keyword_skips(monkeypatch):
    """Ambiguous: two selects, neither looks like a status -> skip, never guess."""
    monkeypatch.setattr(bot, "IDEA_STATUS_PROPERTY", None)
    monkeypatch.setattr(bot, "DEFAULT_STATUS", None)
    resolved = bot.resolve_columns(make_schema(selects={"甲": ["一"], "乙": ["二"]}))
    assert resolved["status_prop"] is None
    assert resolved["status_value"] is None


def test_resolve_missing_select_no_error(monkeypatch):
    monkeypatch.setattr(bot, "IDEA_STATUS_PROPERTY", None)
    monkeypatch.setattr(bot, "DEFAULT_STATUS", None)
    resolved = bot.resolve_columns(make_schema())  # title only
    assert resolved["status_prop"] is None
    assert resolved["category_prop"] is None
    assert resolved["url_prop"] is None


def test_resolve_url_single(monkeypatch):
    monkeypatch.setattr(bot, "IDEA_URL_PROPERTY", None)
    resolved = bot.resolve_columns(make_schema(urls=["链接"]))
    assert resolved["url_prop"] == "链接"


def test_resolve_env_override_wins(monkeypatch):
    monkeypatch.setattr(bot, "IDEA_STATUS_PROPERTY", "优先级")
    monkeypatch.setattr(bot, "DEFAULT_STATUS", None)
    # two selects; override names the non-keyword one explicitly
    resolved = bot.resolve_columns(make_schema(selects={"状态": ["待分析"], "优先级": ["高"]}))
    assert resolved["status_prop"] == "优先级"


def test_resolve_default_status_env_override(monkeypatch):
    monkeypatch.setattr(bot, "IDEA_STATUS_PROPERTY", None)
    monkeypatch.setattr(bot, "DEFAULT_STATUS", "收件箱")
    resolved = bot.resolve_columns(make_schema(selects={"状态": ["待分析", "发展中"]}))
    assert resolved["status_value"] == "收件箱"


# ---------- build_page_properties ----------

def test_build_props_title_only_when_status_missing():
    resolved = {
        "title_prop": "想法", "status_prop": None, "status_value": None,
        "category_prop": None, "category_value": None, "url_prop": None,
    }
    props = bot.build_page_properties(resolved, "买菜")
    assert list(props.keys()) == ["想法"]
    assert props["想法"]["title"][0]["text"]["content"] == "买菜"


def test_build_props_sets_status_first_option():
    resolved = {
        "title_prop": "Idea", "status_prop": "Status", "status_value": "To Review",
        "category_prop": None, "category_value": None, "url_prop": None,
    }
    props = bot.build_page_properties(resolved, "an idea")
    assert props["Status"]["select"]["name"] == "To Review"


def test_build_props_category_empty_by_default():
    resolved = {
        "title_prop": "想法", "status_prop": "状态", "status_value": "待分析",
        "category_prop": "分类", "category_value": None, "url_prop": None,
    }
    props = bot.build_page_properties(resolved, "想法")
    assert "分类" not in props  # left empty; user tags later


def test_build_props_writes_url_when_present():
    resolved = {
        "title_prop": "想法", "status_prop": None, "status_value": None,
        "category_prop": None, "category_value": None, "url_prop": "链接",
    }
    props = bot.build_page_properties(resolved, "看看 https://example.com", url="https://example.com")
    assert props["链接"]["url"] == "https://example.com"


def test_build_props_url_ignored_when_no_url_column():
    resolved = {
        "title_prop": "想法", "status_prop": None, "status_value": None,
        "category_prop": None, "category_value": None, "url_prop": None,
    }
    props = bot.build_page_properties(resolved, "看看 https://example.com", url="https://example.com")
    assert list(props.keys()) == ["想法"]  # nothing lost: text still in title + body


# ---------- extract_url ----------

def test_extract_url_finds_first():
    assert bot.extract_url("看看 https://a.com 和 http://b.com") == "https://a.com"


def test_extract_url_none_when_absent():
    assert bot.extract_url("就是个普通想法") is None


# ---------- create_idea_page: reads schema once, then builds ----------

def _fake_notion(schema):
    captured = {}
    calls = {"retrieve": 0}

    class FakeDatabases:
        def retrieve(self, **kwargs):
            calls["retrieve"] += 1
            return {"properties": schema}

    class FakePages:
        def create(self, **kwargs):
            captured.update(kwargs)
            return {"url": "https://notion.so/fake"}

    class FakeNotion:
        databases = FakeDatabases()
        pages = FakePages()

    return FakeNotion(), captured, calls


def test_create_idea_page_auto_detects_and_caches(monkeypatch):
    schema = make_schema(title="想法", selects={"状态": ["待分析", "发展中"]},
                         multiselects={"分类": ["产品"]})
    fake, captured, calls = _fake_notion(schema)
    monkeypatch.setattr(bot, "notion", fake)
    monkeypatch.setattr(bot, "IDEA_DATABASE_ID", "db123")
    monkeypatch.setattr(bot, "IDEA_TITLE_PROPERTY", None)
    monkeypatch.setattr(bot, "IDEA_STATUS_PROPERTY", None)
    monkeypatch.setattr(bot, "IDEA_CATEGORY_PROPERTY", None)
    monkeypatch.setattr(bot, "DEFAULT_STATUS", None)
    monkeypatch.setattr(bot, "DEFAULT_CATEGORY", None)
    bot.reset_schema_cache()

    result = bot.create_idea_page("买菜的想法")
    bot.create_idea_page("第二条想法")

    assert result["url"] == "https://notion.so/fake"
    assert result["title"] == "买菜的想法"
    assert result["status"] == "待分析"
    assert captured["parent"] == {"database_id": "db123"}
    assert captured["properties"]["想法"]["title"][0]["text"]["content"] == "第二条想法"
    assert captured["properties"]["状态"]["select"]["name"] == "待分析"
    assert "分类" not in captured["properties"]  # empty by default
    assert calls["retrieve"] == 1  # schema fetched once per run, not per message


# ---------- run_once (unchanged) ----------

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
    assert calls["get_updates"] == [None, 103]
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

    def safe_handle(text):
        return f"存入失败：boom"

    confirmed = []

    def track_get_updates(token, offset=None, timeout=0):
        confirmed.append(offset)
        return fake_get_updates(token, offset, timeout)

    bot.run_once("T", track_get_updates, lambda t, c, x: sent.append(x), safe_handle)
    assert confirmed == [None, 201]
    assert sent == ["存入失败：boom"]


# ---------- handle_text: reply adapts to what was actually set ----------

def test_handle_text_returns_error_string_on_failure(monkeypatch):
    def fake_create_idea_page(text):
        raise RuntimeError("boom")

    monkeypatch.setattr(bot, "create_idea_page", fake_create_idea_page)
    result = bot.handle_text("some idea")
    assert isinstance(result, str)
    assert result.startswith("存入失败：")


def test_handle_text_success_with_status(monkeypatch):
    monkeypatch.setattr(bot, "create_idea_page",
                        lambda text: {"url": "https://notion.so/x", "title": "买菜", "status": "待分析"})
    result = bot.handle_text("买菜")
    assert "已存入想法库" in result
    assert "https://notion.so/x" in result
    assert "待分析" in result


def test_handle_text_success_omits_status_when_none(monkeypatch):
    monkeypatch.setattr(bot, "create_idea_page",
                        lambda text: {"url": "https://notion.so/x", "title": "买菜", "status": None})
    result = bot.handle_text("买菜")
    assert "已存入想法库" in result
    assert "状态" not in result  # no "状态：None" noise
