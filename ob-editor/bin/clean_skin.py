"""Acne cleanup for his face in thumbnails (OB 11-01: "get rid of acne in thumbnail ... if there is some on my face").
Spot removal, not smoothing: only small red spots are touched. On a crop round the face, redness = Lab a*; a spot is a connected
patch whose redness stands above the blurred local skin by `thr`, sized between a pinprick and a big pimple (fractions of the face
width). The eyes, the lips and the nose are never touched (generous boxes off the Vision face box), and nothing larger than a pimple
is (so a flushed cheek or the lips stay). Each spot, grown a little, is refilled from the skin around it (normalized blur) plus a
touch of grain. Skin texture outside the spots is the original pixels.
  clean(img RGB/RGBA PIL, face=(x, y, w, h)) -> (img, spots, px)
  python3 -I ~/ob-editor/bin/clean_skin.py IN.png OUT.png x y w h [compare.jpg]   (x y w h: the face box from bin/faces)
Method and rules: ~/.claude/skills/short-form-editor/references/youtube-thumbnails.md
"""
import sys
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage


def _nblur(rgb, w, r):
    num = np.stack([ndimage.gaussian_filter(rgb[..., c] * w, r) for c in range(3)], -1)
    den = ndimage.gaussian_filter(w, r)[..., None]
    return num / np.maximum(den, 1e-4)


def clean(img, face, thr=7.0, keep=None, amax_frac=0.055):
    x, y, w, h = [float(v) for v in face]
    X0, Y0 = int(max(0, x - 0.15 * w)), int(max(0, y - 0.35 * h)); X1, Y1 = int(min(img.width, x + 1.15 * w)), int(min(img.height, y + 1.12 * h))
    mode = img.mode; full = img.convert("RGBA"); crop = full.crop((X0, Y0, X1, Y1))
    rgb = np.asarray(crop.convert("RGB")).astype(np.float32); alpha = np.asarray(crop.getchannel("A")).astype(np.float32) / 255
    a = np.asarray(crop.convert("RGB").convert("LAB").getchannel(1)).astype(np.float32)
    lum = rgb.mean(axis=2)
    bg = ndimage.gaussian_filter(a, w / 22); diff = a - bg
    R, G, B = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    skin = (R > G) & (G > B) & (R - B > 18) & (R - B < 140) & (lum > 70)
    cand = (diff > thr) & (alpha > 0.9) & skin
    yy, xx = np.mgrid[Y0:Y1, X0:X1]; u, v = (xx - x) / w, (yy - y) / h        # face-box coords
    inside = ((u - 0.5) / 0.52) ** 2 + ((v - 0.36) / 0.70) ** 2 < 1            # the face, forehead up to the brim, not the room
    off = ((u > 0.08) & (u < 0.50) & (v > 0.26) & (v < 0.58)) | ((u > 0.50) & (u < 0.92) & (v > 0.26) & (v < 0.58)) \
        | ((u > 0.34) & (u < 0.66) & (v > 0.36) & (v < 0.76)) | ((u > 0.12) & (u < 0.88) & (v > 0.60) & (v < 0.98)) | ~inside
    if keep is not None: off |= keep[Y0:Y1, X0:X1]
    cand &= ~off
    lab, n = ndimage.label(cand)
    if n == 0: return img, 0, 0
    areas = ndimage.sum(np.ones_like(a), lab, index=np.arange(1, n + 1))
    amin, amax = (0.006 * w) ** 2, (amax_frac * w) ** 2
    good = np.zeros(n + 1, bool); good[1:] = (areas >= amin) & (areas <= amax)
    m = good[lab]
    grow = max(1, int(round(0.006 * w)))
    m = ndimage.binary_dilation(m, iterations=grow)
    fill = _nblur(rgb, (~m).astype(np.float32) * (alpha > 0.9), max(2.0, 0.012 * w))
    rng = np.random.default_rng(7); grain = rng.normal(0, 2.2, rgb.shape).astype(np.float32)
    soft = ndimage.gaussian_filter(m.astype(np.float32), max(0.8, 0.003 * w))[..., None]
    out = rgb * (1 - soft) + (fill + grain) * soft
    crop = Image.merge("RGBA", (*Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).split(), crop.getchannel("A")))
    full.paste(crop, (X0, Y0))
    return (full if mode == "RGBA" else full.convert(mode)), int(good.sum()), int(m.sum())


if __name__ == "__main__":
    im = Image.open(sys.argv[1]); f = tuple(float(v) for v in sys.argv[3:7])
    out, n, px = clean(im, f); out.save(sys.argv[2]); print("spots", n, "px", px)
    if len(sys.argv) > 7:
        x, y, w, h = f; box = (int(x - 0.2 * w), int(y - 0.4 * h), int(x + 1.2 * w), int(y + 1.15 * h))
        A, B = im.convert("RGB").crop(box), out.convert("RGB").crop(box)
        s = Image.new("RGB", (A.width * 2 + 10, A.height), (255, 255, 255)); s.paste(A, (0, 0)); s.paste(B, (A.width + 10, 0))
        s.thumbnail((2000, 1200)); s.save(sys.argv[7], quality=90)
