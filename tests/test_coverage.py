from app import coverage

PARENT = """MOTION FOR SUMMARY JUDGMENT

I. Plaintiff's claims are precluded.
Some body text that should not become a contention.
II. Plaintiff lacks standing.
A. The injury is not traceable.
"""


def test_seed_map_extracts_headings_not_body():
    text = coverage.seed_map(PARENT, "their_msj.pdf")
    assert "- [ ] Plaintiff's claims are precluded." in text
    assert "- [ ] Plaintiff lacks standing." in text
    assert "- [ ] The injury is not traceable." in text
    assert "- [ ] MOTION FOR SUMMARY JUDGMENT" in text
    assert "Some body text" not in text


def test_unanswered_lists_only_unchecked():
    m = "- [x] answered one\n- [ ] open one\n- [ ] open two\n"
    assert coverage.unanswered(m) == ["open one", "open two"]
