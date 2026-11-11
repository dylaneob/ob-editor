#!/usr/bin/env python3
"""Real recorded sound effects from Openverse (api.openverse.org, the WordPress team's search of 5M+ openly licensed audio files),
for when the kits (sfx.py, sfx_real, sfx_tai) don't have the sound a moment needs: a cash register, a camera shutter, a crowd gasp.
From @hugomxnning's "3 free sound effect tools for Claude" (OB 2026-11-01: "download this to our editor skill long form and short").

OB 2026-11-01 on licences: "Short form never needs licenses and long form I doubt we need it for sound effects". So no licence
filter and no credits to write. Results still rank CC0 / public domain first, and every download is logged with its source page in
<library>/SOURCES.csv, so a YouTube claim (rare for sound effects) can be answered in a minute.

    python3 -I openverse_sfx.py search "soft whoosh" [--n 5] [--max-s 4] [--out DIR] [--any-length]
    python3 -I openverse_sfx.py sources [--out DIR]

Downloads land in DIR/<query>/ (default /Volumes/T7/OB-EDITS/sfx-library/openverse). Pick between them by ear with earshot
(`~/ob-editor/bin/earshot match DIR "a soft whoosh"`), then plan them like any SFX (skill: Sound is synthesized in code, the caps).
No API key: anonymous requests are rate-limited, so search for what a cut needs, not the whole catalogue.
"""
import csv, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request

API = "https://api.openverse.org/v1/audio/"
UA = "ob-editor-openverse/1.0 (OB Health in-house editor; one query per sound needed)"
LIB = os.path.expanduser("~/ob-editor/assets/sfx_library/openverse")   # rebuild 2026-11-10: the T7 is full and the gate/index read the internal bank; run bank_index.py build after a download
RANK = {"cc0": 0, "pdm": 0, "by": 1, "by-sa": 2, "by-nd": 3, "by-nc": 4, "by-nc-sa": 4, "by-nc-nd": 5, "sampling+": 5, "nc-sampling+": 6}
COLS = ["file", "query", "title", "creator", "license", "license_version", "source", "landing_page", "file_url", "duration_s", "downloaded"]


def get(url, tries=3):
    """Openverse's search is sometimes slow (a two-word query timed out at 30 s on 11-01): 60 s, three tries"""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    for k in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except (TimeoutError, urllib.error.URLError) as e:
            if k == tries - 1 or getattr(e, "code", None) in (400, 401, 403, 404): raise
            time.sleep(2 * (k + 1))


def search(q, n=5, max_s=4.0, out=LIB, any_length=False):
    qs = {"q": q, "page_size": 20, "mature": "false"}   # anonymous requests: 20 a page at most (40 got a 401); the "sound_effect"
    # category returns nothing (most sounds come from Freesound untagged), so the length cap does that job
    data = json.loads(get(API + "?" + urllib.parse.urlencode(qs)))
    res = [r for r in data.get("results", []) if r.get("url")]
    if not any_length:
        res = [r for r in res if r.get("duration") and r["duration"] / 1000 <= max_s]
    res.sort(key=lambda r: (RANK.get((r.get("license") or "").lower(), 7), r.get("duration") or 1e9))
    slug = re.sub(r"[^a-z0-9]+", "-", q.lower()).strip("-")[:40] or "sound"
    d = os.path.join(out, slug); os.makedirs(d, exist_ok=True)
    log = os.path.join(out, "SOURCES.csv"); new = not os.path.exists(log); got = []
    for r in res[:n]:
        ext = (r.get("filetype") or os.path.splitext(urllib.parse.urlparse(r["url"]).path)[1].lstrip(".") or "mp3").lower()
        name = f"{slug}_{len(got) + 1:02d}_{re.sub(r'[^A-Za-z0-9]+', '-', r.get('title') or 'untitled')[:40].strip('-')}.{ext}"
        path = os.path.join(d, name)
        try:
            blob = get(r["url"])
        except Exception as e:   # one dead link doesn't stop the rest
            print(f"  skip {r.get('title')!r}: {e}"); continue
        open(path, "wb").write(blob); got.append(path)
        with open(log, "a", newline="") as f:
            w = csv.writer(f)
            if new: w.writerow(COLS); new = False
            w.writerow([path, q, r.get("title"), r.get("creator"), r.get("license"), r.get("license_version"), r.get("source") or r.get("provider"),
                        r.get("foreign_landing_url"), r.get("url"), round((r.get("duration") or 0) / 1000, 2), time.strftime("%Y-%m-%d %H:%M")])
        print(f"  {len(got)}. {(r.get('duration') or 0) / 1000:5.2f} s  {(r.get('license') or '?'):6s}  {r.get('title')}  ->  {path}")
        time.sleep(0.5)   # gentle on the anonymous rate limit
    print(f"{len(got)} of {len(res)} matching sounds downloaded to {d} ({data.get('result_count', 0)} hits for {q!r})")
    return got


if __name__ == "__main__":
    a = sys.argv[1:]
    opt = lambda k, dflt: a[a.index(k) + 1] if k in a else dflt
    if a[:1] == ["search"] and len(a) > 1:
        search(a[1], int(opt("--n", 5)), float(opt("--max-s", 4)), opt("--out", LIB), "--any-length" in a)
    elif a[:1] == ["sources"]:
        p = os.path.join(opt("--out", LIB), "SOURCES.csv"); print(open(p).read() if os.path.exists(p) else "no downloads yet")
    else:
        print(__doc__); sys.exit(2)
