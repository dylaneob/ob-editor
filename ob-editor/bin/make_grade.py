#!/usr/bin/env python3
"""Build a per-take grade as a Hald CLUT (level 8) so preview and render match exactly.

  python3 make_grade.py OUT.png --ev 0.5 --wb 1.08 0.95 1.0 --warm 0.03 --sat 1.06 --contrast 0.15 [--lift 0.0]

White balance and warmth fade out toward white, so bright screens and white slides stay neutral.
Highlights roll off softly instead of clipping.
"""
import argparse, subprocess, tempfile, os
import numpy as np
from PIL import Image


def s2l(x): return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)
def l2s(x): return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(np.clip(x, 0, None), 1 / 2.4) - 0.055)
def smooth(a, b, x): t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)


def grade(rgb, ev, wb, warm, sat, contrast, lift):
    x = s2l(rgb)
    x = x * (2.0 ** ev)
    L = 0.2126 * x[..., 0] + 0.7152 * x[..., 1] + 0.0722 * x[..., 2]
    protect = 1 - smooth(0.55, 0.95, L)                       # 1 in shadows/mids, 0 near white
    g = 1 + protect[..., None] * (np.array(wb) - 1)
    x = x * g
    mid = np.exp(-((l2s(np.clip(L, 0, 1)) - 0.45) / 0.22) ** 2)  # skin/midtone weight (gamma space)
    x[..., 0] *= 1 + warm * mid; x[..., 2] *= 1 - warm * mid
    # soft highlight roll-off in linear light
    x = np.where(x > 0.8, 0.8 + (1 - np.exp(-(x - 0.8) / 0.2)) * 0.2, x)
    y = l2s(np.clip(x, 0, 1))
    # gentle S-curve around mid-grey + shadow lift
    y = y + contrast * (y - 0.5) * (1 - np.abs(2 * y - 1)) + lift * (1 - y) ** 3
    # saturation (luma-preserving, gamma space)
    lum = 0.2126 * y[..., 0] + 0.7152 * y[..., 1] + 0.0722 * y[..., 2]
    y = lum[..., None] + sat * (y - lum[..., None])
    return np.clip(y, 0, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--ev", type=float, default=0.0)
    ap.add_argument("--wb", type=float, nargs=3, default=[1, 1, 1])
    ap.add_argument("--warm", type=float, default=0.0)
    ap.add_argument("--sat", type=float, default=1.0)
    ap.add_argument("--contrast", type=float, default=0.1)
    ap.add_argument("--lift", type=float, default=0.0)
    a = ap.parse_args()
    with tempfile.TemporaryDirectory() as td:
        ident = os.path.join(td, "id.png")
        subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "haldclutsrc=level=8", "-frames:v", "1", ident], check=True)
        im = np.asarray(Image.open(ident).convert("RGB")).astype(np.float64) / 255.0
    out = grade(im, a.ev, a.wb, a.warm, a.sat, a.contrast, a.lift)
    Image.fromarray((out * 255 + 0.5).astype(np.uint8)).save(a.out)
    print("LUT ->", a.out)


if __name__ == "__main__":
    main()
