#!/usr/bin/env python3
"""Render an edit (or a time range of it): graded/framed A-roll + HyperFrames graphics + voice + synthesized SFX.

  python3 assemble.py WORK_DIR OUT.mp4 [--range START END] [--keep]

Frame-exact: every cut is snapped to the 30000/1001 frame grid and the voice is cut at the same
instants, so sync cannot drift over 150+ cuts. All temp files live on T7 (WORK_DIR/render, TMPDIR).
OB_RENDER_DIR and OB_TMPDIR move them to another drive when T7 is full (C4365, 2026-10-18); hf/assets/aroll stays in WORK_DIR.
"""
import argparse, json, math, os, shutil, subprocess, sys
import numpy as np
from scipy.io import wavfile

FPS_N, FPS_D = 30000, 1001
FPS = FPS_N / FPS_D
SRC = os.environ.get("OB_SRC", "/Volumes/T7/C4352.MP4")
MASTER = os.environ.get("OB_MASTER", "/Volumes/T7/OB-EDITS/C4352_synced_graded.mov")   # synced external audio, same timeline as SRC
LUT = os.path.expanduser("~/ob-editor/luts/ob_grade_warmtan_hald.png")
SFXDIR = os.path.expanduser("~/ob-editor/assets/sfx")
NPX_PREFIX = os.path.expanduser("~/ob-editor")
PUNCH = "crop=3200:1800:320:120,scale=3840:2160:flags=lanczos,"
VBR = int(os.environ.get("OB_VBR", "60"))  # Mbps; OB_VBR=40 for full-length renders when T7 space is tight (YouTube 4K30: 35-45)
VENC = ["-c:v", "h264_videotoolbox", "-b:v", f"{VBR}M", "-maxrate", f"{VBR * 4 // 3}M", "-bufsize", f"{VBR * 2}M", "-profile:v", "high",
        "-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
        "-r", f"{FPS_N}/{FPS_D}", "-video_track_timescale", "30000", "-an"]
COVER = {"chapter", "quote", "myths",          # full-screen cards: no A-roll needed (every other type shows OB)
         "clip", "doc", "photo_full", "num", "math", "dose", "coins", "timeline", "title", "disclaimer",   # C4367 explainer cards
         "wall", "versus", "checklist", "scissors", "detector", "find", "slider", "insert",
         "anchor", "ledger", "ribbon", "jtitle", "jchapter",   # C4372 paper cards (jh_cards.py)
         "reel", "vpair",   # C4395 10-29 moving overlays (reel_cards.py); a vpair "beside" him shows OB
         "ffcover"}   # C4395 10-29 v6: his own b-roll straight from the camera file, no browser render (see the render loop)
def is_cover(e):   # any side card can run full frame ("full": true, C4367); a "beside" paper card or a doc beside him (no "full") shows OB (C4372)
    if e.get("face"): return False   # 10-29: a card that cuts back to OB in those windows (reel, or a full side card) needs the A-roll
    if e.get("full"): return True
    if e.get("beside") or e["type"] == "doc": return False
    return e["type"] in COVER
CLIPAUDIO = os.environ.get("OB_CLIPAUDIO")      # folder of ID.wav for clip holds (C4367: WORK/clips/audio)
SFX_GAIN_DB = {"whoosh": -24, "pop": -22, "tick": -26, "thud": -18}   # 5 dB under the C4352 mix (OB 2026-10-16: "a little quieter")
SFX_MIN_GAP = {"whoosh": 0.6, "pop": 0.3, "tick": 0.35, "thud": 1.0}   # same-type sounds closer than this are skipped (no machine-gun ticks)
SFX_ON = os.environ.get("OB_SFX", "0") == "1"   # OFF unless OB asks (2026-10-16: SFX "gives off young vibes and gets a bad demo, so only on request from me")


import hashlib
def cached(out, key):
    return os.path.exists(out) and os.path.exists(out + ".key") and open(out + ".key").read() == key
def mark(out, key): open(out + ".key", "w").write(key)
def fr(t): return int(round(t * FPS))
def ft(f): return f * FPS_D / FPS_N
def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        sys.exit(f"FAILED: {' '.join(cmd[:8])} ...\n{r.stderr[-2500:]}")
    return r


def encode_piece(src_f0, nframes, framing, out, pre=""):
    """Graded + framed slice of the camera file, exactly nframes long. pre: a shot's own filters before the house LUT (cutlist
    "pre_vf"; C4367 reshoot: the living-room pickups' skin and light correction)."""
    key = f"{src_f0}:{nframes}:{framing}:{os.path.getmtime(LUT)}" + (f":{pre}" if pre else "")
    if cached(out, key): return key
    vf = (PUNCH if framing == "punch" else "") + (pre + "," if pre else "") + "null"
    run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-ss", f"{ft(src_f0):.6f}", "-i", SRC, "-i", LUT,
         "-filter_complex", f"[0:v]{vf}[v0];[v0][1:v]haldclut=interp=tetrahedral[v]", "-map", "[v]",
         "-frames:v", str(nframes)] + VENC + [out])
    mark(out, key); return key


PIP_BOX = (3080, 1218, 660, 842)   # same box as cards.py .pip / add_pip (bottom right, 8 px yellow border, radius 28)
PIP_SRC = (1340, 0, 0.6)           # his A-roll window: source x, source y, scale (as cards.PIP_SRC)
PIP_BW, PIP_RAD, PIC_M = 8, 28, 60
YEL = (247, 220, 58, 255)


def ffcover_layers(e, R, H, vf):
    """2026-11-11 C4465 (OB r2 "you just put a bench, im not in the overlay", M87; r1 client proof, M56/M86): the ffmpeg cover
    gets him in the box (his own A-roll for these frames, live, in sync) and/or proof pictures, matching cards.add_pip/add_pics.
    Returns (extra ffmpeg input args, filter_complex); input 0 is the cover source, output label [vout]."""
    from PIL import Image, ImageDraw, ImageFilter, ImageOps
    L = f"{R}/layers"; os.makedirs(L, exist_ok=True)
    ins, parts, cur, k = [], [f"[0:v]{vf}[b0]"], "b0", [1]

    def png_in(p):
        ins.extend(["-loop", "1", "-framerate", f"{FPS_N}/{FPS_D}", "-i", p]); k[0] += 1; return k[0] - 1

    pp = e.get("ob_pip")
    if pp:
        pp = pp if isinstance(pp, dict) else {}
        x, y, w, h = (pp.get(c, dv) for c, dv in zip("xywh", PIP_BOX))
        sx, sy, s = pp.get("sx", PIP_SRC[0]), pp.get("sy", PIP_SRC[1]), pp.get("s", PIP_SRC[2])
        iw, ih = w - 2 * PIP_BW, h - 2 * PIP_BW
        ring, mask, shad = f"{L}/pip_ring_{w}x{h}.png", f"{L}/pip_mask_{w}x{h}.png", f"{L}/pip_shadow_{w}x{h}.png"
        if not os.path.exists(ring):
            im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); ImageDraw.Draw(im).rounded_rectangle([0, 0, w - 1, h - 1], radius=PIP_RAD, outline=YEL, width=PIP_BW); im.save(ring)
        if not os.path.exists(mask):
            m = Image.new("L", (iw, ih), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, iw - 1, ih - 1], radius=PIP_RAD - PIP_BW, fill=255); m.save(mask)
        if not os.path.exists(shad):   # box-shadow 0 18px 50px rgba(0,0,0,.5)
            sh = Image.new("L", (w + 120, h + 120), 0); ImageDraw.Draw(sh).rounded_rectangle([60, 78, 60 + w, 78 + h], radius=PIP_RAD, fill=128)
            sh = sh.filter(ImageFilter.GaussianBlur(22)); im = Image.new("RGBA", sh.size, (0, 0, 0, 0)); im.putalpha(sh); im.save(shad)
        ins.extend(["-i", f"{H}/assets/aroll/{e['id']}.mp4"]); ai = k[0]; k[0] += 1
        ri, mi, si = png_in(ring), png_in(mask), png_in(shad)
        cw, ch = int(round(iw / s)), int(round(ih / s))
        parts += [f"[{ai}:v]crop={cw}:{ch}:{sx}:{sy},scale={iw}:{ih}:flags=lanczos,format=rgba[pv]", f"[{mi}:v]format=gray[pm]",
                  "[pv][pm]alphamerge[pa]", f"[{cur}][{si}:v]overlay={x - 60}:{y - 60}[ps]", f"[ps][pa]overlay={x + PIP_BW}:{y + PIP_BW}:eof_action=repeat[pq]",
                  f"[pq][{ri}:v]overlay={x}:{y}[pr]"]
        cur = "pr"
    D = ft(e["f1"] - e["f0"])
    for j, p in enumerate(e.get("pics") or []):
        src = f"{H}/assets/{p.get('folder', 'proof')}/{p['key']}.jpg"; w, h = int(p["w"]), int(p["h"])
        out = f"{L}/pic_{hashlib.sha1(f'{src}:{os.path.getmtime(src)}:{w}x{h}'.encode()).hexdigest()[:16]}.png"
        if not os.path.exists(out):   # object-fit: contain in the w x h box, drop-shadow(0 16px 36px rgba(0,0,0,.55)) as cards .pic
            im = ImageOps.exif_transpose(Image.open(src)).convert("RGB"); r = min(w / im.width, h / im.height)
            im = im.resize((max(1, round(im.width * r)), max(1, round(im.height * r))), Image.LANCZOS)
            ox, oy = PIC_M + (w - im.width) // 2, PIC_M + (h - im.height) // 2
            sh = Image.new("L", (w + 2 * PIC_M, h + 2 * PIC_M), 0); ImageDraw.Draw(sh).rectangle([ox, oy + 16, ox + im.width, oy + 16 + im.height], fill=140)
            sh = sh.filter(ImageFilter.GaussianBlur(18)); cv = Image.new("RGBA", sh.size, (0, 0, 0, 0)); cv.putalpha(sh)
            cv.paste(im, (ox, oy)); cv.save(out)
        pi = png_in(out)
        t0 = max(0.0, float(p.get("t0", 0.0))); t1 = min(float(p.get("t1", D)), D + 1)
        yx = (f"{int(p['y']) - PIC_M}+46*pow(max(0,1-(t-{t0:.3f})/0.32),2)" if p.get("enter", "slide") == "slide" else f"{int(p['y']) - PIC_M}")
        parts.append(f"[{cur}][{pi}:v]overlay=x={int(p['x']) - PIC_M}:y='{yx}':eval=frame:enable='between(t,{t0:.3f},{t1:.3f})'[q{j}]"); cur = f"q{j}"
    parts.append(f"[{cur}]format=yuv420p[vout]")
    return ins, ";".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("work"); ap.add_argument("out")
    ap.add_argument("--range", nargs=2, type=float, default=None)
    ap.add_argument("--keep", action="store_true")
    a = ap.parse_args()
    W = a.work; R = os.environ.get("OB_RENDER_DIR") or f"{W}/render"; H = f"{W}/hf"
    os.makedirs(f"{R}/units", exist_ok=True); os.makedirs(f"{H}/assets/aroll", exist_ok=True)
    env = dict(os.environ, TMPDIR=os.environ.get("OB_TMPDIR", "/Volumes/T7/OB-EDITS/tmp"), HYPERFRAMES_NO_TELEMETRY="1")
    os.makedirs(env["TMPDIR"], exist_ok=True)

    segs = json.load(open(f"{W}/cutlist.json"))["segments"]
    evs = json.load(open(f"{W}/events_resolved.json"))["events"]
    # ---- frame grid: source frame ranges per shot, edited frame ranges
    shots, ef = [], 0
    for s in segs:
        a0, b0 = fr(s["src_in"]), fr(s["src_out"])
        if b0 <= a0: continue
        shots.append({"i": s["i"], "src0": a0, "src1": b0, "e0": ef, "e1": ef + (b0 - a0), "framing": s["framing"],
                      "hold": bool(s.get("hold")), "clip": s.get("clip"), "pre": s.get("pre_vf", ""),
                      "punch": sorted(fr(t) for t in s.get("punch_at", []))})   # mid-shot punch-ins (edit seconds; C4367 v2.1): video only
        ef += b0 - a0
    TOTAL = ef
    R0, R1 = (0, TOTAL) if not a.range else (fr(a.range[0]), min(TOTAL, fr(a.range[1])))
    for e in evs:
        e["f0"], e["f1"] = fr(e["edit_in"]), min(TOTAL, fr(e["edit_out"]))
    evs = [e for e in evs if e["f1"] > R0 and e["f0"] < R1]
    # Events are NOT clipped to the range (C4367 2026-10-20): one that starts before it or ends after it is rendered whole and
    # trimmed by the painter, so a test clip shows exactly the frames the full render will (a clipped event used to restart its
    # animation at the range start), and the event renders are shared with the full render's cache.

    def src_pieces(f0, f1):
        """[(src_frame0, nframes, framing)] covering edited frames [f0, f1)."""
        out = []
        for s in shots:
            lo, hi = max(f0, s["e0"]), min(f1, s["e1"])
            if hi <= lo: continue
            # a punch-in toggles wide/punch at its frame and stays toggled to the end of the shot; the voice is untouched
            edges = [lo] + [p for p in s["punch"] if lo < p < hi] + [hi]
            for a_, b_ in zip(edges, edges[1:]):
                k = sum(1 for p in s["punch"] if p <= a_)
                fram = s["framing"] if k % 2 == 0 else ("wide" if s["framing"] == "punch" else "punch")
                out.append((s["src0"] + (a_ - s["e0"]), b_ - a_, fram, s["pre"]))
        return out

    # ---- who owns each frame (C4367 v2 pace pass, 2026-10-20): an event or the A-roll. A card's "holes" (edit seconds) hand its
    # frames back to the A-roll (a face break: the card keeps animating underneath and resumes in step), and "inlay" events sit on
    # top of their parent (footage over a card or over a clip hold, whose sound plays on). Where two events touch, the earlier wins.
    N = R1 - R0
    own = [None] * N
    for e in sorted([e for e in evs if not e.get("inlay")], key=lambda e: -e["f0"]):
        a_, b_ = max(e["f0"], R0), min(e["f1"], R1)
        own[a_ - R0:b_ - R0] = [e] * (b_ - a_)
        for h0, h1 in e.get("holes", []):
            for f in range(max(fr(h0), a_), min(fr(h1), b_)):
                if own[f - R0] is e: own[f - R0] = None
    for e in sorted([e for e in evs if e.get("inlay")], key=lambda e: (e["type"] == "ffcover", e["f0"])):   # his own-footage covers on top (C4395 v6)
        a_, b_ = max(e["f0"], R0), min(e["f1"], R1)
        own[a_ - R0:b_ - R0] = [e] * (b_ - a_)
    units, f = [], 0
    while f < N:
        g = f
        while g < N and own[g] is own[f]: g += 1
        if own[f] is None:
            for p in src_pieces(R0 + f, R0 + g): units.append(("aroll", p, None, None))
        else: units.append(("event", own[f], R0 + f, R0 + g))
        f = g
    print(f"range {ft(R0):.2f}-{ft(R1):.2f}s: {len(units)} units, {len(evs)} graphics")
    # a clip hold is silent reading-pause footage: it must never show. Every hold frame in range sits under a full-frame card.
    for sh in shots:
        if not sh["hold"]: continue
        for f in range(max(R0, sh["e0"]), min(R1, sh["e1"])):
            if own[f - R0] is None or not is_cover(own[f - R0]):
                sys.exit(f"hold {sh['clip']} (edit {ft(max(R0, sh['e0'])):.2f}-{ft(min(R1, sh['e1'])):.2f}s) is not fully covered by a full-frame card (gap at {ft(f):.2f}s)")

    # ---- event A-roll inputs + HyperFrames renders
    os.makedirs(f"{R}/events", exist_ok=True)
    for e in evs:
        n = e["f1"] - e["f0"]
        e["dur"] = round(ft(n), 6)
        if not is_cover(e) or e.get("ob_pip"):   # 2026-11-11 C4465 (M87): a cover with him in the box needs his A-roll too
            parts, keys = [], []
            for j, (s0, nn, fram, pre) in enumerate(src_pieces(e["f0"], e["f1"])):
                pth = f"{R}/units/ar_{e['id']}_{j}.mp4"; keys.append(encode_piece(s0, nn, fram, pth, pre)); parts.append(pth)
            arp = f"{H}/assets/aroll/{e['id']}.mp4"; e["_akey"] = "|".join(keys)
            if not cached(arp, e["_akey"]):
                lst = f"{R}/units/ar_{e['id']}.txt"; open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
                run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", arp]); mark(arp, e["_akey"])
    json.dump({"events": [e for e in evs if e["type"] != "ffcover"]}, open(f"{R}/events_render.json", "w"))   # ffcover: no composition
    run([sys.executable, "-I", os.path.expanduser("~/ob-editor/bin/cards.py"), f"{R}/events_render.json", H])
    for e in evs:
        outp = f"{R}/events/{e['id']}.mp4"
        if e["type"] == "ffcover":   # C4395 v6 (OB 10-29: "make the overlays me more"): a full-frame cover cut from his own camera
            # file with ffmpeg (graded like the "look" b-roll, slow push-in z, "slow" < 1 plays a 60/120 fps clip in slow motion)
            n = e["f1"] - e["f0"]; d = ft(n); sl = e.get("slow", 1); z = e.get("z", 0.05)
            if os.environ.get("OB_NO_PUSH") == "1": z = 0   # 2026-11-11 (R18, OB 11-07 "zooming in and out non stop"): no push on covers
            tag = "ffcover2" if sl != 1 else "ffcover1"   # 10-29: ffcover1 slow-motion renders came out short (-t was an output limit)
            extra = [{"pip": e.get("ob_pip"), "pics": e.get("pics"), "akey": e.get("_akey", ""), "v": 1}] if (e.get("ob_pip") or e.get("pics")) else []
            e["_hkey"] = hashlib.sha1((tag + json.dumps([e["src"], e["in"], sl, n, z] + ([e["layout"], e.get("pre")] if e.get("layout") else []) + extra)).encode()).hexdigest()
            if cached(outp, e["_hkey"]): print("cached", e["id"], flush=True); continue
            look = "curves=all='0/0 0.18/0.12 0.5/0.5 0.82/0.88 1/1',eq=saturation=1.12,colorbalance=rm=0.03:bm=-0.03:rh=0.02:bh=-0.02,format=yuv420p"
            head = (e["pre"] + "," if e.get("pre") else "") + (f"setpts={1 / sl:.6f}*PTS," if sl != 1 else "") + f"fps={FPS_N}/{FPS_D},"
            push = f"scale=w='3840*(1+{z}*t/{d:.3f})':h=-2:eval=frame,crop=3840:2160,"
            if e.get("layout") == "vfill":   # a vertical clip: sharp at full height in the middle over a blurred, darker copy of itself
                vf = (head + "split[a][b];[a]scale=960:-2,crop=960:540,gblur=sigma=14,eq=brightness=-0.14:saturation=0.85,scale=3840:2160[bg];"
                      "[b]scale=-2:2160[fg];[bg][fg]overlay=(W-w)/2:0," + push + look)
            else: vf = head + push + look
            if e.get("ob_pip") or e.get("pics"):   # 2026-11-11 C4465: him in the box (M87) and proof pictures (M56/M86) on the cover
                ins, fc = ffcover_layers(e, R, H, vf)
                run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-ss", f"{e['in']:.3f}", "-t", f"{d * sl + 0.6:.3f}", "-i", e["src"]] + ins +
                    ["-an", "-filter_complex", fc, "-map", "[vout]", "-frames:v", str(n)] + VENC + [outp])
            else:
                run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-ss", f"{e['in']:.3f}", "-t", f"{d * sl + 0.6:.3f}", "-i", e["src"], "-an",
                     "-vf", vf, "-frames:v", str(n)] + VENC + [outp])   # -t before -i: it limits the source read (slow motion stretches it after)
            got = int(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets", "-show_entries", "stream=nb_read_packets",
                                      "-of", "csv=p=0", outp], capture_output=True, text=True).stdout.strip() or 0)
            if got < n: sys.exit(f"ffcover {e['id']} rendered {got} of {n} frames (source {e['src']} at {e['in']}s too short?)")
            mark(outp, e["_hkey"]); print("rendered", e["id"], "(ffmpeg)", flush=True); continue
        e["_hkey"] = hashlib.sha1((open(f"{H}/compositions/{e['id']}.html").read() + e.get("_akey", "")).encode()).hexdigest()
        if cached(outp, e["_hkey"]):
            print("cached", e["id"], flush=True); continue
        r = subprocess.run(["npx", "--prefix", NPX_PREFIX, "hyperframes", "render", H, "-c", f"compositions/{e['id']}.html", "-o", outp,
                            "--fps", f"{FPS_N}/{FPS_D}", "--quality", "looks", "--workers", os.environ.get("OB_HF_WORKERS", "4"),  # 2026-11-03 M5 Pro (was 1 on the 8 GB Air)
                            "--browser-gpu", "--gpu", "--quiet"],
                           capture_output=True, text=True, env=env)
        if r.returncode != 0 or not os.path.exists(outp):
            sys.exit(f"HyperFrames failed on {e['id']}:\n{(r.stdout + r.stderr)[-3000:]}")
        mark(outp, e["_hkey"]); print("rendered", e["id"], flush=True)

    # ---- encode units to identical stream params, then concat. A unit is reused by its key, whatever its index (C4372 v4,
    # 2026-10-23: one small cut early in the film shifted every later index, and the index-named cache re-encoded the rest of it)
    have = {}
    for kf in sorted(os.listdir(f"{R}/units")):
        p_ = f"{R}/units/{kf[:-4]}"
        if kf.endswith(".mp4.key") and not kf.startswith("._") and os.path.exists(p_):   # "._*": macOS sidecar files on the exFAT T7
            have.setdefault(open(f"{R}/units/{kf}", errors="replace").read(), p_)
    paths, made = [], 0
    for k, u in enumerate(units):
        if u[0] == "aroll":
            s0, n, fram, pre = u[1]; key = f"{s0}:{n}:{fram}:{os.path.getmtime(LUT)}" + (f":{pre}" if pre else "")
        else:
            e = u[1]; n = u[3] - u[2]; off = u[2] - e["f0"]   # off > 0: the event resumes after a face break or an inlay
            key = e["_hkey"] + (f":{n}" if off == 0 else f":{off}:{n}")
        if key in have: paths.append(have[key]); continue
        pth = f"{R}/units/k{hashlib.sha1(key.encode()).hexdigest()[:16]}.mp4"; made += 1
        if u[0] == "aroll": encode_piece(s0, n, fram, pth, pre)
        else:
            trim = f"trim=start_frame={off},setpts=PTS-STARTPTS," if off else ""
            run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", f"{R}/events/{e['id']}.mp4",
                 "-vf", f"fps={FPS_N}/{FPS_D},{trim}tpad=stop_mode=clone:stop_duration=1,setsar=1", "-frames:v", str(n)] + VENC + [pth])
            mark(pth, key)
        have[key] = pth; paths.append(pth)
    print(f"units: {len(units)}, {made} encoded, {len(units) - made} reused from earlier renders", flush=True)
    lst = f"{R}/units.txt"; open(lst, "w").write("".join(f"file '{p}'\n" for p in paths))
    run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", f"{R}/video.mp4"])

    if os.environ.get("OB_VIDEO_ONLY") == "1":   # 2026-11-08 (OB Studio long-form adapter): the range's picture only, units kept; no voice, mix or mux
        print(f"video only ({ft(R1 - R0):.2f}s) -> {R}/video.mp4", flush=True); return

    # ---- voice: master audio cut at the same frame boundaries, 6 ms fades at every cut
    sr = 48000
    run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", MASTER, "-vn", "-c:a", "pcm_f32le", "-ar", str(sr), f"{R}/master.wav"])
    _, m = wavfile.read(f"{R}/master.wav")
    if m.ndim == 1: m = m[:, None]
    fade = int(0.006 * sr); ramp = np.linspace(0, 1, fade)[:, None]
    voice = []
    # optional per-shot audio nudge (cutlist segment "audio_shift_ms", + = play that shot's audio later): an external
    # recorder that drops buffers leaves a sawtooth sync error; each shot gets its own measured offset (C4353B, 2026-10-17)
    ash = {s["i"]: s.get("audio_shift_ms", 0.0) / 1000 for s in segs}
    hmu = {s["i"]: s.get("audio_head_mute_ms", 0.0) / 1000 for s in segs}   # mute a click/breath or a removed take's sliver at a shot's edge
    tmu = {s["i"]: s.get("audio_tail_mute_ms", 0.0) / 1000 for s in segs}
    clipcache = {}
    # bleeps (WORK/bleeps.json: master-time spans from bleep_pin.py, or set by hand and checked by ear and whisper; C4395, OB 10-28:
    # "Bleep it"): a 1 kHz tone 3 dB under his voice (voiced 20 ms frames within 20 s of the word), as react_render does
    BL = [b for b in (json.load(open(f"{W}/bleeps.json")) if os.path.exists(f"{W}/bleeps.json") else []) if b.get("t0") is not None]
    tones, nb = [], 0
    for b in BL:
        y = m[int(max(0.0, b["t0"] - 20) * sr):int((b["t1"] + 20) * sr)].astype(np.float64).mean(1); h = 960; nf = len(y) // h
        e2 = (y[:nf * h].reshape(nf, h) ** 2).mean(1); act = e2[e2 > 10 ** (-40 / 10)]
        tones.append((int(round(b["t0"] * sr)), int(round(b["t1"] * sr)), float(np.sqrt(act.mean())) if len(act) else 0.05))
    for sh in shots:
        lo, hi = max(R0, sh["e0"]), min(R1, sh["e1"])
        if hi <= lo: continue
        if sh["hold"]:   # a clip's own sound (mono like the voice), sliced on the same frame boundaries; silence for a card-only hold
            a0, a1 = int(round(ft(lo - sh["e0"]) * sr)), int(round(ft(hi - sh["e0"]) * sr))
            cw = f"{CLIPAUDIO}/{sh['clip']}.wav" if CLIPAUDIO else None
            if cw and os.path.exists(cw):
                if cw not in clipcache:
                    _, ca = wavfile.read(cw); ca = ca.astype(np.float64); clipcache[cw] = ca.mean(1, keepdims=True) if ca.ndim > 1 else ca[:, None]
                piece = clipcache[cw][a0:a1].copy()
            else: piece = np.zeros((0, 1))
            piece = np.pad(piece, ((0, max(0, a1 - a0 - len(piece))), (0, 0)))[:a1 - a0]
            if m.shape[1] > 1: piece = np.repeat(piece, m.shape[1], 1)
            voice.append(piece); continue
        s0, n = sh["src0"] + (lo - sh["e0"]), hi - lo
        a0 = int(round(ft(s0) * sr)); a1 = int(round(ft(s0 + n) * sr))
        d = int(round(ash.get(sh["i"], 0.0) * sr)); a0, a1 = a0 - d, a1 - d
        piece = m[max(a0, 0):a1].astype(np.float64).copy()
        if a0 < 0: piece = np.pad(piece, ((-a0, 0), (0, 0)))
        if len(piece) < a1 - a0: piece = np.pad(piece, ((0, a1 - a0 - len(piece)), (0, 0)))   # past the end of the master
        for B0, B1, ref in tones:   # this piece is master samples [a0, a1)
            i0, i1 = max(B0, a0) - a0, min(B1, a1) - a0
            if i1 - i0 < 16: continue
            tt = np.arange(i1 - i0) / sr; tone = ref * np.sqrt(2) * 10 ** (-3 / 20) * np.sin(2 * np.pi * 1000 * tt)
            f5 = min(int(0.005 * sr), (i1 - i0) // 2); w = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, f5))
            tone[:f5] *= w; tone[-f5:] *= w[::-1]; piece[i0:i1] = tone[:, None]; nb += 1
        h, t_ = int(round(hmu.get(sh["i"], 0.0) * sr)), int(round(tmu.get(sh["i"], 0.0) * sr))
        if h: piece[:h] = 0
        if t_: piece[len(piece) - t_:] = 0
        if len(piece) > 2 * fade + h + t_:
            piece[h:h + fade] *= ramp; e_ = len(piece) - t_; piece[e_ - fade:e_] *= ramp[::-1]
        voice.append(piece)
    voice = np.concatenate(voice)
    if BL: print(f"bleeps: {nb} placed of {len(BL)} pinned words", flush=True)
    target = int(round(ft(R1 - R0) * sr)); voice = np.pad(voice, ((0, max(0, target - len(voice))), (0, 0)))[:target]

    # ---- synthesized SFX bus (sound on entrances only, no exit whooshes: OB 2026-10-16, repetition)
    # variants NAME_1..N rotate so no sound plays twice in a row; +-1.5 dB jitter; same-type minimum gap (OB 2026-10-16)
    import glob, random
    kit, turn, last = {}, {}, {}
    rnd = random.Random(1016)
    for name in SFX_GAIN_DB:
        files = sorted(glob.glob(f"{SFXDIR}/{name}_[0-9]*.wav")) or [f"{SFXDIR}/{name}.wav"]
        kit[name] = [wavfile.read(f)[1].astype(np.float64) / 2 ** 31 * 10 ** (SFX_GAIN_DB[name] / 20) for f in files]
        turn[name], last[name] = 0, -99.0
    bus = np.zeros(len(voice))
    def place(name, t):
        if t - last[name] < SFX_MIN_GAP[name]: return
        i = int(round(t * sr))
        if 0 <= i < len(bus):
            v = kit[name][turn[name] % len(kit[name])]; turn[name] += 1; last[name] = t
            s = v[: len(bus) - i] * 10 ** (rnd.uniform(-1.5, 1.5) / 20); bus[i:i + len(s)] += s
    for e in (evs if SFX_ON else []):   # no SFX bus unless OB_SFX=1
        t0 = ft(e["f0"] - R0); D = ft(e["f1"] - e["f0"]); typ = e["type"]
        if typ == "chapter": place("thud", t0); place("whoosh", max(0, t0 - 0.12))
        elif typ == "quote": place("whoosh", max(0, t0 - 0.1))
        elif typ == "myths":
            place("whoosh", t0)
            for it in e.get("items_t", []): place("tick", t0 + it + 0.55)
        elif typ == "split":
            place("whoosh", t0)
            for it in e.get("items_t", []): place("tick", t0 + max(it, 0.45))
        elif typ == "label": place("tick", t0)
        elif typ == "photo":
            place("whoosh", t0)
            for i, pt in enumerate(e.get("photos_t") or [0.1 + i * 0.3 for i in range(len(e.get("photos", [])))]): place("pop", t0 + pt)
        elif typ == "pills":
            for it in e.get("items_t", []): place("pop", t0 + it)
        elif typ == "equation": place("pop", t0 + 0.1); place("pop", t0 + e.get("right_t", D / 2))
        elif typ in ("stat_ratio",): place("pop", t0 + 0.1)
        elif typ == "stat_bars": place("whoosh", t0 + 0.15)
        elif typ == "stat_list":
            for i in range(len(e["items"])): place("tick", t0 + 0.1 + i * 0.7)
        elif typ == "stat_columns":
            for tt in e.get("cols_t", [0.1]): place("pop", t0 + tt)
        elif typ == "stat_equals":
            for tt in e.get("rows_t", [0.1]): place("pop", t0 + tt)
        elif typ == "stat_count":
            tt = e.get("to_t", D * 0.6)
            for j in range(8): place("tick", t0 + tt + j * 0.11)
        elif typ == "proof_pages":
            for i in range(4): place("pop", t0 + 0.3 + i * 0.22)
            p2 = e.get("page2_t", D / 2); place("whoosh", t0 + p2 - 0.2)
            for i in range(4): place("pop", t0 + p2 + 0.1 + i * 0.2)
        elif typ == "proof_quote":
            place("whoosh", t0)
            for i in range(4): place("pop", t0 + 0.15 + i * 0.14)
        elif typ in ("poster", "end"): place("whoosh", t0 + 0.1)
        elif typ == "myths_overlay":
            for it in e.get("items_t", []): place("tick", t0 + it); place("whoosh", t0 + it + 0.5)
        elif typ == "photo_overlay":
            snd = "tick" if len(e["items"]) > 6 else "pop"     # rapid-fire montage = shutter ticks
            for it in e.get("items_t", []): place(snd, t0 + it)
        elif typ == "study":
            place("whoosh", t0); place("tick", t0 + e.get("hl_t", 1.1))
            if e.get("study", {}).get("stat"): place("pop", t0 + e.get("stat_t", 1.8))
        elif typ == "chart_line":
            place("whoosh", t0); place("pop", t0 + 2.9)
            for tt in e.get("callouts_t", []): place("pop", t0 + tt)
    PLAN = os.environ.get("OB_SFX_PLAN")   # C4367 v3: story/sfx_plan.json {"hits": [{"t": edit s, "file": path, "db": vs voice}]}
    if PLAN:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import score
        vref = score._speech_db(voice.mean(1)); fcache = {}
        def loadf(path):
            if path not in fcache:
                raw = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-i", path, "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
                                     capture_output=True, check=True).stdout
                x = np.frombuffer(raw, np.float32).astype(np.float64); fr_ = int(0.1 * sr)
                k = max(1, len(x) // fr_); pk = 10 * np.log10(max(((x[: k * fr_].reshape(k, fr_) ** 2).mean(1)).max(), 1e-12))
                fcache[path] = (x, pk)
            return fcache[path]
        nh = 0
        for h in json.load(open(PLAN))["hits"]:
            t = h["t"] - ft(R0); x, pk = loadf(h["file"])
            if t + len(x) / sr <= 0 or t >= len(bus) / sr: continue
            g = 10 ** ((vref + h.get("db", -14.0) - pk) / 20); i0 = int(round(t * sr))
            lo, hi = max(0, i0), min(len(bus), i0 + len(x))
            if hi > lo: bus[lo:hi] += g * x[lo - i0: hi - i0]; nh += 1
        print(f"sfx plan: {nh} hits in range", flush=True)
    mix = voice + bus[:, None]
    SCORE = os.environ.get("OB_SCORE")   # C4367 v3: a multi-cue score (score.py), cues in edit seconds
    if SCORE:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import score
        sc = score.build(SCORE, voice.mean(1), sr, ft(R0))
        mix = (mix if mix.shape[1] == 2 else np.repeat(mix, 2, 1)) + sc
        wavfile.write(f"{R}/score_bed.wav", sr, sc.astype(np.float32)); print("score bed built", flush=True)
    MUSIC = os.environ.get("OB_MUSIC")   # licensed bed only (music_bed.py: seamless loop, EQ carved for speech, ducked while he talks)
    if MUSIC:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import music_bed
        bed = music_bed.long_bed(MUSIC, voice.mean(1), sr, float(os.environ.get("OB_MUSIC_REL", "-17")), float(os.environ.get("OB_MUSIC_DUCK", "4")))
        mix = (mix if mix.shape[1] == 2 else np.repeat(mix, 2, 1)) + bed
        wavfile.write(f"{R}/music_bed.wav", sr, bed.astype(np.float32)); print("music bed:", music_bed.long_bed.info, flush=True)
    wavfile.write(f"{R}/mix.wav", sr, mix.astype(np.float32))
    wavfile.write(f"{R}/sfx_only.wav", sr, bus.astype(np.float32))

    # ---- master to -14 LUFS (two-pass loudnorm), mux
    r = run(["ffmpeg", "-nostdin", "-i", f"{R}/mix.wav", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"])
    js = r.stderr[r.stderr.rfind("{"): r.stderr.rfind("}") + 1]; ln = json.loads(js)
    af = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={ln['input_i']}:measured_TP={ln['input_tp']}:"
          f"measured_LRA={ln['input_lra']}:measured_thresh={ln['input_thresh']}:offset={ln['target_offset']}:linear=true")
    # One colour description for the whole file. The A-roll units and the HyperFrames graphics are encoded separately and carry
    # different primaries/transfer tags (unknown vs bt709) over identical bt709 limited-range pixels; YouTube ignores that, but
    # Spotify for Creators rejects the file ("the color details ... change during your video", C4365, 2026-10-19).
    vcodec = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_name", "-of", "csv=p=0",
                             f"{R}/video.mp4"], capture_output=True, text=True).stdout.strip()
    bsf = ("hevc_metadata" if vcodec == "hevc" else "h264_metadata") + "=colour_primaries=1:transfer_characteristics=1:matrix_coefficients=1:video_full_range_flag=0"
    run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", f"{R}/video.mp4", "-i", f"{R}/mix.wav", "-map", "0:v", "-map", "1:a",
         "-c:v", "copy", "-bsf:v", bsf, "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-color_range", "tv",
         "-af", af + ",aresample=48000", "-c:a", "aac", "-b:a", "320k", "-movflags", "+faststart", "-shortest", a.out])
    print("done ->", a.out, f"({ft(R1 - R0):.2f}s)")
    if not a.keep:
        shutil.rmtree(f"{R}/units", ignore_errors=True); os.remove(f"{R}/master.wav")


if __name__ == "__main__":
    main()
