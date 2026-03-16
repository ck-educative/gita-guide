"""
tests/test_verses.py — Tests for verses.json structure and content.
"""

import json
import os
import pytest

VERSES_FILE = os.path.join(os.path.dirname(__file__), "..", "verses.json")

CHAPTER_VERSE_COUNTS = {
    1: 47, 2: 72, 3: 43, 4: 42, 5: 29,
    6: 47, 7: 30, 8: 28, 9: 34, 10: 42,
    11: 55, 12: 20, 13: 35, 14: 27, 15: 20,
    16: 24, 17: 28, 18: 78
}

FAMOUS_VERSES = ["2.47", "2.20", "4.7", "6.19", "18.66"]
DEVANAGARI_RANGE = ('\u0900', '\u097f')


@pytest.fixture(scope="module")
def verses():
    if not os.path.exists(VERSES_FILE):
        pytest.skip("verses.json not found — run: python build_verses.py")
    with open(VERSES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def test_verses_file_exists():
    assert os.path.exists(VERSES_FILE), "verses.json missing — run: python build_verses.py"

def test_verses_total_count(verses):
    assert len(verses) >= 701, f"Expected 700 verses, got {len(verses)}"

def test_verses_all_chapters_present(verses):
    for chapter in range(1, 19):
        chapter_verses = [k for k in verses if k.startswith(f"{chapter}.")]
        assert len(chapter_verses) > 0, f"Chapter {chapter} has no verses"

def test_verses_all_keys_have_correct_format(verses):
    for key in verses:
        parts = key.split(".")
        assert len(parts) == 2, f"Bad key format: {key}"
        assert parts[0].isdigit() and parts[1].isdigit(), f"Non-numeric key: {key}"

def test_verses_chapter_2_has_72_verses(verses):
    ch2 = [k for k in verses if k.startswith("2.")]
    assert len(ch2) == 72, f"Chapter 2 should have 72 verses, got {len(ch2)}"

def test_famous_verses_present(verses):
    for key in FAMOUS_VERSES:
        assert key in verses, f"Famous verse {key} missing"

def test_verse_fields_present(verses):
    for key, data in list(verses.items())[:20]:  # spot-check first 20
        assert "chapter" in data, f"{key} missing 'chapter'"
        assert "verse" in data, f"{key} missing 'verse'"
        assert "sanskrit" in data, f"{key} missing 'sanskrit'"
        assert "transliteration" in data, f"{key} missing 'transliteration'"
        assert "translation" in data, f"{key} missing 'translation'"

def test_verse_chapter_verse_fields_match_key(verses):
    for key, data in list(verses.items())[:50]:
        ch, vs = key.split(".")
        assert data["chapter"] == int(ch), f"{key}: chapter field mismatch"
        assert data["verse"] == int(vs), f"{key}: verse field mismatch"

def test_sanskrit_contains_devanagari(verses):
    has_devanagari = sum(
        1 for v in verses.values()
        if any(DEVANAGARI_RANGE[0] <= c <= DEVANAGARI_RANGE[1] for c in v.get("sanskrit", ""))
    )
    total = len(verses)
    ratio = has_devanagari / total
    assert ratio >= 0.9, f"Only {ratio:.0%} of verses have Devanagari — run: python build_verses.py --reset"

def test_sanskrit_no_pua_characters(verses):
    """Check for Private Use Area characters (the corrupted PDF encoding)."""
    pua_verses = []
    for key, data in verses.items():
        sanskrit = data.get("sanskrit", "")
        if any('\ue000' <= c <= '\uf8ff' for c in sanskrit):
            pua_verses.append(key)
    assert len(pua_verses) == 0, (
        f"{len(pua_verses)} verses still have corrupted PUA characters: "
        f"{pua_verses[:5]} — run: python build_verses.py --reset"
    )

def test_transliteration_not_empty_for_famous(verses):
    for key in FAMOUS_VERSES:
        translit = verses.get(key, {}).get("transliteration", "")
        assert len(translit) > 5, f"{key} has empty transliteration"

def test_translation_not_empty_for_famous(verses):
    for key in FAMOUS_VERSES:
        translation = verses.get(key, {}).get("translation", "")
        assert len(translation) > 10, f"{key} has empty translation"

def test_verse_2_47_content(verses):
    """The most famous verse — spot-check exact content."""
    v = verses.get("2.47", {})
    translit = v.get("transliteration", "").lower()
    assert "karma" in translit or "karman" in translit, \
        f"2.47 transliteration doesn't mention karma: {translit[:80]}"
