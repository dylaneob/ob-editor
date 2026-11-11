#!/usr/bin/env python3
"""Titles and labels never cross a face on full-frame footage, anyone's (C4395 v4, 2026-10-29: the QC gate's text_face failed
CH3/CH9/CH10, chapter titles across a stock person's mouth; his own face is guarded by overlay_touch.py and qc_gate text_face).

  python3 -I card_faces.py rendered WORK ID [ID ...]        frames at 4 fps of render/events/ID.mp4, Apple Vision faces + text
                                                            (bin/frame_obstacles): every real text box touching a face box
  python3 -I card_faces.py windows ZONE NEED_S CLIP [...]   where in a stock clip no face enters the card's title zone
      ZONE = "[x0, y0, x1, y1]" in fractions of the frame (C4395 chapter cards: x0 .03, y0 .26, y1 .48, x1 = title end + .03)
      CLIP = a Pexels id (OB-ARCHIVE/OB-EDITS/stock/pexels/ID.mp4) or a path; prints the face-free windows >= NEED_S seconds
Pick the stock window with `windows` before cutting the piece (prep_broll), and check the render with `rendered`.
"""
import json, os, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import qc_gate as Q
OBS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frame_obstacles")


def frames(path, fps, width):
    td = tempfile.TemporaryDirectory()
    subprocess.run(["nice", "-n", "10", "ffmpeg", "-nostdin", "-v", "error", "-i", path, "-vf", f"fps={fps},scale={width}:-2", "-q:v", "3",
                    f"{td.name}/f%04d.jpg"], check=True)
    for k, f in enumerate(sorted(os.listdir(td.name))):
        try: yield k / fps, json.loads(subprocess.run([OBS, f"{td.name}/{f}"], capture_output=True, text=True).stdout or "{}")
        except ValueError: continue
    td.cleanup()


def rendered(W, ids):
    bad = 0
    for i in ids:
        p = f"{W}/render/events/{i}.mp4"
        if not os.path.exists(p): print(i, "no render"); continue
        hits, n = [], 0
        for t, d in frames(p, 4, 1920):
            n += 1; txt = [x for x in d.get("texts", []) if Q.real_text(x[4])]
            for fx, fy, fw, fh in d.get("faces", []):
                for x, y, w, h, s in txt:
                    a = max(0, min(fx + fw, x + w) - max(fx, x)) * max(0, min(fy + fh, y + h) - max(fy, y))
                    if a: hits.append((round(t + 0.125, 2), round(a / (fw * fh), 2), s[:30]))
        bad += bool(hits)
        print(f"{i:7s} {n:3d} frames, {len(hits):3d} text-on-face, worst {max((h[1] for h in hits), default=0):.0%} of a face"
              + (f"  e.g. {max(hits, key=lambda h: h[1])}" if hits else ""), flush=True)
    return 1 if bad else 0


def windows(zone, need, clips):
    for c in clips:
        src = c if os.path.exists(c) else f"/Volumes/OB-ARCHIVE/OB-EDITS/stock/pexels/{c}.mp4"
        dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", src], capture_output=True, text=True).stdout)
        fps = 4 if dur < 40 else 2; hit = []
        for t, d in frames(src, fps, 960):
            Wd, Hd = d.get("w", 960), d.get("h", 540)
            hit.append(any(fx / Wd < zone[2] and (fx + fw) / Wd > zone[0] and fy / Hd < zone[3] and (fy + fh) / Hd > zone[1] for fx, fy, fw, fh in d.get("faces", [])))
        wins, s = [], None
        for k, h in enumerate(hit + [True]):
            if not h and s is None: s = k
            if h and s is not None:
                if (k - s) / fps >= need: wins.append((round(s / fps, 2), round(k / fps, 2)))
                s = None
        print(f"{os.path.basename(src)}: {dur:.1f} s, a face in the zone in {sum(hit)}/{len(hit)} frames; free windows >= {need} s: {wins[:8]}", flush=True)
    return 0


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) >= 3 and a[0] == "rendered": sys.exit(rendered(a[1].rstrip("/"), a[2:]))
    if len(a) >= 4 and a[0] == "windows": sys.exit(windows(json.loads(a[1]), float(a[2]), a[3:]))
    print(__doc__); sys.exit(2)
