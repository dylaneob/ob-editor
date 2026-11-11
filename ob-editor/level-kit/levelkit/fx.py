"""Drawing helpers for the level test compositor: springs, brand text sprites with the soft shadow, paste with transform."""
import math, os
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
FONT_DIR = os.path.expanduser("~/ob-editor/fonts/BigShoulders/static/")
SS = 1.15                                        # world supersample: world px = 1080-space px * SS
WW, WH = int(round(1080 * SS)), int(round(1920 * SS))
YEL = (255, 212, 0); WHITE = (255, 255, 255); INK = (17, 17, 19); GREY = (150, 150, 152)


def spring(t, f=3.2, d=0.55):
    """0 -> 1 closed-form damped spring (tmpl_fx / canvas_card family). Never stock easing."""
    if t <= 0: return 0.0
    w = 2 * math.pi * f; wd = w * math.sqrt(1 - d * d)
    return 1 - math.exp(-d * w * t) * (math.cos(wd * t) + d * w / wd * math.sin(wd * t))


def kick(t, f=2.6, d=0.32):
    """0 -> 0 impulse: one overshoot that settles (pops and pulses)."""
    if t <= 0: return 0.0
    w = 2 * math.pi * f
    return math.exp(-d * w * t) * math.sin(w * t)


def lin(t, a, b):
    return min(1.0, max(0.0, (t - a) / (b - a))) if b > a else float(t >= a)


def mix(a, b, u):
    return a + (b - a) * u


@lru_cache(maxsize=64)
def font(size, weight="Black"):
    return ImageFont.truetype(os.path.join(FONT_DIR, f"BigShouldersDisplay-{weight}.ttf"), int(round(size)))


@lru_cache(maxsize=512)
def text_sprite(txt, size, color=WHITE, weight="Black", track=0, shadow=True, sh_alpha=0.6):
    """Text (world px) with the brand's soft shadow (y 0.5% W, blur 2.2% W, 60%) as one RGBA sprite. Origin = cap top-left."""
    size_w = size * SS; f = font(size_w, weight)
    widths = [f.getlength(c) for c in txt]; tw = sum(widths) + track * SS * (len(txt) - 1)
    asc, desc = f.getmetrics(); pad = int(size_w * 0.35)
    w, h = int(tw + 2 * pad), int(asc + desc + 2 * pad)
    lay = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(lay); x = pad
    for c, cw in zip(txt, widths):
        d.text((x, pad), c, font=f, fill=color + (255,)); x += cw + track * SS
    if shadow:
        a = lay.getchannel("A").point(lambda v: int(v * sh_alpha))
        sh = Image.new("RGBA", lay.size, (0, 0, 0, 0)); sh.putalpha(a)
        sh = sh.filter(ImageFilter.GaussianBlur(1080 * SS * 0.022 / 2))
        out = Image.new("RGBA", lay.size, (0, 0, 0, 0)); out.alpha_composite(sh, (0, int(1080 * SS * 0.005))); out.alpha_composite(lay)
    else:
        out = lay
    cap_top = pad + f.getbbox("H")[1]
    return out, pad, cap_top, tw


def smear(spr, dx, dy, n=7):
    """Motion blur: average n copies of the sprite along (dx, dy) world px (premultiplied), on a canvas grown to fit."""
    L = math.hypot(dx, dy)
    if L < 3: return spr, 0, 0
    pad_x, pad_y = int(abs(dx) / 2) + 2, int(abs(dy) / 2) + 2
    a = np.asarray(spr, np.float32); pm = a.copy(); pm[..., :3] *= a[..., 3:4] / 255.0
    H, W = a.shape[:2]; acc = np.zeros((H + 2 * pad_y, W + 2 * pad_x, 4), np.float32)
    for i in range(n):
        f = i / (n - 1) - 0.5; ox, oy = int(round(pad_x + f * dx)), int(round(pad_y + f * dy))
        acc[oy:oy + H, ox:ox + W] += pm
    acc /= n; al = acc[..., 3:4]; rgb = np.where(al > 0.5, acc[..., :3] * 255.0 / np.maximum(al, 1e-3), 0)
    out = np.concatenate([np.clip(rgb, 0, 255), np.clip(al, 0, 255)], -1).astype(np.uint8)
    return Image.fromarray(out, "RGBA"), pad_x, pad_y


def paste(dst, spr, x, y, scale=1.0, alpha=1.0, rot=0.0, anchor=(0.5, 0.5), mb=None):
    """Paste RGBA sprite onto dst so that its anchor point lands at world (x, y), scaled and rotated (degrees) about it.
    mb = (dx, dy): the element's travel over one frame (world px); it is smeared over a 180-degree shutter (half of it)."""
    if alpha <= 0.003 or scale <= 0.01: return
    s = spr
    if abs(scale - 1) > 1e-3:
        s = s.resize((max(1, int(s.width * scale)), max(1, int(s.height * scale))), Image.BICUBIC)
    if mb is not None and math.hypot(*mb) * 0.5 >= 3:
        w0, h0 = s.width, s.height; s, px_, py_ = smear(s, mb[0] * 0.5, mb[1] * 0.5)
        anchor = ((anchor[0] * w0 + px_) / s.width, (anchor[1] * h0 + py_) / s.height)
    ax, ay = s.width * anchor[0], s.height * anchor[1]
    if abs(rot) > 0.05:
        big = Image.new("RGBA", (s.width * 2, s.height * 2), (0, 0, 0, 0)); big.paste(s, (int(s.width - ax), int(s.height - ay)))
        s = big.rotate(rot, resample=Image.BICUBIC, center=(s.width, s.height)); ax, ay = s.width / 2, s.height / 2
    if alpha < 0.999:
        a = s.getchannel("A").point(lambda v: int(v * alpha)); s = s.copy(); s.putalpha(a)
    dst.alpha_composite(s, (int(round(x - ax)), int(round(y - ay)))) if (x - ax) >= 0 and (y - ay) >= 0 and (x - ax + s.width) <= dst.width and (y - ay + s.height) <= dst.height else _paste_clip(dst, s, int(round(x - ax)), int(round(y - ay)))


def _paste_clip(dst, s, x, y):
    x0, y0 = max(0, x), max(0, y); x1, y1 = min(dst.width, x + s.width), min(dst.height, y + s.height)
    if x1 <= x0 or y1 <= y0: return
    dst.alpha_composite(s.crop((x0 - x, y0 - y, x1 - x, y1 - y)), (x0, y0))


def drop_shadow(spr, blur=18, alpha=0.45, color=(0, 0, 0)):
    a = spr.getchannel("A").point(lambda v: int(v * alpha))
    sh = Image.new("RGBA", spr.size, color + (0,)); sh.putalpha(a)
    return sh.filter(ImageFilter.GaussianBlur(blur))
