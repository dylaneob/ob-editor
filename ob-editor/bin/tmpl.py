#!/usr/bin/env python3
"""tmpl: one plan-driven compositor for the editor templates (2026-11-04; catalog ~/ob-editor/styles/TEMPLATE-CATALOG.md).
OB 11-04: "doesnt matter just do all of them". Elements come from tmpl_fx.py. Every hard rule of the editor skill still applies:
build the plan from takes.py's kept pieces (bad takes out, zero dead space), never cut him off, shot list before a full render.

    python3 -I tmpl.py render PLAN.json OUT.mp4          (then the QC gate runs by itself, as in every engine)
    python3 -I tmpl.py still PLAN.json OUT.jpg T [T ...]  (composed frames at edit times T, for shot lists)

PLAN.json
  {"cam": CAMERA.MP4, "mic": MIC.wav, "lut": HALD.png (default warm tan) | null, "cx": 0.5 (9:16 crop centre of a landscape camera),
   "timeline": [SEG, ...], "els": [tmpl_fx elements; times on the edit clock, or "on": a spoken word; "z": "behind" = under him],
   "captions": {"y": 1180, "n": 3} | false, "sfx": [{"file": PATH, "at": T | "on": WORD, "db": -18}], "fix": [["heard", "said"(, "L08" | [t0, t1])]]}
  SEG, one of his lines:  {"mic": [a, b], "cam": cam_a, "look": LOOK}      (the camera time where that line's picture starts)
  SEG, a source clip:     {"src": PATH, "in": a, "out": b, "look": LOOK, "audio": true}
  LOOK
    {"name": "full", "zoom": 1.22}                                       his whole frame; "zoom": Dylan Page's zoom-out on a hard cut to him
                                                                         (lands 1.22x in, eases out in ~0.45 s, first frames blurred; T04)
    {"name": "cut", "bg": BG, "face_w": 300, "face_cx": 540, "face_top": 700}     his cut-out (BiRefNet matte, birefnet_cut.py) over BG
    {"name": "inset", "bg": BG, "box": [x0, y0, x1, y1], "face_w": 190}  Karan: his head + chest, matted, clipped to a hard rectangle
    {"name": "card", "bg": BG, "box": [x0, y0, x1, y1], "radius": 40, "face_w": 240, "face_cy": 0.42, "pop": true, "glow": false}
                                                                         his frame in a rounded card (T02 / T06 / T19); his head pops over the top edge
    {"name": "split", "seam": 876, "top": TOP, "drop": true, "face_top": 1066}   a receipt on top, him below at the same scale (T04 / T18);
                                                                         "drop": the panel wipes down (measured curve) and pushes his picture down with it
                                                                         ("push": false keeps him still); "rise": S slides the panel up for the last S s
    {"name": "grid", "cells": [[4 paths], [4 paths]], "swap": [WORD or T], "face_w": 211, "face_top": 651, "clip": [227, 537, 853, 1346]}
                                                                         the 2x2 grid with a clockwise cascade swap + his big cut-out on the seam (T09)
    {"name": "source", "peek": {"cam": cam_a, "side": "left", "in": 0.0, "face_w": 230}}   her clip full frame, his real watching footage as a peek (T15 / T03)
    {"name": "freeze", "src": PATH, "t": T, "punch": 1.4, "box": [x0, y0, x1, y1], "face_w": 190}  her frozen frame, punched in, him as an inset (T15)
    {"name": "box", "src": PATH, "t": T, "box": [224, 796, 632, 1124]}  his frame with her clip playing in OB's reaction box (T03)
    {"name": "broll", "src": PATH, "t": T, "cx": 0.5, "cap_y": 470}     T21 (Sarah Snow): his b-roll full frame, his voice running under it
    {"name": "full", "push": [1.0, 1.13], "cap_y": 470}                  T21: his wide shot with a slow linear push (the text stays still)
  "keep_pauses": 0.8 (T21: breaths up to 0.8 s stay), "music": {"file": PATH, "start": 0, "rel": -18, "duck": 0} (T21 bed)
  "captions": {"style": "serif", "y": 470, "emph": ["okay", "break free"], "stack_until": 6.0}   T21: her glowing EB Garamond blocks
  "captions": {"style": "clean", "y": 1040, "italic": ["but people ask"], "quote": ["old way"]}   T22: Hormozi's white phrases
                                                                         (FX.serif_captions; switch looks on words with a line's "switch")
  BG: "studio" (his own frame, blurred and warm: M38) | "frosted:PATH" (a picture's own blur, T19) | "image:PATH" | "board" (dark warm,
      faint grid) | "src:PATH@T" (a source frame).   TOP: {"image": PATH} | {"src": PATH, "t": T} | {"burst": [paths], "each": 0.6}
      | {"card": PATH} | {"board": true} (the dark board, for a tease grid or a CTA drawn on top: T20)
      | {"title": ["IRAN", "WAR"], "bg": "src:PATH@T" | "image:PATH"} (Dylan Page's item title card over the last receipt, blurred: T04 list)
"""
import json, math, os, shutil, subprocess, sys, tempfile
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

BIN = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, BIN)
import tmpl_fx as FX
import tmpl_board   # T17 Trainbloom boards: registers the "tb" element (11-07)
import tmpl_ig      # 11-10 workshop ads: registers "igtext" (Instagram-native text, no box)
import birefnet_cut as BC   # 11-11: his cut-out is BiRefNet only (rule 9); no Apple person mask, no fallback
W, H, FPS = FX.W, FX.H, FX.FPS
LUT = os.path.expanduser("~/ob-editor/luts/ob_grade_warmtan_hald.png")
SCRATCH = os.path.expanduser("~/ob-scratch/tmpl")
NEEDS_MATTE = {"cut", "inset", "card", "grid", "freeze"}


# ---------- media ----------
def probe_wh(path):
    o = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height:stream_side_data=rotation",
                        "-of", "json", path], capture_output=True, text=True).stdout
    s = json.loads(o)["streams"][0]; w, h = s["width"], s["height"]
    rot = next((abs(int(x.get("rotation", 0))) for x in s.get("side_data_list", []) if "rotation" in x), 0)
    return (h, w) if rot in (90, 270) else (w, h)


def cam_filter(P, w, h):
    """His frame as 1080x1920: a vertical camera scales; a landscape one is cropped 9:16 at P["cx"] first. Graded with the hald LUT."""
    vf = "scale=1080:1920:flags=lanczos" if h > w else f"crop=ih*9/16:ih:(iw-ih*9/16)*{P.get('cx', 0.5)}:0,scale=1080:1920:flags=lanczos"
    fr = P.get("frame")   # 11-11 workshop ads 14-20 (C4443 sat ~150 px lower): {"s": 1.15, "cy": 1.0} = ONE fixed crop for the whole video,
    if fr and fr.get("s", 1.0) > 1.0:   # 1/s of the source height taken from the 4K frame (still a downscale, no motion, not a zoom):
        s, cy = fr["s"], fr.get("cy", 0.5)       # cy 1.0 keeps the bottom edge, so his face sits higher and chest cards clear his chin
        if h > w: vf = f"crop=iw/{s}:ih/{s}:(iw-iw/{s})*{fr.get('cx', 0.5)}:(ih-ih/{s})*{cy},scale=1080:1920:flags=lanczos"   # his upright 2160x3840 camera
        else: vf = f"crop=ih*9/16/{s}:ih/{s}:(iw-ih*9/16/{s})*{P.get('cx', 0.5)}:(ih-ih/{s})*{cy},scale=1080:1920:flags=lanczos"
    return vf


def decode(path, start, n, vf, lut=None, size=(W, H)):
    """n frames from path at start, through vf (and the LUT), as PIL images (a generator)."""
    cmd = ["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{max(0.0, start):.4f}", "-i", path]
    if lut: cmd += ["-i", lut, "-filter_complex", f"[0:v]{vf}[v];[v][1:v]haldclut=shortest=0:repeatlast=1"]
    else: cmd += ["-vf", vf]
    cmd += ["-fps_mode", "passthrough", "-frames:v", str(n), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]   # 11-11: rawvideo's default cfr doubled the
    # first frame on some seeks (ad 4 2x2 V13: his face held 1 frame at 3 of 35 cuts, and that piece ran 1 frame behind its sound)
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE); sz = size[0] * size[1] * 3
    try:
        for _ in range(n):
            b = p.stdout.read(sz)
            if len(b) < sz: break
            yield Image.frombytes("RGB", size, b)
    finally: p.kill()


def src_frame_at(path, t, cache):
    k = ("srcf", path, round(t, 3))
    if k not in cache:
        g = decode(path, t, 1, "scale=1080:-2:flags=lanczos,pad=1080:ih", None, src_size(path, cache)); cache[k] = next(g); g.close()
    return cache[k]


def clip_frame(path, t0, t_loc, cache, n_max=900):
    """Frame t_loc seconds into a source played from t0 (decoded once per (path, t0), at 29.97 fps): footage that plays (M39)."""
    k = ("clip", path, round(t0, 3))
    if k not in cache:
        cache[k] = list(decode(path, t0, n_max, "framerate=fps=30000/1001,scale=1080:-2:flags=lanczos", None, src_size(path, cache)))
    fs = cache[k]; return fs[min(len(fs) - 1, int(round(t_loc * FPS)))] if fs else Image.new("RGB", (W, H))   # round: 1/29.97*29.97 is 0.9999


def src_size(path, cache):
    k = ("srcsz", path)
    if k not in cache:
        w, h = probe_wh(path); cache[k] = (1080, int(round(h * 1080 / w / 2) * 2))
    return cache[k]


def apple_words(wav, tries=6):
    """Apple's on-device word times. 11-06: with the Neural Engine busy (another session), speech_words crashed with 'no ANE
    resources (transient; retry)' and this returned [] in silence: no captions and no word-triggered elements. Now it retries with
    a growing wait and stops the render loudly if it never gets words."""
    import time
    err = ""
    for k in range(tries):
        r = subprocess.run([os.path.join(BIN, "speech_words"), "words", wav], capture_output=True, text=True); o = r.stdout
        if "[" in o: return [dict(w=x["w"], s=float(x["s"]), e=float(x["e"])) for x in json.loads(o[o.index("["):])]
        err = (r.stderr or "")[-300:]
        if "ANE" not in err and "transient" not in err and r.returncode == 0: return []   # it ran fine and heard nothing
        time.sleep(2 + 3 * k)
    print(f"  speech_words failed {tries}x (Neural Engine busy?): whisper.cpp word times instead for {os.path.basename(wav)}", flush=True)
    return whisper_words(wav)


def whisper_words(wav):
    """Fallback word times from local whisper.cpp (large-v3-turbo, Metal/CPU, no Neural Engine), same shape as apple_words."""
    td = tempfile.mkdtemp(dir=SCRATCH); w16 = os.path.join(td, "w16.wav")
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", wav, "-ac", "1", "-ar", "16000", w16], check=True)
    model = os.path.expanduser("~/.whisper-models/ggml-large-v3-turbo.bin")
    subprocess.run(["whisper-cli", "-m", model, "-f", w16, "-ml", "1", "-sow", "-oj", "-of", os.path.join(td, "w"), "-np", "-l", "en"],
                   check=True, capture_output=True)
    d = json.load(open(os.path.join(td, "w.json"))); out = []
    for x in d["transcription"]:
        t = x["text"].strip()
        if not t: continue
        if not any(c.isalnum() for c in t) and out: out[-1]["w"] += t; continue   # punctuation token joins the word before it
        out.append(dict(w=t, s=x["offsets"]["from"] / 1000, e=x["offsets"]["to"] / 1000))
    shutil.rmtree(td, ignore_errors=True); return out


def faces_of(paths):
    """Median face box over frames (Apple Vision `faces`), [x0, y0, x1, y1] in each frame's pixels, or None."""
    o = subprocess.run([os.path.join(BIN, "faces")] + paths, capture_output=True, text=True).stdout.split("\n")
    b = [[int(v) for v in r.split()[1:5]] for r in o if len(r.split()) >= 5 and r.split()[1] != "none"]
    return [float(np.median([x[i] for x in b])) for i in range(4)] if b else None


# ---------- layers ----------
GRID = None
def grid_layer():
    global GRID
    if GRID is None:
        GRID = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(GRID)
        for y in range(8, H, 16):
            for x in range(8, W, 16): d.point((x, y), fill=(255, 255, 255, 14))   # Kallaway measured: 15-16 px pitch, barely visible
    return GRID


def studio_bg(fr):
    """His own studio from the same frame, blurred and warm, moving with him (M38: never a black background)."""
    b = fr.resize((216, 384), Image.BILINEAR).filter(ImageFilter.GaussianBlur(7)); a = np.asarray(b, np.float32) * 0.8
    a[..., 0] *= 1.06; a[..., 2] *= 0.92
    return Image.alpha_composite(Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).resize((W, H), Image.BILINEAR).convert("RGBA"), grid_layer())


def board():
    g = Image.linear_gradient("L").resize((W, H)); a = np.dstack([np.asarray(g, np.float32) * f + c for f, c in ((0.10, 30), (0.08, 24), (0.06, 20))])
    return Image.alpha_composite(Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert("RGBA"), grid_layer())


def bg_of(spec, fr, cache):
    spec = spec or "studio"
    if spec == "studio": return studio_bg(fr)
    if spec == "board":
        if "board" not in cache: cache["board"] = board()
        return cache["board"].copy()
    if spec == "navy":   # Karan (measured 11-07): dark navy gradient #0E122B at the top to #4A5B6F at the bottom, no grid
        if "navy" not in cache:
            g = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]; a = np.array([14, 18, 43], np.float32) * (1 - g) + np.array([68, 83, 106], np.float32) * g
            cache["navy"] = Image.fromarray(np.repeat(a, W, axis=1).astype(np.uint8)).convert("RGBA")
        return cache["navy"].copy()
    if spec == "white":   # Karan's study page sits on white
        return Image.new("RGBA", (W, H), (255, 255, 255, 255))
    if spec in ("paper", "cream", "black"):   # T26 Drew: receipt pages and boards on #F8F8F8 / cream #F2EBE3; his inset b-roll cards on black
        return Image.new("RGBA", (W, H), {"paper": (248, 248, 248), "cream": (242, 235, 227), "black": (0, 0, 0)}[spec] + (255,))
    kind, _, arg = spec.partition(":")
    if kind == "frosted":
        k = ("frost", arg)
        if k not in cache: cache[k] = FX.frosted(FX.load(arg, "RGB"))
        return cache[k].copy()
    if kind == "image": return FX.fit_cover(FX.load(arg, "RGB"), W, H).convert("RGBA")
    if kind == "src":
        p, _, t = arg.rpartition("@"); return FX.fit_cover(src_frame_at(p, float(t), cache), W, H).convert("RGBA")
    if kind == "play":   # "play:PATH@T": her footage playing from T behind him (Squat University's cut-out over footage)
        p, _, t = arg.rpartition("@"); return FX.fit_cover(clip_frame(p, float(t), cache.get("_t_loc", 0.0), cache), W, H).convert("RGBA")
    raise ValueError(f"unknown bg {spec}")


def person(fr, m, face, face_w, cx, top):
    """His matted cut-out, scaled so his face is face_w px wide, its centre at x = cx and its top at y = top. Returns (layer, scale, offset)."""
    s = face_w / max(1.0, face[2] - face[0]); fx, fy = (face[0] + face[2]) / 2 * s, face[1] * s
    big = fr.resize((round(W * s), round(H * s)), Image.LANCZOS).convert("RGBA"); big.putalpha(m.resize(big.size, Image.BILINEAR))
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ox, oy = int(round(cx - fx)), int(round(top - fy))
    lay.paste(big, (ox, oy), big)
    return lay


def clip_rect(lay, box, radius=0, feather=0):
    m = Image.new("L", (W, H), 0); ImageDraw.Draw(m).rounded_rectangle(box, radius, fill=255) if radius else ImageDraw.Draw(m).rectangle(box, fill=255)
    if feather:   # 11-11 (ad 4 2x2 V13 reviewer: a straight chop across his chest): the bottom edge fades out over `feather` px
        y1 = int(box[3]); a_ = np.asarray(m).copy(); ramp = np.linspace(1.0, 0.0, feather + 1)[1:]
        a_[y1 - feather:y1] = (a_[y1 - feather:y1].astype(np.float32) * ramp[:, None]).astype(np.uint8); m = Image.fromarray(a_)
    a = np.minimum(np.asarray(lay.split()[3]), np.asarray(m)); lay.putalpha(Image.fromarray(a)); return lay


def fit_width_over_frost(sf):
    """A source frame at full width; if it isn't 9:16 its own blurred, darkened copy fills above and below (never black bands)."""
    if sf.size == (W, H): return sf.convert("RGBA")
    base = FX.frosted(sf, gain=0.5); y = (H - sf.height) // 2; base.paste(sf.convert("RGBA"), (0, y)); return base


# ---------- looks ----------
def broll_frame(path, t0, t_loc, cache, cx=0.5, lut=None, n=240):
    """T21: his b-roll full frame (a landscape clip cropped 9:16 at cx, graded with the plan LUT), playing from t0. Only the current
    clip stays decoded (1080x1920 frames are 6 MB each)."""
    k = ("broll", path, round(t0, 3), cx)
    if k not in cache:
        for old in [x for x in cache if isinstance(x, tuple) and x and x[0] == "broll"]: del cache[old]
        w, h = probe_wh(path)
        vf = ("scale=1080:1920:flags=lanczos" if h > w else f"crop=ih*9/16:ih:(iw-ih*9/16)*{cx}:0,scale=1080:1920:flags=lanczos") + ",framerate=fps=30000/1001"
        cache[k] = list(decode(path, t0, n, vf, lut))
    fs = cache[k]
    return (fs[min(len(fs) - 1, int(round(t_loc * FPS)))] if fs else Image.new("RGB", (W, H), (20, 18, 16))).convert("RGBA")


def compose(L, t_loc, fr, m, face, sf, ctx, P, seg):
    cache = ctx["cache"]; name = L["name"]; t_run = t_loc + seg.get("look_off", 0.0); cache["_t_loc"] = t_run   # footage time runs across pause cuts
    if name == "broll":   # T21 (Sarah Snow): his life on screen, his voice running under it; no cut-out, no PiP
        return broll_frame(L["src"], L.get("t", 0.0), t_run, cache, L.get("cx", 0.5), P.get("lut", LUT), seg.get("run_n", seg["n"]) + 2), None
    if name == "full" and L.get("push"):   # T21: a slow linear push on his wide shot (hook 1.00 -> 1.13 over ~2.4 s); text does not scale
        s0, s1 = L["push"]; s = s0 + (s1 - s0) * min(1.0, t_loc / max(seg["dur"], 1e-3))
        cx, cy = L.get("zoom_at", (W / 2, H / 2)); return (zoom_frame(fr, s, cx, cy) if s > 1.0005 else fr).convert("RGBA"), None
    if name == "full" and L.get("drift"):   # T26 Drew: push +2.4%/s (40% of shots), hold, or pull -1.6%/s on a closing line
        s = max(1.0, L.get("drift_from", 1.0 if L["drift"] > 0 else 1.0 + abs(L["drift"]) * seg["dur"]) + L["drift"] * t_loc)
        cx, cy = L.get("zoom_at", (W / 2, H * 0.36)); return (zoom_frame(fr, s, cx, cy) if s > 1.0005 else fr).convert("RGBA"), None
    if name == "full":
        z = L.get("zoom")   # Dylan Page: a hard cut to him full frame lands ~1.22x in and eases out in ~0.45 s (FX.zoom_out)
        s = FX.zoom_out(t_loc, z) if z else 1.0
        if s <= 1.0005: return fr.convert("RGBA"), None
        cx, cy = L.get("zoom_at", (W / 2, H / 2)); out = zoom_frame(fr, s, cx, cy)
        ds = s - FX.zoom_out(t_loc + 1 / FPS, z)
        if ds > 0.012:   # his first 3-4 frames are motion-blurred: average this frame's travel
            out = Image.blend(Image.blend(out, zoom_frame(fr, s - ds / 2, cx, cy), 0.5), zoom_frame(fr, s - ds, cx, cy), 0.33)
        return out.convert("RGBA"), None
    if name == "source":
        pk = L.get("peek") or {}
        if pk.get("mode") == "card" and fr is not None:
            # T25 Michael Read (DfRw4sMtL7P, 11-07): HE is full frame at his desk reacting live (his real playback, M34) while the
            # other creator's clip plays with its sound in a 9:16 rounded card over the wall beside his head: measured x 576-944,
            # y 260-912, radius ~16, a thin light border. On from frame 0; gone on the hard cut to his first word.
            z = pk.get("zoom", 1.0); base = (zoom_frame(fr, z, *pk.get("zoom_at", (W / 2, H / 2))) if z > 1.0005 else fr).convert("RGBA")
            x0, y0, x1, y1 = pk.get("box", (576, 260, 944, 912)); bw, bh = x1 - x0, y1 - y0; r = pk.get("radius", 16)
            u = FX.ease_out(t_loc - pk.get("in", 0.0), pk.get("dur", 0.0)) if pk.get("dur") else 1.0
            if u > 0:
                cs = 0.9 + 0.1 * u; cw, ch = int(bw * cs), int(bh * cs); cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
                tile = FX.fit_cover(sf, cw, ch).convert("RGBA"); msk = FX.rounded_mask(cw, ch, r).point(lambda v: int(v * u))
                if pk.get("shadow", True):
                    sh = Image.new("L", (W, H), 0); ImageDraw.Draw(sh).rounded_rectangle([cx - cw / 2 + 6, cy - ch / 2 + 10, cx + cw / 2 + 6, cy + ch / 2 + 10], r, fill=int(120 * u))
                    base.alpha_composite(Image.merge("RGBA", (*[Image.new("L", (W, H), 0)] * 3, sh.filter(ImageFilter.GaussianBlur(14)))))
                base.paste(tile, (int(cx - cw / 2), int(cy - ch / 2)), msk)
                bc = tuple(pk.get("border", (246, 214, 210))); ImageDraw.Draw(base).rounded_rectangle([cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2], r, outline=bc + (int(255 * u),), width=pk.get("border_w", 3))
            return base, None
        base = fit_width_over_frost(sf)
        if pk and fr is not None and m is not None and face:
            if pk.get("mode") == "slide":
                # Karan (11-07, 10 fps): he brings himself in from the right edge in ~0.3 s and STAYS for the whole runway. Body size is
                # OB's 11-04 pick ("am i just a head, i liked what we were doing"): upper body, face ~185 px. Face kept left of IG's right rail.
                # Deep pass 11-07 (23 reaction reels): in at 1.1-1.6 s over ~0.6 s easing out, rests at face centre ~(1000, 1380), face ~250,
                # ~18% off the edge; holds silent (median 6.4 s); whips OUT in ~0.27 s easing in, with motion blur, ending on the cut.
                fw = pk.get("face_w", 250); fx = pk.get("face_cx", 1000); off = W - fx + fw * 1.6
                u = FX.ease_out(t_loc - pk.get("in", 1.3), pk.get("dur", 0.6)); od = pk.get("out", 0.27)   # bulk 11-07: in at 1.30 s median
                v = min(1.0, max(0.0, (t_loc - (seg["dur"] - od)) / od)) ** 3 if od else 0.0
                if u > 0 and v < 1:
                    cx = fx + (1 - u) * off + v * off; top = pk.get("face_top", 1380 - 0.65 * fw)
                    lay = person(fr, m, face, fw, cx, top)
                    if v > 0:   # motion blur on the whip-out: this frame's travel averaged
                        dv = off * (min(1.0, max(0.0, (t_loc + 1 / FPS - (seg["dur"] - od)) / od)) ** 3 - v)
                        lay = Image.blend(Image.blend(lay, person(fr, m, face, fw, cx + dv / 2, top), 0.5), person(fr, m, face, fw, cx + dv, top), 0.33)
                    base.alpha_composite(lay)
            elif pk.get("mode", "corner") == "corner":
                # OB 11-04 on the test: "on the original reaction am i just a head, i liked what we were doing". His FDOE corner
                # cut-out (presets/fdoe-audit Locked values): upper body, body running off the bottom edge, face 175-195 px wide,
                # face left edge 0.12-0.19 W, face top 0.66-0.74 H. On from frame 1 (two people at 0.4 s, PROVEN-OPENERS rule 1).
                fw = pk.get("face_w", 185); cx = pk.get("face_left", 150) + fw / 2
                base.alpha_composite(person(fr, m, face, fw, cx, pk.get("face_top", 1300)))
            else:   # Karan's peek: head and shoulders sliding in at the edge (an option, not OB's default)
                u = FX.ease_out(t_loc - pk.get("in", 0.0), 0.3); fw = pk.get("face_w", 230)
                side = pk.get("side", "left"); cx = (150 if side == "left" else W - 150) + (-1 if side == "left" else 1) * (1 - u) * 420
                lay = person(fr, m, face, fw, cx, pk.get("face_top", 1250)); clip_rect(lay, (0, 860, W, 1500)); base.alpha_composite(lay)
        return base, None
    if name == "freeze":
        k = ("freeze", L["src"], L["t"], L.get("punch", 1.4))
        if k not in cache:
            f0 = fit_width_over_frost(src_frame_at(L["src"], L["t"], cache)); p = L.get("punch", 1.4); cx, cy = L.get("punch_at", (W / 2, H * 0.4))
            big = f0.resize((round(W * p), round(H * p)), Image.LANCZOS); x, y = int(cx * p - cx), int(cy * p - cy)
            cache[k] = big.crop((x, y, x + W, y + H))
        base = cache[k].copy(); lay = person(fr, m, face, L.get("face_w", 190), (L["box"][0] + L["box"][2]) / 2, L["box"][1] + L.get("pad_top", 90))
        return base, clip_rect(lay, L["box"])
    if name == "box":   # T03: his frame (him watching) with her 9:16 clip playing in OB's box, bottom on the frame edge (reaction preset)
        base = fr.convert("RGBA"); x0, y0, bw, bh = L.get("box", (224, 796, 632, 1124))
        clip = clip_frame(L["src"], L.get("t", 0.0), t_run, cache); base.paste(FX.fit_cover(clip, bw, bh), (x0, y0)); return base, None
    if name == "cut":
        base = bg_of(L.get("bg"), fr, cache)
        if L.get("spot"):   # Karan (11-07): small cut-out, face centre on one of his spots, a flat bottom edge across his chest
            fw = L.get("face_w", 168); cx, cy = L["spot"]; lay = person(fr, m, face, fw, cx, cy - 0.65 * fw)
            return base, clip_rect(lay, (0, 0, W, int(L.get("bottom", cy + 2.0 * fw))))
        return base, person(fr, m, face, L.get("face_w", 300), L.get("face_cx", W / 2), L.get("face_top", 700))
    if name == "inset":
        base = bg_of(L.get("bg", "studio"), fr, cache); bx = L["box"]
        lay = person(fr, m, face, L.get("face_w", 190), (bx[0] + bx[2]) / 2, bx[1] + L.get("pad_top", 90))
        return base, clip_rect(lay, bx)
    if name == "plate":   # T26 Drew: a full-frame page / board / still with his voice over it (no OB on screen)
        return bg_of(L.get("bg", "paper"), fr, cache), None
    if name == "bcard":   # T26 Drew: b-roll in a rounded card x 87-993, y 408-1428 (905x1020), radius 54, on black with a soft glow
        x0, y0, x1, y1 = L.get("box", (87, 408, 993, 1428)); bw, bh = x1 - x0, y1 - y0
        base = Image.new("RGBA", (W, H), (0, 0, 0, 255)); clip = clip_frame(L["src"], L.get("t", 0.0), t_run, cache)
        gl = Image.new("L", (W, H), 0); ImageDraw.Draw(gl).rounded_rectangle([x0, y0, x1, y1], L.get("radius", 54), fill=90)
        base.alpha_composite(Image.merge("RGBA", (*[Image.new("L", (W, H), 255)] * 3, gl.filter(ImageFilter.GaussianBlur(20)))))
        base.paste(FX.fit_cover(clip, bw, bh).convert("RGBA"), (x0, y0), FX.rounded_mask(bw, bh, L.get("radius", 54)))
        return base, None
    if name == "glide":   # Karan DeUQXhMtwNs 60.6-68 s: his box starts big over the picture, then shrinks and glides off it, no cut
        a, b = L["from"], L["to"]; u = t_loc - L.get("at", 0.4); d = L.get("dur", 1.4)
        e = 0.0 if u <= 0 else 1.0 if u >= d else (lambda x: x * x * (3 - 2 * x))(u / d)
        lerp = lambda p, q: p + (q - p) * e
        C = dict(L, name="card", box=[int(round(lerp(p, q))) for p, q in zip(a["box"], b["box"])], face_w=lerp(a["face_w"], b["face_w"]))
        return compose(C, t_loc, fr, m, face, sf, ctx, P, seg)
    if name == "card":
        base = bg_of(L.get("bg", "studio"), fr, cache); x0, y0, x1, y1 = L["box"]; bw, bh = x1 - x0, y1 - y0
        s = L.get("face_w", 240) / max(1.0, face[2] - face[0]); fcx, fcy = (face[0] + face[2]) / 2 * s, (face[1] + face[3]) / 2 * s
        big = fr.resize((round(W * s), round(H * s)), Image.LANCZOS)
        cx0 = int(min(max(0, fcx - bw / 2), big.width - bw)); cy0 = int(min(max(0, fcy - bh * L.get("face_cy", 0.42)), big.height - bh))
        tile = big.crop((cx0, cy0, cx0 + bw, cy0 + bh)).convert("RGBA")
        if L.get("glow"):
            gl = Image.new("L", (W, H), 0); ImageDraw.Draw(gl).rounded_rectangle([x0, y0, x1, y1], L.get("radius", 40), fill=255)
            gl = gl.filter(ImageFilter.GaussianBlur(18)).point(lambda v: int(v * 0.4)); base.alpha_composite(Image.merge("RGBA", (*[Image.new("L", (W, H), c) for c in FX.YEL], gl)))
        base.paste(tile, (x0, y0), FX.rounded_mask(bw, bh, L.get("radius", 40), bottom_open=y1 >= H))
        pop = None
        if L.get("pop") and m is not None:   # his head over the card's top edge (T02 'head popping out')
            mm = m.resize(big.size, Image.BILINEAR).crop((cx0, cy0 - 400, cx0 + bw, cy0)) if cy0 >= 400 else None
            if mm is not None:
                head = big.crop((cx0, cy0 - 400, cx0 + bw, cy0)).convert("RGBA"); head.putalpha(mm)
                pop = Image.new("RGBA", (W, H), (0, 0, 0, 0)); pop.paste(head, (x0, y0 - 400), head)
                a = np.asarray(pop.split()[3]).copy(); a[:, :x0] = 0; a[:, x1:] = 0; pop.putalpha(Image.fromarray(a))
        return base, pop
    if name == "split":
        seam = L.get("seam", 876); base = studio_bg(fr)
        s_face_top = L.get("face_top", seam + 290); dy = int(s_face_top - face[1]) if face else seam   # 290: his cap clears the seam (Dylan Page's 190 assumes no tall cap)
        frac = FX.drop_in(t_loc) if L.get("drop") else 1.0
        # DfVXmUnBInZ: on a drop-in his picture is pushed down with the panel's edge, from where it sat full frame (same ease)
        if L.get("ob_push"):   # T26 Drew: his half pushes in ~2%/s through the hook (Dylan Page's never zooms)
            fr = zoom_frame(fr, 1.0 + L["ob_push"] * t_loc, W / 2, face[1] if face else H * 0.35)
        base.paste(fr.convert("RGBA"), (0, int(round(dy * frac)) if L.get("drop") and L.get("push", True) else dy))   # same scale, never zoomed
        rising = L.get("rise") is not None and seg["dur"] - t_loc < L["rise"]
        if rising: frac = FX.slide_up(t_loc - (seg["dur"] - L["rise"]))
        top = top_panel(L["top"], t_run, seam, cache)
        if frac >= 1.0 or (frac > 0 and rising):
            base.paste(top, (0, int(seam * (frac - 1.0))))
        elif frac > 0:   # the drop-in is a wipe: the edge comes down while the receipt drifts its last 54 px into place
            drift = int(round(54 * seam / 876 * (1.0 - frac))); h = int(round(seam * frac))
            base.paste(top.crop((0, drift, W, drift + h)), (0, 0))
        return base, None
    if name == "grid":
        cells = L["cells"]; sw = [FX.trigger({"on": x, "lead": 0.0} if isinstance(x, str) else {"at": x}, ctx["words"], default=1e9) for x in L.get("swap", [])]
        base = Image.new("RGBA", (W, H)); order = [(0, 0), (540, 0), (540, 960), (0, 960)]           # TL > TR > BR > BL
        t = seg["t0"] + t_loc
        for i, (x, y) in enumerate(order):
            k = sum(1 for s in sw if t >= s + i * 0.18) % len(cells)   # each swap cascades clockwise, 0.18 s apart (Eugene measured 0.13-0.23)
            kk = ("cell", cells[k][i]); pth = cells[k][i]
            z = 1.0 + L.get("push", 0.03) * min(1.0, t / max(1.0, seg["dur"] + seg["t0"]))   # a slow linear push across the grid's whole run ("push": 0 = still, OB no-zoom ads 11-10)
            if pth.lower().endswith((".mp4", ".mov")):   # 11-10: a stock clip plays in the cell from the moment it lands (tmpl_ig clip cache)
                nsw = sum(1 for s_ in sw if t >= s_ + i * 0.18); j_ = nsw   # it landed at the last swap that changed THIS cell: a swap
                while j_ and cells[j_ % len(cells)][i] == cells[(j_ - 1) % len(cells)][i]: j_ -= 1   # elsewhere doesn't restart it (11-10)
                appear = sw[j_ - 1] + i * 0.18 if j_ else L.get("start", 0.0)
                tg = ctx.get("t_grid", t); tl_c = (round(tg * FPS) - round(appear * FPS)) / FPS   # whole frames since the cell landed
                fr_c = tmpl_ig.clip_frame_at(pth, 600, 1066, tl_c, cache, L.get("clip_in", {}).get(pth, 0.0), L.get("clip_dur", 12.0),
                                             tuple(L.get("clip_focus", {}).get(pth, (0.5, 0.5))))
                c = fr_c if z == 1.0 else fr_c.resize((round(600 * z), round(1066 * z)), Image.BILINEAR)
            else:   # "photo_focus": {path: (fx, fy)} places the 600x1066 crop (11-10: a centred face in a bottom cell sat behind him)
                pf = L.get("photo_focus", {}).get(pth); kk = ("cell", pth, tuple(pf) if pf else None)
                if kk not in cache: cache[kk] = (fit_cover_at(FX.load(pth, "RGB"), 600, 1066, *pf) if pf else FX.fit_cover(FX.load(pth, "RGB"), 600, 1066)).convert("RGBA")
                c = cache[kk].resize((round(600 * z), round(1066 * z)), Image.BILINEAR)
            ox, oy = (c.width - 540) // 2, (c.height - 960) // 2
            base.paste(c.crop((ox, oy, ox + 540, oy + 960)), (x, y))
        lay = person(fr, m, face, L.get("face_w", 211), W / 2, L.get("face_top", 651))
        return base, clip_rect(lay, L.get("clip", [227, 537, 853, 1346]), feather=int(L.get("feather", 0)))
    raise ValueError(f"unknown look {name}")


def fit_cover_at(im, w, h, fx=0.5, fy=0.5):
    """FX.fit_cover with the crop placed at (fx, fy) of the spare width/height, 0-1 (0.5, 0.5 = FX.fit_cover)."""
    s = max(w / im.width, h / im.height); r = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)
    x = round((r.width - w) * min(1.0, max(0.0, fx))); y = round((r.height - h) * min(1.0, max(0.0, fy)))
    return r.crop((x, y, x + w, y + h))


def top_panel(T, t_loc, seam, cache):
    if T.get("board"): return FX._panel_bg(W, seam).copy()   # the warm dark board under a tease grid or a drawn element (T20)
    if "image" in T: return FX.fit_cover(FX.load(T["image"], "RGB"), W, seam).convert("RGBA")
    if "src" in T:
        sf = clip_frame(T["src"], T.get("t", 0.0), t_loc, cache) if T.get("play", True) else src_frame_at(T["src"], T.get("t", 0.0), cache)
        return FX.fit_cover(sf, W, seam).convert("RGBA")
    if "card" in T:   # a screenshot shown whole (a wide Cronometer card), on its own frosted blur, with a slow push
        k = ("topcard", T["card"], seam)
        if k not in cache:
            im = FX.load(T["card"], "RGB"); bg = FX.fit_cover(FX.frosted(im).convert("RGB"), W, seam).convert("RGBA")
            cw = T.get("w", 980); ch = round(im.height * cw / im.width); cache[k] = (bg, im.resize((cw, ch), Image.LANCZOS).convert("RGBA"))
        bg, card = cache[k]; out = bg.copy(); z = 1.0 + 0.015 * t_loc
        c2 = card.resize((round(card.width * z), round(card.height * z)), Image.LANCZOS)
        cy = max(seam / 2, FX.SAFE_TOP + 30 + c2.height / 2)
        out.paste(c2, ((W - c2.width) // 2, int(cy - c2.height / 2)), FX.rounded_mask(c2.width, c2.height, 16)); return out
    if "burst" in T:
        i = min(len(T["burst"]) - 1, int(t_loc // T.get("each", 0.6))); return FX.fit_cover(FX.load(T["burst"][i], "RGB"), W, seam).convert("RGBA")
    if "title" in T:   # Dylan Page's item title card: {"title": ["IRAN", "WAR"], "bg": "src:PATH@T" | "image:PATH"} (the previous receipt)
        k = ("titlebg", T.get("bg"), seam)
        if k not in cache:
            b = T.get("bg"); kind, _, arg = (b or "").partition(":")
            if kind == "src": p, _, tt = arg.rpartition("@"); im = src_frame_at(p, float(tt), cache)
            elif kind == "image": im = FX.load(arg, "RGB")
            else: im = None
            cache[k] = FX.fit_cover(FX.frosted(im, gain=0.42).convert("RGB"), W, seam).convert("RGBA") if im is not None else FX._panel_bg(W, seam).copy()
        return FX.title_card(T["title"], seam, cache[k], t_loc)
    raise ValueError("top panel needs image, src, card, burst, title or board")


def zoom_frame(fr, s, cx, cy):
    """His frame scaled by s about (cx, cy), cropped back to W x H (the zoom-out on a cut to full frame)."""
    big = fr.resize((round(W * s), round(H * s)), Image.BICUBIC); x, y = int(round(cx * s - cx)), int(round(cy * s - cy))
    return big.crop((x, y, x + W, y + H))


# ---------- render ----------
def expand_lines(P):
    """"lines" -> timeline pieces, the rule's way: each line runs from a word to a word (Apple words on the mic clock, "words_json"),
    cut by zero_dead.cut_words (edges at the first onset and the last word's end, every 70 ms+ pause out, nothing inside a word cut).
    A line: {"from": "Because", "to": "calories", "near": 181.0, "look": LOOK, "switch": [{"word": W, "near": T, "look": LOOK}],
    "tail": 0.15 (last line only: seconds kept after
    the last word so it decays to silence)}; camera time = mic time + P["off"].
    Source clips go in the same list as {"src": ...} entries, unchanged."""
    if "lines" not in P: return P["timeline"]
    import zero_dead as Z
    words = json.load(open(P["words_json"])); env = Z.level_env(P["mic"]); tl = []
    norm = lambda s: s.lower().strip(".,!?\"'")
    for L in P["lines"]:
        if "src" in L: tl.append(L); continue
        near = L.get("near", 0.0)
        i0 = next(i for i, w in enumerate(words) if float(w["s"]) >= near - L.get("tol", 0.6) and norm(w["w"]) == norm(L["from"]))
        i1 = next(i for i, w in enumerate(words) if i >= i0 and float(w["s"]) >= L.get("to_after", 0.0) and norm(w["w"]) == norm(L["to"]))
        ws = [dict(w=w["w"], s=float(w["s"]), e=float(w["e"])) for w in words]
        pcs = Z.cut_words(env, ws, i0, i1, FPS, lo=L.get("start_at"), hi=L.get("end_at")); cuts = []   # start_at/end_at: mic-time caps where the ASR runs a word into the next one
        if P.get("drop_blips", True) and len(pcs) > 1:   # 11-11 (workshop ads 7, 8, 9, 13): a breath or click inside a long pause came out as its own
            # 0.1-0.4 s piece with no word in it, and its edges sat in his breath (gate edges FAIL); a piece no word of the line overlaps is dropped
            kept = [(a, b) for a, b in pcs if any(ws[i]["e"] > a + 0.02 and ws[i]["s"] < b - 0.02 for i in range(i0, i1 + 1))]
            pcs = kept or pcs
        if P.get("keep_pauses"):   # T21 (Sarah Snow, OB 11-06 "keep it all"): her breaths stay; only pauses longer than this are cut
            mg = [pcs[0]]
            for a, b in pcs[1:]:
                if a - mg[-1][1] <= P["keep_pauses"]: mg[-1] = (mg[-1][0], b)
                else: mg.append((a, b))
            pcs = mg
        if L.get("tail"):   # the edit's last line: let the last word decay (11-04 T20: the file ended on "-tion" at -30 dB, gate FAIL)
            pcs[-1] = (pcs[-1][0], round((pcs[-1][1] + L["tail"]) * FPS) / FPS)
        for sw in L.get("switch", []):   # a look change on a word inside one breath: split at the quietest 10 ms before it
            j = next(i for i in range(i0 + 1, i1 + 1) if norm(words[i]["w"]) == norm(sw["word"])   # "near": mic time, when the word repeats
                     and float(words[i]["s"]) >= sw.get("near", 0.0) - sw.get("tol", 0.3))
            lo, hi = float(words[j - 1]["e"]) - 0.06, float(words[j]["s"]) + 0.12
            k0, k1 = int(lo / Z.HOP), max(int(lo / Z.HOP) + 1, int(hi / Z.HOP)); ts = (k0 + int(np.argmin(env[k0:k1]))) * Z.HOP + 0.015
            cuts.append((round(ts * FPS) / FPS, sw["look"], sw.get("id", L.get("id"))))
        look, lid = L["look"], L.get("id")
        for a, b in pcs:
            for ts, lk, li in sorted(cuts):
                if a < ts < b: tl.append({"mic": [a, ts], "cam": a + P["off"], "look": look, "line": lid}); a = ts
                if a >= ts: look, lid = lk, li
            tl.append({"mic": [a, b], "cam": a + P["off"], "look": look, "line": lid})
    return tl


def plan_segments(P):
    segs, t = [], 0.0
    for s in expand_lines(P):
        d = dict(s)
        d["dur"] = (s["mic"][1] - s["mic"][0]) if "mic" in s else (s["out"] - s["in"])
        d["t0"] = t; d["f0"] = int(round(t * FPS)); t += d["dur"]; d["f1"] = int(round(t * FPS)); d["n"] = d["f1"] - d["f0"]
        p = segs[-1] if segs else None   # pieces of one line cut at its pauses share one look: footage in it keeps playing (11-07 gap audit)
        d["look_off"] = p["look_off"] + p["dur"] if p is not None and p.get("look") is d.get("look") and p.get("line") == d.get("line") else 0.0
        segs.append(d)
    for i in range(len(segs) - 1, -1, -1):   # each piece knows how many frames its whole look run needs (b-roll decodes once)
        nx = segs[i + 1] if i + 1 < len(segs) else None
        segs[i]["run_n"] = nx["run_n"] if nx is not None and nx["look_off"] > 0 and nx.get("look") is segs[i].get("look") else int(round((segs[i]["look_off"] + segs[i]["dur"]) * FPS))
    return segs, t


def prepare(P, segs, td):
    """Words on the edit clock, mattes and face boxes for every segment whose look cuts him out (or peeks)."""
    words, wavs = [], []
    for i, s in enumerate(segs):
        wav = os.path.join(td, f"a{i:03d}.wav")
        if "mic" in s:
            subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{s['mic'][0]:.4f}", "-t", f"{s['dur']:.4f}", "-i", P["mic"], "-ac", "2", "-ar", "48000", wav], check=True)
            words += [dict(w, s=w["s"] + s["t0"], e=w["e"] + s["t0"]) for w in apple_words(wav)]
        elif s.get("audio", True):
            subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{s['in']:.4f}", "-t", f"{s['dur']:.4f}", "-i", s["src"], "-vn", "-ac", "2", "-ar", "48000", wav], check=True)
        else:
            subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "lavfi", "-t", f"{s['dur']:.4f}", "-i", "anullsrc=r=48000:cl=stereo", wav], check=True)
        wavs.append(wav)
    for fx in P.get("fix", []):   # Apple mishears ("salmon" -> "Zen"): ["zen", "salmon"]; ["asic", null] drops the word
        heard, said = fx[0], fx[1]; sc = fx[2] if len(fx) > 2 else None   # 11-10: a 3rd item scopes it: a line id ("L08"), [t0, t1] or T (+-1.2 s), edit clock
        if isinstance(sc, str):
            ss = [s for s in segs if s.get("line") == sc]; sc = (min(s["t0"] for s in ss) - 0.05, max(s["t0"] + s["dur"] for s in ss) + 0.05)
        elif isinstance(sc, (int, float)): sc = (sc - 1.2, sc + 1.2)
        inside = lambda w, sc=sc: sc is None or sc[0] <= w["s"] < sc[1]
        if heard.startswith("="):   # exact spelling only ("=Less" fixes the sentence-start "Less" but not "eats less,")
            hit = lambda w, h=heard[1:]: w["w"].strip() == h and inside(w)
        else: hit = lambda w, h=heard: FX._n(w["w"]) == FX._n(h) and inside(w)
        words = [w for w in words if not (said is None and hit(w))]
        if said is not None: [w.update(w=said) for w in words if hit(w)]
    cw, ch = probe_wh(P["cam"]); vf = cam_filter(P, cw, ch); lut = P.get("lut", LUT); os.makedirs(os.path.join(td, "mi"), exist_ok=True)
    if any(s["look"]["name"] in NEEDS_MATTE or s["look"]["name"] == "source" for s in segs if (s.get("cam") if "mic" in s else (s["look"].get("peek") or {}).get("cam")) is not None):
        BC.check()   # 11-11: stop before decoding when BiRefNet cannot run (one line: what is missing, how to fix it)
    stretches = []
    for i, s in enumerate(segs):
        cam_a = s.get("cam") if "mic" in s else (s["look"].get("peek") or {}).get("cam")
        if cam_a is None: continue
        need = s["look"]["name"] in NEEDS_MATTE or (s["look"]["name"] == "source")
        fs = []
        for k, fr in enumerate(decode(P["cam"], cam_a, s["n"], vf, lut)):
            if need or k in (0, s["n"] // 2, s["n"] - 1):
                p = os.path.join(td, "mi", f"{i:03d}_{k:04d}.png"); fr.resize((540, 960), Image.BILINEAR).save(p, compress_level=1); fs.append(p)
        mids = [f for f in fs if int(os.path.basename(f)[4:8]) in (0, s["n"] // 2, max(0, s["n"] - 1))][:3]
        fc = faces_of(mids); s["face"] = [v * 2 for v in fc] if fc else None
        s["need_matte"] = need
        if need:
            lm = os.path.getmtime(lut) if lut and os.path.exists(lut) else 0
            stretches.append({"src": P["cam"], "t0": cam_a, "n": s["n"], "fps": FPS, "size": (540, 960), "look": f"tmpl decode vf={vf} lut={lut}@{lm:.0f} bilinear passthrough",
                              "frames": [os.path.join(td, "mi", f"{i:03d}_{k:04d}.png") for k in range(s["n"])]})
    if stretches:   # 11-11: BiRefNet only (OB 11-06/11-09, rule 9): birefnet_cut.py, cached; the Apple person mask and fg_mask_dir are gone
        P["_matte_info"] = BC.masks(stretches, os.path.join(td, "mo"), td, work=P.get("_work"), only=P.get("_matte_only"))
    return words, wavs, vf, lut


def mix_audio(P, segs, wavs, words, td, total):
    lst = os.path.join(td, "l.txt"); open(lst, "w").write("".join(f"file '{w}'\n" for w in wavs))
    voice, raw = os.path.join(td, "voice.wav"), os.path.join(td, "raw.wav")
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-ar", "48000", "-ac", "1", raw], check=True)
    import voice_master as VM
    from scipy.io import wavfile
    sr, x = wavfile.read(raw); x = x.astype(np.float64) / (32768.0 if x.dtype == np.int16 else 1.0)
    lines = [(int(round(s["t0"] * sr)), int(round((s["t0"] + s["dur"]) * sr))) for s in segs]
    z, rep = VM.master(x, sr, -14.0, lines); wavfile.write(voice, sr, z.astype(np.float32))
    print(f"  voice: {rep['out_lufs']:.1f} LUFS, true peak {rep['out_true_peak']:.1f}, flat tops {rep['flat_tops']}")
    mu = P.get("music")
    if mu:   # T21: her soft bed under the voice, not ducked ({"file", "start", "rel": -18, "duck": 0}); OB picks the track by ear
        import music_mix as MM
        bed = MM.bed(os.path.expanduser(mu["file"]), mu.get("start", 0.0), z, sr, mu.get("rel", -18), mu.get("duck", 0))
        vz = z if z.ndim == 2 else np.stack([z, z], axis=1); n = min(len(vz), len(bed))
        mix = np.concatenate([vz[:n] + bed[:n], vz[n:]]) if len(vz) > n else vz[:n] + bed[:n]
        tmpm = os.path.join(td, "vm_raw.wav"); wavfile.write(tmpm, sr, mix.astype(np.float32)); voice = os.path.join(td, "voice_music.wav")
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", tmpm, "-af", "alimiter=limit=0.84:level=false", voice], check=True)
        print(f"  music: {os.path.basename(mu['file'])} at {mu.get('rel', -18)} dB under the voice, duck {mu.get('duck', 0)} dB")
    fx = P.get("sfx", [])
    if not fx: return voice
    ins, flt, k = ["-i", voice], [], 0
    for e in fx:
        t = FX.trigger(e, words, default=None)
        if t is None: print(f"  sfx: no word '{e.get('on')}' heard, skipped"); continue
        k += 1; ins += ["-i", os.path.expanduser(e["file"])]; ms = int(max(0.0, t + e.get("lead", 0.15) + e.get("delay", 0.0)) * 1000)   # its peak on the word (not 0.15 s early), + "delay" s (a click after the word)
        st = e.get("start", 0.0)   # "start": trim the head too (Drew's riser: only its last 0.8 s swell, ending on the cut)
        flt.append(f"[{k}:a]aformat=sample_rates=48000:channel_layouts=stereo,atrim={st}:{st + e.get('len', 2.0)},asetpts=PTS-STARTPTS,volume={e.get('db', -20)}dB,adelay={ms}|{ms}[s{k}]")
    if not k: return voice
    lab = "".join(f"[s{j}]" for j in range(1, k + 1))
    out = os.path.join(td, "mix.wav")
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", *ins, "-filter_complex",
                    ";".join(flt + [f"[0:a]{lab}amix=inputs={len(ins) // 2}:normalize=0:duration=first,alimiter=limit=0.84:level=false[m]"]), "-map", "[m]", out], check=True)
    return out


def placed_face(L):
    """Where a look puts his face on the output frame ([x0, y0, x1, y1]), for looks that scale him to a face width."""
    n = L["name"]
    if n == "cut" and L.get("spot"): fw = L.get("face_w", 168); cx, top = L["spot"][0], L["spot"][1] - 0.65 * fw
    elif n == "cut": fw, cx, top = L.get("face_w", 300), L.get("face_cx", W / 2), L.get("face_top", 700)
    elif n == "grid": fw, cx, top = L.get("face_w", 211), W / 2, L.get("face_top", 651)
    elif n in ("inset", "freeze"): fw, cx, top = L.get("face_w", 190), (L["box"][0] + L["box"][2]) / 2, L["box"][1] + L.get("pad_top", 90)
    else: return None
    return [cx - fw / 2, top, cx + fw / 2, top + fw * 1.3]


def frame_for(P, seg, k, fr, td, ctx):
    L = seg["look"]; t = seg["t0"] + k / FPS; t_loc = k / FPS
    m = None
    if seg.get("need_matte"):
        p = os.path.join(td, "mo", f"{seg['i']:03d}_{k:04d}.png")
        if os.path.exists(p):
            # his BiRefNet matte at 540x960 (birefnet_cut.py), scaled up. The "mf" branch below served Apple's foreground matte
            # (fg_mask_dir), which is no longer made (11-11), so it never runs; kept so old temp layouts still read.
            a = np.asarray(Image.open(p).convert("L")); pf = p.replace(os.sep + "mo" + os.sep, os.sep + "mf" + os.sep)
            if os.path.exists(pf):   # inside his silhouette take the foreground matte's solid fill (held mic); outside keep his fine edges
                from scipy import ndimage
                f = np.asarray(Image.open(pf).convert("L").resize((a.shape[1], a.shape[0]), Image.BILINEAR))
                inside = ndimage.binary_closing(a > 20, structure=np.ones((41, 41), bool))   # his silhouette with notches up to ~80 px closed (a mic)
                a = np.where(inside, np.maximum(a, f), a)
            m = Image.fromarray(a.astype(np.uint8)).resize((W, H), Image.BILINEAR)
    sf = None
    if "src" in seg: sf = ctx["src_frames"][min(k, len(ctx["src_frames"]) - 1)]
    face = seg.get("face") or [440, 600, 640, 800]
    ctx["t_grid"] = (seg["f0"] + k) / FPS   # 11-10: the output frame's own time; seg t0 sits up to half a frame off the grid at each cut,
                                            # so clips indexed by t repeated or skipped a frame there (frame-diff scan); clips index by this
    base, him = compose(L, t_loc, fr, m, face, sf, ctx, P, seg)
    c = {"words": ctx["words"], "cache": ctx["cache"], "face": face if L["name"] == "full" else None, "line": seg.get("line"),
         "line_t0": ctx.get("line_t0"), "line_t1": ctx.get("line_t1"), "t_grid": ctx["t_grid"]}
    ctx["cache"]["_block"] = None; ctx["cache"]["_cap_hide"] = False   # T22: cards, labels, bubbles, the pill mark the caption band
    FX.draw_all(base, P.get("els", []), t, c, layer="behind")
    if him is not None: base.alpha_composite(him)
    FX.draw_all(base, P.get("els", []), t, c, layer="front")
    cap = P.get("captions", {"y": 1180, "n": 3})
    if cap and "mic" in seg:
        y = L.get("cap_y", cap.get("y", 1180))
        if L["name"] == "full" and seg.get("face"): y = max(y, int(seg["face"][3] + 80))
        fo = placed_face(L)
        if fo and fo[1] - 60 < y < fo[3] + 60:   # the caption would sit on his face: above it when his face is low, else under the chin
            y = int(fo[1] - 90) if fo[1] > 1000 else int(fo[3] + 80)
        sw = [w for w in ctx["words"] if seg["t0"] - 0.05 <= w["s"] < seg["t0"] + seg["dur"]]   # groups reset at every cut (11-04: "689 CALORIES 893" ran across a step turn)
        if cap.get("style") == "serif":   # T21: her glowing serif blocks, placed in the empty sky of each picture (L "cap_y" per shot)
            cy = L.get("cap_y", cap.get("y", 470))
            if cy == "auto":   # the quietest band of this shot, found once on its first frame (B3)
                if "_cap_auto" not in seg: seg["_cap_auto"] = FX.quiet_band(base)
                cy = seg["_cap_auto"]
            FX.serif_captions(base, t, sw, cap, face=(seg.get("face") if L["name"] == "full" else L.get("face")),
                              seg_end=seg["t0"] + seg["dur"], y=cy)
        elif L.get("caps") is False: pass
        elif cap.get("style") == "box":   # T26 Drew: box karaoke, the whole page shown, upcoming words dimmed
            FX.box_captions(base, t, sw, dict(cap, y=L.get("cap_y", cap.get("y", 1074))), seg_end=seg["t0"] + seg["dur"])
        elif cap.get("style") == "clean":   # T22 (Hormozi): white mixed-case phrases on his chest, out of the way of his cards
            cc = dict(cap, **{k: L["caption_" + k] for k in ("y", "n") if "caption_" + k in L})   # 11-10: a look's "caption_y"; 11-11: "caption_n" (2x2 proof pairs: 2 words stay between the bottom-row faces)
            FX.clean_captions(base, t, sw, cc, face=(seg.get("face") if L["name"] == "full" else None),
                              seg_end=seg["t0"] + seg["dur"], block=ctx["cache"].get("_block"), hide=ctx["cache"].get("_cap_hide"))
        else:
            FX.captions(base, t, sw, y=min(y, 1440), n=cap.get("n", 3), face=c["face"])
    return base.convert("RGB")


def render(plan_path, out, stills=None):
    P = json.load(open(plan_path)); os.makedirs(SCRATCH, exist_ok=True); td = tempfile.mkdtemp(dir=SCRATCH)
    try:
        segs, total = plan_segments(P)
        for i, s in enumerate(segs): s["i"] = i
        P["_work"] = BC.find_work(plan_path, P)   # 11-11: the matte cache and the engine's matte record live in the job's WORK
        if stills:   # 11-11: a still mattes only its own frames (BiRefNet is ~5 s a frame on CPU)
            P["_matte_only"] = []
            for t in stills:
                s = next(x for x in segs if x["t0"] <= t < x["t0"] + x["dur"] or x is segs[-1]); P["_matte_only"].append(f"{s['i']:03d}_{int((t - s['t0']) * FPS):04d}.png")
        words, wavs, vf, lut = prepare(P, segs, td)
        ctx = {"words": words, "cache": {}, "line_t0": {}, "line_t1": {}}
        for s in segs:   # T17 boards (tmpl_board): each line's first and last instant on the edit clock
            if s.get("line") is not None:
                ctx["line_t0"][s["line"]] = min(ctx["line_t0"].get(s["line"], 1e9), s["t0"]); ctx["line_t1"][s["line"]] = max(ctx["line_t1"].get(s["line"], 0), s["t0"] + s["dur"])
        if stills:
            for t in stills:
                s = next(x for x in segs if x["t0"] <= t < x["t0"] + x["dur"] or x is segs[-1]); k = int((t - s["t0"]) * FPS)
                fr = _cam_frame(P, s, k, vf, lut); _src_frames(s, ctx, k + 1)
                img = frame_for(P, s, k, fr, td, ctx); p = f"{os.path.splitext(out)[0]}_{t:06.2f}.jpg"; img.save(p, quality=92); print("still", p)
            return
        audio = mix_audio(P, segs, wavs, words, td, total)
        enc = subprocess.Popen(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", "30000/1001", "-i", "-",
                                "-i", audio, "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p",
                                "-c:a", "aac_at", "-b:a", "256k", "-shortest", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
        for s in segs:
            _src_frames(s, ctx, s["n"])
            cam_a = s.get("cam") if "mic" in s else (s["look"].get("peek") or {}).get("cam")
            gen = decode(P["cam"], cam_a, s["n"], vf, lut) if cam_a is not None else None
            for k in range(s["n"]):
                fr = next(gen, None) if gen else None
                if fr is None: fr = Image.new("RGB", (W, H), (20, 18, 16))
                enc.stdin.write(frame_for(P, s, k, fr, td, ctx).tobytes())
            if gen: gen.close()
        enc.stdin.close(); enc.wait()
        if P.get("_matte_info"):   # 11-11: the engine says what cut him out, so the gate does not rest on the editor's word
            cut_looks = [s["look"]["name"] for s in segs if s.get("need_matte")]
            rp = BC.record(P["_work"], "tmpl.py", plan_path, P["_matte_info"], cut_looks)
            print(f"  matte record: {rp}" if rp else "  matte record: none (no WORK folder for this plan; declare matte birefnet in the manifest)")
        gsegs, gcam, theirs = [], [], []
        for s in segs:
            if "mic" in s:
                gsegs.append((P["mic"], s["mic"][0], s["mic"][1], s["t0"]))
                if s["look"]["name"] == "broll": theirs.append([s["t0"], s["t0"] + s["dur"]])   # T21: his voice over b-roll, no lips to check
                else: gcam.append((P["cam"], s["cam"], s["cam"] + s["dur"], s["t0"]))
            else: gsegs.append((s["src"], s["in"], s["out"], s["t0"])); theirs.append([s["t0"], s["t0"] + s["dur"]])
            if s["look"]["name"] == "freeze": theirs.append([s["t0"], s["t0"] + s["dur"]])
            if s["look"]["name"] == "split": theirs.append([s["t0"], s["t0"] + s["dur"], 0, 0, W, s["look"].get("seam", 876)])
        for el in P.get("els", []):
            if el["type"] == "image":
                cx, cy, w = el.get("box", (W / 2, 640, 860)); im = FX.load(el["path"]); h = w * im.height / im.width; t0 = FX.trigger(el, words)
                theirs.append([t0, el.get("until", total), int(cx - w / 2), int(cy - h / 2), int(cx + w / 2), int(cy + h / 2)])
        json.dump(words, open(os.path.splitext(out)[0] + ".words.json", "w"))
        print(f"wrote {out}: {int(round(total * FPS))} frames, {total:.2f} s, {len(words)} words")
        import qc_gate as Q
        if P.get("keep_pauses"): os.environ["OB_QC_PAUSE_MAX"] = str(P["keep_pauses"] + 0.15)   # T21: her breaths are the style, not dead air
        Q.after_render(out, segs=gsegs, cam=gcam, theirs=theirs or None)
        os.environ.pop("OB_QC_PAUSE_MAX", None)
    finally:
        shutil.rmtree(td, ignore_errors=True)


def _cam_frame(P, s, k, vf, lut):
    cam_a = s.get("cam") if "mic" in s else (s["look"].get("peek") or {}).get("cam")
    if cam_a is None: return Image.new("RGB", (W, H), (20, 18, 16))
    g = decode(P["cam"], cam_a + k / FPS, 1, vf, lut); fr = next(g, None); g.close(); return fr


def _src_frames(s, ctx, n):
    """A source segment's frames, decoded once (short clips only: the whole segment sits in memory)."""
    if "src" not in s: ctx["src_frames"] = []; return
    sz = src_size(s["src"], ctx["cache"])
    ctx["src_frames"] = list(decode(s["src"], s["in"], n, "framerate=fps=30000/1001,scale=1080:-2:flags=lanczos", None, sz)) or [Image.new("RGB", sz)]


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) == 3 and a[0] == "render": render(a[1], a[2])
    elif len(a) >= 4 and a[0] == "still": render(a[1], a[2], stills=[float(x) for x in a[3:]])
    else: print(__doc__); sys.exit(2)
