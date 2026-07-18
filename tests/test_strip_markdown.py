from app.ollama_client import strip_markdown


def test_strips_the_artifacts_seen_in_real_answers():
    raw = ('The context mentions: * **Motions to Dismiss:** a mention of '
           '"24\\_MOTION TO DISMISS.md". * **Complaints:** the '
           '"12\\_FIRST\\_AMENDED\\_COMPLAINT.pdf". Cited: > 24 _See_ Compl.')
    out = strip_markdown(raw)
    assert "**" not in out
    assert "\\_" not in out
    assert "24_MOTION TO DISMISS.md" in out
    assert "12_FIRST_AMENDED_COMPLAINT.pdf" in out
    assert "_See_" not in out and "See Compl." in out


def test_bullets_headings_and_code_flatten():
    raw = "## Summary\n* first point\n- second point\n`Rule 12(b)(6)` applies"
    out = strip_markdown(raw)
    assert out.splitlines()[0] == "Summary"
    assert "• first point" in out and "• second point" in out
    assert "`" not in out and "Rule 12(b)(6) applies" in out


def test_snake_case_filenames_survive_italic_stripping():
    assert strip_markdown("see 12_FIRST_AMENDED_COMPLAINT.pdf") == \
        "see 12_FIRST_AMENDED_COMPLAINT.pdf"


def test_plain_prose_unchanged():
    text = "You have 14 days to respond. The hearing is on August 3, 2026."
    assert strip_markdown(text) == text
