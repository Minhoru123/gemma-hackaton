from app.extract import _extract_json


def test_extract_json_from_surrounding_prose():
    text = 'Here you go: {"summary": "A divorce hearing notice.", "risks": ["Miss the deadline -> default judgment."]} Done.'
    data = _extract_json(text)
    assert data["summary"].startswith("A divorce")
    assert data["risks"][0].startswith("Miss the deadline")


def test_extract_json_bad_input_returns_empty():
    assert _extract_json("no json here") == {}
