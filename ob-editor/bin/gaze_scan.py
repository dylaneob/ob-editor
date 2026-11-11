#!/usr/bin/env python3
"""Find every moment in an EDL's cut where OB isn't looking into the lens (reading a script, glancing away).
OB 2026-10-18: "im looking away, make sure im always looking".

Samples the cut at 15 fps straight from the source (each row's own crop), runs `gaze` (Apple Vision eye landmarks)
and flags eyes-down where eye openness (eye height / width) < OPEN; a blink is shorter than MIN_S, so only runs of
MIN_S or more count. Prints the runs in edit time and writes WORK/gaze/NAME.json {samples, away}.

  python3 gaze_scan.py WORK NAME [--open 0.205] [--min 0.3]
Calibrated on C4359/C4360 (10-18): on the lens 0.24-0.35, reading 0.10-0.19.
"""
import argparse, glob, json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lecture_render as LR   # noqa: E402

GAZE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gaze")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("work"); ap.add_argument("name")
    ap.add_argument("--open", type=float, default=0.205); ap.add_argument("--min", type=float, default=0.3)
    a = ap.parse_args()
    spec = json.load(open(f"{a.work}/{a.name}_edl.json")); rows = spec["rows"]
    src = next(p for p in (f"/Volumes/T7/{spec['take']}.MP4", f"/Volumes/T7/RAW-FOOTAGE/camera/{spec['take']}.MP4") if os.path.exists(p))
    d = f"{a.work}/gaze/{a.name}"; os.makedirs(d, exist_ok=True)
    for f in glob.glob(f"{d}/*.jpg"): os.remove(f)
    for i, r in enumerate(rows):
        crop = LR.FRAMES.get(r.get("framing") or "wide", "")
        subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-ss", f"{r['src_in']:.3f}", "-t", f"{r['src_out'] - r['src_in']:.3f}",
                        "-i", src, "-vf", f"{crop}scale=540:960,fps=15", "-q:v", "3", f"{d}/r{i:02d}_%04d.jpg"], check=True)
    files = sorted(glob.glob(f"{d}/*.jpg"))
    out = subprocess.run([GAZE, *files], capture_output=True, text=True).stdout.split("\n")
    samples = []
    for line in out:
        p = line.split()
        if len(p) < 6: continue
        b = os.path.basename(p[0]); i = int(b[1:3]); k = int(b[4:8]) - 1
        t = rows[i]["edit_in"] + k / 15.0   # 15 fps since 2026-11-03 (was 10)
        op = float(p[5]) if p[5] != "nan" else None
        samples.append({"t": round(t, 2), "row": i, "open": op, "pupil_y": float(p[3]) if p[3] != "nan" else None})
    samples.sort(key=lambda s: s["t"])
    away, cur = [], None
    for s in samples:
        down = s["open"] is None or s["open"] < a.open
        if down and cur is None: cur = [s["t"], s["t"], s["row"]]
        elif down: cur[1] = s["t"]
        elif cur is not None:
            if cur[1] - cur[0] + 1/15 >= a.min: away.append({"t0": cur[0], "t1": round(cur[1] + 1/15, 2), "row": cur[2]})
            cur = None
    if cur is not None and cur[1] - cur[0] + 1/15 >= a.min: away.append({"t0": cur[0], "t1": round(cur[1] + 1/15, 2), "row": cur[2]})
    json.dump({"samples": samples, "away": away}, open(f"{a.work}/gaze/{a.name}.json", "w"), indent=1)
    tot = sum(x["t1"] - x["t0"] for x in away)
    print(f"{a.name}: {len(samples)} samples, {len(away)} looking-away runs, {tot:.1f} s of {spec['duration']:.1f} s")
    for x in away:
        print(f"  {x['t0']:6.2f}-{x['t1']:6.2f} ({x['t1'] - x['t0']:.1f} s)  row {x['row']:2d} | {rows[x['row']]['caption'][:60]}")


if __name__ == "__main__":
    main()
