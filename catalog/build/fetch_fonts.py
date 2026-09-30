"""Fetch the CJK fallback fonts for the ZH edition (not committed: ~57 MB).

    python3 build/fetch_fonts.py
"""
import re, subprocess, sys, urllib.request
from pathlib import Path

DEST = Path(__file__).resolve().parents[1] / "assets" / "fonts"
CSS = ("https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;700"
       "&family=Noto+Serif+SC:wght@500;600&display=swap")
UA = {"User-Agent": "Mozilla/5.0"}

css = urllib.request.urlopen(urllib.request.Request(CSS, headers=UA)).read().decode()
for block in re.findall(r"@font-face\s*{(.*?)}", css, re.S):
    fam = re.search(r"font-family: '([^']+)'", block).group(1).replace(" ", "")
    w = re.search(r"font-weight: (\d+)", block).group(1)
    url = re.search(r"url\((https[^)]+)\)", block).group(1)
    out = DEST / f"{fam}-{w}-normal.ttf"
    if out.exists():
        print("have", out.name); continue
    out.write_bytes(urllib.request.urlopen(urllib.request.Request(url, headers=UA)).read())
    print("fetched", out.name, out.stat().st_size // 1024, "KB")
