from ld_audit.formatters import strip_rich_markup, to_json, to_markdown


def test_strip_rich_markup():
    text = "[bold green]ON[/bold green]"
    assert strip_rich_markup(text) == "ON"

    text = "[red]OFF[/red] (staging)"
    assert strip_rich_markup(text) == "OFF (staging)"


def test_to_markdown():
    headers = ["Col1", "Col2"]
    rows = [
        [
            "Key1",
            "[green]ON[/green]",
            "John",
            "2023-01-01",
            "2023-01-02",
            "https://app.launchdarkly.com/test-project/production/features/Key1",
        ],
    ]

    markdown = to_markdown(headers, rows)

    assert "| Col1 | Col2 |" in markdown
    assert "| --- | --- |" in markdown
    assert (
        "| [Key1](https://app.launchdarkly.com/test-project/production/features/Key1) | ON | John | 2023-01-01 | 2023-01-02 |"
        in markdown
    )


def test_to_json():
    headers = ["Col1", "Col2"]
    rows = [
        [
            "Key1",
            "[green]ON[/green]",
            "John",
            "2023-01-01",
            "2023-01-02",
            "https://app.launchdarkly.com/test-project/production/features/Key1",
        ],
    ]

    json_str = to_json(headers, rows)
    import json

    data = json.loads(json_str)

    assert len(data) == 1
    assert data[0]["key"] == "Key1"
    assert data[0]["environments"] == "ON"
    assert data[0]["maintainer"] == "John"
    assert data[0]["url"] == "https://app.launchdarkly.com/test-project/production/features/Key1"
