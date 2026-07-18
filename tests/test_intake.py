import os
import config
from app import authorities, intake


def _setup(tmp_path):
    config.DB_PATH = str(tmp_path / "t.db")
    config.INTAKE_DIR = str(tmp_path / "intake")
    config.INTAKE_DONE_DIR = str(tmp_path / "intake" / "completed")
    config.FETCH_LIST = str(tmp_path / "FETCH_LIST.md")
    os.makedirs(config.INTAKE_DIR, exist_ok=True)
    authorities.init_db()
    authorities.add_authority("Known Case", "2020 UT 51", "text",
                              confirmed_by="David")


def test_process_intake_diffs_queues_and_moves(tmp_path):
    _setup(tmp_path)
    drop = os.path.join(config.INTAKE_DIR, "their_msj.txt")
    with open(drop, "w") as f:
        f.write("They cite 2020 UT 51 and also 550 U.S. 544.")
    reports = intake.process_intake()
    assert len(reports) == 1
    r = reports[0]
    assert r["known"] == ["2020 UT 51"]
    assert r["unknown"] == ["550 U.S. 544"]
    assert r["queued"] == 1
    assert not os.path.exists(drop)
    assert os.path.exists(os.path.join(config.INTAKE_DONE_DIR, "their_msj.txt"))
    with open(config.FETCH_LIST) as f:
        assert "550 U.S. 544 (seen in their_msj.txt" in f.read()


def test_fetch_list_dedupes_across_files(tmp_path):
    _setup(tmp_path)
    for name in ("a.txt", "b.txt"):
        with open(os.path.join(config.INTAKE_DIR, name), "w") as f:
            f.write("See 550 U.S. 544.")
    reports = intake.process_intake()
    assert [r["queued"] for r in reports] == [1, 0]
    with open(config.FETCH_LIST) as f:
        assert f.read().count("550 U.S. 544") == 1
