#!/usr/bin/env python3
"""Render an approved reaction edit (or a time range of it).

  python3 react_render.py WORK_DIR SOURCE.MP4 OUT.mp4 [--range START END] [--keep]

Picture: OB graded with his LUT. While a clip plays, OB sits in the left panel and the clip on the
right (react_geom.py). Every graphic is a HyperFrames render over its own base clip.
Sound: the clip's clean audio while it plays. OB's mic is muted during plays except where he talks (gate.json); there the
clip's own file keeps playing 8 dB down and his mic has the clip's speaker bleed spectrally suppressed (OB 2026-10-16: "you
play the computer audio and not just the original"). OB shots kept inside a replay get the same suppression.
Grade: WORK_DIR/lut.png when present (the Hald CLUT OB picked for this take), else the warm tan default.
Synthesized SFX only with OB_SFX=1 (off by default); the mix is mastered like C4352 (two-pass loudnorm, LRA 11) plus a gentle expander, ~-14.5 LUFS.
Frame-exact: every cut sits on the 30000/1001 grid and the audio is cut at the same instants.
Held graphics (waiting on a fact-check answer) never render.
Speed (2026-11-03, Mac mini M5 Pro, 18 cores, 64 GB): graphics render OB_JOBS at a time (3 here, 1 on a Mac under 32 GB,
which keeps the old one-by-one order) with OB_HF_WORKERS Chrome workers each (default 2 when parallel). Picture units encode
OB_JOBS at a time too, but the media engine's 4K HEVC encoder (~55 fps, shared by every render on the Mac) caps that phase.
Scratch (graphics renders, HyperFrames temp, units, the mix) lives on the internal SSD in ~/ob-scratch/<work dir name> when it
has 80 GB free (REACT_SCRATCH picks another place; the T7 is exFAT, slow with thousands of temp frames). Units there are kept
after the render, so a re-render after OB's notes encodes only the shots and graphics that changed. OUT goes where it says.
"""
import argparse, glob, hashlib, json, os, random, re, shutil, subprocess, sys, threading, time
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
from scipy.io import wavfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from react_geom import OB_X, OB_W, OB_SRC_X, CLIP_X, CLIP_W, PIP_W, PIP_VH, PIP_B, PIP_M, PIP_FONT, PIP_D

FPS_N, FPS_D = 30000, 1001
FPS = FPS_N / FPS_D
ED = os.path.expanduser("~/ob-editor")
LUT, TOPO, SFXDIR = f"{ED}/luts/ob_grade_warmtan_hald.png", f"{ED}/assets/topo_bg.png", f"{ED}/assets/sfx"
PUNCH = "crop=3200:1800:320:120,scale=3840:2160:flags=lanczos,"
# HEVC by default: ~6 GB for 32 min at 24 Mbps, about what YouTube gets from 40-45 Mbps H.264 (T7 is near full).
CODEC = os.environ.get("OB_CODEC", "hevc")
VBR = int(os.environ.get("OB_VBR", "24" if CODEC == "hevc" else "40"))   # Mbps
VENC = (["-c:v", "hevc_videotoolbox", "-b:v", f"{VBR}M", "-tag:v", "hvc1", "-profile:v", "main"] if CODEC == "hevc" else
        ["-c:v", "h264_videotoolbox", "-b:v", f"{VBR}M", "-maxrate", f"{VBR * 4 // 3}M", "-bufsize", f"{VBR * 2}M", "-profile:v", "high"]) + \
       ["-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
        "-r", f"{FPS_N}/{FPS_D}", "-video_track_timescale", "30000", "-an"]
VKEY = hashlib.sha1(" ".join(VENC).encode()).hexdigest()[:10]   # pieces made with other encoder settings never mix in a concat
RAM_GB = int(subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True).stdout or 0) / 2 ** 30
JOBS = max(1, int(os.environ.get("OB_JOBS") or (3 if RAM_GB >= 32 and (os.cpu_count() or 1) >= 12 else 1)))
HF_WORKERS = os.environ.get("OB_HF_WORKERS") or ("2" if JOBS > 1 else "1")
HF = [f"{ED}/node_modules/.bin/hyperframes"] if os.path.exists(f"{ED}/node_modules/.bin/hyperframes") else ["npx", "--prefix", ED, "hyperframes"]   # 0.08 s to start vs 0.36 via npx


def pool(fn, items):
    """fn(x) for every x, JOBS at a time (JOBS=1: one by one, in order). The first failure cancels what hasn't started and is raised."""
    if JOBS <= 1 or len(items) <= 1: return [fn(x) for x in items]
    with ThreadPoolExecutor(JOBS) as ex:
        fs = [ex.submit(fn, x) for x in items]
        try:
            for f_ in as_completed(fs): f_.result()
        except BaseException:
            for f_ in fs: f_.cancel()
            raise
        return [f_.result() for f_ in fs]


def free_gb(path): st = os.statvfs(path); return st.f_bavail * st.f_frsize / 1e9


def need(path, gb, what, margin=1.0):
    f = free_gb(path)
    print(f"disk: {f:.1f} GB free before {what} (needs ~{gb:.1f})", flush=True)
    if f < gb + margin: sys.exit(f"Not enough space on {path} for {what}: {f:.1f} GB free, ~{gb + margin:.1f} GB needed")
COVER = {"skip"}                     # full-screen cards with no OB under them
SR = 48000
SFX_GAIN_DB = {"whoosh": -24, "pop": -22, "tick": -26, "thud": -18}   # OB 2026-10-16: quieter, it got repetitive
SFX_MIN_GAP = {"whoosh": 0.6, "pop": 0.3, "tick": 0.35, "thud": 1.0}  # the same sound again sooner than this is dropped
SFX_ON = os.environ.get("OB_SFX", "0") == "1" and sys.exit("react_render: OB_SFX=1 used the code-made kit (assets/sfx), banned without bank_miss (M59). Pick sounds from the bank: sfx_pick.py WORK --route ROUTE writes story/sfx_plan.json; mix it with assemble.py OB_SFX_PLAN (rebuild 2026-11-10)") or False   # OFF unless OB asks (2026-10-16: SFX "gives off young vibes and gets a bad demo, so only on request from me")


def cached(out, key): return os.path.exists(out) and os.path.exists(out + ".key") and open(out + ".key").read() == key
def mark(out, key): open(out + ".key", "w").write(key)
def fr(t): return int(round(t * FPS))
def ft(f): return f * FPS_D / FPS_N


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0: sys.exit(f"FAILED: {' '.join(map(str, cmd[:10]))} ...\n{r.stderr[-2500:]}")
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("work"); ap.add_argument("src"); ap.add_argument("out")
    ap.add_argument("--range", nargs=2, type=float, default=None); ap.add_argument("--keep", action="store_true")
    ap.add_argument("--graphics-only", action="store_true", help="render the graphics (cached) and stop")
    ap.add_argument("--audio-only", action="store_true", help="only the sound mix, no picture: OUT = 16 kHz mono wav (join QC before a render)")
    a = ap.parse_args()
    W, SRC = a.work, a.src; R, H = f"{W}/render", f"{W}/hf"
    global LUT
    if os.path.exists(f"{W}/lut.png"): LUT = f"{W}/lut.png"   # the grade OB picked for this take
    print("grade:", LUT, flush=True)
    # scratch: graphics renders, HyperFrames temp, units and the mix on the internal SSD (2026-11-03), else WORK_DIR/render
    SCR = os.environ.get("REACT_SCRATCH") or (os.path.expanduser(f"~/ob-scratch/{os.path.basename(os.path.abspath(W))}")
                                              if free_gb(os.path.expanduser("~")) > 80 else R)
    EVD, MIX, U = f"{SCR}/events", f"{SCR}/mix_qc.wav" if a.audio_only else f"{SCR}/mix.wav", f"{SCR}/units"
    for d in (U, EVD, f"{H}/assets/base", f"{H}/assets/montage"): os.makedirs(d, exist_ok=True)
    KEEP_U = os.path.realpath(U) != os.path.realpath(f"{R}/units")   # units off the T7 stay for the next render
    SRCID = f"{os.path.getsize(SRC)}:{int(os.path.getmtime(SRC))}"   # kept units must never outlive a re-exported camera file
    print(f"scratch: {SCR} ({'units kept' if KEEP_U else 'units cleared after the mux'}); {JOBS} at a time, {HF_WORKERS} HyperFrames workers each", flush=True)
    # HyperFrames' frame-extract cache lives under TMPDIR: use a private one, emptied after every render, so this
    # job never adds to the shared cache in OB-EDITS/tmp (T7 space, 2026-10-16)
    TMP = f"{SCR}/tmp"; os.makedirs(TMP, exist_ok=True)
    env = dict(os.environ, TMPDIR=TMP, HYPERFRAMES_NO_TELEMETRY="1")

    # ---- frame grid: each shot's source frames and edited frames
    shots, ef = [], 0
    for s in json.load(open(f"{W}/react_cutlist.json"))["shots"]:
        a0, b0 = fr(s["src_in"]), fr(s["src_out"])
        if s["layout"] == "insert":   # B-roll insert: its own frames, no camera time
            n = fr(s["dur"]); shots.append(dict(s, src0=a0, src1=a0, e0=ef, e1=ef + n)); ef += n; continue
        if b0 <= a0: continue
        shots.append(dict(s, src0=a0, src1=b0, e0=ef, e1=ef + b0 - a0)); ef += b0 - a0
    TOTAL = ef
    R0, R1 = (0, TOTAL) if not a.range else (fr(a.range[0]), min(TOTAL, fr(a.range[1])))
    allev = json.load(open(f"{W}/react_events.json"))["events"]
    evs, last = [], 0
    for e in sorted((e for e in allev if not e.get("held")), key=lambda e: e["edit_in"]):
        e["f0"], e["f1"] = max(fr(e["edit_in"]), last), min(TOTAL, fr(e["edit_out"]))
        if e["f1"] - e["f0"] < 6: continue
        last = e["f1"]; evs.append(e)
    evs = [e for e in evs if e["f1"] > R0 and e["f0"] < R1] if not a.audio_only else []
    for e in evs: e["f0"], e["f1"] = max(e["f0"], R0), min(e["f1"], R1)
    print(f"{len(shots)} shots, {ft(TOTAL) / 60:.2f} min; range {ft(R0):.2f}-{ft(R1):.2f}s; {len(evs)} graphics "
          f"(held, not rendered: {[e['id'] for e in allev if e.get('held')]})", flush=True)

    def pieces(f0, f1):
        """[(shot, src_frame0, nframes)] covering edited frames [f0, f1)."""
        out = []
        for s in shots:
            lo, hi = max(f0, s["e0"]), min(f1, s["e1"])
            if hi > lo: out.append((s, s["src0"] + (lo - s["e0"]), hi - lo))
        return out

    clipname = {}
    for line in open(f"{W}/clips_index.txt"):
        k_, name_, _ = line.rstrip("\n").split("\t"); clipname[int(k_[1:])] = name_

    def pkey(s, s0, n, lay):
        return f"{VKEY}:{SRCID}:{lay}:{s0}:{n}:{s.get('framing')}:{s.get('clip')}:{s.get('offset')}:{s.get('bites')}:{OB_X}:{CLIP_X}:{os.path.getmtime(LUT)}" + (f":{PIP_W}:{PIP_VH}:{PIP_B}:{PIP_M}:{PIP_D}:{s.get('credit')}" if lay == "pip" else "") + (f":px{s.get('pip_x')}:{s.get('pip_side')}" if lay == "pip" and (s.get('pip_x') is not None or s.get('pip_side')) else "")

    def pip_box(s):
        """(x, y, w, h) of the clip box on the 4K canvas: top right, the clip's whole frame (16:9 width PIP_W, 9:16 height PIP_VH)."""
        r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0",
                            f"{W}/clips/{s['clip']}"], capture_output=True, text=True).stdout.strip().split(",")
        cw, ch = int(r[0]), int(r[1])
        if ch > cw: bh = PIP_VH; bw = int(round((bh - 2 * PIP_B) * cw / ch)) + 2 * PIP_B
        else: bw = PIP_W; bh = int(round((bw - 2 * PIP_B) * ch / cw)) + 2 * PIP_B
        bw += bw % 2; bh += bh % 2
        if s.get("pip_side") == "L": return PIP_M, PIP_M, bw, bh   # C4415 rev 2: he sits right in this footage, so the box goes left (never over him)
        return 3840 - PIP_M - bw, PIP_M, bw, bh

    def credit_png(s, bx):
        """the source credit under the box (brand: Big Shoulders ExtraBold, white, soft shadow), a transparent 4K PNG"""
        from PIL import Image, ImageDraw, ImageFont, ImageFilter
        txt = s.get("credit", ""); out = f"{U}/credit_{hashlib.sha1((txt + str(bx)).encode()).hexdigest()[:10]}.png"
        if os.path.exists(out): return out
        x, y, bw, bh = bx; f = ImageFont.truetype(os.path.expanduser(PIP_FONT), 60); f.set_variation_by_name("ExtraBold")
        lay = Image.new("RGBA", (3840, 2160), (0, 0, 0, 0)); d = ImageDraw.Draw(lay); tw = d.textlength(txt, font=f); tx, ty = (x if x < 1920 else x + bw - tw), y + bh + 22
        d.text((tx, ty + 19), txt, font=f, fill=(0, 0, 0, 153)); lay = lay.filter(ImageFilter.GaussianBlur(28))
        ImageDraw.Draw(lay).text((tx, ty), txt, font=f, fill=(255, 255, 255, 255))
        tmp_ = f"{out}.{threading.get_ident()}.png"; lay.save(tmp_); os.replace(tmp_, out); return out   # whole, even with 2 jobs on one credit

    def encode(s, s0, n, out, layout=None):
        """One piece of picture, exactly n frames: OB full frame (wide/punch), the split screen, or an insert."""
        lay = layout or s["layout"]
        key = pkey(s, s0, n, lay)
        if cached(out, key): return key
        if lay == "insert":   # each soundbite's clip sharp in the centre over a blurred, darkened fill of itself
            assert n == s["e1"] - s["e0"], "an insert is always rendered whole"
            cmd, fc = ["ffmpeg", "-nostdin", "-loglevel", "error", "-y"], ""
            for i, bt in enumerate(s["bites"]):
                cmd += ["-ss", f"{bt[1]:.3f}", "-t", f"{bt[2] - bt[1]:.3f}", "-i", f"{W}/clips/{clipname[bt[0]]}"]
                fc += (f"[{i}:v]fps={FPS_N}/{FPS_D},setsar=1,split[a{i}][b{i}];"
                       f"[a{i}]scale=3840:2160:force_original_aspect_ratio=increase,crop=3840:2160,boxblur=60:3,eq=brightness=-0.16:saturation=0.85[g{i}];"
                       f"[b{i}]scale=-2:2160:flags=lanczos[f{i}];[g{i}][f{i}]overlay=(W-w)/2:0,format=yuv420p,setpts=PTS-STARTPTS[v{i}];")
            fc += "".join(f"[v{i}]" for i in range(len(s["bites"]))) + f"concat=n={len(s['bites'])}:v=1:a=0[c];"
            fc += f"[c]tpad=start_duration={s.get('pad_in', 0)}:start_mode=clone:stop_duration={s.get('pad_out', 0) + 0.5}:stop_mode=clone[v]"
            run(cmd + ["-filter_complex", fc, "-map", "[v]", "-frames:v", str(n)] + VENC + [out])
        elif lay == "ob":
            vf = (PUNCH if s.get("framing") == "punch" else "") + "null"
            run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-ss", f"{ft(s0):.6f}", "-i", SRC, "-i", LUT,
                 "-filter_complex", f"[0:v]{vf}[v0];[v0][1:v]haldclut=interp=tetrahedral[v]", "-map", "[v]", "-frames:v", str(n)] + VENC + [out])
        elif lay == "pip":   # RP frame (OB 11-03): OB graded full frame, the clip in a white-bordered top-right box, its credit under it
            ct0 = max(0.0, ft(s0) - s["offset"]); bx = pip_box(s)
            x, y, bw, bh = bx
            cw_, ch_ = 3840 - PIP_D, int(round(2160 * (3840 - PIP_D) / 3840 / 2)) * 2   # his frame punched in from the left (OB 11-03: bigger boxes, never over him)
            px_ = int(s.get("pip_x", PIP_D)); px_ = max(0, min(3840 - cw_, px_))   # C4415 rev 2 (OB 11-04 "1:41 ... so much dead space"): per-shot crop on his face
            fc = (f"[0:v]crop={cw_}:{ch_}:{px_}:0,scale=3840:2160:flags=lanczos,setsar=1[o0];[o0][1:v]haldclut=interp=tetrahedral[ob];"
                  f"[2:v]fps={FPS_N}/{FPS_D},scale={bw - 2 * PIP_B}:{bh - 2 * PIP_B}:flags=lanczos,setsar=1,"
                  f"pad={bw}:{bh}:{PIP_B}:{PIP_B}:color=white[cl];[ob][cl]overlay=x={x}:y={y}:eof_action=repeat[o1];[o1][3:v]overlay=0:0[v]")
            run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-ss", f"{ft(s0):.6f}", "-i", SRC, "-i", LUT,
                 "-ss", f"{ct0:.6f}", "-i", f"{W}/clips/{s['clip']}", "-loop", "1", "-framerate", f"{FPS_N}/{FPS_D}", "-i", credit_png(s, bx),
                 "-filter_complex", fc, "-map", "[v]", "-frames:v", str(n)] + VENC + [out])
        else:   # split: topo card, OB panel on the left (graded), the clip on the right (as filmed)
            fc = (f"[0:v]crop={OB_W}:2160:{OB_SRC_X}:0[o0];[o0][1:v]haldclut=interp=tetrahedral[ob];"
                  f"[2:v]scale=3840:2160,setsar=1,format=yuv420p[bg];[bg][ob]overlay={OB_X}:0[b1];")
            cmd = ["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-ss", f"{ft(s0):.6f}", "-i", SRC, "-i", LUT,
                   "-loop", "1", "-framerate", f"{FPS_N}/{FPS_D}", "-i", TOPO]
            if lay == "split":
                ct0 = max(0.0, ft(s0) - s["offset"])
                cmd += ["-ss", f"{ct0:.6f}", "-i", f"{W}/clips/{s['clip']}"]
                fc += (f"[3:v]fps={FPS_N}/{FPS_D},scale={CLIP_W}:2160:force_original_aspect_ratio=decrease:flags=lanczos,setsar=1[cl];"
                       f"[b1][cl]overlay=x={CLIP_X}+({CLIP_W}-overlay_w)/2:y=(2160-overlay_h)/2:eof_action=repeat[v]")
            else:  # split_empty: the montage fills the clip panel itself
                fc += "[b1]null[v]"
            run(cmd + ["-filter_complex", fc, "-map", "[v]", "-frames:v", str(n)] + VENC + [out])
        mark(out, key); return key

    # ---- graphics: each is a HyperFrames render over its own base clip. Keys are worked out first, so a graphic
    #      whose final unit or render already exists is skipped without rebuilding anything (T7 space is tight).
    for e in evs:
        n = e["f1"] - e["f0"]; e["dur"] = round(ft(n), 6)
        e["_parts"] = [] if e["type"] in COVER else [(s, s0, nn, "split_empty" if e["type"] == "montage" else s["layout"]) for s, s0, nn in pieces(e["f0"], e["f1"])]
        e["_bkey"] = "|".join(pkey(*pt) for pt in e["_parts"])
    if not a.audio_only: json.dump({"events": [{k: v for k, v in e.items() if k != "_parts"} for e in evs]}, open(f"{R}/events_render.json", "w"))
    if evs: run([sys.executable, "-I", f"{ED}/bin/react_cards.py", f"{R}/events_render.json", H])   # render-mode compositions (base as <video>)
    def gfx(e):
        n = e["f1"] - e["f0"]; outp = f"{EVD}/{e['id']}.mp4"
        e["_hkey"] = hashlib.sha1((open(f"{H}/compositions/{e['id']}.html").read() + e["_bkey"]).encode()).hexdigest()
        e["_unit"], e["_ukey"] = f"{U}/ev_{e['id']}.mp4", f"{e['_hkey']}:{n}:{VKEY}"
        if cached(e["_unit"], e["_ukey"]) or cached(outp, e["_hkey"]): print("cached", e["id"], flush=True); return
        bp, parts, t0 = f"{H}/assets/base/{e['id']}.mp4", [], time.time()
        if e["_parts"]:
            for j, (s, s0, nn, lay) in enumerate(e["_parts"]):
                pp = f"{U}/b_{e['id']}_{j}.mp4"; encode(s, s0, nn, pp, lay); parts.append(pp)
            lst = f"{U}/b_{e['id']}.txt"; open(lst, "w").write("".join(f"file '{pp}'\n" for pp in parts))
            run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", bp])
        if e["type"] == "montage":   # B-roll clips in the montage panel, muted
            slot = e["dur"] / len(e["items_r"])
            for i, it in enumerate(e["items_r"]):
                if it["kind"] != "clip": continue
                run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-ss", f"{it['start']:.3f}", "-t", f"{slot + 0.3:.3f}", "-i", f"{W}/clips/{clipname[it['k']]}",
                     "-an", "-vf", f"fps={FPS_N}/{FPS_D},scale={CLIP_W}:-2:flags=lanczos", "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p",
                     f"{H}/assets/montage/{e['id']}_m{i}.mp4"])
        tmp = f"{TMP}/{e['id']}"; os.makedirs(tmp, exist_ok=True)   # its own HyperFrames temp, so parallel renders never share one
        r = subprocess.run(HF + ["render", H, "-c", f"compositions/{e['id']}.html", "-o", outp,
                                 "--fps", f"{FPS_N}/{FPS_D}", "--quality", "looks", "--workers", HF_WORKERS, "--browser-gpu", "--gpu", "--quiet"],
                           capture_output=True, text=True, env=dict(env, TMPDIR=tmp))
        if r.returncode != 0 or not os.path.exists(outp): sys.exit(f"HyperFrames failed on {e['id']}:\n{(r.stdout + r.stderr)[-3000:]}")
        mark(outp, e["_hkey"]); print("rendered", e["id"], f"({e['dur']:.1f}s) in {time.time() - t0:.0f} s", flush=True)
        shutil.rmtree(tmp, ignore_errors=True)
        if not a.keep:   # its base was only needed for this render
            for f_ in parts + [p_ + ".key" for p_ in parts] + [bp]:
                if os.path.exists(f_): os.remove(f_)
    tg = time.time(); pool(gfx, evs)
    if evs: print(f"graphics: {len(evs)} in {time.time() - tg:.0f} s", flush=True)
    if a.graphics_only: print("graphics done", flush=True); return

    paths, consumable = [], set()
    if not a.audio_only:
        # ---- the edited timeline as units: picture pieces between graphics, graphic units from their renders
        units, f = [], R0
        while f < R1:
            cur = next((e for e in evs if e["f0"] <= f < e["f1"]), None)
            if cur: units.append(("event", cur)); f = cur["f1"]; continue
            nxt = next((e["f0"] for e in evs if e["f0"] > f), R1)
            for pc in pieces(f, min(nxt, R1)): units.append(("base", pc))
            f = min(nxt, R1)
        # graphic renders first: fold each into its unit and delete the render, so the drive never holds both at once
        def fold(e):
            n = e["f1"] - e["f0"]; src_r = f"{EVD}/{e['id']}.mp4"
            if not cached(e["_unit"], e["_ukey"]):
                run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", src_r,
                     "-vf", f"fps={FPS_N}/{FPS_D},tpad=stop_mode=clone:stop_duration=1,setsar=1", "-frames:v", str(n)] + VENC + [e["_unit"]])
                mark(e["_unit"], e["_ukey"])
            if not a.keep:
                for f_ in (src_r, src_r + ".key"):
                    if os.path.exists(f_): os.remove(f_)
        tu = time.time(); pool(fold, [u[1] for u in units if u[0] == "event"])
        # base units are named by key, not position, so a cut upstream leaves every other unit cached
        bpath = lambda s, s0, n: f"{U}/u_{hashlib.sha1(pkey(s, s0, n, s['layout']).encode()).hexdigest()[:16]}.mp4"
        if (not a.keep or os.environ.get("REACT_CLEAN_ORPHANS")) and (R0, R1) == (0, TOTAL):   # units a cut or a changed graphic left behind only take space: clear them first
            plan = [bpath(*u[1]) if u[0] == "base" else u[1]["_unit"] for u in units]
            live = set(plan) | {p + ".key" for p in plan}; gone_ = [f_ for f_ in glob.glob(f"{U}/*") if f_ not in live and not os.path.basename(f_).startswith("credit_")]
            print(f"orphan units: {len(gone_)} files, {sum(os.path.getsize(f_) for f_ in gone_) / 1e9:.2f} GB freed", flush=True)
            for f_ in gone_: os.remove(f_)
        base_ = [u[1] for u in units if u[0] == "base" and not cached(bpath(*u[1]), pkey(*u[1], u[1][0]["layout"]))]
        need(U, ft(sum(pc[2] for pc in base_)) * VBR / 8 / 1000, f"the picture units still to encode ({ft(sum(pc[2] for pc in base_)):.0f} s)", margin=0.3)
        done_, lk = [0], threading.Lock()
        def enc(pc):
            s, s0, n = pc; encode(s, s0, n, bpath(s, s0, n))
            with lk:
                done_[0] += 1
                if done_[0] % 20 == 1 or done_[0] == len(base_): print(f"units {done_[0]}/{len(base_)} encoded", flush=True)
        pool(enc, base_)
        print(f"units: {len(base_)} encoded, {sum(1 for u in units if u[0] == 'base') - len(base_)} cached, in {time.time() - tu:.0f} s", flush=True)
        paths, consumable = [], set()
        for u in units:
            if u[0] == "base": pth = bpath(*u[1]); consumable.add(pth)
            else: pth = u[1]["_unit"]
            paths.append(pth)

    # ---- sound, cut at the same frame boundaries
    # the mic as mono float32 on disk, memory-mapped: the Mac has 8 GB and may be rendering something else
    raw = f"{SCR}/mic48_mono.f32"
    if not os.path.exists(raw):
        run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", f"{W}/mic_synced.wav", "-ac", "1", "-ar", str(SR), "-f", "f32le", raw])
    mic = np.memmap(raw, dtype=np.float32, mode="r")
    clips_audio, gains = {}, {}
    def rms_active(x):   # loudness of the voiced part only (20 ms frames above -40 dBFS)
        h = 960; nfr = len(x) // h; r = np.sqrt((x[:nfr * h].reshape(nfr, h) ** 2).mean(1) + 1e-12); act = r[r > 10 ** (-40 / 20)]
        return float(np.sqrt((act ** 2).mean())) if len(act) else 1e-3
    def active_sq(x):   # sum of squares and count over voiced 20 ms frames, so OB's level is measured without one big array
        h = 960; nfr = len(x) // h; e = (x[:nfr * h].reshape(nfr, h).astype(np.float64) ** 2).mean(1); act = e[e > 10 ** (-40 / 10)]
        return act.sum(), len(act)
    acc = [active_sq(np.asarray(mic[int(ft(s["src0"]) * SR): int(ft(s["src1"]) * SR)])) for s in shots if s["layout"] == "ob"]
    ob_ref = float(np.sqrt(sum(a_ for a_, _ in acc) / max(1, sum(n_ for _, n_ in acc))))
    def load_clip(name):
        if name in clips_audio: return
        wv = f"{SCR}/clip_{len(clips_audio)}.wav"
        run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", f"{W}/clips/{name}", "-vn", "-ac", "1", "-ar", str(SR), "-c:a", "pcm_f32le", wv])
        _, ca = wavfile.read(wv); clips_audio[name] = ca.astype(np.float32)
        gains[name] = ob_ref / rms_active(ca) * 10 ** (-1 / 20)   # clip sits 1 dB under OB's voice
    for s in shots:
        if s["layout"] in ("split", "pip"): load_clip(s["clip"])
        if s["layout"] == "insert":
            for bt in s["bites"]: load_clip(clipname[bt[0]])
    def ramp_env(t0, n, spans, r):
        """1 inside spans (recording time), 0 outside, with linear ramps of r seconds."""
        t = t0 + np.arange(n) / SR; env = np.zeros(n, np.float32)
        for a0, b0 in spans:
            env = np.maximum(env, np.clip(np.minimum((t - (a0 - r)) / r, ((b0 + r) - t) / r), 0, 1))
        return env
    from scipy.signal import stft, istft
    from scipy.ndimage import maximum_filter1d, uniform_filter1d
    gate = json.load(open(f"{W}/gate.json")) if os.path.exists(f"{W}/gate.json") else []
    NF, HOPF, DUCK = 2048, 512, 10 ** (-8 / 20)   # the clip keeps playing 8 dB under his talk-overs
    def aligned_clip(name, offset, t0, n):
        ca = clips_audio[name]; c0 = int(round((t0 - offset) * SR)); cl = ca[max(0, c0): max(0, c0) + n]
        cl = np.pad(cl, (max(0, -c0), 0))[:n]; return np.pad(cl, (0, n - len(cl))).astype(np.float64)
    HM = {}
    def play_hm(g):   # bleed magnitude transfer |mic|/|clip| for one play, measured where only the clip sounds
        key = (g["clip"], round(g["rec_in"], 3))
        if key in HM: return HM[key]
        load_clip(g["clip"]); t0_, t1_ = g["rec_in"], g["rec_out"]; n_ = int((t1_ - t0_) * SR)
        y = np.asarray(mic[int(t0_ * SR): int(t0_ * SR) + n_], np.float64); x = aligned_clip(g["clip"], g["offset"], t0_, len(y))
        _, _, Y = stft(y, SR, nperseg=NF, noverlap=NF - HOPF); _, _, X = stft(x, SR, nperseg=NF, noverlap=NF - HOPF)
        tt = t0_ + np.arange(Y.shape[1]) * HOPF / SR; quiet = np.ones(len(tt), bool)
        for a_, b_ in g.get("ob_speech", []): quiet &= ~((tt > a_ - 0.3) & (tt < b_ + 0.3))
        mag = np.abs(X).sum(0); act = quiet & (mag > np.percentile(mag, 40))
        HM[key] = np.median(np.abs(Y[:, act]) / (np.abs(X[:, act]) + 1e-9), axis=1) if act.sum() > 20 else None
        return HM[key]
    def suppress(y, x, hm, beta=2.0, floor=0.1):   # C4353 test: bleed -15..-22 dB, his voice -2 dB, words intact
        if hm is None or len(y) < NF: return y
        _, _, Y = stft(y, SR, nperseg=NF, noverlap=NF - HOPF); _, _, X = stft(x, SR, nperseg=NF, noverlap=NF - HOPF)
        B = hm[:, None] * maximum_filter1d(uniform_filter1d(np.abs(X), 3, axis=1), 9, axis=1)
        G = uniform_filter1d(np.clip(1 - beta * B / (np.abs(Y) + 1e-9), floor, 1.0), 3, axis=0)
        _, z = istft(Y * G, SR, nperseg=NF, noverlap=NF - HOPF); z = z[: len(y)]
        return np.pad(z, (0, len(y) - len(z)))
    def play_of(name, t0_, t1_):
        return next((g for g in gate if g["clip"] == name and g["rec_in"] - 0.5 <= t0_ and t1_ <= g["rec_out"] + 0.5), None)
    fade = int(0.006 * SR); up = np.linspace(0, 1, fade, dtype=np.float32)
    voice, gated = [], []
    for k_s, s in enumerate(shots):
        lo, hi = max(R0, s["e0"]), min(R1, s["e1"])
        if hi <= lo: continue
        s0 = s["src0"] + (lo - s["e0"]); n_s = int(round(ft(hi - lo) * SR)); t0 = ft(s0); a0 = int(round(t0 * SR))
        if s["layout"] == "insert":   # the soundbites, back to back after the lead-in, 8 ms fades on each
            assert lo == s["e0"] and hi == s["e1"], "an insert is always rendered whole"
            piece = np.zeros(n_s, np.float32); at = int(round(s.get("pad_in", 0) * SR)); f8 = int(0.008 * SR); r8 = np.linspace(0, 1, f8, dtype=np.float32)
            for bt in s["bites"]:
                nm = clipname[bt[0]]; seg = clips_audio[nm][int(round(bt[1] * SR)): int(round(bt[2] * SR))] * gains[nm]
                seg = seg.copy(); seg[:f8] *= r8; seg[-f8:] *= r8[::-1]; m_ = min(len(seg), n_s - at)
                if m_ > 0: piece[at:at + m_] += seg[:m_]
                at += len(seg)
            voice.append(piece); continue
        piece = np.array(mic[a0:a0 + n_s], dtype=np.float64); piece = np.pad(piece, (0, n_s - len(piece)))
        if s["layout"] in ("split", "pip"):
            sp = list(s.get("ob_speech", []))
            prev = shots[k_s - 1] if k_s else None   # same take, he is mid-word as the clip resumes: his mic stays open 0.35 s
            if lo == s["e0"] and prev is not None and prev["layout"] == "ob" and abs(ft(prev["src1"]) - t0) < 1.0:
                tail = np.asarray(mic[int(ft(prev["src1"]) * SR) - int(0.06 * SR): int(ft(prev["src1"]) * SR)], np.float64)
                if len(tail) and 10 * np.log10((tail ** 2).mean() + 1e-12) > 20 * np.log10(ob_ref) - 12: sp.append((t0, t0 + 0.35))
            cl = aligned_clip(s["clip"], s["offset"], t0, n_s)
            if sp:
                g = play_of(s["clip"], ft(s["src0"]), ft(s["src1"])) or {"clip": s["clip"], "rec_in": ft(s["src0"]), "rec_out": ft(s["src1"]), "offset": s["offset"], "ob_speech": sp}
                piece = suppress(piece, cl, play_hm(g))
            g_ob = ramp_env(t0, n_s, sp, 0.03); g_cl = 1 - (1 - DUCK) * ramp_env(t0, n_s, sp, 0.12)
            gm = play_of(s["clip"], ft(s["src0"]), ft(s["src1"]))
            if gm and gm.get("mute_clip"):   # clip time spans whose own sound never plays (C4354: a copyrighted song under OB's read)
                tcl = (t0 - s["offset"]) + np.arange(n_s) / SR; mute = np.zeros(n_s, np.float32)
                for c0_, c1_ in gm["mute_clip"]: mute = np.maximum(mute, np.clip(np.minimum((tcl - (c0_ - 0.03)) / 0.03, ((c1_ + 0.03) - tcl) / 0.03), 0, 1))
                g_cl = g_cl * (1 - mute)
            piece = piece * g_ob + cl * gains[s["clip"]] * g_cl
            gated.append((ft(lo - R0), ft(hi - R0), len(sp)))
        elif s.get("from_repeat"):   # OB talking while a clip replayed (clip hidden): take the replay's bleed out of his mic
            g = next((g for g in gate if g["rec_in"] - 0.5 <= ft(s["src0"]) and ft(s["src1"]) <= g["rec_out"] + 0.5), None)
            if g: piece = suppress(piece, aligned_clip(g["clip"], g["offset"], t0, n_s), play_hm(g))
        piece = piece.astype(np.float32)
        if len(piece) > 2 * fade: piece[:fade] *= up; piece[-fade:] *= up[::-1]
        voice.append(piece)
    voice = np.concatenate(voice); target = int(round(ft(R1 - R0) * SR))
    voice = np.pad(voice, (0, max(0, target - len(voice))))[:target]
    # bleeps (WORK_DIR/bleeps.json, source-time spans pinned by bleep_pin.py): a 1 kHz tone 3 dB under his voice
    BL = [b for b in (json.load(open(f"{W}/bleeps.json")) if os.path.exists(f"{W}/bleeps.json") else []) if b.get("t0") is not None]
    nb = 0
    for b in BL:
        for s in shots:
            if s["layout"] == "insert": continue
            a_, b_ = max(b["t0"], ft(s["src0"])), min(b["t1"], ft(s["src1"]))
            if b_ <= a_: continue
            i0 = int(round((ft(s["e0"] - R0) + a_ - ft(s["src0"])) * SR)); i1 = int(round((ft(s["e0"] - R0) + b_ - ft(s["src0"])) * SR))
            i0, i1 = max(0, i0), min(len(voice), i1)
            if i1 - i0 < 16: continue
            tt = np.arange(i1 - i0) / SR; tone = (ob_ref * np.sqrt(2) * 10 ** (-3 / 20) * np.sin(2 * np.pi * 1000 * tt)).astype(np.float32)
            f5 = min(int(0.005 * SR), (i1 - i0) // 2); w = (0.5 - 0.5 * np.cos(np.linspace(0, np.pi, f5))).astype(np.float32)
            tone[:f5] *= w; tone[-f5:] *= w[::-1]; voice[i0:i1] = tone; nb += 1
    if BL: print(f"bleeps: {nb} placed of {len(BL)} pinned words", flush=True)

    # ---- synthesized SFX bus, only with OB_SFX=1. Sound on entrances only, no exit whooshes; variants NAME_1..N, never
    #      the same file twice in a row; +-1.5 dB jitter; same-type minimum gaps in time order (OB 2026-10-16: "so repetitive")
    hits = []
    def place(name, t, db=0.0): hits.append((t, name, db))
    for s in shots:   # an insert lands with a whoosh
        if s["layout"] == "insert" and R0 <= s["e0"] < R1: place("whoosh", max(0, ft(s["e0"] - R0) - 0.1))
    for e in evs:
        t0 = ft(e["f0"] - R0); D = ft(e["f1"] - e["f0"]); typ = e["type"]
        if typ == "title": place("thud", t0); place("whoosh", max(0, t0 - 0.12))
        elif typ == "stamp": place("thud", t0 + 0.05)
        elif typ == "pop": place("pop", t0)
        elif typ in ("label", "term"): place("tick", t0)
        elif typ == "skip": place("whoosh", t0)
        elif typ == "montage":
            place("whoosh", t0)
            for i in range(len(e["items_r"])): place("tick", t0 + i * D / len(e["items_r"]), -6)
        elif typ == "overlay":
            flash = e["layout"] == "flash"
            for it in sorted(set(e["items_t"])): place("tick" if flash else "pop", t0 + it, -8 if flash else -3)
        elif typ in ("study", "chart"):
            place("whoosh", t0); place("tick", t0 + 1.2)
            if typ == "chart" or e.get("chart"): place("pop", t0 + (2.4 if typ == "chart" else 2.6), -4)
        elif typ == "end": place("whoosh", t0)
    if not a.audio_only: json.dump(sorted(hits), open(f"{R}/sfx_cues.json", "w"))   # with a no-SFX mix.wav, all a later SFX version needs
    if SFX_ON:
        kit = {}
        for name in SFX_GAIN_DB:
            kit[name] = []
            for f in sorted(glob.glob(f"{SFXDIR}/{name}_[0-9]*.wav")) or [f"{SFXDIR}/{name}.wav"]:
                _, sx = wavfile.read(f); sx = sx.astype(np.float32) / 2 ** 31
                kit[name].append((sx.mean(axis=1) if sx.ndim > 1 else sx) * 10 ** (SFX_GAIN_DB[name] / 20))
        bus = np.zeros(len(voice), np.float32); rnd = random.Random(1016); last_t, prev_v, used, gapped = {}, {}, 0, 0
        for t, name, db in sorted(hits):
            i = int(round(t * SR))
            if not 0 <= i < len(bus): continue
            if t - last_t.get(name, -99.0) < SFX_MIN_GAP[name]: gapped += 1; continue
            k = rnd.choice([j for j in range(len(kit[name])) if j != prev_v.get(name)] or [0]); last_t[name], prev_v[name] = t, k
            sx = kit[name][k][: len(bus) - i] * 10 ** ((db + rnd.uniform(-1.5, 1.5)) / 20); bus[i:i + len(sx)] += sx; used += 1
        print(f"sfx: {used} placed, {gapped} dropped by the minimum gaps", flush=True)
        wavfile.write(f"{R}/sfx_only.wav", SR, bus)
        voice += bus; del bus
    else: print(f"sfx: off ({len(hits)} cues saved; OB_SFX=1 mixes them in)", flush=True)
    # 11-04 (C4415): an optional licensed score under the mix, before the master: WORK_DIR/score.json (or OB_SCORE), bin/score.py's
    #   cue sheet in edit time (one Mixkit track per chapter, ducked under every voice in the mix). The mix goes stereo for it.
    SCORE = os.environ.get("OB_SCORE") or (f"{W}/score.json" if os.path.exists(f"{W}/score.json") else None)
    if SCORE and not a.audio_only:
        import score as _score
        bed = _score.build(json.load(open(SCORE)), voice, SR, ft(R0)).astype(np.float32)
        voice = np.stack([voice, voice], 1) + bed[: len(voice)]
        print(f"score: {SCORE} under the mix ({bed.shape[0] / SR:.1f} s)", flush=True); del bed
    wavfile.write(MIX, SR, voice.astype(np.float32))   # mono float32 (float64 doubles the T7 space); the mux writes it as stereo (a score makes it stereo)
    if a.audio_only:   # the raw mix (no master): what the joins sound like
        run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", MIX, "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", a.out]); os.remove(MIX)
        print("audio only ->", a.out, flush=True); return

    # ---- master. OB 2026-10-16: "why is there such a bad room echo". The camera's sound was never in the mix (the
    #      render matches the external mic at r=0.86, the camera at 0.28); the echo was the master: 2:1 compression plus
    #      +17 dB into a -3 dBFS limiter squashed every syllable and lifted the room tail right after words 6-10 dB over
    #      the raw mic. Now C4352's master (two-pass loudnorm, LRA 11, a slow leveller that keeps the dry mic's
    #      dynamics), aimed at -13 because its dynamic mode lands ~1 LU short, then a gentle downward expander that
    #      pulls the late room tail under the raw mic's. Test on the intro: tail 80-160 ms after a word -22..-25 dB
    #      (raw -24..-29, old master -16..-21), -14.6 LUFS, every word intact.
    EXP = "agate=mode=downward:range=0.2:threshold=0.03:ratio=2:attack=3:release=90:knee=2"
    def stats(af):
        r_ = run(["ffmpeg", "-nostdin", "-i", MIX, "-af", af + ",ebur128=peak=true", "-f", "null", "-"])
        tp_ = re.findall(r"True peak:\s*\n\s*Peak:\s+(-?[\d.]+) dBFS", r_.stderr)
        return (float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r_.stderr)[-1]), float(tp_[-1]) if tp_ else None,
                float(re.findall(r"LRA:\s+([\d.]+) LU", r_.stderr)[-1]))
    r_ = run(["ffmpeg", "-nostdin", "-i", MIX, "-af", "highpass=f=70,loudnorm=I=-13:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"])
    m_ = json.loads(r_.stderr[r_.stderr.rindex("{"): r_.stderr.rindex("}") + 1])
    af = (f"highpass=f=70,loudnorm=I=-13:TP=-1.5:LRA=11:measured_I={m_['input_i']}:measured_TP={m_['input_tp']}:"
          f"measured_LRA={m_['input_lra']}:measured_thresh={m_['input_thresh']}:offset={m_['target_offset']}:linear=true,{EXP}")
    I_, TP_, LRA_ = stats(af)
    ln = {"integrated_LUFS": I_, "true_peak_dBFS_mono": TP_, "LRA": LRA_, "loudnorm": m_.get("normalization_type"), "chain": af}
    print(f"master: {I_} LUFS, true peak {TP_} dBFS (mono; the stereo mux is 3 dB lower), LRA {LRA_} ({m_.get('normalization_type')})", flush=True)
    if os.path.exists(raw) and not a.keep: os.remove(raw)
    od = os.path.dirname(os.path.abspath(a.out))
    if os.stat(od).st_dev == os.stat(U).st_dev and not KEEP_U: need(od, 0.5, "the final mux")   # units are deleted as the mux consumes them: net footprint ~one unit + audio
    else: need(od, ft(R1 - R0) * VBR / 8 / 1000 + 0.2, "the final mux (output on another drive)")   # T7 full: write the final locally, move it after
    assert len(set(paths)) == len(paths), "a unit is used twice: deleting it as consumed would break the mux"
    lst = f"{R}/units.txt"; open(lst, "w").write("".join(f"file '{pp}'\n" for pp in paths))
    proc = subprocess.Popen(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-i", MIX,
                             "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-af", af + ",aresample=48000", "-ac", "2", "-c:a", "aac", "-b:a", "320k",
                             "-movflags", "+faststart", "-shortest", a.out], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    order, gone = {pp: k for k, pp in enumerate(paths)}, set()
    while proc.poll() is None:
        if not a.keep and not KEEP_U:
            lo = subprocess.run(["lsof", "-Fn", "-p", str(proc.pid)], capture_output=True, text=True).stdout
            opened = [order[l[1:]] for l in lo.splitlines() if l.startswith("n") and l[1:] in order]
            if opened:
                for pp in paths[:min(opened)]:   # ffmpeg is past these and has closed them
                    if pp in consumable and pp not in gone:
                        for f_ in (pp, pp + ".key"):
                            if os.path.exists(f_): os.remove(f_)
                        gone.add(pp)
        time.sleep(0.5)
    err = proc.stderr.read()
    if proc.returncode != 0: sys.exit(f"final mux failed:\n{err[-2500:]}")
    json.dump({"range": [ft(R0), ft(R1)], "frames": R1 - R0, "graphics": [e["id"] for e in evs], "gated_plays": gated,
               "clip_gain_db": {c: round(20 * np.log10(g_), 1) for c, g_ in gains.items()}, "master": ln}, open(f"{R}/render_log.json", "w"), indent=1)
    print("done ->", a.out, f"({ft(R1 - R0):.2f}s)", flush=True)
    try:   # 2026-10-28: the QC gate runs on every render (OB: "wire it in"); deliver.py keeps a FAIL out of his AirDrop folders
        sys.path.insert(0, os.path.expanduser("~/ob-editor/bin")); import qc_gate
        # 11-03 (ledger M36, OB: "the lips dont sync"): where every full-frame shot of him comes from, so the gate measures lip
        # sync on each (camera sound vs his mic in the render). Clip-box and insert shots carry the clip's sound, so they stay out.
        cam = [(SRC, ft(s["src0"] + lo - s["e0"]), ft(s["src0"] + hi - s["e0"]), ft(lo - R0))
               for s in shots if s["layout"] == "ob" for lo, hi in [(max(R0, s["e0"]), min(R1, s["e1"]))] if hi > lo]
        if cam: qc_gate.record_pieces(a.out, [(f"{W}/mic_synced.wav",) + c[1:] for c in cam], cam)
        qc_gate.after_render(a.out, ours=[[round(ft(e["f0"] - R0), 3), round(ft(e["f1"] - R0), 3)] for e in evs])   # spans with our graphics (text_face, 11-04)
    except Exception as e: print("qc_gate not run:", e, flush=True)
    if not a.keep:
        if not KEEP_U: shutil.rmtree(U, ignore_errors=True)
        for d_ in {R, SCR}:
            for f_ in os.listdir(d_):
                if (f_.startswith("clip_") and f_.endswith(".wav")) or f_ == "mic48_mono.f32": os.remove(f"{d_}/{f_}")


if __name__ == "__main__":
    main()
