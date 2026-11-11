#!/usr/bin/env python3
"""Canvas + card: animated graphics above OB while he sits in a wide card at the bottom (OB 2026-11-04 on Kallaway's reel
DfUhxJqxLxP: "for this format we have the me in the bottom down but you never make animations like this above me for this format").
Style card: ~/ob-editor/styles/framework-canvas.md (decoded 10-28, "Build on first use"). Brand: Big Shoulders, #FFD400 accent.

Layout (1080x1920): black dot-grid canvas; his card x 72-1008, y 1240-1720 (rounded, soft edge glow), clear of the IG bands;
1-2 caption words just above the card; graphics in y 220-1120. Every element lands on the word that names it, with a spring.

Elements (a plan's "els", times in edit seconds, or "on": a spoken word that triggers it):
  {"type": "title", "words": ["SOUFIANE'S", "BREAKFAST"], "at": 0.0}      word-by-word rise, yellow underline draws after
  {"type": "count", "value": 630, "unit": "KCAL", "on": "calories"}       counts up over 0.6 s
  {"type": "rows", "items": [["GUACAMOLE", "FIBER · OMEGA 9", "guacamole"], ...]}   01-04 rows spring up on their word;
                                                                          the newest gets the accent bar, older ones dim
Use from an engine: CC.render_frame(t, card_img, plan, words) -> 1080x1920 RGB image.
Demo:  python3 -I canvas_card.py demo PLAN.json OUT.mp4
  PLAN.json: {"cam": CAMERA, "mic": MIC_WAV, "pieces": [[mic_a, mic_b, cam_a], ...], "crop_y": 0.18, "els": [...], "words": [...]?}
"""
import json, math, os, subprocess, sys, tempfile
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

BIN = os.path.dirname(os.path.abspath(__file__))
BRAND = json.load(open(os.path.expanduser("~/ob-editor/brand/brand.json")))
FONT = os.path.expanduser(BRAND["font"])
W, H, FPS = 1080, 1920, 30000 / 1001
CARD = (72, 1240, 1008, 1720)
ACCENT = tuple(int(BRAND["accent"][i:i + 2], 16) for i in (1, 3, 5))
_F = {}


def font(size, weight="ExtraBold"):
    k = (size, weight)
    if k not in _F:
        f = ImageFont.truetype(FONT, size)
        try: f.set_variation_by_name(weight)
        except Exception: pass
        _F[k] = f
    return _F[k]


def spring(t, freq=3.2, damp=0.55):
    """0 -> 1, a damped spring (closed form): POP-like overshoot, settles in ~0.45 s."""
    if t <= 0: return 0.0
    w = 2 * math.pi * freq; wd = w * math.sqrt(1 - damp ** 2)
    return 1 - math.exp(-damp * w * t) * (math.cos(wd * t) + damp * w / wd * math.sin(wd * t))


def ease(t, d):   # 0 -> 1 over d seconds, smooth (for draws and fades)
    x = min(1.0, max(0.0, t / d)); return x * x * (3 - 2 * x)


_BG = None
def canvas():
    global _BG
    if _BG is None:
        bg = Image.new("RGB", (W, H), (5, 5, 5)); d = ImageDraw.Draw(bg)
        for y in range(10, H, 22):
            for x in range(10, W, 22): d.point((x, y), fill=(34, 34, 34))
        v = Image.radial_gradient("L").resize((W, H)).point(lambda p: int(p * 0.55))   # darker edges
        _BG = Image.composite(Image.new("RGB", (W, H), (0, 0, 0)), bg, v)
    return _BG.copy()


def trigger(el, words, key="on"):
    if el.get("at") is not None: return el["at"]
    w = el.get(key, "").lower()
    hit = next((x for x in words if x["w"].lower().strip(".,!?").startswith(w)), None) if w else None
    return hit["s"] if hit else el.get("fallback", 0.0)


def draw_title(img, el, t, words):
    t0 = trigger(el, words); x0 = 90; y = el.get("y", 260); d = ImageDraw.Draw(img)
    size = 118
    while size > 60 and font(size, "Black").getlength(" ".join(el["words"])) > W - 2 * x0: size -= 4   # the whole title fits (11-04 test ran off the edge)
    f = font(size, "Black"); x = x0
    for i, w in enumerate(el["words"]):
        ti = t - (t0 + i * el.get("gap", 0.18))
        if ti < 0: break
        p = spring(ti); a = int(255 * min(1, ti / 0.12))
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0)); ImageDraw.Draw(layer).text((x, y + (1 - p) * 60), w, font=f, fill=(255, 255, 255, a))
        img.alpha_composite(layer); x += f.getlength(w + " ")
    tu = t - (t0 + len(el["words"]) * el.get("gap", 0.18))
    if tu > 0:   # the yellow underline draws left to right under the whole title
        tw = f.getlength(" ".join(el["words"])); u = ease(tu, 0.35)
        d.rounded_rectangle([x0, y + int(size * 1.12), x0 + tw * u, y + int(size * 1.12) + 12], 6, fill=ACCENT + (255,))


def draw_count(img, el, t, words):
    t0 = trigger(el, words); tc = t - t0
    if tc < 0: return
    v = int(round(el["value"] * ease(tc, 0.6))); p = spring(tc); f = font(170, "Black"); fu = font(74, "ExtraBold")
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(layer); y = el.get("y", 440) + (1 - p) * 50
    s = f"{v:,}"; d.text((90, y), s, font=f, fill=ACCENT + (255,)); d.text((90 + f.getlength(s) + 22, y + 78), el.get("unit", ""), font=fu, fill=(255, 255, 255, 235))
    img.alpha_composite(layer)


def draw_rows(img, el, t, words):
    y0, rh, gap = el.get("y", 620), 110, 16; items = el["items"]
    ts = [trigger({"on": it[2], "fallback": it[3] if len(it) > 3 else 0.0}, words) for it in items]
    live = max((i for i, s in enumerate(ts) if t >= s), default=-1)
    fa, fb, fn = font(66, "Black"), font(50, "Bold"), font(46, "Bold")   # sized for a phone (11-04 test: 42 px details were too small)
    for i, (it, s) in enumerate(zip(items, ts)):
        tr = t - s
        if tr < 0: continue
        p = spring(tr); a = min(1.0, tr / 0.12); dim = 1.0 if i == live else 0.55
        y = y0 + i * (rh + gap) + (1 - p) * 70
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
        d.rounded_rectangle([90, y, W - 90, y + rh], 18, fill=(24, 24, 24, int(240 * a)))
        if i == live: d.rounded_rectangle([90, y, 104, y + rh], 6, fill=ACCENT + (int(255 * a),))
        d.text((130, y + rh / 2), f"{i + 1:02d}", font=fn, anchor="lm", fill=(150, 150, 150, int(255 * a * dim)))
        d.text((210, y + rh / 2), it[0], font=fa, anchor="lm", fill=(255, 255, 255, int(255 * a * dim)))
        d.text((W - 120, y + rh / 2), it[1], font=fb, anchor="rm", fill=(ACCENT if i == live else (200, 200, 200)) + (int(255 * a * dim),))
        img.alpha_composite(layer)


def draw_card(img, card):
    x0, y0, x1, y1 = CARD; m = Image.new("L", (x1 - x0, y1 - y0), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, x1 - x0 - 1, y1 - y0 - 1], 36, fill=255)
    glow = Image.new("L", img.size, 0); glow.paste(m, (x0, y0)); glow = glow.filter(ImageFilter.GaussianBlur(18)).point(lambda v: int(v * 0.35))
    img.alpha_composite(Image.merge("RGBA", (Image.new("L", img.size, 120), Image.new("L", img.size, 150), Image.new("L", img.size, 190), glow)))
    img.paste(card.resize((x1 - x0, y1 - y0), Image.LANCZOS).convert("RGBA"), (x0, y0), m)


def draw_caption(img, t, words):
    cur = [w for w in words if w["s"] - 0.02 <= t]
    if not cur or t > cur[-1]["e"] + 0.5: return
    k = len(cur) - 1; grp = cur[max(0, k - (k % 2)):k + 1]   # 1-2 words at a time
    txt = " ".join(w["w"].upper().strip(",.") for w in grp); f = font(64, "ExtraBold")
    sh = Image.new("L", img.size, 0); ImageDraw.Draw(sh).text((W / 2, 1180 + 4), txt, font=f, anchor="mm", fill=255)
    img.alpha_composite(Image.merge("RGBA", (*[Image.new("L", img.size, 0)] * 3, sh.filter(ImageFilter.GaussianBlur(10)).point(lambda v: int(v * 0.6)))))
    d = ImageDraw.Draw(img); x = W / 2 - f.getlength(txt) / 2
    for i, w in enumerate(grp):   # the live (last) word in the brand yellow
        s = w["w"].upper().strip(",.") + (" " if i < len(grp) - 1 else "")
        d.text((x, 1180), s, font=f, anchor="lm", fill=ACCENT if i == len(grp) - 1 else (255, 255, 255)); x += f.getlength(s)


DRAW = {"title": draw_title, "count": draw_count, "rows": draw_rows}


def render_frame(t, card, plan, words):
    img = canvas().convert("RGBA")
    for el in plan["els"]: DRAW[el["type"]](img, el, t, words)
    draw_card(img, card); draw_caption(img, t, words)
    return img.convert("RGB")


def apple_words(wav):
    o = subprocess.run([os.path.join(BIN, "speech_words"), "words", wav], capture_output=True, text=True).stdout
    return [dict(w=x["w"], s=float(x["s"]), e=float(x["e"])) for x in json.loads(o[o.index("["):])] if "[" in o else []


def demo(plan_path, out):
    P = json.load(open(plan_path)); cam, mic = P["cam"], P["mic"]; pcs = P["pieces"]
    with tempfile.TemporaryDirectory() as td:
        words, t, fa = [], 0.0, []
        for k, (a, b, ca) in enumerate(pcs):   # his voice, piece by piece, and its words on the edit's clock
            subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{a:.4f}", "-t", f"{b - a:.4f}", "-i", mic, "-ac", "1", "-ar", "48000", f"{td}/p{k}.wav"], check=True)
            fa.append(f"{td}/p{k}.wav"); words += [dict(w, s=w["s"] + t, e=w["e"] + t) for w in apple_words(f"{td}/p{k}.wav")]; t += b - a
        for fix in P.get("fix", []): [w.update(w=fix[1]) for w in words if w["w"].lower().strip(".,") == fix[0]]
        open(f"{td}/l.txt", "w").write("".join(f"file '{x}'\n" for x in fa))
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", f"{td}/l.txt", "-af", "loudnorm=I=-14:TP=-1.5:LRA=7", "-ar", "48000", f"{td}/a.wav"], check=True)
        cw, ch = 2160, int(2160 * (CARD[3] - CARD[1]) / (CARD[2] - CARD[0])); cy = int(P.get("crop_y", 0.18) * 3840)
        enc = subprocess.Popen(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", "30000/1001", "-i", "-", "-i", f"{td}/a.wav",
                                "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p", "-c:a", "aac_at", "-b:a", "256k", "-shortest", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
        t_out, f0 = 0.0, 0
        for a, b, ca in pcs:   # frames from the running total of exact times (M32), so picture and sound stay together
            f1 = int(round((t_out + b - a) * FPS)); n = f1 - f0
            dec = subprocess.Popen(["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{ca:.4f}", "-i", cam, "-frames:v", str(n), "-vf", f"crop={cw}:{ch}:0:{cy},scale=936:480",
                                   "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
            for k in range(n):
                buf = dec.stdout.read(936 * 480 * 3)
                if len(buf) < 936 * 480 * 3: break
                enc.stdin.write(render_frame((f0 + k) / FPS, Image.frombytes("RGB", (936, 480), buf), P, words).tobytes())
            dec.kill(); f0 = f1; t_out += b - a
        enc.stdin.close(); enc.wait()
    sys.path.insert(0, BIN); import qc_gate as Q   # the gate's pieces record, with the camera map for its lip-sync check (M36)
    segs, cams, t = [], [], 0.0
    for a, b, ca in pcs: segs.append((mic, a, b, t)); cams.append((cam, ca, ca + b - a, t)); t += b - a
    Q.record_pieces(out, segs, cams)
    json.dump(words, open(os.path.splitext(out)[0] + ".words.json", "w"))
    print(f"wrote {out}: {f0} frames, {len(words)} words: {' '.join(w['w'] for w in words)}")


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) == 3 and a[0] == "demo": demo(a[1], a[2])
    else: print(__doc__); sys.exit(2)
