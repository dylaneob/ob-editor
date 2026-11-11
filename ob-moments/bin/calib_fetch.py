#!/usr/bin/env python3
"""
calib_fetch.py — pull auto-sub transcripts for every Short in the calibration
manifest. Skips ones already fetched; continues past failures (some Shorts have
no captions). Gentle rate-limit. Writes calib/subs/<id>.en.srt.
"""
import json, os, subprocess, time, sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "calib")
SUBS = os.path.join(ROOT, "subs")


def main():
    os.makedirs(SUBS, exist_ok=True)
    rows = json.load(open(os.path.join(ROOT, "shorts_manifest.json")))
    ok = fail = skip = 0
    for i, r in enumerate(rows, 1):
        vid = r["id"]
        out = os.path.join(SUBS, f"{vid}.en.srt")
        if os.path.exists(out):
            skip += 1
            continue
        try:
            subprocess.run(
                ["yt-dlp", "--skip-download", "--write-auto-sub", "--sub-lang", "en",
                 "--convert-subs", "srt", "-o", os.path.join(SUBS, "%(id)s.%(ext)s"),
                 f"https://www.youtube.com/watch?v={vid}"],
                capture_output=True, text=True, timeout=60)
            ok += 1 if os.path.exists(out) else 0
            fail += 0 if os.path.exists(out) else 1
        except Exception:
            fail += 1
        if i % 25 == 0:
            print(f"[fetch] {i}/{len(rows)}  ok={ok} fail={fail} skip={skip}", flush=True)
        time.sleep(0.25)
    print(f"[fetch] DONE ok={ok} fail={fail} skip={skip} "
          f"total_srt={len([f for f in os.listdir(SUBS) if f.endswith('.srt')])}", flush=True)


if __name__ == "__main__":
    main()
