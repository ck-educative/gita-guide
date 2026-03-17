"""
build_verses.py — Build complete 700-verse Sanskrit database.

Strategy:
  1. Fetch IAST transliteration + translation from vedicscriptures.github.io API
  2. Convert IAST transliteration → Devanagari using indic-transliteration
     (gita-big.pdf uses Sanskrit 2003 font with proprietary PUA glyph mapping
      which cannot be decoded by standard PDF tools — conversion is more reliable)

Usage:
  python build_verses.py          # build / resume
  python build_verses.py --reset  # wipe and rebuild from scratch
  python build_verses.py --stats  # show current database stats
"""

import argparse
import os
import sys

# Add project root to path so config.py is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
import logging
import os
import re
import sys
import time
import urllib.request

from config import ingest_config, app_config

os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/build_verses.log"),
    ],
)
logger = logging.getLogger(__name__)

# ── Sources ───────────────────────────────────────────────────
SANSKRIT_PDF_URL = "http://www.sanskritweb.net/sansdocs/gita-big.pdf"
SANSKRIT_PDF_PATH = os.path.join(
    os.getenv("SOURCES_DIR", "./sources"), "gita_sanskrit_devanagari.pdf"
)
API_BASE = "https://vedicscriptures.github.io/slok"
TRANSLATORS = ["siva", "gambir", "purohit", "tej", "san"]


# ── Download ──────────────────────────────────────────────────

def download_pdf(url: str, path: str) -> bool:
    if os.path.exists(path):
        logger.info("PDF already downloaded: %s", path)
        return True
    os.makedirs(os.path.dirname(path), exist_ok=True)
    logger.info("Downloading Sanskrit PDF from %s ...", url)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            with open(path, "wb") as f:
                f.write(r.read())
        size_mb = os.path.getsize(path) / 1_000_000
        logger.info("Downloaded: %s (%.1f MB)", path, size_mb)
        return True
    except Exception as e:
        logger.error("Download failed: %s", e)
        return False


# ── Parse Sanskrit PDF ────────────────────────────────────────

def extract_sanskrit_from_pdf(pdf_path: str) -> dict:
    """
    Parse gita-big.pdf and extract Sanskrit verses.

    The sanskritweb PDF uses markers like:
      Chapter 1, Verse 1  or  1.1  or  ||1.1||  or  BG 1.1
    followed by the Devanagari text block.

    Returns dict: { "1.1": "Sanskrit text...", ... }
    """
    try:
        from pypdf import PdfReader
    except ImportError:
        logger.error("pypdf not installed. Run: pip install pypdf")
        return {}

    logger.info("Parsing Sanskrit PDF: %s", pdf_path)
    reader = PdfReader(pdf_path)
    full_text = ""
    for page in reader.pages:
        text = page.extract_text()
        if text:
            full_text += text + "\n"

    logger.info("Extracted %d characters from PDF", len(full_text))

    # Try multiple patterns to find verse markers
    # Pattern 1: ||1.1|| or |1.1| style (common in Sanskrit texts)
    # Pattern 2: BG 1.1 or Bg. 1.1
    # Pattern 3: Chapter 1, Verse 1
    # Pattern 4: plain 1.1 at line start

    patterns = [
        r'\|\|?\s*(\d{1,2})[.\-](\d{1,3})\s*\|\|?',   # ||1.1||
        r'[Bb][Gg]\.?\s+(\d{1,2})[.\-](\d{1,3})',       # BG 1.1
        r'Chapter\s+(\d{1,2})[,.]?\s+[Vv]erse\s+(\d{1,3})',  # Chapter 1, Verse 1
        r'^\s*(\d{1,2})[.\-](\d{1,3})\s*$',             # 1.1 on its own line
    ]

    verses_sanskrit = {}

    for pattern in patterns:
        matches = list(re.finditer(pattern, full_text, re.MULTILINE))
        if len(matches) > 50:  # found a working pattern
            logger.info("Using pattern: %s — found %d matches", pattern, len(matches))

            for i, match in enumerate(matches):
                chapter = int(match.group(1))
                verse = int(match.group(2))
                key = f"{chapter}.{verse}"

                # Extract text between this match and the next
                start = match.end()
                end = matches[i + 1].start() if i + 1 < len(matches) else start + 500

                raw = full_text[start:end].strip()

                # Keep only lines that look like Devanagari (Unicode range 0900–097F)
                devanagari_lines = []
                for line in raw.split("\n"):
                    line = line.strip()
                    if line and any('\u0900' <= c <= '\u097f' for c in line):
                        devanagari_lines.append(line)

                sanskrit = " ".join(devanagari_lines).strip()

                # Fall back to raw text if no Devanagari detected
                if not sanskrit:
                    sanskrit = raw[:300].strip()

                if sanskrit and key not in verses_sanskrit:
                    verses_sanskrit[key] = sanskrit

            break  # stop trying patterns once one works

    if not verses_sanskrit:
        logger.warning(
            "Could not extract verse markers from PDF. "
            "The PDF may use a non-standard format. "
            "Falling back to API for Sanskrit text."
        )

    logger.info("Extracted Sanskrit for %d verses from PDF", len(verses_sanskrit))
    return verses_sanskrit


# ── IAST → Devanagari conversion ─────────────────────────────

def iast_to_devanagari(iast_text: str) -> str:
    """Convert IAST transliteration to Devanagari Unicode."""
    try:
        from indic_transliteration import sanscript
        from indic_transliteration.sanscript import transliterate
        return transliterate(iast_text, sanscript.IAST, sanscript.DEVANAGARI)
    except ImportError:
        logger.warning("indic-transliteration not installed. Run: pip install indic-transliteration")
        return ""
    except Exception as e:
        logger.debug("IAST conversion failed: %s", e)
        return ""


# ── API for transliteration + translation ─────────────────────

def fetch_json(url: str, timeout: int = 15):
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return None


def fetch_verse_api(chapter: int, verse: int) -> dict | None:
    """Fetch Sanskrit (slok), transliteration and translation from vedicscriptures API."""
    data = fetch_json(f"{API_BASE}/{chapter}/{verse}")
    if not data:
        return None

    translation = ""
    for key in TRANSLATORS:
        t = data.get(key, {})
        if t and t.get("et", "").strip():
            translation = t["et"].strip()
            break

    iast = data.get("transliteration", "").strip()

    # Convert IAST to Devanagari — better quality than the API's slok field
    # which sometimes contains encoding artifacts
    devanagari = iast_to_devanagari(iast) if iast else data.get("slok", "").strip()

    return {
        "sanskrit_api": data.get("slok", "").strip(),   # raw from API (may have artifacts)
        "sanskrit": devanagari,                          # converted from IAST — clean Unicode
        "transliteration": iast,
        "translation": translation,
    }


# ── Save / stats ──────────────────────────────────────────────

def save(verses: dict, path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(verses, f, ensure_ascii=False, indent=2)


def print_stats(verses: dict):
    total = len(verses)
    has_sanskrit    = sum(1 for v in verses.values() if v.get("sanskrit"))
    has_translit    = sum(1 for v in verses.values() if v.get("transliteration"))
    has_translation = sum(1 for v in verses.values() if v.get("translation"))
    print(f"\n  Total verses:         {total} / 700")
    print(f"  With Sanskrit:        {has_sanskrit}")
    print(f"  With transliteration: {has_translit}")
    print(f"  With translation:     {has_translation}\n")


# ── Main ──────────────────────────────────────────────────────

def fetch_one(args_tuple):
    """Worker function for parallel fetching. Returns (key, verse_dict | None)."""
    chapter, verse = args_tuple
    data = fetch_verse_api(chapter, verse)
    key = f"{chapter}.{verse}"
    if data:
        return key, {
            "chapter": chapter,
            "verse": verse,
            "sanskrit": data.get("sanskrit", "") or data.get("sanskrit_api", ""),
            "transliteration": data.get("transliteration", ""),
            "translation": data.get("translation", ""),
            "word_meaning": "",
        }
    return key, None


def build(reset: bool = False, only_chapter: int = None, workers: int = 10):
    from concurrent.futures import ThreadPoolExecutor, as_completed

    logger.info("=== Gita Guide — Building Verse Database ===")
    output_file = app_config.verses_file

    # Load existing
    verses = {}
    if not reset and os.path.exists(output_file):
        with open(output_file, "r", encoding="utf-8") as f:
            try:
                verses = json.load(f)
                existing = sum(1 for v in verses.values() if v.get("sanskrit"))
                logger.info("Resuming — %d / 700 verses have Sanskrit", existing)
            except json.JSONDecodeError:
                verses = {}

    # Build list of (chapter, verse) tuples to fetch
    chapters = ingest_config.chapter_verse_counts
    if only_chapter:
        if only_chapter not in chapters:
            logger.error("Invalid chapter %d — must be 1–18", only_chapter)
            sys.exit(1)
        chapters = {only_chapter: chapters[only_chapter]}
        logger.info("Chapter %d only (%d verses)", only_chapter, chapters[only_chapter])

    todo = []
    for chapter, verse_count in chapters.items():
        for verse in range(1, verse_count + 1):
            key = f"{chapter}.{verse}"
            already = verses.get(key, {})
            if already.get("sanskrit") and already.get("transliteration"):
                continue  # skip already-complete verses
            todo.append((chapter, verse))

    if not todo:
        logger.info("All verses already complete.")
        print_stats(verses)
        return

    total = len(todo)
    logger.info("Fetching %d verses with %d parallel workers...", total, workers)

    failed = []
    done = 0

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(fetch_one, t): t for t in todo}
        for future in as_completed(futures):
            key, verse_dict = future.result()
            if verse_dict:
                verses[key] = verse_dict
            else:
                ch, vs = futures[future]
                failed.append(key)
                verses[key] = {
                    "chapter": ch, "verse": vs,
                    "sanskrit": "", "transliteration": "",
                    "translation": f"Bhagavad Gita {key}",
                    "word_meaning": "",
                }
                logger.warning("✗ %s — no data", key)

            done += 1
            if done % 50 == 0 or done == total:
                logger.info("  %d / %d fetched...", done, total)
                save(verses, output_file)

    save(verses, output_file)
    logger.info("\n=== Complete ===")
    print_stats(verses)
    if failed:
        logger.warning("Failed (%d): %s", len(failed), ", ".join(failed[:10]))
    logger.info("Saved to: %s", output_file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build Bhagavad Gita verse database")
    parser.add_argument("--reset", action="store_true",
                        help="Wipe existing data and rebuild from scratch")
    parser.add_argument("--stats", action="store_true",
                        help="Show current stats and exit")
    parser.add_argument("--chapter", type=int, default=None,
                        help="Only fetch a single chapter (1–18)")
    parser.add_argument("--workers", type=int, default=10,
                        help="Parallel workers (default: 10)")
    args = parser.parse_args()

    if args.stats:
        if os.path.exists(app_config.verses_file):
            with open(app_config.verses_file) as f:
                print_stats(json.load(f))
        else:
            print("No verses.json found. Run: python build_verses.py")
    else:
        build(reset=args.reset, only_chapter=args.chapter, workers=args.workers)
