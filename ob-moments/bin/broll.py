#!/usr/bin/env python3
"""broll.py — fetch matched stock B-roll from Pexels (free API) by keyword.

Search Pexels Videos for a keyword, pick the best clip (prefers the requested
orientation, a usable duration, and the highest resolution <= 1080p link), and
download it to a local cache. Used by the EXPLAINER render mode to lay a matched
visual over each concrete noun the speaker names.

KEY: set PEXELS_API_KEY in the env, or drop the key in ~/.pexels_key (one line).
Get a free key at https://www.pexels.com/api/ . No attribution required.

CLI:
  broll.py "gut microbiome" --orientation portrait --min-dur 3
  broll.py --plan plan.json --outdir workdir/broll   # batch: resolve every keyword

A plan is a JSON list of {"keyword": str, "start": float, "end": float,
"mode": "full"|"pip"}. Batch mode downloads one clip per unique keyword and
writes plan.resolved.json mapping each entry to a local file (or null on miss,
so the renderer holds on the speaker and the edit list keeps the placeholder).
"""
import argparse, json, os, re, sys, urllib.parse, urllib.request

CACHE = os.path.expanduser("~/ob-moments/cache/broll")
API = "https://api.pexels.com/videos/search"


def _key():
    k = os.environ.get("PEXELS_API_KEY", "").strip()
    if not k:
        kf = os.path.expanduser("~/.pexels_key")
        if os.path.exists(kf):
            k = open(kf).read().strip()
    return k


def _slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60]


def search(keyword, orientation="portrait", min_dur=2, max_dur=30):
    """Return (mp4_url, meta) for the best match, or (None, reason)."""
    key = _key()
    if not key:
        return None, "no PEXELS_API_KEY (set env or ~/.pexels_key)"
    q = urllib.parse.urlencode({"query": keyword, "orientation": orientation,
                                "per_page": 15, "size": "medium"})
    req = urllib.request.Request(f"{API}?{q}", headers={"Authorization": key})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.load(r)
    except Exception as e:
        return None, f"pexels api error: {e}"
    vids = data.get("videos", [])
    if not vids:
        return None, "no results"
    # score: right orientation already filtered; prefer usable duration, then a
    # video-file link at ~1080p (not 4k = smaller/faster, not tiny)
    best, best_score = None, -1
    for v in vids:
        dur = v.get("duration", 0)
        if dur < min_dur:
            continue
        for f in v.get("video_files", []):
            h = f.get("height") or 0
            if not f.get("link", "").endswith(".mp4"):
                continue
            # prefer 1080p-ish, penalize 4k (huge) and sub-720
            res_score = 1000 - abs(1080 - h)
            dur_score = 100 if min_dur <= dur <= max_dur else 40
            score = res_score + dur_score
            if score > best_score:
                best_score, best = score, (f["link"], {"id": v["id"], "dur": dur,
                                                        "h": h, "w": f.get("width")})
    if not best:
        return None, "no suitable file"
    return best


def download(keyword, orientation="portrait", min_dur=2):
    """Fetch + cache the best clip for keyword. Returns local path or None."""
    os.makedirs(CACHE, exist_ok=True)
    dst = os.path.join(CACHE, f"{_slug(keyword)}-{orientation}.mp4")
    if os.path.exists(dst) and os.path.getsize(dst) > 10000:
        return dst
    url, meta = search(keyword, orientation, min_dur)
    if not url:
        sys.stderr.write(f"[broll] MISS '{keyword}': {meta}\n")
        return None
    try:
        urllib.request.urlretrieve(url, dst)
    except Exception as e:
        sys.stderr.write(f"[broll] download failed '{keyword}': {e}\n")
        return None
    sys.stderr.write(f"[broll] OK '{keyword}' -> {os.path.basename(dst)} "
                     f"({meta.get('h')}p {meta.get('dur')}s)\n")
    return dst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("keyword", nargs="?")
    ap.add_argument("--orientation", default="portrait", choices=["portrait", "landscape"])
    ap.add_argument("--min-dur", type=float, default=2)
    ap.add_argument("--plan", help="JSON list of {keyword,start,end,mode} to resolve in batch")
    ap.add_argument("--out")
    a = ap.parse_args()

    if not _key():
        sys.exit("[broll] no Pexels key. Get one free at https://www.pexels.com/api/ "
                 "then: export PEXELS_API_KEY=... (or echo it into ~/.pexels_key)")

    if a.plan:
        plan = json.load(open(a.plan))
        resolved = []
        for e in plan:
            kw = e.get("keyword")
            path = download(kw, a.orientation, a.min_dur) if kw else None
            resolved.append({**e, "file": path})
        out = a.plan.replace(".json", "") + ".resolved.json"
        json.dump(resolved, open(out, "w"), indent=1)
        hits = sum(1 for r in resolved if r.get("file"))
        print(f"[broll] resolved {hits}/{len(resolved)} keyword(s) -> {out}")
        return

    if not a.keyword:
        sys.exit("usage: broll.py <keyword>  |  broll.py --plan plan.json")
    p = download(a.keyword, a.orientation, a.min_dur)
    if not p:
        sys.exit(1)
    if a.out and p != a.out:
        import shutil; shutil.copy(p, a.out); p = a.out
    print(p)


if __name__ == "__main__":
    main()
