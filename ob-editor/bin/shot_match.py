#!/usr/bin/env python3
"""Per-shot exposure and white-balance match for a lecture_render EDL, so window light that changed during the take
doesn't make lines jump in brightness or colour (OB 2026-10-18: "i was overexposed a little bit" / "the lighting changed
throughout filming").

For each row: 3 frames (25/50/75 %), Apple Vision face box, mean skin colour of the inner face. Then, with the warm
base grade (make_grade.grade), solve the row's EV so the graded skin luma hits TARGET, and a red/blue white-balance
nudge so its skin R/B hits RB. Writes one Hald LUT per distinct (ev, wb) into WORK/luts/ and stores it as row["lut"].

  python3 shot_match.py WORK NAME TARGET [--rb 1.20] [--dry]      (TARGET: skin luma 0-255 after grading, e.g. 160)
"""
import argparse, json, os, subprocess, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_grade import grade   # noqa: E402

BASE = dict(wb=[1.06, 0.99, 0.94], warm=0.09, sat=1.09, contrast=0.18, lift=0.0)     # W1 warm, OB's pick 10-17
FACES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "faces")
Y = np.array([0.2126, 0.7152, 0.0722])


def skin_pixels(work, take, t, tag):
    f = f"{work}/expo/{tag}.png"
    if not os.path.exists(f):
        os.makedirs(f"{work}/expo", exist_ok=True)
        subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-ss", f"{t:.3f}", "-i", f"/Volumes/T7/{take}.MP4",
                        "-frames:v", "1", "-vf", "scale=1080:1920", f], check=True)
    box = subprocess.run([FACES, f], capture_output=True, text=True).stdout.split()
    if len(box) < 5: return None
    x0, y0, x1, y1 = map(int, box[1:5])
    a = np.asarray(Image.open(f).convert("RGB")).astype(np.float64) / 255
    return a[y0 + 60:y1 - 40, x0 + 60:x1 - 60].reshape(-1, 3)


def solve(px, target, rb_target):
    """EV and wb (R and B gains on top of BASE) so the graded skin has luma `target` and R/B `rb_target`."""
    kr = 1.0
    for _ in range(8):                                     # alternate: white balance, then exposure
        lo, hi = -1.5, 1.5
        for _ in range(30):
            ev = (lo + hi) / 2
            g = grade(px[None], ev=ev, **dict(BASE, wb=[BASE["wb"][0] * kr, BASE["wb"][1], BASE["wb"][2] / kr]))[0]
            L = (g.mean(0) @ Y) * 255
            lo, hi = (ev, hi) if L < target else (lo, ev)
        m = g.mean(0); kr *= (rb_target / (m[0] / m[2])) ** 0.8
    return round(ev, 2), round(float(kr), 3), round(float(L), 1), round(float(m[0] / m[2]), 3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("work"); ap.add_argument("name"); ap.add_argument("target", type=float)
    ap.add_argument("--rb", type=float, default=1.27)      # W1's warmth on an average shot (OB's pick 10-17)
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    p = f"{a.work}/{a.name}_edl.json"; spec = json.load(open(p))
    take = spec["take"]; made = {}
    for i, r in enumerate(spec["rows"]):
        d = r["src_out"] - r["src_in"]
        px = [skin_pixels(a.work, take, r["src_in"] + q * d, f"{a.name}_{i:02d}_{int(q * 100)}") for q in (0.25, 0.5, 0.75)]
        px = [x for x in px if x is not None]
        if not px: print(f"row {i}: no face, keeps the take grade"); continue
        allpx = np.concatenate(px)
        ev, kr, L, rb = solve(allpx, a.target, a.rb)
        name = f"M{int(a.target)}_{take}_e{ev:+.2f}_k{kr:.3f}".replace("+", "p").replace("-", "m")
        if name not in made and not a.dry:
            wb = [BASE["wb"][0] * kr, BASE["wb"][1], BASE["wb"][2] / kr]
            subprocess.run([sys.executable, "-I", os.path.join(os.path.dirname(os.path.abspath(__file__)), "make_grade.py"), f"{a.work}/luts/{name}.png",
                            "--ev", str(ev), "--wb", *map(str, wb), "--warm", str(BASE["warm"]), "--sat", str(BASE["sat"]),
                            "--contrast", str(BASE["contrast"])], check=True, capture_output=True)
        made[name] = True
        raw = (allpx.mean(0) @ Y) * 255
        print(f"row {i:2d}  raw skin {raw:5.1f} -> {L:5.1f}  ev {ev:+.2f}  R/B gain {kr:.3f} -> R/B {rb:.3f}  | {r['caption'][:44]}")
        r["lut"] = name
    if not a.dry:
        spec["match"] = {"target": a.target, "rb": a.rb}
        json.dump(spec, open(p, "w"), indent=1)
        print(f"{len(made)} LUTs, rows tagged in {p}")


if __name__ == "__main__":
    main()
