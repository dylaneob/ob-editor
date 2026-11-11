#!/usr/bin/env python3
"""
yt_retention.py — pull your real audience-retention curve per video (owner-only).

This is the ground truth the calibration needs: for each of your videos it returns
~100 points of `audienceWatchRatio` (>1.0 = a rewatch spike) across the video's
timeline, plus `relativeRetentionPerformance` (how the whole video holds vs peers).
Unlike the public "most replayed" heatmap, this works for EVERY video you own at ANY
view count, because it's your data.

Usage:
  python3 bin/yt_retention.py <VIDEO_ID>          # one video, prints the curve
  python3 bin/yt_retention.py --all               # every long-form id in the yt-meta
                                                    cache → calib/retention/<id>.json
Run bin/yt_auth.py once first.
"""
import os, sys, json, glob
import datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from yt_auth import get_creds                                   # noqa

CACHE = os.path.expanduser("~/ob-social-dashboard/data/yt-meta")
OUT = os.path.join(HERE, "..", "calib", "retention")


def client():
    from googleapiclient.discovery import build
    return build("youtubeAnalytics", "v2", credentials=get_creds(), cache_discovery=False)


def retention(yta, video_id):
    """Return {elapsed_ratio:[...], watch_ratio:[...], rel_performance:float|None} or None."""
    resp = yta.reports().query(
        ids="channel==MINE", startDate="2005-01-01",
        endDate=dt.date.today().isoformat(),
        metrics="audienceWatchRatio,relativeRetentionPerformance",
        dimensions="elapsedVideoTimeRatio", filters=f"video=={video_id}",
    ).execute()
    rows = resp.get("rows") or []
    if not rows:
        return None
    return {
        "video_id": video_id,
        "elapsed_ratio": [r[0] for r in rows],
        "watch_ratio": [r[1] for r in rows],
        "rel_performance": rows[0][2] if len(rows[0]) > 2 else None,
    }


def long_form_ids():
    ids = []
    for f in glob.glob(os.path.join(CACHE, "*.json")):
        try:
            d = json.load(open(f))
            if int(d.get("duration") or 0) > 90:
                ids.append(d.get("id") or os.path.basename(f)[:-5])
        except Exception:
            pass
    return ids


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    yta = client()
    if sys.argv[1] == "--all":
        os.makedirs(OUT, exist_ok=True)
        ids = long_form_ids()
        got = 0
        for i, vid in enumerate(ids, 1):
            try:
                r = retention(yta, vid)
            except Exception as e:
                print(f"  {vid}: error {e}", file=sys.stderr); continue
            if r:
                json.dump(r, open(os.path.join(OUT, f"{vid}.json"), "w"))
                got += 1
            if i % 20 == 0:
                print(f"[retention] {i}/{len(ids)}  with_data={got}", file=sys.stderr)
        print(f"[retention] done: {got}/{len(ids)} videos had retention data -> {OUT}")
    else:
        r = retention(yta, sys.argv[1])
        print(json.dumps(r, indent=2) if r else "no retention data for that video")


if __name__ == "__main__":
    main()
