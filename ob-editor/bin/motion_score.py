#!/usr/bin/env python3
"""Motion score of a finished video, measured from its pixels (2026-10-28, from the reels OB sent to upgrade the editor: Adilet's
De4byPBoLWT "scores its own motion and fixes the weak moments", speedy_devv's DeyusrQMOmi "checks every frame" and flags a JUMP).
Works on ANY file: our renders from every pipeline (tenten2, react, lecture, tier, assemble.py), posted reels and the reference
being copied, so "match the reference's pace" is the same measurement on both. precheck.sh / pace_check.py stay the plan-based gates
for long-form; this one reads the render itself, so it also sees what a plan can't (a GSAP flash frame, a panel that never moved).

For every frame (gray, 144x256, at the file's own frame rate; 50/60 fps files are read at half rate) it takes the share of pixels that changed since the frame before, then reports:
  events     a visual change starting: a cut, a card or word landing, a zoom kick, a slide. A frame whose changed area jumps above
             both a floor and 3x the median of the 0.4 s before it; events closer than 0.2 s count once.
  cuts       a change over most of the frame (a hard cut or a full-frame swap).
  idle       time more than --still seconds (1.2) after the last event while the picture is also near-static (under 1.2% of it
             moving, averaged over 0.2 s), so a scrolling timeline or a moving camera counts as alive. "Nothing still > 1.2 s" is the
             rule in Adilet's patterns.md; it matches the motion library's A2 (a panel holds no more than about 0.5 s).
  live       10 x the share of the runtime that is NOT idle: the score out of 10.
  first      seconds until anything first moves (over 1.2% of the frame changing). A video that opens on a frozen picture shows it
             here; the references move from frame 1.
  flash      a single frame that differs from both neighbours while they match each other: a one-frame glitch or a frame-0 flash.
             Any flash fails the file (exit 1) unless --allow-flash. Sabotage test on 8 s of GUT Kyle (2026-10-28): a white
             frame, a black box over the captions (8.5% of the frame), a red box (19%) and a yellow frame 0 were caught; a 2.8% box
             was missed (it hides under a talking head's own motion). A designed cover on frame 0 also reads as a flash.

  python3 -I motion_score.py FILE [FILE ...] [--png DIR] [--json OUT.json] [--still 1.2] [--min-live 0] [--allow-flash]

--png DIR writes a strip per file (bars: changed area per 0.1 s; green ticks: events; blue: cuts; red bands: idle; red marks: flash
frames) so the weak moments can be read at a glance. --min-live N fails (exit 1) any file scoring under N. Exit codes: 0 clean,
1 a flash frame or a score under --min-live, 2 a file could not be read.

Calibration (2026-10-28) is in references/motion-library.md, section F: the four reference reels against OB's delivered edits.
"""
import argparse, json, os, subprocess, sys
import numpy as np

W, H = 144, 256
DIFF = 14            # a pixel "changed" when its gray level moved more than this
FLOOR = 0.012        # an event needs at least this share of the frame changing
JUMP = 3.0           # ... and this many times the median of the 0.4 s before it
CUT = 0.55           # a change over this share of the frame is a cut / full-frame swap
MERGE = 0.2          # events closer than this are one event


def frames(path):
    """Gray frames at the file's own rate (never resampled to a rate it doesn't have: a resample duplicates frames, which would
    hide a one-frame flash). 50/60 fps files are read at exactly half rate, so per-frame change means the same thing everywhere."""
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate", "-of", "csv=p=0",
                        path], capture_output=True, text=True).stdout.strip()
    r = r.splitlines()[0].split(",")[0] if r else r   # ffprobe 8 can print "30000/1001," (a trailing empty field): C4407 tests read "unreadable" (11-03)
    try:
        num, den = (int(x) for x in r.split("/")); fps = num / den
    except ValueError:
        return None, 0
    vf = f"scale={W}:{H}:flags=area,format=gray"
    if fps > 31: vf = f"fps={num}/{2 * den}," + vf; fps /= 2
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", path, "-an", "-vf", vf, "-f", "rawvideo", "-"],
                         capture_output=True).stdout
    n = len(raw) // (W * H)
    if n < 3: return None, 0
    f = np.frombuffer(raw[:n * W * H], np.uint8).reshape(n, H, W).astype(np.int16)
    # 3x3 box blur so codec noise doesn't count as change
    p = np.pad(f, ((0, 0), (1, 1), (1, 1)), mode="edge")
    return sum(p[:, y:y + H, x:x + W] for y in range(3) for x in range(3)) // 9, fps


def measure(path, still):
    f, FPS = frames(path)
    if f is None: return None
    n = len(f); dur = n / FPS; base_n = max(2, round(0.4 * FPS)); mov_n = max(3, round(0.23 * FPS) | 1)
    area = np.zeros(n)
    area[1:] = (np.abs(f[1:] - f[:-1]) > DIFF).mean(axis=(1, 2))
    # events: onsets above the recent baseline
    ev, last = [], -1e9
    for t in range(1, n):
        base = np.median(area[max(1, t - base_n):t]) if t > 1 else 0.0
        if area[t] > FLOOR and area[t] > JUMP * base and (t - last) / FPS >= MERGE:
            ev.append(t); last = t
    cuts, lastc = [], -1e9
    for t in range(1, n):
        if area[t] > CUT and (t - lastc) / FPS >= MERGE: cuts.append(t); lastc = t
    # flash frames: t differs from t-1 and t+1, while t-1 and t+1 match each other
    # (and it stands out from the motion around it, so a deliberate flicker animation that changes every frame doesn't count)
    flash = []
    for t in range(1, n - 1):
        a, b = area[t], area[t + 1]
        if a > 0.02 and b > 0.02 and area[t - 1] < 0.5 * min(a, b) and (t + 2 >= n or area[t + 2] < 0.5 * min(a, b)):
            ab = (np.abs(f[t + 1] - f[t - 1]) > DIFF).mean()
            if ab < 0.45 * min(a, b): flash.append(t)
    # the opening frames (0, or 0-1, or 0-2) differ from a steady picture right after them: a card painted on frame 0 only (the GSAP
    # frame-0 bug) or a slate. The first frame is what a feed shows before play, so it counts as a flash.
    j = next((j for j in range(1, min(4, n - 2)) if area[j] > 0.04), None)
    if j is not None and area[j + 1] < 0.25 * area[j] and (np.abs(f[j + 1] - f[0]) > DIFF).mean() > 0.5 * area[j]:
        flash.insert(0, 0)
    # idle: more than `still` seconds since the last event (frame 0 counts as an event: the first picture) and nothing moving now
    moving = np.convolve(area, np.ones(mov_n) / mov_n, mode="same") > FLOOR
    marks = [0] + ev
    idle = np.zeros(n, bool)
    for k, s in enumerate(marks):
        e = marks[k + 1] if k + 1 < len(marks) else n
        lo = s + int(round(still * FPS))
        if lo < e: idle[lo:e] = True
    idle &= ~moving
    runs, t = [], 0
    while t < n:
        if idle[t]:
            j = t
            while j < n and idle[j]: j += 1
            runs.append((round(t / FPS, 2), round(j / FPS, 2))); t = j
        else: t += 1
    gaps = np.diff([0] + ev + [n]) / FPS
    live = 10 * (1 - idle.mean())
    return {"file": path, "dur": round(dur, 2), "events": len(ev), "events_min": round(len(ev) / dur * 60, 1),
            "cuts": len(cuts), "cuts_min": round(len(cuts) / dur * 60, 1),
            "gap_median": round(float(np.median(gaps)), 2), "gap_p90": round(float(np.percentile(gaps, 90)), 2),
            "gap_max": round(float(gaps.max()), 2), "idle_share": round(float(idle.mean()), 3), "live": round(live, 1),
            "first": next((round(t / FPS, 2) for t in range(1, n) if area[t] > FLOOR), None), "flash": [round(t / FPS, 3) for t in flash],
            "idle_runs": sorted(runs, key=lambda r: r[0] - r[1])[:8],
            "event_times": [round(t / FPS, 2) for t in ev], "cut_times": [round(t / FPS, 2) for t in cuts],
            "fps": round(FPS, 3), "_area": area, "_idle": idle}


def strip(m, out):
    from PIL import Image, ImageDraw
    area, idle, fps = m["_area"], m["_idle"], m["fps"]; n = len(area); dur = n / fps; bins = int(np.ceil(dur * 10))   # 0.1 s bins
    Wp, Hp, top = min(2000, max(600, bins * 3)), 150, 22   # capped so a long edit still reads on one screen
    im = Image.new("RGB", (Wp, Hp + top + 16), (250, 250, 248)); d = ImageDraw.Draw(im)
    x = lambda t: int(t / dur * Wp)
    for b in range(bins):
        sl = slice(int(b * fps / 10), max(int(b * fps / 10) + 1, min(n, int((b + 1) * fps / 10))))
        if idle[sl].all(): d.rectangle([x(b / 10), top, x((b + 1) / 10), top + Hp], fill=(255, 214, 214))
        h = int(np.sqrt(min(1.0, area[sl].max())) * Hp)
        d.rectangle([x(b / 10), top + Hp - h, x((b + 1) / 10) - 1, top + Hp], fill=(60, 60, 60))
    for t in m["event_times"]: d.line([x(t), 4, x(t), top - 2], fill=(20, 150, 60), width=2)
    for t in m["cut_times"]: d.line([x(t), top, x(t), top + 8], fill=(30, 90, 220), width=3)
    for t in m["flash"]: d.polygon([(x(t) - 5, top + Hp + 14), (x(t) + 5, top + Hp + 14), (x(t), top + Hp + 2)], fill=(220, 30, 30))
    for s in range(0, int(dur) + 1, 5): d.text((x(s) + 2, top + Hp + 3), f"{s}s", fill=(90, 90, 90))
    d.text((Wp - 330, 6), f"live {m['live']}/10  events {m['events_min']}/min  idle {m['idle_share']:.0%}", fill=(0, 0, 0))
    im.save(out); return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("files", nargs="+"); ap.add_argument("--png"); ap.add_argument("--json")
    ap.add_argument("--still", type=float, default=1.2); ap.add_argument("--min-live", type=float, default=0.0)
    ap.add_argument("--allow-flash", action="store_true")
    a = ap.parse_args()
    rows, bad, missing = [], 0, 0
    print(f"{'file':44s} {'dur':>6s} {'ev/min':>7s} {'cut/min':>7s} {'gap med':>7s} {'p90':>5s} {'max':>5s} {'idle':>5s} "
          f"{'live':>5s} {'first':>5s} flash")
    for p in a.files:
        m = measure(p, a.still)
        if m is None: print(f"{os.path.basename(p)[:44]:44s} unreadable"); missing += 1; continue
        print(f"{os.path.basename(p)[:44]:44s} {m['dur']:6.1f} {m['events_min']:7.1f} {m['cuts_min']:7.1f} {m['gap_median']:7.2f} "
              f"{m['gap_p90']:5.2f} {m['gap_max']:5.2f} {m['idle_share']:5.0%} {m['live']:5.1f} {str(m['first']):>5s} {len(m['flash'])}")
        if m["idle_runs"]: print("    longest idle: " + ", ".join(f"{s:.1f}-{e:.1f}s" for s, e in m["idle_runs"][:5]))
        if m["flash"]: print("    FLASH frames at: " + ", ".join(f"{t:.3f}s" for t in m["flash"][:12]))
        if a.png:
            os.makedirs(a.png, exist_ok=True)
            print("    strip: " + strip(m, os.path.join(a.png, os.path.splitext(os.path.basename(p))[0] + "_motion.png")))
        if (m["flash"] and not a.allow_flash) or m["live"] < a.min_live: bad += 1
        rows.append({k: v for k, v in m.items() if not k.startswith("_")})
    if a.json:
        with open(a.json, "w") as fh: json.dump(rows, fh, indent=1)
    sys.exit(2 if missing else (1 if bad else 0))


if __name__ == "__main__":
    main()
