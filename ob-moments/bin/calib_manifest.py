#!/usr/bin/env python3
"""
calib_manifest.py — build a calibration manifest of OB's published YouTube Shorts.

For each Short (<=90s) in the yt-meta cache, record views + metadata and compute an
ERA-ADJUSTED OUTLIER RATIO: views divided by the median views of Shorts posted within
+/-45 days. This controls for channel growth and algorithm era so we're measuring how
much a Short over/under-performed *its own moment*, not raw views (which just track
how long ago it was posted and how big the channel was then).

Writes calib/shorts_manifest.json.
"""
import json, glob, os, statistics as st

CACHE = os.path.expanduser("~/ob-social-dashboard/data/yt-meta")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "calib")
WINDOW_DAYS = 45
MIN_NEIGHBORS = 8


def ordinal(yyyymmdd):
    try:
        y, m, d = int(yyyymmdd[:4]), int(yyyymmdd[4:6]), int(yyyymmdd[6:8])
        return y * 372 + m * 31 + d           # cheap monotonic day index
    except Exception:
        return None


def main():
    os.makedirs(OUT, exist_ok=True)
    rows = []
    for f in glob.glob(os.path.join(CACHE, "*.json")):
        try:
            j = json.load(open(f))
        except Exception:
            continue
        dur = j.get("duration")
        try:
            dur = int(dur)
        except Exception:
            continue
        if dur > 90:
            continue
        v = j.get("view_count")
        if not isinstance(v, int) or v <= 0:
            continue
        od = ordinal(j.get("upload_date", "") or "")
        if od is None:
            continue
        rows.append({
            "id": j.get("id") or os.path.basename(f)[:-5],
            "dur": dur, "views": v, "upload_date": j.get("upload_date"),
            "ord": od,
            "likes": j.get("like_count") or 0,
            "comments": j.get("comment_count") or 0,
            "followers_at_pull": j.get("channel_follower_count") or 0,
            "title": (j.get("title") or "").strip(),
        })

    # era-adjusted outlier ratio: views / median(views of neighbors within +/-45 days)
    for r in rows:
        neigh = [x["views"] for x in rows
                 if x is not r and abs(x["ord"] - r["ord"]) <= WINDOW_DAYS * (372 / 365.0)]
        if len(neigh) < MIN_NEIGHBORS:
            # widen to nearest 20 by date if the window is too sparse
            near = sorted(rows, key=lambda x: abs(x["ord"] - r["ord"]))[1:21]
            neigh = [x["views"] for x in near]
        med = st.median(neigh) if neigh else r["views"]
        r["local_median_views"] = med
        r["outlier"] = round(r["views"] / med, 3) if med else 1.0
        r["engagement"] = round((r["likes"] + r["comments"]) / r["views"], 4) if r["views"] else 0.0

    for r in rows:
        r.pop("ord", None)
    rows.sort(key=lambda r: -r["outlier"])
    json.dump(rows, open(os.path.join(OUT, "shorts_manifest.json"), "w"), indent=2)
    vs = [r["views"] for r in rows]
    print(f"[calib] {len(rows)} shorts with views")
    print(f"[calib] views: median {int(st.median(vs))}, max {max(vs)}, min {min(vs)}")
    print(f"[calib] outlier ratio: median {st.median([r['outlier'] for r in rows]):.2f}, "
          f"top {rows[0]['outlier']:.1f}x ({rows[0]['title'][:40]})")
    print(f"[calib] wrote {os.path.join(OUT, 'shorts_manifest.json')}")


if __name__ == "__main__":
    main()
