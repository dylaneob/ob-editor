#!/usr/bin/env python3
"""
trending_sounds.py — refresh data/trending-sounds.json from a live, unauthenticated source.

Why this exists: IG's own "trending audio" surface lives only inside the mobile app's
Reels/professional dashboard — there is no public web page or API for it. TikTok's
Creative Center trending-music page is client-side rendered (its raw HTML carries no
song data) and requires the app/login for real browsing. The one source found that
(a) is reachable with a plain HTTP GET, no login, no JS execution, and (b) embeds real
song/artist/usage data directly in server-rendered HTML is tokchart.com's homepage —
but only its top ~5 rows are unblurred for non-subscribers; rows 6-25+ are paywalled.

This script:
  1. curls https://tokchart.com/ (stdlib subprocess, desktop user-agent)
  2. parses the server-rendered <table> rows with regex for title/artist/genre/UGC-count
  3. rewrites data/trending-sounds.json with whatever real rows it found
  4. prints a one-line summary to stdout
  5. on any failure (network, markup change, paywall-only), fails gracefully: leaves the
     existing trending-sounds.json untouched and prints named manual alternatives.

stdlib + curl subprocess only. No pip installs, no headless browser.

Usage: python3 bin/trending_sounds.py
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_PATH = os.path.join(HERE, "..", "data", "trending-sounds.json")

SOURCE_URL = "https://tokchart.com/"
SOURCE_LABEL = ("tokchart.com (free/unauthenticated homepage — top ~5 rows are "
                "unblurred; rows 6-25 require paid subscription and are not fetched)")

MANUAL_ALTERNATIVES = """\
[trending_sounds] Could not refresh from tokchart.com. Manual alternatives:
  1. TikTok in-app: Create -> Add sound -> "Trending" tab (requires the TikTok app).
  2. TikTok Ads Creative Center (web, but JS-rendered + often region/login gated):
     https://ads.tiktok.com/business/creativecenter/inspiration/popular/music/pc/en
  3. tokchart.com in a real browser (https://tokchart.com/) — a paid plan unlocks
     the full top-25+ list instead of just the free top ~5.
  4. tokboard (https://www.tokboard.com/) if it's back up — was unreachable (HTTP 530)
     as of 2026-07-04.
  5. Instagram in-app: Reels camera -> Audio search -> "Trending" shelf, or
     Professional Dashboard -> Content You Shared -> trending audio suggestions.
     IG trending audio has no public web/API surface at all — app-only by design.
  6. Ask a coach/team member with the TikTok or IG app open to screenshot the
     trending-sounds shelf directly.
The existing data/trending-sounds.json was left unchanged.
"""


def curl_get(url, timeout=20):
    """Fetch a URL with curl via subprocess. Returns (ok, body_or_error)."""
    try:
        result = subprocess.run(
            [
                "curl", "-s", "-L", "--max-time", str(timeout),
                "-A", ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"),
                url,
            ],
            capture_output=True, text=True, timeout=timeout + 5,
        )
    except Exception as e:
        return False, f"curl subprocess failed: {e}"
    if result.returncode != 0:
        return False, f"curl exited {result.returncode}: {result.stderr.strip()}"
    if not result.stdout or len(result.stdout) < 500:
        return False, "curl returned an empty/too-short response"
    return True, result.stdout


# Row blocks are delimited by <tr ...> ... </tr>. We split on those and extract
# title/artist/genre/UGC-count *within each row* so columns never misalign across rows.
ROW_SPLIT_RE = re.compile(r'<tr\b.*?</tr>', re.S)
TITLE_RE = re.compile(r'font-medium max-w-\[150px\][^>]*>([^<]*)</div>', re.S)
ARTIST_RE = re.compile(r'flex gap-x-1 items-center max-w-\[180px\][^>]*>\s*([^<\n]*?)\s*</div>', re.S)
GENRE_RE = re.compile(r'<span>((?:Pop|Dance|Alternative|Hip-Hop|R&B|Rock|Electronic|'
                       r'Country|Latin|Afrobeats|K-Pop|Indie|Folk)[^<]*)</span>')
# First font-bold stat column in a row is chart score; the "UGC Videos" column is the
# second occurrence of the font-bold/text-gray-500 pair inside that row.
STAT_PAIR_RE = re.compile(
    r'font-bold">\s*([\d.,]+[KM]?\+?)\s*</div>\s*<div class="pl-4 text-xs text-gray-500">\s*([\d,]+\+?)'
)


BLUR_MARKER = "preview-row-blur"


def parse_tokchart(html):
    """Extract only the real (non-blurred/non-paywalled) rows. Returns list of dicts.

    tokchart marks paywalled rows with a `preview-row-blur` CSS class on wrapper divs
    and fills them with placeholder text ("Hidden Song Title", "Subscribe Now", etc).
    We cut the document off at the first occurrence of that marker so we never parse
    placeholder rows as if they were real trending sounds.
    """
    cutoff = html.find(BLUR_MARKER)
    real_html = html if cutoff == -1 else html[:cutoff]

    sounds = []
    for row in ROW_SPLIT_RE.findall(real_html):
        title_m = TITLE_RE.search(row)
        if not title_m or not title_m.group(1).strip():
            continue
        title = title_m.group(1).strip()

        artist_m = ARTIST_RE.search(row)
        artist = artist_m.group(1).strip() if artist_m and artist_m.group(1).strip() else "unknown"
        # dedupe accidental "Name , Name" artist captures from nested markup
        parts = [p.strip() for p in artist.split(",")]
        if len(parts) > 1 and all(p == parts[0] for p in parts):
            artist = parts[0]

        genre_m = GENRE_RE.search(row)
        genre = genre_m.group(1) if genre_m else None

        stat_pairs = STAT_PAIR_RE.findall(row)
        # first pair = chart score, second pair (if present) = UGC videos
        ugc = stat_pairs[1] if len(stat_pairs) > 1 else None

        note_parts = []
        if genre:
            note_parts.append(f"{genre} genre")
        if ugc:
            note_parts.append(f"{ugc[0]} UGC videos ({ugc[1]} exact)")
        note = "; ".join(note_parts) if note_parts else "tiktok trending sound (tokchart free tier)"
        sounds.append({
            "name": title,
            "artist": artist,
            "platform": "tiktok",
            "note": note,
        })
    return sounds


def main():
    ok, body = curl_get(SOURCE_URL)
    if not ok:
        print(f"[trending_sounds] fetch failed: {body}", file=sys.stderr)
        print(MANUAL_ALTERNATIVES, file=sys.stderr)
        sys.exit(1)

    try:
        sounds = parse_tokchart(body)
    except Exception as e:
        print(f"[trending_sounds] parse failed (site markup likely changed): {e}", file=sys.stderr)
        print(MANUAL_ALTERNATIVES, file=sys.stderr)
        sys.exit(1)

    if not sounds:
        print("[trending_sounds] fetch succeeded but no rows parsed — site markup likely changed.",
              file=sys.stderr)
        print(MANUAL_ALTERNATIVES, file=sys.stderr)
        sys.exit(1)

    out = {
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "source": SOURCE_LABEL,
        "sounds": sounds,
        "refresh_how": (
            "Run `python3 bin/trending_sounds.py` from ~/ob-moments. It curls "
            "https://tokchart.com/ (plain GET, desktop user-agent, no login), parses "
            "the server-rendered HTML rows for the free/unblurred top sounds, and "
            "rewrites this file with fresh data + a new fetched_at date. If tokchart's "
            "markup changes or the page goes fully client-rendered/paywalled, the "
            "script fails gracefully and prints manual alternatives (TikTok Creative "
            "Center app, tokchart.com in-browser, tokboard, kworb if it returns, or the "
            "Sounds/Discover tab inside the TikTok/IG app — trending audio discovery is "
            "largely app-only by design). Treat data as directional, not authoritative; "
            "verify any specific sound is business-safe in-app before using it."
        ),
    }

    with open(OUT_PATH, "w") as f:
        json.dump(out, f, indent=2)

    print(f"[trending_sounds] wrote {len(sounds)} sounds from {SOURCE_URL} -> {OUT_PATH}")
    for s in sounds:
        print(f"  - {s['name']} — {s['artist']} ({s['note']})")


if __name__ == "__main__":
    main()
