"""
download_image.py — Downloads free public domain Gita artwork for the app.
Run: python download_image.py
"""

import urllib.request
import os

# Public domain / CC0 sources — tries each until one works
SOURCES = [
    (
        "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8d/Bhagavad_Gita_by_Vyasa.jpg/800px-Bhagavad_Gita_by_Vyasa.jpg",
        "Bhagavad Gita manuscript — Wikimedia Commons (Public Domain)"
    ),
    (
        "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3c/Mahabharata_-_Bhagavad_Gita_-_Krishna_and_Arjuna.jpg/800px-Mahabharata_-_Bhagavad_Gita_-_Krishna_and_Arjuna.jpg",
        "Krishna and Arjuna — Wikimedia Commons (Public Domain)"
    ),
    (
        "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6e/Kurukshetra.jpg/800px-Kurukshetra.jpg",
        "Kurukshetra battlefield — Wikimedia Commons (Public Domain)"
    ),
]

OUTPUT = os.path.join("static", "gita_hero.jpg")

def download():
    os.makedirs("static", exist_ok=True)

    if os.path.exists(OUTPUT):
        print(f"Image already exists at {OUTPUT}")
        return

    for url, description in SOURCES:
        print(f"Trying: {description}")
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req, timeout=15) as r:
                with open(OUTPUT, "wb") as f:
                    f.write(r.read())
            print(f"✓ Saved to {OUTPUT}")
            return
        except Exception as e:
            print(f"  Failed: {e}")

    print("\nAll sources failed. Please manually place an image at:")
    print(f"  {OUTPUT}")
    print("Any JPG or PNG will work — rename it to gita_hero.jpg")

if __name__ == "__main__":
    download()
