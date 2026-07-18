from app import dates


def test_textual_forms():
    assert dates.find_date("Hearing on April 14, 2026 at 9 AM") == "2026-04-14"
    assert dates.find_date("Entered Apr. 3 2026") == "2026-04-03"
    assert dates.find_date("on the 14th of April, 2026") == "2026-04-14"
    assert dates.find_date("due August 3rd, 2026") == "2026-08-03"


def test_numeric_us_forms_including_cmecf_stamp():
    assert dates.find_date("Document 24 Filed 04/14/26 PageID.361") == "2026-04-14"
    assert dates.find_date("served 4/9/2026 by mail") == "2026-04-09"


def test_iso_form():
    assert dates.find_date("filed_date: 2026-04-14") == "2026-04-14"


def test_first_date_in_document_order_wins():
    text = "Filed 04/14/26. A hearing was previously held on March 2, 2026."
    assert dates.find_date(text) == "2026-04-14"


def test_impossible_dates_are_skipped_not_returned():
    # 13/45 is no date; the real one later in the text should win.
    assert dates.find_date("ref 13/45/2026, hearing June 1, 2026") == "2026-06-01"
    assert dates.find_date("nothing datelike here") == ""


def test_valid_iso_is_semantic_not_just_format():
    assert dates.valid_iso("2026-04-14") == "2026-04-14"
    assert dates.valid_iso("2026-02-30") == ""   # Feb 30 doesn't exist
    assert dates.valid_iso("2026-13-01") == ""   # month 13 doesn't exist
    assert dates.valid_iso("0026-04-14") == ""   # implausible year
    assert dates.valid_iso("04/14/2026") == ""   # wrong shape for this gate
    assert dates.valid_iso(None) == ""


def test_multiple_texts_checked_in_order():
    assert dates.find_date("", "no dates", "July 1, 2026") == "2026-07-01"
