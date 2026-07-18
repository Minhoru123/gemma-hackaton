from app.ingest import strip_frontmatter


def test_strips_yaml_block():
    text = "---\ncase_name: \"Meyer\"\nyear: 1923\n---\n\nThe opinion text."
    assert strip_frontmatter(text) == "The opinion text."


def test_leaves_plain_text_alone():
    assert strip_frontmatter("No frontmatter here.") == "No frontmatter here."


def test_leaves_unclosed_block_alone():
    text = "---\nnot closed"
    assert strip_frontmatter(text) == text
