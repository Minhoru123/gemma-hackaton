from app.main import _safe


def test_safe_returns_value_on_success():
    issues = []
    assert _safe("stage", lambda: 42, 0, issues) == 42
    assert issues == []


def test_safe_degrades_to_default_on_failure():
    issues = []
    result = _safe("analysis", lambda: 1 / 0, {"doc_type": "other"}, issues)
    assert result == {"doc_type": "other"}
    assert issues == ["analysis"]


def test_safe_collects_multiple_failures():
    issues = []
    _safe("a", lambda: 1 / 0, None, issues)
    _safe("b", lambda: [][1], None, issues)
    assert issues == ["a", "b"]
