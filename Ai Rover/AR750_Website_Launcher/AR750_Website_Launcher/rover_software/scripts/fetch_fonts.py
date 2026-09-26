"""Make the console look right with no internet.

The website links to Google Fonts. That is fine at home; in a field with no
signal the browser silently falls back. Run this ONCE while the Pi is online:

    python3 scripts/fetch_fonts.py

It downloads the font files into ar750/web/static/fonts/ and writes
static/fonts.css so the console uses the local copies from then on. Nothing
else changes, and you can run it again any time.
"""
from __future__ import annotations

import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(os.path.dirname(HERE), "ar750", "web", "static")
FONT_DIR = os.path.join(STATIC, "fonts")

CSS_URL = ("https://fonts.googleapis.com/css2"
           "?family=Archivo:wght@500;600;700"
           "&family=IBM+Plex+Mono:wght@400;500"
           "&family=IBM+Plex+Sans:wght@400;500;600&display=swap")

# ask as a modern browser so Google sends woff2 rather than old formats
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0 Safari/537.36")


def main() -> int:
    os.makedirs(FONT_DIR, exist_ok=True)
    print("asking Google Fonts for the stylesheet...")
    try:
        req = urllib.request.Request(CSS_URL, headers={"User-Agent": UA})
        css = urllib.request.urlopen(req, timeout=20).read().decode("utf-8")
    except Exception as e:
        print("could not reach Google Fonts: %s" % e)
        print("connect the Pi to the internet and try again.")
        return 1

    urls = sorted(set(re.findall(r"url\((https://[^)]+\.woff2)\)", css)))
    if not urls:
        print("no font files in the reply, nothing to do")
        return 1
    print("downloading %d font files..." % len(urls))

    for url in urls:
        name = url.rsplit("/", 1)[-1]
        if not name.endswith(".woff2"):
            name += ".woff2"
        dest = os.path.join(FONT_DIR, name)
        if not os.path.exists(dest):
            try:
                data = urllib.request.urlopen(
                    urllib.request.Request(url, headers={"User-Agent": UA}),
                    timeout=30).read()
                with open(dest, "wb") as f:
                    f.write(data)
                print("  %s  %d KB" % (name, len(data) // 1024))
            except Exception as e:
                print("  could not fetch %s: %s" % (name, e))
                continue
        css = css.replace(url, "/static/fonts/" + name)

    header = ("/* Downloaded by scripts/fetch_fonts.py so the console works\n"
              "   with no internet. Delete this file to go back to loading the\n"
              "   fonts from Google. */\n")
    with open(os.path.join(STATIC, "fonts.css"), "w", encoding="utf-8") as f:
        f.write(header + css)

    print("\nDone. The console now uses the fonts in static/fonts/.")
    print("Reload the page on your phone to see it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
