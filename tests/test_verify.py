import config
from app import authorities, verify

OPINION = ("The court held that a facial challenge requires the challenger to "
           "establish that no set of circumstances exists under which the Act "
           "would be valid, a heavy burden indeed.")


def _seed(tmp_path):
    config.DB_PATH = str(tmp_path / "t.db")
    authorities.init_db()
    authorities.add_authority("Salerno", "481 U.S. 739", OPINION,
                              confirmed_by="David")


def test_clean_draft_passes(tmp_path):
    _seed(tmp_path)
    draft = ('A facial challenge requires that "no set of circumstances exists '
             'under which the Act would be valid." 481 U.S. 739.')
    report = verify.verify_draft(draft)
    assert report["ok"] is True
    assert report["quotes"]["matched"]


def test_unknown_citation_fails(tmp_path):
    _seed(tmp_path)
    report = verify.verify_draft("See 999 F.3d 111.")
    assert report["ok"] is False
    assert report["citations"]["unknown"] == ["999 F.3d 111"]


def test_unconfirmed_citation_fails(tmp_path):
    _seed(tmp_path)
    authorities.add_authority("Web Case", "123 F.3d 456", "text", confirmed_by="")
    report = verify.verify_draft("See 123 F.3d 456.")
    assert report["ok"] is False
    assert report["citations"]["unconfirmed"] == ["123 F.3d 456"]


def test_quote_with_elision_and_brackets_matches(tmp_path):
    _seed(tmp_path)
    draft = ('"[N]o set of circumstances exists ... under which the Act would '
             'be valid." 481 U.S. 739.')
    report = verify.verify_draft(draft)
    assert report["ok"] is True


def test_altered_quote_fails(tmp_path):
    _seed(tmp_path)
    draft = ('"no set of circumstances could ever exist under which the Act '
             'would be valid" 481 U.S. 739.')
    report = verify.verify_draft(draft)
    assert report["ok"] is False
    assert report["quotes"]["unmatched"]


def test_marker_fails(tmp_path):
    _seed(tmp_path)
    report = verify.verify_draft("The deadline is [[CONFIRM DEADLINE]].")
    assert report["ok"] is False
    assert report["markers"] == ["[[CONFIRM DEADLINE]]"]


def test_coverage_gate(tmp_path):
    _seed(tmp_path)
    cov = "- [x] Their preclusion argument\n- [ ] Their standing argument\n"
    report = verify.verify_draft("Draft body. 481 U.S. 739.", coverage_text=cov)
    assert report["ok"] is False
    assert report["coverage_unanswered"] == ["Their standing argument"]
