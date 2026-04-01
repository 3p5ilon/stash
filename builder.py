"""
builder.py — stash bookmark builder

Dependencies:
    pip install pillow pillow-heif playwright
    playwright install chromium

How it works:
    - Scans screenshots/YEAR/ for new images
    - For each URL: launches a real headless Chromium browser,
      loads the page fully (JS included), reads og:title / <title>
    - This is exactly how Telegram/Slack/WhatsApp generate link previews
    - Titles are cached in bookmarks.json so re-runs are instant
"""

import json
import os
import re
from urllib.parse import quote, urlparse

from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()

try:
    from playwright.sync_api import sync_playwright

    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False
    print(
        "playwright not found — run: pip install playwright && playwright install chromium"
    )

SCREENSHOTS_DIR = "screenshots"
BOOKMARKS_FILE = "bookmarks.json"
STASH_FILE = "stash.json"


def fetch_title(url):
    """
    Fetch og:title using a real headless Chromium browser.
    Handles JS-rendered pages (YouTube, Coursera, Twitter etc.)
    """
    if not HAS_PLAYWRIGHT:
        return None

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/123.0.0.0 Safari/537.36"
        )
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=15000)
            # wait a bit for JS meta tags to populate
            page.wait_for_timeout(1500)

            # try og:title first
            og = page.evaluate("""
                () => {
                    const m = document.querySelector('meta[property="og:title"]');
                    return m ? m.getAttribute('content') : null;
                }
            """)
            if og and og.strip():
                return og.strip()

            # fallback to <title>
            title = page.title()
            return title.strip() if title else None

        except Exception as e:
            print(f"      ✗ {e}")
            return None
        finally:
            browser.close()


def favicon_url(url):
    hostname = urlparse(url).hostname or ""
    return f"https://www.google.com/s2/favicons?domain={hostname}&sz=32"


# ── load existing bookmarks.json ──
data = {}
if os.path.exists(BOOKMARKS_FILE):
    data = json.load(open(BOOKMARKS_FILE))


def all_entries(d):
    return [bm for year in d.values() for cat in year.values() for bm in cat]


existing_by_image = {e["image"]: e for e in all_entries(data)}

# ── scan screenshots/YEAR/ for new images ──
new_count = 0

for entry in sorted(os.scandir(SCREENSHOTS_DIR), key=lambda e: e.name):
    if not entry.is_dir() or not entry.name.isdigit():
        continue
    year = entry.name

    for file in sorted(os.listdir(entry.path)):
        filepath = f"{SCREENSHOTS_DIR}/{year}/{file}"
        if not os.path.isfile(filepath):
            continue
        try:
            Image.open(filepath).verify()
        except:
            continue

        if filepath in existing_by_image:
            continue

        data.setdefault(year, {}).setdefault("", []).append(
            {
                "image": filepath,
                "url": "",
                "category": "",
                "title": "",
                "favicon": "",
            }
        )
        print(f"  + {filepath}")
        new_count += 1

if new_count:
    json.dump(data, open(BOOKMARKS_FILE, "w"), indent=2)
    print(f"\n{new_count} new image(s) added to {BOOKMARKS_FILE}")
    print("Fill in url and category for each, then run builder.py again.")
    raise SystemExit

# ── fetch missing titles / favicons ──
for bm in all_entries(data):
    if not bm.get("url"):
        continue

    needs_title = not bm.get("title") or bm["title"] == bm["url"]
    if needs_title:
        print(f"  fetching: {bm['url']}")
        t = fetch_title(bm["url"])
        if t:
            bm["title"] = t
            print(f"    ✓ {t[:70]}")
        else:
            bm["title"] = bm["url"]
            print(f"    ✗ failed — set title manually in {BOOKMARKS_FILE}")

    if not bm.get("favicon"):
        bm["favicon"] = favicon_url(bm["url"])

# ── rebuild by category + add image dimensions ──
years = sorted(data.keys(), reverse=True)
out = {}

for year, cats in data.items():
    new_cats = {}
    for bm_list in cats.values():
        for bm in bm_list:
            if not bm.get("url"):
                continue
            cat = bm.get("category") or "Uncategorized"
            try:
                im = Image.open(bm["image"])
                w, h = im.width, im.height
            except:
                w, h = 800, 600

            new_cats.setdefault(cat, []).append(
                {
                    "image": f"{os.path.dirname(bm['image'])}/{quote(os.path.basename(bm['image']))}",
                    "url": bm["url"],
                    "title": bm["title"],
                    "favicon": bm["favicon"],
                    "w": w,
                    "h": h,
                }
            )
    if new_cats:
        out[year] = new_cats

# save bookmarks.json with updated titles
json.dump(data, open(BOOKMARKS_FILE, "w"), indent=2)

# save stash.json for the browser
json.dump({"years": years, "data": out}, open(STASH_FILE, "w"), indent=2)

total = sum(len(v) for cats in out.values() for v in cats.values())
print(f"\nDone → {STASH_FILE} ({total} bookmarks)")
print("Preview: python3 -m http.server 8000")
