"""
extract_pdf_sanskrit.py — Extract Sanskrit from gita-big.pdf by reading
the font's embedded ToUnicode CMap table.

The PDF uses "Sanskrit 2003" font with Private Use Area glyph mappings.
This script:
  1. Opens the PDF with pdfminer.six
  2. Extracts the ToUnicode CMap from the embedded font
  3. Builds a PUA → Devanagari Unicode mapping table
  4. Re-reads all pages, decoding PUA characters using that map
  5. Parses verse markers and saves clean Sanskrit to verses.json

Usage:
  python extract_pdf_sanskrit.py                        # preview extracted text
  python extract_pdf_sanskrit.py --save                 # merge into verses.json
  python extract_pdf_sanskrit.py --dump-cmap            # print the font encoding map
  python extract_pdf_sanskrit.py --page 5               # preview a specific page
"""

import argparse
import json
import os
import re
import sys

PDF_PATH = os.path.join(os.getenv("SOURCES_DIR", "./sources"), "gita_sanskrit_devanagari.pdf")
VERSES_FILE = "./verses.json"

CHAPTER_VERSE_COUNTS = {
    1: 47, 2: 72, 3: 43, 4: 42, 5: 29,
    6: 47, 7: 30, 8: 28, 9: 34, 10: 42,
    11: 55, 12: 20, 13: 35, 14: 27, 15: 20,
    16: 24, 17: 28, 18: 78
}


# ── Step 1: Extract ToUnicode CMap from embedded font ─────────

def extract_cmap_from_pdf(pdf_path: str) -> dict:
    """
    Open the PDF, find the Sanskrit 2003 font resource,
    parse its ToUnicode CMap and return a dict:
      { pua_char: devanagari_unicode_char, ... }
    """
    try:
        from pdfminer.high_level import extract_pages
        from pdfminer.layout import LTPage
        from pdfminer.pdfdocument import PDFDocument
        from pdfminer.pdfpage import PDFPage
        from pdfminer.pdfparser import PDFParser
        from pdfminer.pdftypes import resolve1
        from pdfminer.pdfinterp import PDFResourceManager
    except ImportError:
        print("ERROR: pdfminer.six not installed. Run: pip install pdfminer.six")
        sys.exit(1)

    cmap = {}

    with open(pdf_path, "rb") as f:
        parser = PDFParser(f)
        doc = PDFDocument(parser)

        for page in PDFPage.create_pages(doc):
            resources = resolve1(page.resources)
            if not resources:
                continue

            fonts = resolve1(resources.get("Font", {}))
            if not fonts:
                continue

            for font_name, font_ref in fonts.items():
                font_obj = resolve1(font_ref)
                if not isinstance(font_obj, dict):
                    continue

                to_unicode_ref = font_obj.get("ToUnicode")
                if not to_unicode_ref:
                    continue

                to_unicode = resolve1(to_unicode_ref)
                if not hasattr(to_unicode, "get_data"):
                    continue

                cmap_data = to_unicode.get_data().decode("latin-1", errors="replace")
                parsed = parse_cmap_data(cmap_data)
                cmap.update(parsed)

                if len(cmap) > 100:
                    print(f"  Found CMap in font '{font_name}' — {len(cmap)} mappings")
                    return cmap  # found it, stop early

    print(f"  Total CMap entries found: {len(cmap)}")
    return cmap


def parse_cmap_data(cmap_text: str) -> dict:
    """
    Parse a ToUnicode CMap stream.
    Handles both:
      <XX> <YYYY>          (single char mapping)
      <XX> <YYYY>          (in beginbfchar/endbfchar blocks)
    """
    mapping = {}

    # Match: <hex_src> <hex_dst>
    pattern = re.compile(r'<([0-9A-Fa-f]{2,4})>\s*<([0-9A-Fa-f]{4,8})>')

    for src_hex, dst_hex in pattern.findall(cmap_text):
        try:
            src_codepoint = int(src_hex, 16)
            dst_codepoint = int(dst_hex, 16)
            src_char = chr(src_codepoint)
            dst_char = chr(dst_codepoint)

            # Only map if destination is Devanagari (0900–097F) or common punctuation
            if 0x0900 <= dst_codepoint <= 0x097F or dst_codepoint in (0x0964, 0x0965, 0x200C, 0x200D):
                mapping[src_char] = dst_char
            elif 0xE000 <= src_codepoint <= 0xF8FF:
                # PUA source — keep mapping regardless of destination
                mapping[src_char] = dst_char
        except (ValueError, OverflowError):
            continue

    return mapping


# ── Step 2: Decode text using the CMap ────────────────────────

def decode_with_cmap(text: str, cmap: dict) -> str:
    """Replace PUA characters with their mapped Unicode equivalents."""
    if not cmap:
        return text
    return "".join(cmap.get(ch, ch) for ch in text)


# ── Step 3: Extract text page by page ─────────────────────────

def extract_text_pages(pdf_path: str, cmap: dict) -> list[str]:
    """Extract text from all pages, decoding with cmap."""
    try:
        from pdfminer.high_level import extract_text_to_fp
        from pdfminer.high_level import extract_pages
        from pdfminer.layout import LTTextContainer, LTChar
    except ImportError:
        print("ERROR: pdfminer.six not installed.")
        sys.exit(1)

    pages = []

    try:
        from pdfminer.high_level import extract_pages
        from pdfminer.layout import LTTextContainer

        for page_layout in extract_pages(pdf_path):
            page_text = ""
            for element in page_layout:
                if isinstance(element, LTTextContainer):
                    page_text += element.get_text()
            decoded = decode_with_cmap(page_text, cmap)
            pages.append(decoded)

    except Exception as e:
        print(f"Extraction error: {e}")

    return pages


# ── Step 4: Parse verse markers from decoded text ──────────────

def parse_verses_from_text(pages: list[str]) -> dict:
    """
    Find verse markers like ॥2.47॥ or ।।2.47।। or ||2.47||
    and extract the Sanskrit text before each marker.
    Returns { "2.47": "sanskrit text...", ... }
    """
    full_text = "\n".join(pages)

    # Patterns for verse markers in Devanagari-style and ASCII
    # ॥chapter.verse॥  or  ||chapter.verse||  or  2.47 etc.
    marker_patterns = [
        r'॥\s*(\d{1,2})[.\-](\d{1,3})\s*॥',       # ॥2.47॥
        r'।।\s*(\d{1,2})[.\-](\d{1,3})\s*।।',       # ।।2.47।।
        r'\|\|\s*(\d{1,2})[.\-](\d{1,3})\s*\|\|',   # ||2.47||
        r'\|?\s*(\d{1,2})[.\-](\d{1,3})\s*\|',       # |2.47|
        r'(?<!\d)(\d{1,2})[.\-](\d{1,3})(?!\d)',     # plain 2.47
    ]

    verses = {}

    for pattern in marker_patterns:
        matches = list(re.finditer(pattern, full_text))
        if len(matches) >= 50:
            print(f"  Using marker pattern: {repr(pattern)} — {len(matches)} matches found")
            for i, m in enumerate(matches):
                chapter, verse_num = int(m.group(1)), int(m.group(2))

                # Validate against known chapter/verse counts
                max_verse = CHAPTER_VERSE_COUNTS.get(chapter, 0)
                if not (1 <= chapter <= 18 and 1 <= verse_num <= max_verse):
                    continue

                key = f"{chapter}.{verse_num}"

                # Text between previous marker end and this marker start
                prev_end = matches[i - 1].end() if i > 0 else 0
                raw = full_text[prev_end:m.start()].strip()

                # Keep only lines with Devanagari characters
                deva_lines = [
                    line.strip() for line in raw.split("\n")
                    if line.strip() and any('\u0900' <= c <= '\u097f' for c in line)
                ]
                sanskrit = " ".join(deva_lines).strip()

                if sanskrit and key not in verses:
                    verses[key] = sanskrit

            if verses:
                return verses

    return verses


# ── Step 5: Merge into verses.json ────────────────────────────

def merge_into_verses_json(pdf_sanskrit: dict, verses_file: str):
    """Merge PDF-extracted Sanskrit into existing verses.json."""
    if os.path.exists(verses_file):
        with open(verses_file, "r", encoding="utf-8") as f:
            verses = json.load(f)
    else:
        verses = {}

    updated = 0
    for key, sanskrit in pdf_sanskrit.items():
        if key in verses:
            verses[key]["sanskrit"] = sanskrit
            updated += 1
        else:
            ch, vs = key.split(".")
            verses[key] = {
                "chapter": int(ch), "verse": int(vs),
                "sanskrit": sanskrit,
                "transliteration": "", "translation": "", "word_meaning": "",
            }
            updated += 1

    with open(verses_file, "w", encoding="utf-8") as f:
        json.dump(verses, f, ensure_ascii=False, indent=2)

    print(f"  Updated {updated} verses in {verses_file}")


# ── Main ──────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--save", action="store_true", help="Merge into verses.json")
    parser.add_argument("--dump-cmap", action="store_true", help="Print CMap entries")
    parser.add_argument("--page", type=int, default=None, help="Preview specific page")
    args = parser.parse_args()

    if not os.path.exists(PDF_PATH):
        print(f"PDF not found: {PDF_PATH}")
        print("Make sure gita_sanskrit_devanagari.pdf is in your sources/ folder.")
        sys.exit(1)

    print(f"PDF: {PDF_PATH} ({os.path.getsize(PDF_PATH)/1e6:.1f} MB)")

    # Step 1: Extract CMap
    print("\nStep 1 — Extracting font CMap...")
    cmap = extract_cmap_from_pdf(PDF_PATH)

    if args.dump_cmap:
        print("\nCMap entries (PUA → Devanagari):")
        for src, dst in sorted(cmap.items(), key=lambda x: ord(x[0])):
            src_cp = ord(src)
            dst_cp = ord(dst)
            if 0xE000 <= src_cp <= 0xF8FF:
                print(f"  U+{src_cp:04X} → U+{dst_cp:04X}  {dst}")
        return

    if not cmap:
        print("\nWARNING: No CMap found. The font may be fully embedded without ToUnicode.")
        print("Trying raw text extraction anyway...")

    # Step 2: Extract and decode text
    print("\nStep 2 — Extracting and decoding page text...")
    pages = extract_text_pages(PDF_PATH, cmap)
    print(f"  Extracted {len(pages)} pages")

    if args.page is not None:
        idx = args.page - 1
        if 0 <= idx < len(pages):
            print(f"\n--- Page {args.page} ---")
            print(pages[idx][:2000])
        else:
            print(f"Page {args.page} out of range (1–{len(pages)})")
        return

    # Step 3: Parse verse markers
    print("\nStep 3 — Parsing verse markers...")
    pdf_verses = parse_verses_from_text(pages)
    print(f"  Found Sanskrit for {len(pdf_verses)} / 700 verses")

    if not pdf_verses:
        print("\nNo verses parsed. Run with --page 5 to inspect the raw decoded text.")
        print("If the text still shows PUA characters, the font has no ToUnicode CMap.")
        return

    # Preview first 5
    print("\nSample verses:")
    for key in list(pdf_verses.keys())[:5]:
        print(f"  {key}: {pdf_verses[key][:60]}")

    if args.save:
        print(f"\nStep 4 — Merging into {VERSES_FILE}...")
        merge_into_verses_json(pdf_verses, VERSES_FILE)
        print("Done. Restart the app to see updated Sanskrit.")
    else:
        print("\nRun with --save to merge into verses.json")


if __name__ == "__main__":
    main()
