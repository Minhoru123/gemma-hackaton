import config
from app import authorities


def test_canonicalize_normalizes_spacing_dashes_and_case():
    assert authorities.canonicalize("utah code §78B-7-804") == \
        authorities.canonicalize("Utah Code §  78B–7–804,")


def test_extract_citations_finds_cases_statutes_and_rules():
    text = ("Under 42 U.S.C. § 1983 and Utah Code § 78B-7-804, see State v. "
            "K.T.B., 2020 UT 51, 472 P.3d 843; URCP 7(q); Bell Atl. Corp. v. "
            "Twombly, 550 U.S. 544.")
    cites = authorities.extract_citations(text)
    assert "42 U.S.C. § 1983" in cites
    assert "Utah Code § 78B-7-804" in cites
    assert "2020 UT 51" in cites
    assert "472 P.3d 843" in cites
    assert "URCP 7(q)" in cites
    assert "550 U.S. 544" in cites


def test_extract_citations_dedupes_by_canonical_form():
    cites = authorities.extract_citations("2020 UT 51 ... 2020  UT  51")
    assert cites == ["2020 UT 51"]


def test_compound_citation_resolves_via_aliases(tmp_path):
    config.DB_PATH = str(tmp_path / "t.db")
    authorities.init_db()
    compound = "262 U.S. 390 (1923); 43 S.Ct. 625"
    authorities.add_authority(
        "Meyer v. Nebraska", compound, "opinion text",
        confirmed_by="library", aliases=authorities.extract_citations(compound))
    for cite in ("262 U.S. 390", "43 S.Ct. 625", compound):
        row = authorities.get_by_citation(cite)
        assert row and row["name"] == "Meyer v. Nebraska", cite
    assert authorities.get_by_citation("999 U.S. 1") is None


def test_sibling_captures_share_a_citation(tmp_path):
    config.DB_PATH = str(tmp_path / "t.db")
    authorities.init_db()
    cite = "Utah Code § 78B-7-804"
    authorities.add_authority("Version fragment", cite, "short text",
                              confirmed_by="library")
    authorities.add_authority("Full statute", cite, "the full statute text",
                              confirmed_by="")
    rows = authorities.get_all_by_citation(cite)
    assert len(rows) == 2
    assert rows[0]["name"] == "Full statute"  # most complete text first
    # Re-adding the same (citation, name) replaces, not duplicates.
    authorities.add_authority("Full statute", cite, "the full statute text v2",
                              confirmed_by="")
    assert len(authorities.get_all_by_citation(cite)) == 2
    # One confirmed sibling makes the citation citable.
    diff = authorities.diff_citations(f"See {cite}.")
    assert diff["known"] == [cite]


def test_add_get_and_diff(tmp_path):
    config.DB_PATH = str(tmp_path / "t.db")
    authorities.init_db()
    authorities.add_authority("State v. K.T.B.", "2020 UT 51",
                              "some opinion text", confirmed_by="David")
    authorities.add_authority("Web Case", "123 F.3d 456", "web text",
                              confirmed_by="")  # Tier 2, unconfirmed
    row = authorities.get_by_citation("2020  UT 51")
    assert row["name"] == "State v. K.T.B."
    diff = authorities.diff_citations(
        "See 2020 UT 51, 123 F.3d 456, and 550 U.S. 544.")
    assert diff["known"] == ["2020 UT 51"]
    assert diff["unconfirmed"] == ["123 F.3d 456"]
    assert diff["unknown"] == ["550 U.S. 544"]
