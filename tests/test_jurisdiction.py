import config
from app import jurisdiction, store


FEDERAL_CAPTION = """
IN THE UNITED STATES DISTRICT COURT
FOR THE DISTRICT OF UTAH, CENTRAL DIVISION

JANE DOE, Plaintiff,
v.
STATE OF UTAH, et al., Defendants.

Case No. 2:26-cv-00412
STATE DEFENDANTS' MOTION TO DISMISS
"""

UTAH_CAPTION = """
IN THE THIRD JUDICIAL DISTRICT COURT
IN AND FOR SALT LAKE COUNTY, STATE OF UTAH

JOHN ROE, Petitioner,
v.
JANE ROE, Respondent.

Case No. 264900123
MOTION FOR TEMPORARY ORDERS
"""


def test_detects_federal_from_caption():
    assert jurisdiction.detect(FEDERAL_CAPTION) == "federal"


def test_detects_utah_from_caption():
    assert jurisdiction.detect(UTAH_CAPTION) == "utah"


def test_federal_caption_wins_over_state_of_utah_in_body():
    # A federal brief about Utah defendants cites Utah statutes constantly;
    # the caption, not the body, decides.
    text = FEDERAL_CAPTION + "\n" + (
        "The State of Utah argues that Utah Code § 78B-7-804 controls. "
        "Under Utah law the claim fails.\n") * 20
    assert jurisdiction.detect(text) == "federal"


def test_weak_signals_used_when_caption_silent():
    assert jurisdiction.detect(
        "Response due within 14 days under Fed. R. Civ. P. 12.") == "federal"
    assert jurisdiction.detect(
        "Response due within 14 days under Utah R. Civ. P. 7.") == "utah"


def test_conflicting_weak_signals_stay_unknown():
    text = ("Compare Fed. R. Civ. P. 12 with Utah R. Civ. P. 7, which "
            "track each other.")
    assert jurisdiction.detect(text) == ""


def test_plain_letter_stays_unknown():
    assert jurisdiction.detect(
        "Dear client, we received the enclosed papers and will call you.") == ""


def test_case_jurisdiction_persists_and_rejects_junk(tmp_path):
    config.DB_PATH = str(tmp_path / "t.db")
    store.init_db()
    assert jurisdiction.get_case() == ""
    jurisdiction.set_case("federal")
    assert jurisdiction.get_case() == "federal"
    jurisdiction.set_case("mars")  # invalid values are ignored
    assert jurisdiction.get_case() == "federal"
