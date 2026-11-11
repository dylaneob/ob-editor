#!/usr/bin/env python3
"""Match a new take's look to an earlier take of the same set, baked into one Hald CLUT (level 8).

For pickups filmed in different light (C4367 reshoot, 2026-10-20: OB has no blackout curtain, so the
new takes are brighter and cooler than the night original). Built and tested on C4365 (daylight,
Oct 18) -> C4367 (night, Oct 19), same set, same camera settings.

  python3 match_grade.py --ref REF.MP4 --target NEW.MP4 --out NEW_hald.png \
      [--base-lut ~/ob-editor/luts/ob_grade_warmtan_hald.png] [--n 24] \
      [--ref-span 60 2700] [--target-span 5 600] [--sheet SHEET.jpg] [--sheet-times REFT,NEWT ...]

How it matches (camera space, before the house grade):
  1. Sample N frames from each file (raw, ungraded), pooled.
  2. Lightness: quantile-match the new take's L* to the reference (a smooth, monotone curve).
  3. Colour: at each lightness quantile, shift a*/b* so the new take's average colour there equals
     the reference's (lamp-lit highlights and daylight-filled mids get different corrections).
     Saturation is left alone unless --scale-sat.

Tested 2026-10-20, C4365 (Oct 18 ~5:20 PM, daylight) -> C4367 (Oct 19 night), house grade on both:
  average brightness 0.31 -> 0.21 (night original 0.21); warmth R/B 1.42 -> 1.56 (original 1.60).
  Daylight drifted inside that 17-minute shoot, so fit one LUT per pickup block (--target-span),
  not one for the whole day. A whole-frame background regression (per-channel curves) was tried
  and dropped: banding and magenta/cyan casts on skin.
  4. Bake: apply the match to an identity Hald CLUT, then run the house LUT over it, so the output
     LUT = house(match(x)). Use it in place of the house LUT for the new take's shots only.
"""
import argparse, os, subprocess, tempfile
import numpy as np
from PIL import Image

HOUSE = os.path.expanduser("~/ob-editor/luts/ob_grade_warmtan_hald.png")
W, H = 480, 270

# ---- colour space (sRGB/bt709 primaries, D65)
M_RGB2XYZ = np.array([[0.4124564, 0.3575761, 0.1804375],
                      [0.2126729, 0.7151522, 0.0721750],
                      [0.0193339, 0.1191920, 0.9503041]])
M_XYZ2RGB = np.linalg.inv(M_RGB2XYZ)
WHITE = np.array([0.95047, 1.0, 1.08883])


def s2l(x): return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)
def l2s(x): return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(np.clip(x, 0, None), 1 / 2.4) - 0.055)


def rgb2lab(rgb):
    xyz = s2l(rgb) @ M_RGB2XYZ.T / WHITE
    f = np.where(xyz > (6 / 29) ** 3, np.cbrt(xyz), xyz / (3 * (6 / 29) ** 2) + 4 / 29)
    L = 116 * f[..., 1] - 16
    return np.stack([L, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def lab2rgb(lab):
    fy = (lab[..., 0] + 16) / 116
    f = np.stack([fy + lab[..., 1] / 500, fy, fy - lab[..., 2] / 200], -1)
    xyz = np.where(f > 6 / 29, f ** 3, 3 * (6 / 29) ** 2 * (f - 4 / 29)) * WHITE
    return np.clip(l2s(np.clip(xyz @ M_XYZ2RGB.T, 0, None)), 0, 1)


# ---- sampling
def duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", path],
                       capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def grab(path, t, out, w=W, h=H):
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", path, "-frames:v", "1",
                    "-vf", f"scale={w}:{h}:flags=area", out], check=True)
    return np.asarray(Image.open(out).convert("RGB")).astype(np.float64) / 255.0


def sample(path, n, span, td, tag):
    d = duration(path)
    a, b = span if span else (0.05 * d, 0.95 * d)
    b = min(b, d - 1)
    return np.concatenate([grab(path, t, f"{td}/{tag}{i}.png").reshape(-1, 3) for i, t in enumerate(np.linspace(a, b, n))])


# ---- the match
Q = np.linspace(0.002, 0.998, 250)          # quantile grid
NB = 16                                      # lightness bins for the colour correction


def smooth1d(y, k=5):
    pad = np.pad(y, (k, k), mode="edge")
    return np.convolve(pad, np.ones(2 * k + 1) / (2 * k + 1), mode="same")[k:-k]


def fit(ref_rgb, tgt_rgb):
    R, T = rgb2lab(ref_rgb), rgb2lab(tgt_rgb)
    qr, qt = np.quantile(R[:, 0], Q), np.quantile(T[:, 0], Q)
    qt = np.maximum.accumulate(qt + np.arange(len(qt)) * 1e-6)   # strictly increasing
    qr = np.maximum.accumulate(smooth1d(qr, 3))
    # colour per lightness quantile bin: mean a/b of the target vs the reference in the same quantile band
    edges = np.linspace(0, 1, NB + 1)
    ut = np.interp(T[:, 0], qt, Q); ur = np.interp(R[:, 0], np.quantile(R[:, 0], Q), Q)
    mt, mr, centers = np.zeros((NB, 2)), np.zeros((NB, 2)), (edges[:-1] + edges[1:]) / 2
    for k in range(NB):
        st = (ut >= edges[k]) & (ut < edges[k + 1]); sr = (ur >= edges[k]) & (ur < edges[k + 1])
        mt[k] = T[st, 1:].mean(0) if st.any() else 0; mr[k] = R[sr, 1:].mean(0) if sr.any() else 0
    mt = np.stack([smooth1d(mt[:, j], 1) for j in range(2)], -1); mr = np.stack([smooth1d(mr[:, j], 1) for j in range(2)], -1)
    # chroma spread around those means
    ct = T[:, 1:] - np.stack([np.interp(ut, centers, mt[:, j]) for j in range(2)], -1)
    cr = R[:, 1:] - np.stack([np.interp(ur, centers, mr[:, j]) for j in range(2)], -1)
    s = float(np.clip(np.sqrt((cr ** 2).sum(1).mean() / max((ct ** 2).sum(1).mean(), 1e-9)), 0.8, 1.25))
    return {"qt": qt, "qr": qr, "centers": centers, "mt": mt, "mr": mr, "s": s}


def apply(m, rgb):
    lab = rgb2lab(rgb)
    u = np.interp(lab[..., 0], m["qt"], Q)
    # inside the sampled range: quantile map; outside it: identity slope, so nothing clips or folds
    L = np.interp(u, Q, m["qr"])
    lo, hi = m["qt"][0], m["qt"][-1]
    L = np.where(lab[..., 0] < lo, lab[..., 0] - lo + m["qr"][0], L)
    L = np.where(lab[..., 0] > hi, lab[..., 0] - hi + m["qr"][-1], L)
    out = np.empty_like(lab); out[..., 0] = np.clip(L, 0, 100)
    for j in range(2):
        mt = np.interp(u, m["centers"], m["mt"][:, j]); mr = np.interp(u, m["centers"], m["mr"][:, j])
        out[..., 1 + j] = mr + m["s"] * (lab[..., 1 + j] - mt)
    # leave near-white (lamp globes, white cards) and near-black alone so they stay clean
    w = np.clip((lab[..., 0] - 92) / 6, 0, 1)[..., None]
    return lab2rgb(out) * (1 - w) + rgb * w


def bake(m, base, out):
    with tempfile.TemporaryDirectory() as td:
        ident = f"{td}/id.png"; mid = f"{td}/match.png"
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "lavfi", "-i", "haldclutsrc=level=8", "-frames:v", "1", ident], check=True)
        im = np.asarray(Image.open(ident).convert("RGB")).astype(np.float64) / 255.0
        Image.fromarray((apply(m, im) * 255 + 0.5).astype(np.uint8)).save(mid)
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", mid, "-i", base,
                        "-filter_complex", "[0:v][1:v]haldclut=interp=tetrahedral", "-frames:v", "1", out], check=True)


def graded(path, t, lut, out, w=960, h=540):
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", path, "-i", lut, "-filter_complex",
                    f"[0:v]scale={w}:{h}:flags=area[v];[v][1:v]haldclut=interp=tetrahedral", "-frames:v", "1", out], check=True)
    return Image.open(out).convert("RGB")


def stats(img):
    x = np.asarray(img).astype(np.float64) / 255.0
    Y = 0.2126 * x[..., 0] + 0.7152 * x[..., 1] + 0.0722 * x[..., 2]
    m = x.reshape(-1, 3).mean(0)
    return f"Y mean {Y.mean():.3f} p5 {np.percentile(Y, 5):.3f} p50 {np.percentile(Y, 50):.3f} p95 {np.percentile(Y, 95):.3f} R/B {m[0] / max(m[2], 1e-6):.2f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True); ap.add_argument("--target", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--base-lut", default=HOUSE); ap.add_argument("--n", type=int, default=24)
    ap.add_argument("--ref-span", nargs=2, type=float); ap.add_argument("--target-span", nargs=2, type=float)
    ap.add_argument("--sheet"); ap.add_argument("--sheet-times", nargs="*", default=[])
    ap.add_argument("--scale-sat", action="store_true", help="also scale chroma spread to the reference (tested 10-20: slightly duller wood; off by default)")
    a = ap.parse_args()
    with tempfile.TemporaryDirectory() as td:
        m = fit(sample(a.ref, a.n, a.ref_span, td, "r"), sample(a.target, a.n, a.target_span, td, "t"))
        if not a.scale_sat: m["s"] = 1.0
        print(f"fit: chroma scale {m['s']:.2f}")
        bake(m, a.base_lut, a.out)
        print(f"LUT -> {a.out}")
        if a.sheet:
            from PIL import ImageDraw
            rows = []
            for pair in a.sheet_times:
                rt, tt = (float(v) for v in pair.split(","))
                before = graded(a.target, tt, a.base_lut, f"{td}/b.png")
                after = graded(a.target, tt, a.out, f"{td}/a.png")
                goal = graded(a.ref, rt, a.base_lut, f"{td}/g.png")
                for lab_, im in (("NEW TAKE, house grade only", before), ("NEW TAKE, matched", after), ("ORIGINAL, house grade", goal)):
                    print(f"  t={tt if im is not goal else rt:7.1f} {lab_:<28} {stats(im)}")
                rows.append((before, after, goal))
            w, h = rows[0][0].size
            sheet = Image.new("RGB", (w * 3, h * len(rows) + 60), (12, 12, 12))
            d = ImageDraw.Draw(sheet)
            for c, title in enumerate(["New take, house grade only", "New take, matched", "Original (the target look)"]):
                d.text((c * w + 20, 20), title, fill=(255, 220, 0))
            for r, row in enumerate(rows):
                for c, im in enumerate(row): sheet.paste(im, (c * w, 60 + r * h))
            sheet.save(a.sheet, quality=88)
            print("sheet ->", a.sheet)


if __name__ == "__main__":
    main()
