"""The level kit's pipeline, one step per subcommand, all driven by a plan.json (schema in ../README.md).

  python3 -I ~/ob-editor/level-kit/lk.py recut  PLAN [--lock N]   tighten plan.raw_pieces into butt-joined pieces (keeps each piece's
                                                         words + rise/decay), prove every edge on the raw mic, write plan.pieces
  python3 -I ~/ob-editor/level-kit/lk.py verify PLAN [--lock N]   after hand edits to plan.pieces: re-chain, re-prove edges + silence
  python3 -I ~/ob-editor/level-kit/lk.py aroll  PLAN             graded A-roll frames (LUT) for every camera frame the cut shows
  ~/OpenMontage/.venv/bin/python -I ~/ob-editor/level-kit/lk.py matte PLAN   BiRefNet matte per camera frame (lock, Neural Engine check)
  python3 -I ~/ob-editor/level-kit/lk.py cells  PLAN [NAME ...]  each grid cell clip -> 720x1280 JPEG frames at 29.97
  python3 -I ~/ob-editor/level-kit/lk.py audio  PLAN             his mic pieces through voice_master.py + the SFX plan -> mix.wav
  python3 -I ~/ob-editor/level-kit/lk.py render PLAN [K0 K1]     frames through levelkit.engine (8 workers, COMP_WORKERS)
  python3 -I ~/ob-editor/level-kit/lk.py encode PLAN             frames + mix -> plan.final (x264 crf 17, AAC 256k)
  python3 -I ~/ob-editor/level-kit/lk.py review PLAN             a frame every 0.5 s on contact sheets + blackdetect / freezedetect
  python3 -I ~/ob-editor/level-kit/lk.py gate   PLAN             qc_gate.after_render with every piece (edges on the raw take) + lipsync map
  python3 -I ~/ob-editor/level-kit/lk.py stills PLAN T [T ...]   engine stills (no encode) for quick looks

Run from ~/ob-editor/level-kit (or put it on PYTHONPATH). Heavy steps call render_slots.wait_free() first."""
import json, math, os, subprocess, sys, time
import numpy as np
from levelkit.clock import Plan, FPS
BIN = os.path.expanduser("~/ob-editor/bin"); sys.path.insert(0, BIN)
SR = 48000; ASSETS = os.path.expanduser("~/ob-editor/assets/")


def slots():
    try:
        import render_slots; render_slots.wait_free(log=print)
    except Exception as e: print("render_slots:", e)


def ff(*a, **kw):
    return subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", *a], check=True, **kw)


def mono(path, ss=None, dur=None, sr=SR):
    a = ["ffmpeg", "-nostdin", "-v", "error"] + (["-ss", f"{ss:.4f}", "-t", f"{dur:.4f}"] if ss is not None else []) + ["-i", path, "-af", "pan=mono|c0=c0", "-ar", str(sr), "-f", "f32le", "-"]
    return np.frombuffer(subprocess.run(a, capture_output=True, check=True).stdout, np.float32).astype(np.float64)


# ---------------- recut ----------------
def recut(P, lock=0):
    """Each raw piece keeps its words and their rise and decay (to p90 - 32 dB plus 10 ms, zero_dead's tail rule); the gaps go and
    the pieces butt-join (the gate's dead-air rule M01: silence 3% or less, none over 0.2 s). Locked pieces are kept as they are."""
    import zero_dead as Z, qc_gate
    from scipy.io import wavfile
    raw = P.p["raw_pieces"]; locked = P.p.get("locked_pieces", [])[:lock]
    out = [list(x) for x in locked]; e = (out[-1][0] + out[-1][2] - out[-1][1]) if out else 0.0
    for (a, b, lid) in raw[len(locked):]:
        x = mono(P.mic, a, b - a, 16000)
        env = Z.level_env(x); p90 = np.percentile(env, 90); on = np.where(env > p90 - Z.TAIL)[0]
        na = a + max(0.0, on[0] * Z.HOP - 0.010); nb = a + min(b - a, on[-1] * Z.HOP + Z.WIN + 0.010)
        out.append([round(e, 4), round(na, 4), round(nb, 4), lid]); e += nb - na
        print(f"{lid:8s} a {a:.3f}->{na:.3f}  b {b:.3f}->{nb:.3f}")
    vo = []
    for (_, na, nb, _) in out:
        y = mono(P.mic, na, nb - na).astype(np.float32).copy(); f = 240; y[:f] *= np.linspace(0, 1, f); y[-f:] *= np.linspace(1, 0, f); vo.append(y)
    p = P.wpath("audio", "voice_tight.wav"); wavfile.write(p, SR, np.concatenate(vo))
    print("length", round(e, 3), "dead_space", Z.dead_space(p))
    print("edges", qc_gate.c_edges(p, segs=[(P.mic, a, b, t) for t, a, b, _ in out]))
    P.p["pieces"] = out; json.dump(P.p, open(P.path, "w"), indent=1); return out


def verify(P, lock=0):
    """After hand edits to plan.pieces (a split inside a pause, an edge moved back): re-chain edit_in after the locked pieces,
    rebuild the butt-joined voice and prove the edges and the silence again."""
    import zero_dead as Z, qc_gate
    from scipy.io import wavfile
    ps = [list(x) for x in P.p["pieces"]]; e = ps[lock - 1][0] + ps[lock - 1][2] - ps[lock - 1][1] if lock else 0.0
    for q in ps[lock:]: q[0] = round(e, 4); e += q[2] - q[1]
    vo = []
    for (_, na, nb, _) in ps:
        y = mono(P.mic, na, nb - na).astype(np.float32).copy(); f = 240; y[:f] *= np.linspace(0, 1, f); y[-f:] *= np.linspace(1, 0, f); vo.append(y)
    p = P.wpath("audio", "voice_tight.wav"); wavfile.write(p, SR, np.concatenate(vo))
    print("length", round(e, 3), "dead_space", Z.dead_space(p))
    print("edges", qc_gate.c_edges(p, segs=[(P.mic, a, b, t) for t, a, b, _ in ps]))
    P.p["pieces"] = ps; json.dump(P.p, open(P.path, "w"), indent=1)


# ---------------- A-roll frames ----------------
def runs(js):
    js = sorted(set(js)); out = []
    for j in js:
        if out and j == out[-1][1] + 1: out[-1][1] = j
        else: out.append([j, j])
    return out


def aroll(P, w=1440, h=2560):
    need = [j for j in P.cam_frames_needed() if not os.path.exists(P.aroll_path(j))]
    os.makedirs(os.path.join(P.work, "aroll"), exist_ok=True)
    for j0, j1 in runs(need):
        n = j1 - j0 + 1; slots()
        ff("-ss", f"{(j0 - 0.5) / P.fps:.4f}", "-i", P.cam, "-i", P.lut, "-filter_complex", f"[0:v]scale={w}:{h}:flags=lanczos[v];[v][1:v]haldclut,format=yuvj420p",
           "-frames:v", str(n), "-q:v", "2", "-start_number", str(j0), os.path.join(P.work, "aroll", "c_%06d.jpg"))
        print("aroll", j0, j1, n, flush=True)
    print("aroll frames needed", len(P.cam_frames_needed()), "missing", sum(not os.path.exists(P.aroll_path(j)) for j in P.cam_frames_needed()))


# ---------------- matte ----------------
VISION = ("person_mask", "fg_cutout", "fg_mask_dir", "faces", "gaze", "face_quality", "subject_instances", "frame_obstacles",
          "vision_boxes", "ocrfind", "speech_words", "person_extent", "matte_hq", "matte_ob", "birefnet", "matte_run")


def ane_busy():
    me = os.getpid(); why = []
    for l in subprocess.run(["ps", "-axo", "pid,pcpu,command"], capture_output=True, text=True).stdout.splitlines()[1:]:
        pid, cpu, cmd = l.split(None, 2)
        if int(pid) == me or "grep" in cmd: continue
        if "ANECompilerService" in cmd and float(cpu) > 1.0: why.append(f"ANECompilerService {cpu}%")
        if any(v in cmd for v in VISION) and "levelkit" not in cmd: why.append(cmd[:90])
    return why


def matte(P):
    """BiRefNet (matte_hq's model and alpha()) on every camera frame the cut shows. One matte job at a time (the machine-wide
    lock, yielded every 20 frames). CoreML only when the Neural Engine is idle, else OB_MATTE_DEVICE=cpu (about 6 s a frame).
    Temporal smoothing 0.35 of the previous frame, reset wherever the camera frames are not consecutive (every cut)."""
    import fcntl
    from PIL import Image
    lock = open(os.path.expanduser("~/ob-editor/.locks/matte_cpu.lock"), "w")
    print("[matte] waiting for the matte lock", flush=True); fcntl.flock(lock, fcntl.LOCK_EX)
    busy = ane_busy()
    if busy or os.environ.get("OB_MATTE_DEVICE") == "cpu": os.environ["OB_MATTE_DEVICE"] = "cpu"; print("[matte] CPU", busy, flush=True)
    else: print("[matte] Neural Engine idle: CoreML", flush=True)
    import matte_hq
    sess = matte_hq.session(); print("[matte] providers", sess.get_providers(), flush=True)
    os.makedirs(os.path.join(P.work, "matte"), exist_ok=True)
    js = P.cam_frames_needed(); prev, last = None, None; t = time.time(); done = 0
    for j in js:
        if last is None or j != last + 1: prev = None
        last = j; dst = P.matte_path(j)
        if os.path.exists(dst):
            prev = np.asarray(Image.open(dst), np.float32) / 255.0; continue
        a = matte_hq.alpha(sess, Image.open(P.aroll_path(j)).convert("RGB"))
        if prev is not None: a = 0.65 * a + 0.35 * prev
        prev = a; Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).save(dst + ".part.png"); os.replace(dst + ".part.png", dst)
        done += 1
        if done % 20 == 0: fcntl.flock(lock, fcntl.LOCK_UN); time.sleep(1.5); fcntl.flock(lock, fcntl.LOCK_EX)
        if done % 25 == 0: print(f"[matte] {done} new, {(time.time() - t) / done:.2f} s/frame, at cam frame {j}", flush=True)
    print(f"[matte] done {done} new frames in {time.time() - t:.0f} s", flush=True)


# ---------------- cells ----------------
def cells(P, only=()):
    """plan.cells = {NAME: {src, in, dur, speed=1, lut=true, cx=0.5, cy=0.5, zoom=1}}: 9:16 crops at 720x1280, 29.97 fps JPEGs.
    cx/cy place the crop centre in the source (fractions), zoom > 1 crops tighter. Stock is graded with his LUT too (one look)."""
    for name, c in P.p["cells"].items():
        if only and name not in only: continue
        out = os.path.join(P.work, "cells", name); os.makedirs(out, exist_ok=True)
        if len(os.listdir(out)) > 10 and not only: continue
        for f in os.listdir(out): os.remove(os.path.join(out, f))
        sp = c.get("speed", 1.0); cx, cy, z = c.get("cx", 0.5), c.get("cy", 0.5), c.get("zoom", 1.0)
        crop = (f"crop='min(iw,ih*9/16)/{z}':'min(ih,iw*16/9)/{z}':'(iw-min(iw,ih*9/16)/{z})*{cx}':'(ih-min(ih,iw*16/9)/{z})*{cy}',"
                "scale=720:1280:flags=lanczos")
        vf = (f"setpts={1 / sp}*PTS," if sp != 1.0 else "") + "fps=30000/1001," + crop
        n = int(round(c["dur"] * P.fps)); src = os.path.expanduser(c["src"])
        if c.get("lut", True):
            ff("-ss", str(c["in"]), "-i", src, "-i", P.lut, "-filter_complex", f"[0:v]{vf}[v];[v][1:v]haldclut,format=yuvj420p", "-frames:v", str(n), "-q:v", "3", f"{out}/c_%04d.jpg")
        else:
            ff("-ss", str(c["in"]), "-i", src, "-vf", vf + ",format=yuvj420p", "-frames:v", str(n), "-q:v", "3", f"{out}/c_%04d.jpg")
        print(name, n, len(os.listdir(out)), flush=True)


# ---------------- audio ----------------
def rms100(x):
    w = int(0.1 * SR); return max(np.sqrt(np.mean(x[i:i + w] ** 2) + 1e-12) for i in range(0, max(1, len(x) - w + 1), w // 4))


def audio(P):
    """His mic pieces, mastered by voice_master.py exactly like his renders (per-line ride, -14 LUFS, gentle limiter), placed on
    the edit clock with 6 ms edge fades, plus plan.sfx: [{file, cue, off, db, why, hp}] each aligned on its own peak, db = its
    loudest 100 ms vs his speech level (18-25 dB under). Nothing in the first 0.5 s. Mono master, written as dual-mono stereo."""
    from scipy.io import wavfile
    from scipy.signal import butter, sosfilt
    work = os.path.join(P.work, "audio"); os.makedirs(work, exist_ok=True)
    segs, lines, order = [], {}, []
    for e, a, b, lid in P.pieces:
        segs.append(mono(P.mic, a, b - a)); lines.setdefault(lid, []).append([a, b])
        if lid not in order: order.append(lid)
    wavfile.write(os.path.join(work, "voice_cat.wav"), SR, np.concatenate(segs).astype(np.float32))
    json.dump({"lines": [{"id": l, "pieces": lines[l]} for l in order]}, open(os.path.join(work, "lines.json"), "w"))
    r = subprocess.run([sys.executable, "-I", os.path.join(BIN, "voice_master.py"), "master", os.path.join(work, "voice_cat.wav"),
                        os.path.join(work, "voice_master.wav"), "--lines", os.path.join(work, "lines.json")], capture_output=True, text=True)
    print("voice_master:", r.stdout.strip()[-500:], r.stderr.strip()[-300:])
    vm = mono(os.path.join(work, "voice_master.wav"))
    out = np.zeros(int(P.end * SR) + SR // 10); pos = 0
    for (e, a, b, lid), x in zip(P.pieces, segs):
        n = len(x); y = vm[pos:pos + n].copy(); pos += n
        f = int(0.006 * SR); ramp = np.linspace(0, 1, f); y[:f] *= ramp; y[-f:] *= ramp[::-1]
        i0 = int(round(e * SR)); out[i0:i0 + n] += y[:len(out) - i0]
    voice = out.copy(); w = int(0.1 * SR)
    lv = np.array([np.sqrt(np.mean(voice[i:i + w] ** 2) + 1e-12) for i in range(0, len(voice) - w, w // 2)])
    speech = np.median(lv[lv > 10 ** (-40 / 20)]); print(f"speech level {20 * np.log10(speech):.1f} dBFS")
    plan = []
    for s_ in P.p.get("sfx", []):
        path = os.path.join(ASSETS, s_["file"]); s = mono(path); t = P.resolve(s_["cue"]) + s_.get("off", 0.0)
        hp = s_.get("hp", 35 if "sub_drop" in s_["file"] else 0)
        if hp:   # M55: sub drops are mostly infrasound; two high-pass stages, then a 1.2 s hold and a 0.5 s fade
            sos = butter(2, hp, "highpass", fs=SR, output="sos"); s = sosfilt(sos, sosfilt(sos, s))
            if "sub_drop" in s_["file"]: s = s[:int(1.7 * SR)] * np.concatenate([np.ones(int(1.2 * SR)), np.linspace(1, 0, int(1.7 * SR) - int(1.2 * SR))])
        pk = int(np.argmax(np.abs(s))); g = speech * 10 ** (s_["db"] / 20) / rms100(s); i0 = int(round(t * SR)) - pk
        if i0 < int(0.5 * SR): raise SystemExit(f"SFX in the first 0.5 s: {s_.get('why')}")
        seg = s * g; out[i0:i0 + len(seg)] += seg[:max(0, len(out) - i0)]
        plan.append({"t_peak": round(t, 3), "start": round(i0 / SR, 3), "file": s_["file"], "db_vs_speech": s_["db"], "why": s_.get("why", "")})
    out = out[:int(round(P.n / P.fps * SR))]
    st = np.stack([out, out], 1)
    mu = P.p.get("music")
    if mu:                                                     # the bed: music_mix.bed's levels (rel_db under his voice, ducked
        import music_mix                                       # duck_db while he speaks), then dead cuts under the punch line
        b = music_mix.bed(os.path.expanduser(mu["track"]), mu.get("start", 0.0), voice[:len(out)], SR, mu.get("rel_db", -16.0), mu.get("duck_db", 5.0))
        for c0, c1 in mu.get("cuts", []):                      # cut dead on the punch line, back on the next sentence (10 ms ramps, no click)
            i0, i1 = int(P.resolve(c0) * SR), int(P.resolve(c1) * SR); r = int(0.01 * SR)
            b[i0:i1] = 0; b[i0 - r:i0] *= np.linspace(1, 0, r)[:, None]; b[i1:i1 + r] *= np.linspace(0, 1, r)[:, None]
        st = st + b[:len(st)]
        print(f"music: {os.path.basename(mu['track'])} from {mu.get('start', 0.0)} s, {mu.get('rel_db', -16.0)} dB under his voice, ducked {mu.get('duck_db', 5.0)} dB, cuts {mu.get('cuts', [])}")
    peak = np.abs(st).max(); print(f"mix peak {20 * np.log10(peak):.2f} dBFS")
    if peak > 10 ** (-1.0 / 20): st *= 10 ** (-1.0 / 20) / peak; print("trimmed to -1 dBFS peak")
    p_mix = os.path.join(work, "mix.wav"); wavfile.write(p_mix, SR, st.astype(np.float32))
    tp = true_peak(p_mix)                                      # the gate FAILs over -1 dBTP: keep 0.5 dB of room
    if tp > -1.5: st *= 10 ** ((-1.5 - tp) / 20); wavfile.write(p_mix, SR, st.astype(np.float32)); print(f"true peak {tp:.2f} -> -1.5 dBTP")
    json.dump(plan, open(os.path.join(P.dir, "sfx_placed.json"), "w"), indent=1)
    ev = len({round(p["t_peak"]) for p in plan}); print(f"SFX: {len(plan)} hits, ~{ev} events, {ev / (P.end / 60):.1f} events/min")
    sfx_rules(plan)


def true_peak(path):
    r = subprocess.run(["ffmpeg", "-nostdin", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
    try: return float(r[r.rfind("Peak:"):].split()[1])
    except Exception: return 0.0


def sfx_rules(plan, max_same=3):
    """OB 11-06: vary the sound design. No single file more than 3 times, never one family on every hit, and no Kenney ticks
    (sfx_real/tick_*: the sound he hated on A/E, where it was 9-11 of 20-26 hits). Prints the count per file and family."""
    import collections
    fam = lambda f: os.path.basename(f).split(".")[0].rstrip("0123456789_-").replace("camera-", "").replace("mouse-", "")
    files = collections.Counter(p["file"] for p in plan); fams = collections.Counter(fam(p["file"]) for p in plan)
    bad = [f"{f} x{n}" for f, n in files.items() if n > max_same] + [f for f in files if f.startswith("sfx_real/tick")]
    if len(fams) == 1 and len(plan) > 1: bad.append("one family on every hit")
    print("SFX families:", dict(fams)); print("SFX rules:", "OK" if not bad else "BROKEN " + ", ".join(bad))
    return not bad


# ---------------- render / encode / review / gate ----------------
def render(P, k0=0, k1=None):
    from multiprocessing import Pool
    from levelkit import engine
    od = os.path.join(P.work, "out"); os.makedirs(od, exist_ok=True); k1 = P.n if k1 is None else k1
    todo = [k for k in range(k0, k1) if not os.path.exists(f"{od}/f_{k:05d}.png")]
    wait = [k for k in todo if not os.path.exists(P.matte_path(P.cam_frame(k)))]   # never render a frame before its own matte exists
    if wait: print(f"{len(wait)} frames wait for their matte (first {wait[0]}): skipped"); todo = [k for k in todo if k not in set(wait)]
    slots()
    with Pool(int(os.environ.get("COMP_WORKERS", "8")), initializer=engine.init, initargs=(P.path,)) as pool:
        for i, k in enumerate(pool.imap_unordered(engine.job, todo, chunksize=4)):
            if i % 100 == 0: print(f"{i}/{len(todo)}", flush=True)
    print("rendered", len(todo))


def encode(P):
    slots()
    ff("-framerate", "30000/1001", "-i", os.path.join(P.work, "out", "f_%05d.png"), "-i", os.path.join(P.work, "audio", "mix.wav"),
       "-frames:v", str(P.n), "-c:v", "libx264", "-preset", "slow", "-crf", os.environ.get("CRF", "17"), "-profile:v", "high", "-pix_fmt", "yuv420p",
       "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-r", "30000/1001", "-c:a", "aac", "-b:a", "256k", "-ar", "48000",
       "-movflags", "+faststart", "-shortest", os.path.expanduser(P.p["final"]))
    print(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration,size,bit_rate:stream=codec_name,width,height,r_frame_rate,sample_rate",
                          "-of", "compact", os.path.expanduser(P.p["final"])], capture_output=True, text=True).stdout)


def review(P, per_row=8, rows=2):
    from PIL import Image, ImageDraw
    rd = os.path.join(P.work, "review"); os.makedirs(rd, exist_ok=True)
    for f in os.listdir(rd): os.remove(os.path.join(rd, f))
    ff("-i", os.path.expanduser(P.p["final"]), "-vf", "fps=2", f"{rd}/r_%03d.png")
    fs = sorted(f for f in os.listdir(rd) if f.startswith("r_")); W, H = 190, 338; per = per_row * rows; sheets = []
    for s0 in range(0, len(fs), per):
        sub = fs[s0:s0 + per]; sh = Image.new("RGB", (per_row * W, rows * (H + 16)), (0, 0, 0)); d = ImageDraw.Draw(sh)
        for i, f in enumerate(sub):
            x, y = (i % per_row) * W, (i // per_row) * (H + 16)
            sh.paste(Image.open(f"{rd}/{f}").convert("RGB").resize((W, H)), (x, y)); d.text((x + 3, y + H + 2), f"{(int(f[2:5]) - 1) * 0.5 + 0.25:.2f}", fill=(255, 212, 0))
        p = os.path.join(P.work, f"review_{s0 // per:02d}.jpg"); sh.save(p, quality=86); sheets.append(p)
    for flt in ("blackdetect=d=0.1:pix_th=0.10", "freezedetect=n=0.003:d=1.2"):
        r = subprocess.run(["ffmpeg", "-nostdin", "-v", "info", "-i", os.path.expanduser(P.p["final"]), "-vf", flt, "-an", "-f", "null", "-"], capture_output=True, text=True)
        hits = [l for l in r.stderr.splitlines() if "black_start" in l or "freeze_start" in l]
        print(flt.split("=")[0], "hits:", len(hits), hits[:6])
    print("\n".join(sheets))


def gate(P):
    import qc_gate
    out = os.path.expanduser(P.p["final"])
    segs = [(P.mic, a, b, e) for e, a, b, _ in P.pieces]; cam = [(P.cam, a, b, e) for e, a, b, _ in P.pieces]
    script = os.path.join(P.dir, "script_words.txt")
    open(script, "w").write(" ".join(w["w"] for w in P.words()) + "\n")
    ok = qc_gate.after_render(out, segs=segs, script=script, cam=cam)
    print("GATE", "PASS" if ok else "NOT PASS", qc_gate.report_path(out))


def stills(P, ts):
    from levelkit import engine
    engine.init(P.path); od = os.path.join(P.work, "stills"); os.makedirs(od, exist_ok=True)
    for t in ts:
        k = int(round(float(t) * P.fps)); p = f"{od}/t_{float(t):06.2f}.jpg"; engine.render(k).convert("RGB").save(p, quality=88); print(p)


def main(argv):
    if len(argv) < 2: print(__doc__); return
    cmd, plan = argv[0], argv[1]; P = Plan(plan); rest = argv[2:]
    if cmd == "recut": recut(P, int(rest[rest.index("--lock") + 1]) if "--lock" in rest else 0)
    elif cmd == "verify": verify(P, int(rest[rest.index("--lock") + 1]) if "--lock" in rest else 0)
    elif cmd == "aroll": aroll(P)
    elif cmd == "matte": matte(P)
    elif cmd == "cells": cells(P, rest)
    elif cmd == "audio": audio(P)
    elif cmd == "render": render(P, *(int(x) for x in rest[:2]))
    elif cmd == "encode": encode(P)
    elif cmd == "review": review(P)
    elif cmd == "gate": gate(P)
    elif cmd == "stills": stills(P, rest)
    else: print(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
