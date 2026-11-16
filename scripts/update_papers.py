#!/usr/bin/env python3
"""Rebuild the Neighbor Papers cards in index.html from the Substack feed.

Fills the block between <!-- papers:start --> and <!-- papers:end --> with the
three most recent posts from https://thecivicneighbor.substack.com. Empty slots
become "coming soon" cards that point to the signup form.

Usage:
  python3 scripts/update_papers.py                 # fetch live from Substack
  python3 scripts/update_papers.py --json posts.json   # use a saved API response
"""
import html
import json
import re
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

PUB = "https://thecivicneighbor.substack.com"
API = PUB + "/api/v1/posts?limit=50"
SLOTS = 3
ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"
START, END = "<!-- papers:start -->", "<!-- papers:end -->"

ARROW = ('<svg class="icon" viewBox="0 0 24 24" width="18" height="18" fill="none" '
         'stroke="currentColor" stroke-width="1.6" stroke-linecap="round" '
         'stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14"/>'
         '<path d="m13 6 6 6-6 6"/></svg>')
SMALL = {"a", "an", "and", "as", "at", "but", "by", "for", "in", "nor", "of",
         "on", "or", "the", "to", "up", "vs", "via"}


def nice_title(t):
    t = " ".join(t.split())
    if t != t.upper():
        return t
    words = t.lower().split(" ")
    out = []
    for i, w in enumerate(words):
        if 0 < i < len(words) - 1 and w in SMALL:
            out.append(w)
        else:
            out.append(w[:1].upper() + w[1:])
    return " ".join(out)


def fetch_posts(json_path=None):
    if json_path:
        data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    else:
        req = urllib.request.Request(API, headers={"User-Agent": "Mozilla/5.0 (site build)"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.load(r)
    posts = data.get("posts", data) if isinstance(data, dict) else data
    posts = [p for p in posts if p.get("is_published", True) and p.get("audience") in (None, "everyone", "only_free")]
    posts.sort(key=lambda p: p.get("post_date", ""), reverse=True)
    return posts


def card(n, p):
    title = html.escape(nice_title(p["title"]))
    url = html.escape(p.get("canonical_url") or f'{PUB}/p/{p["slug"]}')
    names = [b.get("name") for b in p.get("publishedBylines") or [] if b.get("name")]
    byline = names[0] if names and names[0] != "The Civic Neighbor Project" else ""
    d = datetime.fromisoformat(p["post_date"].replace("Z", "+00:00"))
    date = f"{d.strftime('%B')} {d.day}, {d.year}"
    by = html.escape(f"{byline} · {date}" if byline else date)
    sub = (p.get("subtitle") or "").strip()
    sub_html = f'\n            <p class="sub">{html.escape(sub)}</p>' if sub else ""
    return (f'          <a class="paper" href="{url}">\n'
            f'            <span class="no">No. {n}</span>\n'
            f'            <h3>{title}</h3>{sub_html}\n'
            f'            <span class="by">{by}</span>\n'
            f'            <span class="go">Read on Substack {ARROW}</span>\n'
            f'          </a>')


def soon(n):
    return (f'          <a class="paper soon" href="#join">\n'
            f'            <span class="no">No. {n}</span>\n'
            f'            <h3>Coming soon</h3>\n'
            f'            <span class="by">Subscribe to get it first</span>\n'
            f'            <span class="go">Subscribe {ARROW}</span>\n'
            f'          </a>')


def main():
    json_path = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None
    posts = fetch_posts(json_path)
    # Number posts oldest-first so No. 1 stays No. 1; show the newest three.
    total = len(posts)
    shown = posts[:SLOTS]
    cards = [card(total - i, p) for i, p in enumerate(shown)]
    cards += [soon(total + k + 1) for k in range(SLOTS - len(shown))]
    block = START + "\n" + "\n".join(cards) + "\n          " + END
    s = INDEX.read_text(encoding="utf-8")
    new = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda m: block, s, count=1, flags=re.S)
    if START not in s:
        sys.exit("papers markers not found in index.html")
    if new != s:
        INDEX.write_text(new, encoding="utf-8")
        print(f"updated: {len(shown)} of {total} post(s)")
    else:
        print("no change")


if __name__ == "__main__":
    main()
