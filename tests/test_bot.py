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
