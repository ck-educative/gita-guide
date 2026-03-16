"""
tests/test_build_verses.py — Tests for scripts/build_verses.py logic.

Run:
    pytest tests/test_build_verses.py          # with mock API (fast, no network)
    pytest tests/test_build_verses.py -v       # verbose output
"""

from unittest.mock import patch


# ── iast_to_devanagari ────────────────────────────────────────

def test_iast_to_devanagari_returns_string():
    from build_verses import iast_to_devanagari
    result = iast_to_devanagari("karma")
    assert isinstance(result, str)
    assert len(result) > 0

def test_iast_to_devanagari_produces_devanagari():
    from build_verses import iast_to_devanagari
    result = iast_to_devanagari("karmaṇyevādhikāraste mā phaleṣu kadācana")
    assert any('\u0900' <= c <= '\u097f' for c in result), \
        f"No Devanagari characters in output: {result}"

def test_iast_to_devanagari_empty_input():
    from build_verses import iast_to_devanagari
    assert iast_to_devanagari("") == ""


# ── fetch_verse_api ───────────────────────────────────────────

def test_fetch_verse_api_returns_none_on_network_failure():
    from build_verses import fetch_verse_api
    with patch("build_verses.fetch_json", return_value=None):
        assert fetch_verse_api(1, 1) is None

def test_fetch_verse_api_parses_response_fields():
    from build_verses import fetch_verse_api
    mock = {
        "slok": "raw slok text",
        "transliteration": "karmaṇyevādhikāraste",
        "tej": {"et": "You have the right to perform your duty."}
    }
    with patch("build_verses.fetch_json", return_value=mock):
        result = fetch_verse_api(2, 47)
    assert result is not None
    assert result["transliteration"] == "karmaṇyevādhikāraste"
    assert "right to perform" in result["translation"]

def test_fetch_verse_api_includes_sanskrit_field():
    from build_verses import fetch_verse_api
    mock = {
        "slok": "raw slok",
        "transliteration": "dharma",
        "tej": {"et": "Some translation."}
    }
    with patch("build_verses.fetch_json", return_value=mock):
        result = fetch_verse_api(1, 1)
    assert "sanskrit" in result
    assert isinstance(result["sanskrit"], str)


# ── fetch_one (parallel worker) ───────────────────────────────

def test_fetch_one_returns_correct_key():
    from build_verses import fetch_one
    mock = {"slok": "x", "transliteration": "karma", "tej": {"et": "Translation."}}
    with patch("build_verses.fetch_json", return_value=mock):
        key, _ = fetch_one((2, 47))
    assert key == "2.47"

def test_fetch_one_returns_verse_dict_on_success():
    from build_verses import fetch_one
    mock = {"slok": "x", "transliteration": "karma", "tej": {"et": "Translation."}}
    with patch("build_verses.fetch_json", return_value=mock):
        key, verse = fetch_one((2, 47))
    assert verse is not None
    assert verse["chapter"] == 2
    assert verse["verse"] == 47

def test_fetch_one_returns_none_on_api_failure():
    from build_verses import fetch_one
    with patch("build_verses.fetch_json", return_value=None):
        key, verse = fetch_one((1, 1))
    assert key == "1.1"
    assert verse is None
