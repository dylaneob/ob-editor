#!/usr/bin/env python3
"""Render a lecture reel from its EDL: frame-exact graded cut (punch-ins, TV fixes) -> HyperFrames
cards/captions -> camera voice + synthesized SFX at -14 LUFS.

  python3 lecture_render.py WORK NAME                    # A master   -> WORK/out/NAME_A.mp4
  python3 lecture_render.py WORK NAME --flash FLASH.json # V trial: flash-forward + the A master -> WORK/out/NAME_V.mp4

WORK is the batch dir (NAME_edl.json, hf/, luts/, tvpatch/, C43xx.wav). Like assemble.py (YouTube),
every cut sits on the 30000/1001 frame grid and the voice is cut at the same instants, so sync
cannot drift. Pieces and renders are cached by content key under WORK/render/NAME. Temp on T7.
Row options in the EDL: "framing": "wide"|"punch" (default: odd rows punch), "patch": tvpatch npz
name (default per reel below), "fill": "room" (gap gets room tone instead of the source).
"""
import argparse, hashlib, json, os, subprocess, sys
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfiltfilt

FPS_N, FPS_D = 30000, 1001
FPS = FPS_N / FPS_D
SR = 48000
BIN = os.path.expanduser("~/ob-editor/bin")
CV_PY = os.path.expanduser("~/OpenMontage/.venv/bin/python")
SFXDIR = os.path.expanduser(os.environ.get("OB_SFX_KIT") or sys.exit("lecture_render: the code-made kit (assets/sfx) is no longer the default (M59: bank first). Run sfx_pick.py WORK --route ROUTE for the plan; set OB_SFX_KIT=~/ob-editor/assets/sfx only when the plan records a bank_miss (rebuild 2026-11-10)"))
NPX_PREFIX = os.path.expanduser("~/ob-editor")
TAKES = {"L05": ("C4350", "C4350_B"), "L02": ("C4351", "C4351_B"), "HZ": ("C4349", "C4349_B"),
         "RESET": ("C4148", "G_B"), "LOSERS": ("C4149", "G_B"),    # night reels 10-16: grade B picked
         "REACT": ("C4356", "R_W1"),                                # Tim glow-up reaction 10-17: B2 rejected ("make it warmer"), OB picked W1
         "ADS1": ("C4359", "R_W1"), "ADS2": ("C4360", "R_W1"), "ADS1P": ("C4359", "R_W1")}      # 10-18 "what if fat loss is easy" remakes; the EDL's "grade" wins
PATCH = {"HZ": {5: "s05", 6: "s05", 7: "s05", 11: "s07", 12: "s07", 13: "s07", 14: "s07", 15: "s07", 16: "s07"}}
PUNCH = "crop=2000:3556:80:60,"
# 1.3x crops of the 2160x3840 frame that lift his face to the top third, so a clip panel or card can sit over his
# chest: "react_watch" while he looks down at his phone, "react_talk" when he talks to camera (C4356, 10-17)
FRAMES = {"wide": "", "punch": PUNCH, "react_watch": "crop=1600:2844:280:981,", "react_watch2": "crop=1600:2844:280:833,", "react_talk": "crop=1662:2954:249:504,",
          "react_talk2": "crop=1565:2783:297:579,",   # 1.38x, same face height: alternates with react_talk to hide jump cuts
          # ads C4359/C4360: face centre (1000, 1300) of 2160x3840, kept at mid-width and 32% height
          "ad_wide": "crop=1878:3339:63:222,", "ad_punch": "crop=1662:2954:171:345,"}
PANEL_W, PANEL_H = 632, 1124         # the reaction clip box: OB's own reels' 9:16 box (1230/0719), the whole clip, never cropped.
# OB 2026-10-21 on C4356: "you last time put it in a square rather than a normal frame like my others" (it was 740x840, centre-cropped)
# OB 10-19 "why is the quality so shit now, i shot it in 4k": the old pieces (h264_videotoolbox 24M) kept only ~78% of the
# fine detail of a lossless 4K->1080 downscale. x264 CRF 12 is near-transparent; VENC_TAG goes into the piece cache keys.
VENC_TAG = "x264crf12"
VENC = ["-c:v", "libx264", "-preset", "medium", "-crf", "12", "-profile:v", "high",
        "-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
        "-r", f"{FPS_N}/{FPS_D}", "-video_track_timescale", "30000", "-an"]
HF_TAG = "png+x264crf12"          # HyperFrames output settings, part of the gfx cache key
SFX_GAIN_DB = {"whoosh": -19, "pop": -17, "tick": -21, "thud": -13}      # same mix as the YouTube render


def fr(t): return int(round(t * FPS))
def ft(f): return f * FPS_D / FPS_N
def ss(f): return f"{ft(f) - 0.002:.4f}"          # just before frame f, so every decoder lands on f
def cached(out, key): return os.path.exists(out) and os.path.exists(out + ".key") and open(out + ".key").read() == key
def mark(out, key): open(out + ".key", "w").write(key)


def run(cmd, env=None):
    r = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if r.returncode != 0:
        sys.exit(f"FAILED: {' '.join(map(str, cmd[:10]))} ...\n{(r.stdout + r.stderr)[-3000:]}")
    return r


def mtime(p): return str(os.path.getmtime(p)) if os.path.exists(p) else "-"


def nframes(path):
    """Frame count from the container. Some MP4s add side data, so csv can print '60,': take the first field."""
    out = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=nb_frames", "-of", "csv=p=0", path]).stdout
    return int(out.strip().split(",")[0].split()[0])


def piece(src, lut, src_f0, n, framing, npz, out, R, tag, freeze=None):
    key = f"{src}:{src_f0}:{n}:{framing}:{lut}:{mtime(lut)}:{npz or '-'}:{mtime(npz) if npz else '-'}:{freeze}:{VENC_TAG}"
    if cached(out, key): return
    if freeze:      # (frames, still_frame): hold one settled frame for the first frames, then play on (he was still sitting down)
        fn, still_f = freeze; vf = FRAMES.get(framing, "") + "scale=1080:1920:flags=lanczos"
        run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-ss", ss(still_f), "-i", src, "-ss", ss(src_f0 + fn), "-i", src, "-i", lut, "-filter_complex",
             f"[0:v]trim=end_frame=1,loop=loop={fn - 1}:size=1:start=0,setpts=N/(30000/1001)/TB[a];[1:v]setpts=PTS-STARTPTS[b];"
             f"[a][b]concat=n=2:v=1:a=0[c];[c]{vf}[v0];[v0][2:v]haldclut=interp=tetrahedral[v]", "-map", "[v]", "-frames:v", str(n)] + VENC + [out])
        mark(out, key); return
    inp = ["-ss", ss(src_f0), "-i", src]; head = "[0:v]"; li = 1
    if npz:
        z = np.load(npz); X, Y = int(z["rect"][0]), int(z["rect"][1])
        band = f"{R}/band_{tag}.mov"
        bkey = f"{key}:band"
        if not cached(band, bkey):
            t0 = float(ss(src_f0))
            run([CV_PY, f"{BIN}/tv_patch.py", "band", npz, src, f"{t0:.4f}", f"{t0 + n / FPS + 0.3:.4f}", band, str(n)])
            nb = nframes(band)
            if nb != n: sys.exit(f"TV patch {band} has {nb} frames, needs {n}: the typo would flash back")
            mark(band, bkey)
        inp += ["-i", band]; head = f"[0:v][1:v]overlay={X}:{Y}:eof_action=pass[pv];[pv]"; li = 2
    vf = FRAMES.get(framing, "") + "scale=1080:1920:flags=lanczos"
    run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y"] + inp + ["-i", lut, "-filter_complex",
         f"{head}{vf}[v0];[v0][{li}:v]haldclut=interp=tetrahedral[v]", "-map", "[v]", "-frames:v", str(n)] + VENC + [out])
    mark(out, key)


def build_panel(work, name, spec, rows, starts, R):
    """The reaction's clip track, frame-exact with the edit: rows with panel_in show the source clip from that time
    (centre-cropped to the panel), every other row is black (the panel is hidden there)."""
    src = spec["clip"]["video"]; os.makedirs(f"{R}/panel", exist_ok=True)
    cw = 1080; ch = round(cw * PANEL_H / PANEL_W / 2) * 2
    parts, keys = [], []
    for i, r in enumerate(rows):
        n = starts[i + 1] - starts[i]; out = f"{R}/panel/q{i:03d}.mp4"
        p_in = r.get("panel_in"); dy = r.get("panel_dy", 0.0)
        key = f"{src}:{p_in}:{n}:{dy}:{PANEL_W}x{PANEL_H}"
        if not cached(out, key):
            if p_in is None:
                cmd = ["-f", "lavfi", "-i", f"color=c=black:s={PANEL_W}x{PANEL_H}:r={FPS_N}/{FPS_D}", "-frames:v", str(n)]
            else:
                y0 = f"(ih-{ch})/2+({dy})*(ih-{ch})/2"
                cmd = ["-ss", f"{p_in:.3f}", "-i", src, "-vf", f"fps={FPS_N}/{FPS_D},crop={cw}:{ch}:0:{y0},scale={PANEL_W}:{PANEL_H}:flags=lanczos",
                       "-frames:v", str(n)]
            run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y"] + cmd + VENC + [out]); mark(out, key)
            assert nframes(out) == n, f"panel piece {i} has the wrong frame count"
        parts.append(out); keys.append(open(out + ".key").read())
    clip = f"{work}/hf/assets/{name}_clip.mp4"; ckey = hashlib.sha1("|".join(keys).encode()).hexdigest()
    if not cached(clip, ckey):
        lst = f"{R}/panel/list.txt"; open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
        run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", clip]); mark(clip, ckey)
    print(f"{name}: panel track {nframes(clip)} frames", flush=True)


def load_sfx():
    kit = {}
    for k in SFX_GAIN_DB:
        sr, x = wavfile.read(f"{SFXDIR}/{k}.wav")
        x = x.astype(np.float64) / (32768.0 if x.dtype == np.int16 else 2 ** 31 if x.dtype == np.int32 else 1.0)
        if x.ndim > 1: x = x.mean(1)
        assert sr == SR, f"{k} is {sr} Hz"
        kit[k] = x * 10 ** (SFX_GAIN_DB[k] / 20)
    return kit


def room_tone(x):
    """Quietest 0.6 s of the take (the mic's own room), for gaps that can't use the source."""
    hop = int(SR * 0.05); n = len(x) // hop
    lev = 10 * np.log10((x[:n * hop].reshape(n, hop) ** 2).mean(1) + 1e-12)
    w = 12; best = min(range(n - w), key=lambda i: lev[i:i + w].max())
    return x[best * hop:(best + w) * hop]


def build(work, name, edl_path, R, out_tag):
    base = name[:-1] if name.endswith("V") else name          # "L05V" = the V opening of L05
    take, lutn = TAKES[base]
    # the T7 was reorganized on 10-16 (camera files -> RAW-FOOTAGE/camera, music -> MUSIC): look in both places
    src = next((p for p in (f"/Volumes/T7/{take}.MP4", f"/Volumes/T7/RAW-FOOTAGE/camera/{take}.MP4") if os.path.exists(p)), None)
    if not src: sys.exit(f"can't find {take}.MP4 on the T7 (root or RAW-FOOTAGE/camera)")
    lut = f"{work}/luts/{lutn}.png"
    spec = json.load(open(edl_path)); rows = spec["rows"]
    if spec.get("grade"): lut = f"{work}/luts/{spec['grade']}.png"      # grade picked per EDL (ads, 10-18)
    D_f = fr(spec["duration"])
    # frame grid: row i owns [fr(edit_in_i), fr(edit_in_{i+1})) of the reel, its gap included
    starts = [fr(r["edit_in"]) for r in rows] + [D_f]
    os.makedirs(f"{R}/pieces", exist_ok=True)
    parts, keys = [], []
    for i, r in enumerate(rows):
        n = starts[i + 1] - starts[i]; src_f0 = fr(r["src_in"])
        framing = r.get("framing") or ("punch" if i % 2 else "wide")
        pname = r.get("patch") or PATCH.get(base, {}).get(r.get("orig", i))
        npz = f"{work}/tvpatch/{pname}.npz" if pname else None
        out = f"{R}/pieces/p{i:03d}.mp4"
        frz = (fr(r["freeze_until"] - r["src_in"]), fr(r["freeze_frame"])) if r.get("freeze_until") else None
        rlut = f"{work}/luts/{r['lut']}.png" if r.get("lut") else lut      # per-line exposure/colour match (shot_match.py, 10-18)
        piece(src, rlut, src_f0, n, framing, npz, out, R, f"{i:03d}", frz)
        parts.append(out); keys.append(open(out + ".key").read())
        r["_n"], r["_src_f0"] = n, src_f0
    cut = f"{work}/hf/assets/{name}_cut.mp4"; ckey = hashlib.sha1("|".join(keys).encode()).hexdigest()
    if not cached(cut, ckey):
        lst = f"{R}/pieces/list.txt"; open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
        run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", cut]); mark(cut, ckey)
    nf = nframes(cut)
    print(f"{name}: cut {nf} frames (expected {D_f})", flush=True)
    assert abs(nf - D_f) <= 1, "frame count drifted"
    if any(r.get("panel_in") is not None for r in rows):
        build_panel(work, name, spec, rows, starts, R)
    if os.environ.get("STOP_AFTER_CUT"): sys.exit(0)

    # ---- voice: same instants as the video, mono (both camera channels carry the one mic)
    sr, x = wavfile.read(f"{work}/{take}.wav"); x = x.astype(np.float64) / 32768.0; x = x.mean(1) if x.ndim > 1 else x
    assert sr == SR
    tone = room_tone(x); total = round(ft(D_f) * SR); voice = np.zeros(total)
    fade = int(0.008 * SR); clipped = 0
    for i, r in enumerate(rows):
        a = round(ft(starts[i]) * SR); b = round(ft(starts[i + 1]) * SR); L = b - a
        if r.get("audio") == "clip":       # a reaction's source clip speaks on these rows (its own clean audio)
            if "_clipwav" not in spec:
                csr, cx = wavfile.read(spec["clip"]["wav"]); assert csr == SR, f"clip wav is {csr} Hz"
                cx = cx.astype(np.float64) / 32768.0; spec["_clipwav"] = cx.mean(1) if cx.ndim > 1 else cx
            c0 = round(r["clip_in"] * SR); seg = spec["_clipwav"][c0:c0 + L].copy()
        else:
            s0 = round(ft(r["_src_f0"]) * SR); seg = x[s0:s0 + L].copy()
        if len(seg) < L: seg = np.pad(seg, (0, L - len(seg)))
        clipped += int((np.abs(seg) > 0.995).sum())
        if r.get("fill") == "room":
            k = max(0, min(L, round((r["src_out"] - ft(r["_src_f0"])) * SR)))
            fill = np.resize(tone, L - k); xf = min(int(0.012 * SR), k, L - k)
            if xf > 0:
                ramp = np.linspace(0, 1, xf); fill[:xf] = seg[k:k + xf] * (1 - ramp) + fill[:xf] * ramp
            seg[k:] = fill
        joined_prev = i > 0 and rows[i - 1].get("gap", 0) == 0 and abs(rows[i - 1]["src_out"] - r["src_in"]) < 0.002
        joined_next = i + 1 < len(rows) and r.get("gap", 0) == 0 and abs(r["src_out"] - rows[i + 1]["src_in"]) < 0.002
        if not joined_prev: seg[:fade] *= np.linspace(0, 1, fade)     # joined rows run straight through: no fade at the join
        if not joined_next: seg[-fade:] *= np.linspace(1, 0, fade)
        voice[a:b] = seg
    voice = sosfiltfilt(butter(2, 80, btype="highpass", fs=SR, output="sos"), voice)
    voice = level_voice(voice, R, name)
    print(f"{name}: voice {total / SR:.2f} s, samples at full scale: {clipped}", flush=True)

    # ---- SFX, keyed to the same cue times the cards use
    kit = load_sfx(); bus = np.zeros(total)
    def place(k, t):
        if k not in kit:              # variant takes ("pop_3") share the base sound's gain
            sr_k, xk = wavfile.read(f"{SFXDIR}/{k}.wav"); assert sr_k == SR, f"{k} is {sr_k} Hz"
            xk = xk.astype(np.float64) / (32768.0 if xk.dtype == np.int16 else 2 ** 31 if xk.dtype == np.int32 else 1.0)
            kit[k] = (xk.mean(1) if xk.ndim > 1 else xk) * 10 ** (SFX_GAIN_DB[k.split("_")[0]] / 20)
        a = int(round(t * SR)); s = kit[k][: max(0, total - a)]
        if a >= 0 and len(s): bus[a:a + len(s)] += s
    f1_out = 0.0
    if spec.get("viz"):             # OB 10-16: animated diagrams; their sounds come from lecture_viz, keyed to the same words
        sys.path.insert(0, BIN); import lecture_viz
        for k, t in lecture_viz.sfx_events(spec, f"{work}/hf"): place(k, t)
    elif spec.get("frame1"):
        later = [r["edit_in"] for r in rows if (r["cue"] or {}).get("card") and r["edit_in"] >= 0.3]
        f1_out = min(2.5, (later[0] - 0.45) if later else 2.5); place("whoosh", f1_out - 0.06)
    cur = None
    for r in ([] if spec.get("viz") else rows):
        c = r.get("cue") or {}
        if c.get("card") and r["edit_in"] >= f1_out:
            cur = c
            if not c.get("instant"): place("pop", r["edit_in"] + 0.03)
            if c["card"] in ("table", "list", "checks") and not c.get("instant"):
                for j in range(len(c["rows"])): place("tick", r["edit_in"] + 0.30 + j * 0.45)
        if c.get("hide"): cur = None
        if c.get("stamp") and cur is not None: place("thud", r["edit_in"] + 0.12)
    mix = voice + bus
    if spec.get("music") and not os.environ.get("NO_MUSIC"):     # OB 10-16: his saved viral track under the voice, ducked while he talks (stereo mix)
        sys.path.insert(0, BIN); import music_mix
        mu = dict(spec["music"])
        if not os.path.exists(mu["file"]):
            alt = f"/Volumes/T7/MUSIC/{os.path.basename(mu['file'])}"
            if not os.path.exists(alt): sys.exit(f"music track missing: {mu['file']} (and not in /Volumes/T7/MUSIC)")
            mu["file"] = alt
        bed = music_mix.bed(mu["file"], mu.get("start", 0.0), voice, SR, mu.get("rel", -16.0), mu.get("duck", 5.0))
        mix = mix[:, None].repeat(2, 1) + bed[: len(mix)]
        print(f"{name}: music bed {os.path.basename(mu['file'])} from {mu.get('start', 0)} s, {mu.get('rel', -16)} dB under the voice", flush=True)
    mixp = f"{R}/{name}_mix_raw{'_nomusic' if os.environ.get('NO_MUSIC') else ''}.wav"
    wavfile.write(mixp, SR, mix.astype(np.float32))
    if os.environ.get("AUDIO_ONLY"):      # preview builds: the mix only, no HyperFrames render
        return None, mixp, spec

    # ---- graphics: frame-aligned copy of the EDL -> HyperFrames composition with the cut underneath
    spec_r = {k: v for k, v in spec.items() if not k.startswith("_")}; spec_r["duration"] = round(ft(D_f), 6)   # "_clipwav" is a cache
    edl_r = f"{R}/{name}_edl_render.json"; json.dump(spec_r, open(edl_r, "w"), indent=1)
    run([sys.executable, "-I", f"{BIN}/{'lecture_viz.py' if spec.get('viz') else 'lecture_cards.py'}", edl_r, f"{work}/hf", name])
    comp = f"{work}/hf/compositions/{name}.html"
    gfx = f"{R}/{name}_gfx.mp4"; gkey = hashlib.sha1((open(comp).read() + ckey + HF_TAG).encode()).hexdigest()
    if not cached(gfx, gkey):
        env = dict(os.environ, TMPDIR="/Volumes/T7/OB-EDITS/tmp", HYPERFRAMES_NO_TELEMETRY="1")
        os.makedirs("/Volumes/T7/OB-EDITS/tmp", exist_ok=True)
        print(f"{name}: HyperFrames render ...", flush=True)
        # quality (10-19): A-roll frames as PNG not JPEG, software x264 CRF 12 not the ~10 Mbps GPU encode
        cache = ["--frames-cache-dir", "/Volumes/OB-ARCHIVE/OB-EDITS/hf-frames-cache"] if os.path.isdir("/Volumes/OB-ARCHIVE") else []
        r = subprocess.run(["npx", "--prefix", NPX_PREFIX, "hyperframes", "render", f"{work}/hf", "-c", f"compositions/{name}.html", "-o", gfx,
                            "--fps", f"{FPS_N}/{FPS_D}", "--crf", "12", "--video-frame-format", "png", "--workers", "1", "--browser-gpu", "--quiet"] + cache,
                           capture_output=True, text=True, env=env)
        if r.returncode != 0 or not os.path.exists(gfx):
            sys.exit(f"HyperFrames failed on {name}:\n{(r.stdout + r.stderr)[-3000:]}")
        mark(gfx, gkey)
    return gfx, f"{R}/{name}_mix_raw.wav", spec


def lufs(path, pre=""):
    """Integrated loudness and true peak (EBU R128) of a file, after optional filters."""
    r = run(["ffmpeg", "-nostdin", "-i", path, "-vn", "-af", (pre + "," if pre else "") + "ebur128=peak=true", "-f", "null", "-"])
    I = float(r.stderr[r.stderr.rfind("I:"):].split()[1]); tp = float(r.stderr[r.stderr.rfind("Peak:"):].split()[1])
    return I, tp


def level_voice(voice, R, name):
    """Camera voice peaks run ~22 dB over its loudness (plosives, a near-clip), which blocks a clean -14.
    Gentle 2.5:1 leveling above -26 dBFS, then the voice is set to -20 LUFS (mono) so the SFX gains
    sit under it the same way in every reel."""
    pre, post = f"{R}/{name}_voice_pre.wav", f"{R}/{name}_voice_lev.wav"
    wavfile.write(pre, SR, voice.astype(np.float32))
    run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", pre, "-af", "acompressor=threshold=-26dB:ratio=2.5:attack=8:release=150:makeup=1",
         "-c:a", "pcm_f32le", post])
    _, v = wavfile.read(post); v = v.astype(np.float64)
    I, _ = lufs(post)
    os.remove(pre); os.remove(post)
    return v * 10 ** ((-20.0 - I) / 20)


def loudnorm_mux(video, wav, out):
    """Master the mix as delivered (stereo, both channels the same): gain to -14 LUFS, then a peak limiter
    at -3 dBFS so true peaks stay under -1 dBTP after AAC. Linear and predictable, no loudnorm pumping."""
    ch = int(run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=channels", "-of", "csv=p=0", wav]).stdout.strip().split(",")[0])
    pan = "pan=stereo|c0=c0|c1=c0" if ch == 1 else "aformat=channel_layouts=stereo"   # stereo music mixes keep both channels
    I, _ = lufs(wav, pan); g = -14.0 - I
    af = f"{pan},volume={g:.2f}dB,alimiter=limit=0.708:attack=1:release=60:level=false,aresample=48000"
    run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", video, "-i", wav, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
         "-af", af, "-c:a", "aac_at", "-b:a", "256k", "-movflags", "+faststart", "-shortest", out])   # Apple AAC: native aac overshot to -0.1 dBTP
    Io, tpo = lufs(out)
    print(f"done -> {out}  (mix {I:.1f} LUFS stereo, gain {g:+.1f} dB -> {Io:.1f} LUFS, true peak {tpo:.1f} dBFS)", flush=True)
    try:   # 2026-10-28: the QC gate runs on every render (OB: "wire it in"); deliver.py keeps a FAIL out of his AirDrop folders
        sys.path.insert(0, os.path.expanduser("~/ob-editor/bin")); import qc_gate; qc_gate.after_render(out)
    except Exception as e: print("qc_gate not run:", e, flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("work"); ap.add_argument("name"); ap.add_argument("--flash")
    a = ap.parse_args()
    W = a.work; os.makedirs(f"{W}/out", exist_ok=True)
    if not a.flash:
        R = f"{W}/render/{a.name}"; os.makedirs(R, exist_ok=True)
        gfx, mix, _ = build(W, a.name, f"{W}/{a.name}_edl.json", R, "A")
        if gfx is None: print(f"audio only -> {mix}"); return
        loudnorm_mux(gfx, mix, f"{W}/out/{a.name}_A.mp4")
        if os.environ.get("ALSO_NOMUSIC") and json.load(open(f"{W}/{a.name}_edl.json")).get("music"):
            # voice + SFX only, same picture: a fallback in case Instagram mutes the baked-in song
            os.environ["NO_MUSIC"] = "1"; os.environ["AUDIO_ONLY"] = "1"
            _, mix2, _ = build(W, a.name, f"{W}/{a.name}_edl.json", R, "A")
            loudnorm_mux(gfx, mix2, f"{W}/out/{a.name}_A_nomusic.mp4")
            del os.environ["NO_MUSIC"], os.environ["AUDIO_ONLY"]
        return
    # V: flash-forward opening, a whoosh on the jump, then the finished A from its first frame
    RA = f"{W}/render/{a.name}"; gA, mA = f"{RA}/{a.name}_gfx.mp4", f"{RA}/{a.name}_mix_raw.wav"
    assert os.path.exists(gA) and os.path.exists(mA), "render the A master first"
    vname = a.name + "V"; R = f"{W}/render/{vname}"; os.makedirs(R, exist_ok=True)
    gF, mF, _ = build(W, vname, a.flash, R, "V")
    lst = f"{R}/join.txt"; open(lst, "w").write(f"file '{gF}'\nfile '{gA}'\n")
    vid = f"{R}/{vname}_video.mp4"
    run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", vid])
    sf, xf = wavfile.read(mF); sa, xa = wavfile.read(mA)
    nfF = nframes(gF)
    xf = np.pad(xf, (0, max(0, round(ft(nfF) * SR) - len(xf))))[: round(ft(nfF) * SR)]
    joined = np.concatenate([xf, xa]).astype(np.float64)
    w = load_sfx()["whoosh"]; t = round((ft(nfF) - 0.12) * SR); joined[t:t + len(w)] += w[: len(joined) - t]
    wavfile.write(f"{R}/{vname}_mix_raw.wav", SR, joined.astype(np.float32))
    loudnorm_mux(vid, f"{R}/{vname}_mix_raw.wav", f"{W}/out/{a.name}_V.mp4")


if __name__ == "__main__":
    main()
