#!/usr/bin/env python3
"""Trial-reel versions of a posted reaction reel, in one tool (OB 2026-10-20 picked this upgrade: "the trial-version builder").

It replaces the three one-offs of 10-20 (1006 apple pie make_variants.py, 0719 brookie make_brookie.py, 1230 supermodels
make_models.py). Every version = a new intro made of creator clips, opened in a box over the posted reel's own watching frames
(box) or full screen first and then sprung into that box (zoom), then the posted reel unchanged from the join. No raw footage
needed. (Versions that need new spoken lines from raw takes, like the apple pie L1-L3, stay in make_variants.py.)

  trial_variants.py probe POSTED.mp4 [--out DIR]   finds the box, the box phase, the cuts and the join -> probe.json + probe.jpg
  trial_variants.py clips SPEC.json                every source clip: speaker segments (on-screen name labels), the follow card,
                                                   transcript, songs and audio problems -> clips.json + clips_<key>.jpg
  trial_variants.py render SPEC.json [ID ...]      renders (default: all), one at a time, after other sessions' renders finish
  trial_variants.py qc SPEC.json [ID ...]          streams, loudness, true peak, quiet runs, black/frozen frames, frames at every
                                                   cut, VMAF of the unchanged tail vs the posted reel, transcripts across each cut
  trial_variants.py page SPEC.json OUTDIR          full-length 720p previews + index.html; prints publish batches (<= 60 MB each)
  trial_variants.py deliver SPEC.json              copies every version to the iCloud folder named in the spec, byte-checked

SPEC.json (relative paths are relative to the spec's folder; times are in seconds of each file):
  {"prefix": "MT", "title": "Supermodel Trial Reels", "kicker": "1230 · supermodels on muscle", "note": "page paragraph",
   "posted": "/Volumes/T7/1230 (3)(1).mp4", "out": "..", "tag": "@yuli.longevity", "icloud": "OB-READY ... (Oct 20)",
   "box": [220, 782, 640, 1138],      the new box: probe's new_box (the posted box + 4 px a side, so the old clip never shows)
   "box_frames": 96 | "all",          frames the intro sits in the box ("all" = until the join, the 0719 brookie layout)
   "bg_start": 0 | "join",            posted frame the box background starts on ("join" = the frames just before the join)
   "join": 824,                       posted frame where the reel continues unchanged
   "zoom_full": 1.1, "seg_lufs": -14.0, "max_gain": 6.0, "silent_below": -40.0, "silent_fill": null | seconds in posted,
   "fade_in": 0.008, "cut_fade": 0.008, "end_fade": 0.008, "join_fade": 0.005,
   "sources": {"A": "creators/a.mp4"},
   "segments": {"A.cand": {"src": "A", "t0": 0.0, "t1": 5.5667, "who": "Candice", "ashift": 0.0}},
   "variants": [{"key": "IR", "name": "Irina first", "segs": ["A.irin", "A.cand"], "layouts": "ZB", "opens": "Irina: ..."}]}
"""
import argparse, difflib, functools, html, json, math, os, re, shutil, subprocess, sys, tempfile, time
from fractions import Fraction
import numpy as np
from PIL import Image, ImageDraw, ImageFont

BIN = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, BIN)
SR = 48000
FONT = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 18)
# 4x oversampled limiter at -2 dBFS: a plain -1 dBFS alimiter left +1.1 dBFS true peak after AAC on the 1230 set (10-20)
LIMIT = "aresample=192000,alimiter=limit=0.794:attack=1:release=50:level=false,aresample=48000"
BUSY = (r"assemble\.py|react_render\.py|lecture_render\.py|tier_render\.py|render_clip\.py|hyperframes render|"
        r"make_models\.py|make_brookie\.py|make_variants\.py|trial_variants\.py render")
WHISPER_MED = os.path.expanduser("~/.whisper-models/ggml-medium.en.bin"); WHISPER_BASE = os.path.expanduser("~/.whisper-models/ggml-base.en.bin")


def run(cmd, **kw): return subprocess.run(cmd, capture_output=True, check=True, **kw)


@functools.lru_cache(None)
def info(path):
    d = json.loads(run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height,r_frame_rate:format=duration",
                        "-of", "json", path], text=True).stdout)
    v = next(s for s in d["streams"] if s["codec_type"] == "video")
    return dict(w=int(v["width"]), h=int(v["height"]), fps=Fraction(v["r_frame_rate"]), dur=float(d["format"]["duration"]),
                audio=any(s["codec_type"] == "audio" for s in d["streams"]))


def frames(path, t0, n, fps, w, h):
    """n frames from t0 at fps, scaled to fill w x h. Same-fps sources are cut by frame number (exact), others resampled."""
    sf = info(path)["fps"]
    if sf == fps: f0 = int(round(t0 * sf)); pre = []; vf = f"trim=start_frame={f0}:end_frame={f0 + n},setpts=PTS-STARTPTS,"
    else: pre = ["-ss", f"{t0:.4f}"]; vf = f"fps={fps},"
    vf += f"scale={w}:{h}:force_original_aspect_ratio=increase:flags=lanczos,crop={w}:{h},setsar=1"
    raw = run(["ffmpeg", "-nostdin", "-loglevel", "error"] + pre + ["-i", path, "-vf", vf, "-frames:v", str(n), "-f", "rawvideo",
               "-pix_fmt", "rgb24", "-"]).stdout
    a = np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3)
    if len(a) < n: a = np.concatenate([a, np.repeat(a[-1:], n - len(a), 0)])      # clip ran out: held frame, qc flags the freeze
    return a


def frame_at(path, t, w=None, h=None):
    vf = ["-vf", f"scale={w}:{h}"] if w else []
    i = info(path); w, h = w or i["w"], h or i["h"]
    raw = run(["ffmpeg", "-nostdin", "-loglevel", "error", "-ss", f"{t:.4f}", "-i", path, "-frames:v", "1"] + vf +
              ["-f", "rawvideo", "-pix_fmt", "rgb24", "-"]).stdout
    return np.frombuffer(raw, np.uint8).reshape(h, w, 3) if len(raw) == w * h * 3 else None


def audio(path, t, dur=None):
    cmd = ["ffmpeg", "-nostdin", "-loglevel", "error", "-ss", f"{t:.4f}"] + (["-t", f"{dur:.4f}"] if dur else []) + \
          ["-i", path, "-vn", "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"]
    x = np.frombuffer(run(cmd).stdout, np.float32).reshape(-1, 2).astype(np.float64)
    if dur: n = int(round(dur * SR)); x = np.pad(x, ((0, max(0, n - len(x))), (0, 0)))[:n]
    return x


def lufs(x):
    p = subprocess.run(["ffmpeg", "-nostdin", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", "-af", "ebur128", "-f", "null", "-"],
                       input=x.astype(np.float32).tobytes(), capture_output=True)
    s = p.stderr.decode(); i = s.rfind("I:")
    return float(s[i:].split()[1]) if i >= 0 else -70.0


def fade(x, a_in, a_out):
    if a_in: g = int(a_in * SR); x[:g] *= np.linspace(0, 1, g)[:, None]
    if a_out: g = int(a_out * SR); x[-g:] *= np.linspace(1, 0, g)[:, None]
    return x


def env_db(path, t0=0.0, dur=None, hop=160, sr=16000):
    """10 ms RMS level in dB of the mono mix (for pauses, onsets and silence)."""
    cmd = ["ffmpeg", "-nostdin", "-loglevel", "error", "-ss", f"{t0:.4f}"] + (["-t", f"{dur:.4f}"] if dur else []) + \
          ["-i", path, "-vn", "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"]
    x = np.frombuffer(run(cmd).stdout, np.float32)
    n = len(x) // hop
    return 20 * np.log10(np.sqrt((x[:n * hop].reshape(n, hop).astype(np.float64) ** 2).mean(1)) + 1e-9)


def spring(t, k=260.0, c=22.0):                 # SNAP (cards.py); clamped at 1 by the caller, so the box never shrinks past BOX
    w0 = math.sqrt(k); z = c / (2 * w0); wd = w0 * math.sqrt(1 - z * z)
    return 1 - math.exp(-z * w0 * t) * (math.cos(wd * t) + (z * w0 / wd) * math.sin(wd * t))


def scene_cuts(path, thr=0.25, crop=None):
    vf = (f"crop={crop}," if crop else "") + f"select='gt(scene,{thr})',showinfo"
    err = subprocess.run(["ffmpeg", "-nostdin", "-i", path, "-an", "-vf", vf, "-f", "null", "-"], capture_output=True, text=True).stderr
    return [float(x) for x in re.findall(r"pts_time:([0-9.]+)", err)]


def wait_free():
    """One render at a time on this Mac, across sessions (two at once crashed the app on 10-16)."""
    me = set(); p = os.getpid()
    while p > 1:
        me.add(p); out = subprocess.run(["ps", "-o", "ppid=", "-p", str(p)], capture_output=True, text=True).stdout.strip()
        p = int(out) if out else 1
    said = False
    while True:
        pids = [int(x) for x in subprocess.run(["pgrep", "-f", BUSY], capture_output=True, text=True).stdout.split()]
        others = [x for x in pids if x not in me]
        if not others: return
        if not said: print(f"waiting for another render to finish (pids {others})", flush=True); said = True
        time.sleep(30)


# ---------------------------------------------------------------------------------------------------------------- spec
def load(path):
    S = json.load(open(path)); base = os.path.dirname(os.path.abspath(path))
    ab = lambda p: p if os.path.isabs(p) else os.path.normpath(os.path.join(base, p))
    S["_spec"] = os.path.abspath(path); S["_base"] = base
    S["posted"] = ab(S["posted"]); S["out"] = ab(S.get("out", "..")); S["sources"] = {k: ab(v) for k, v in S["sources"].items()}
    P = info(S["posted"]); S["_fps"], S["_w"], S["_h"] = P["fps"], P["w"], P["h"]
    for k, v in dict(zoom_full=1.1, seg_lufs=-14.0, max_gain=6.0, silent_below=-40.0, silent_fill=None, fade_in=0.008, cut_fade=0.008,
                     end_fade=0.008, join_fade=0.005, bg_start=0, prefix="TV", title="Trial Reels", kicker="", note="", tag="").items():
        S.setdefault(k, v)
    S["_variants"] = []
    for v in S["variants"]:
        for m in v.get("layouts", "ZB"):
            S["_variants"].append(dict(id=f"{m}-{v['key']}", mode=m, key=v["key"], segs=v["segs"], opens=v.get("opens", ""),
                                       name=f"{'zoom out' if m == 'Z' else 'box'}, {v['name']}"))
    return S


def seg(S, key):
    d = dict(S["segments"][key]); src = S["sources"][d["src"]]; fps = S["_fps"]
    if "f0" in d: sf = info(src)["fps"]; d["t0"] = d["f0"] / sf; d["t1"] = d["f1"] / sf
    d["n"] = int(round((d["t1"] - d["t0"]) * fps)); d["path"] = src; d["key"] = key
    return d


def out_path(S, v): return f"{S['out']}/{S['prefix']}-{v['id']} {v['name']}.mp4"


def layout(S, segs):
    total = sum(s["n"] for s in segs)
    nb = total if S["box_frames"] == "all" else int(S["box_frames"])
    bg0 = int(S["join"]) - nb if S["bg_start"] == "join" else int(S["bg_start"])
    return total, nb, bg0


# -------------------------------------------------------------------------------------------------------------- render
def render(S, v):
    fps = S["_fps"]; W, H = S["_w"], S["_h"]; FULL = (0, 0, W, H); BOX = tuple(S["box"])
    os.makedirs(f"{S['out']}/_work/tmp", exist_ok=True); tag = f"{S['out']}/_work/tmp/{v['id']}"; out = out_path(S, v)
    segs = [seg(S, k) for k in v["segs"]]; total, nb, bg0 = layout(S, segs)
    # 1. the box phase: the first nb frames of the clips over the posted reel's own frames from bg0
    bg = frames(S["posted"], bg0 / fps, nb, fps, W, H)
    cf, need = [], nb
    for s in segs:
        if need <= 0: break
        k = min(need, s["n"]); cf.append(frames(s["path"], s["t0"], k, fps, W, H)); need -= k
    cf = np.concatenate(cf)
    enc = subprocess.Popen(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(fps), "-i", "-", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "6", "-pix_fmt", "yuv420p",
                            f"{tag}_intro.mp4"], stdin=subprocess.PIPE)
    zf = float(S["zoom_full"])
    for i in range(nb):
        t = i / fps
        if v["mode"] == "Z" and t < zf: rect = FULL
        elif v["mode"] == "Z": p = min(1.0, spring(t - zf)); rect = tuple(a + (b - a) * p for a, b in zip(FULL, BOX))
        else: rect = BOX
        if rect == FULL: im = Image.fromarray(cf[i])
        else:
            im = Image.fromarray(bg[i]); x, y, w, h = (int(round(q)) for q in rect)
            im.paste(Image.fromarray(cf[i]).resize((w, h), Image.LANCZOS), (x, y))
        enc.stdin.write(np.asarray(im, np.uint8).tobytes())
    enc.stdin.close(); enc.wait(); del bg, cf
    # 2. audio: each clip at seg_lufs (boost capped), near-silent clips get silent_fill, short fades at every cut, then the posted reel
    parts, notes = [], []
    for j, s in enumerate(segs):
        dur = s["n"] / fps; a = audio(s["path"], s["t0"] + s.get("ashift", 0.0), dur); L = lufs(a); g = min(S["max_gain"], S["seg_lufs"] - L)
        if L + g < S["silent_below"] and S["silent_fill"] is not None:
            a = audio(S["posted"], float(S["silent_fill"]), dur); L = lufs(a); g = min(S["max_gain"], S["seg_lufs"] - L); notes.append(f"{s['key']}: posted sound")
        a *= 10 ** (g / 20)
        parts.append(fade(a, S["fade_in"] if j == 0 else S["cut_fade"], S["end_fade"] if j == len(segs) - 1 else S["cut_fade"]))
    parts.append(fade(audio(S["posted"], int(S["join"]) / fps), S["join_fade"], 0))
    np.concatenate(parts).astype(np.float32).tofile(f"{tag}.f32")
    run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", f"{tag}.f32", f"{tag}.wav"])
    # 3. picture: the intro, the rest of the clips full screen, then the posted reel from the join
    pieces, left = [], nb
    for s in segs:
        if left >= s["n"]: left -= s["n"]; continue
        pieces.append((s["path"], s["t0"] + left / fps, s["n"] - left)); left = 0
    ins = ["-i", f"{tag}_intro.mp4"]; fc = "[0:v]setpts=PTS-STARTPTS,format=yuv420p,setsar=1[v0];"
    for k, (path, t0, n) in enumerate(pieces, 1):
        if info(path)["fps"] == fps:
            f0 = int(round(t0 * fps)); ins += ["-i", path]; tr = f"trim=start_frame={f0}:end_frame={f0 + n},setpts=PTS-STARTPTS"
        else: ins += ["-ss", f"{t0:.4f}", "-t", f"{n / fps + 1:.4f}", "-i", path]; tr = f"setpts=PTS-STARTPTS,fps={fps},trim=end_frame={n}"
        fc += f"[{k}:v]{tr},scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H},setsar=1,format=yuv420p[v{k}];"
    nbk = len(pieces) + 1; ins += ["-i", S["posted"], "-i", f"{tag}.wav"]
    fc += f"[{nbk}:v]trim=start_frame={int(S['join'])},setpts=PTS-STARTPTS,format=yuv420p,setsar=1[v{nbk}];"
    fc += "".join(f"[v{k}]" for k in range(nbk + 1)) + f"concat=n={nbk + 1}:v=1:a=0[v];[{nbk + 1}:a]{LIMIT}[a]"
    run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y"] + ins + ["-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-c:v", "libx264",
         "-preset", "fast", "-crf", "16", "-pix_fmt", "yuv420p", "-r", str(fps), "-c:a", "aac_at", "-b:a", "256k", "-movflags", "+faststart", out])
    print("done", os.path.basename(out), *(["(" + "; ".join(notes) + ")"] if notes else []), flush=True)


# ------------------------------------------------------------------------------------------------------------------ qc
def qc(S, want, asr=True):
    import vmaf_check
    Q = f"{S['out']}/_work/qc"; os.makedirs(Q, exist_ok=True); fps = float(S["_fps"]); rep, rows = [], []
    for v in S["_variants"]:
        if want and v["id"] not in want: continue
        f = out_path(S, v)
        if not os.path.exists(f): rep.append(f"{v['id']:6s} MISSING"); continue
        segs = [seg(S, k) for k in v["segs"]]; total, nb, _ = layout(S, segs)
        cuts, t = [], 0
        for s in segs: t += s["n"]; cuts.append(round(t / fps, 3))
        join = cuts[-1]; cuts = cuts[:-1]
        i = info(f); loud = subprocess.run(["ffmpeg", "-nostdin", "-i", f, "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"],
                                         capture_output=True, text=True).stderr
        I = float(loud[loud.rfind("I:"):].split()[1]); pk = float(loud[loud.rfind("Peak:"):].split()[1])
        e = env_db(f, 0, join + 1.5); runs, cur = [], None
        for k, q in enumerate(list(e < -40) + [False]):
            if q and cur is None: cur = k
            elif not q and cur is not None:
                if k - cur >= 30: runs.append((round(cur / 100, 2), round((k - cur) / 100, 2)))
                cur = None
        bf = subprocess.run(["ffmpeg", "-nostdin", "-t", f"{join + 1:.2f}", "-i", f, "-an", "-vf",
                             "freezedetect=n=0.002:d=0.4,blackdetect=d=0.1:pix_th=0.05", "-f", "null", "-"], capture_output=True, text=True).stderr
        dead = re.findall(r"(freeze_start|black_start): ?([0-9.]+)", bf)
        vm = vmaf_check.score(S["posted"], f, ref_start=int(S["join"]) / fps, dist_start=total / fps, sub=3)   # exact, not the rounded join
        line = (f"{v['id']:6s} {i['w']}x{i['h']} {float(i['fps']):.3f} fps {i['dur']:.2f} s | {I:.1f} LUFS, true peak {pk:+.1f} dBFS | "
                f"cuts {cuts} join {join} | quiet>=0.3 s {runs or 'none'} | black/frozen {dead or 'none'} | "
                f"tail VMAF {vm['mean']} (1%-low {vm['p1']})")
        if asr:
            words = []
            for c in cuts + [join]:
                tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
                run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-ss", f"{max(0, c - 1.4):.3f}", "-t", "2.8", "-i", f, "-vn", "-ac", "1",
                     "-ar", "16000", tmp])
                txt = subprocess.run(["whisper-cli", "-m", WHISPER_BASE, "-f", tmp, "-nt"], capture_output=True, text=True).stdout
                os.unlink(tmp); words.append(f"  {c:7.3f} | " + " ".join(txt.split()))
            line += "\n" + "\n".join(words)
        rep.append(line)
        zf = float(S["zoom_full"]); be = nb / fps
        ts = sorted(set([0.03, 0.6] + ([zf, zf + 0.2] if v["mode"] == "Z" else []) + [min(1.6, be - 0.1), be - 0.1, be + 0.15] +
                        [x for c in cuts for x in (c - 0.1, c + 0.1)] + [join - 0.1, join + 0.1, join + 3.0]))
        ts = [round(x, 2) for x in ts if 0 <= x < i["dur"]]; tw, th = 120, 213
        r = Image.new("RGB", (len(ts) * (tw + 3) + 84, th + 26), (18, 18, 16)); d = ImageDraw.Draw(r); d.text((6, 6), v["id"], fill=(247, 220, 58), font=FONT)
        for k, x in enumerate(ts):
            fr = frame_at(f, x, tw, th)
            if fr is not None: r.paste(Image.fromarray(fr), (84 + k * (tw + 3), 24))
            d.text((84 + k * (tw + 3) + 3, 2), f"{x:.2f}", fill=(255, 255, 255), font=FONT)
        r.save(f"{Q}/{v['id']}.jpg", quality=86); rows.append(r)
    if rows and not want:
        sheet = Image.new("RGB", (max(x.width for x in rows), sum(x.height for x in rows)), (0, 0, 0)); y = 0
        for r in rows: sheet.paste(r, (0, y)); y += r.height
        sheet.save(f"{Q}/_all.jpg", quality=84)
    open(f"{Q}/report.txt", "a" if want else "w").write("\n".join(rep) + "\n"); print("\n".join(rep))


# ---------------------------------------------------------------------------------------------------------------- page
def page(S, P):
    os.makedirs(P, exist_ok=True); esc = lambda s: html.escape(s, quote=True); cards, sizes = [], []
    for v in S["_variants"]:
        f = out_path(S, v)
        if not os.path.exists(f): continue
        pv, po = f"{P}/v_{v['id']}.mp4", f"{P}/p_{v['id']}.jpg"
        run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", f, "-vf", "scale=720:1280:flags=lanczos", "-c:v", "libx264", "-preset", "medium",
             "-b:v", "1300k", "-maxrate", "1800k", "-bufsize", "2600k", "-pix_fmt", "yuv420p", "-c:a", "aac_at", "-b:a", "96k", "-movflags", "+faststart", pv])
        run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-ss", "0.6", "-i", pv, "-frames:v", "1", "-q:v", "4", po])
        sizes.append((os.path.basename(pv), os.path.getsize(pv) + os.path.getsize(po), os.path.basename(po)))
        who = " &rarr; ".join(esc(S["segments"][k].get("who", k)) for k in v["segs"])
        cards.append(f"<figure class='vid'><video controls playsinline preload='none' poster='p_{v['id']}.jpg' src='v_{v['id']}.mp4'></video>"
                     f"<figcaption><b>{v['id']}</b> <span class='kind'>{'Zoom out' if v['mode'] == 'Z' else 'Box'}</span>"
                     + (f"<br>Opens on {v['opens']}" if v["opens"] else "") + f"<br><span class='cred'>{who} &rarr; you</span></figcaption></figure>")
    icloud = esc(S.get("icloud", ""))
    page_html = f"""<title>{esc(S['title'])}</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>
:root {{ --bg:#f4f2ef; --card:#ffffff; --ink:#1c1a18; --muted:#69635d; --line:#e3ded7; --accent:#9a4a26; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --bg:#141211; --card:#1e1c1a; --ink:#eee9e3; --muted:#a49b92; --line:#302c28; --accent:#de8a5e; color-scheme:dark }} }}
:root[data-theme="dark"] {{ --bg:#141211; --card:#1e1c1a; --ink:#eee9e3; --muted:#a49b92; --line:#302c28; --accent:#de8a5e; color-scheme:dark }}
* {{ box-sizing:border-box }}
body {{ background:var(--bg); color:var(--ink); margin:0; font:15px/1.5 -apple-system,"Segoe UI",Roboto,sans-serif;
       padding-left:max(16px,env(safe-area-inset-left,0px)); padding-right:max(16px,env(safe-area-inset-right,0px)); }}
main {{ max-width:900px; margin:0 auto; padding-block:20px 60px; display:grid; gap:22px; }}
h1 {{ font-size:30px; line-height:1.1; margin:0; text-wrap:balance }}
.kick {{ font-size:13px; letter-spacing:1px; text-transform:uppercase; color:var(--muted); }}
.note {{ color:var(--muted); margin:6px 0 0; max-width:64ch }}
.ready {{ margin:12px 0 0; padding:10px 12px; background:var(--card); border:1px solid var(--line); border-left:4px solid var(--accent); border-radius:10px; max-width:64ch }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(200px,1fr)); gap:14px }}
.vid {{ margin:0; background:var(--card); border:1px solid var(--line); border-radius:14px; overflow:hidden; display:grid; min-width:0 }}
.vid video {{ width:100%; max-width:100%; aspect-ratio:9/16; background:#000; display:block }}
.vid figcaption {{ padding:8px 10px 10px; font-size:13px }} .vid b {{ color:var(--accent); font-size:15px }}
.kind {{ font-weight:600 }} .cred {{ color:var(--muted) }}
code {{ font-family:ui-monospace,Menlo,monospace; font-size:12.5px; overflow-wrap:anywhere }}
</style>
<main>
<header><div class="kick">{esc(S['kicker'])} · {len(cards)} trial reels</div><h1>{esc(S['title'])}</h1>
<p class="note">{S['note']} <b>Zoom out</b> opens on the clip full screen, then shrinks it to show you watching. <b>Box</b> shows you watching from the first frame.{(' Tag ' + esc(S['tag']) + ' on every one.') if S['tag'] else ''}</p>
<p class="ready"><b>Ready to post, nothing to stitch.</b> Each file in iCloud Drive &ldquo;{icloud}&rdquo; is the full reel.
On your phone: Files, open one, Share, Save Video, then post it from Photos. Also on the T7 in <code>{esc(S['out'].replace('/Volumes/T7/', ''))}</code>.
These previews are lighter copies of the same full reels.</p></header>
<div class="grid">{''.join(cards)}</div>
</main>
"""
    open(f"{P}/index.html", "w").write(page_html)
    batches, cur, size = [], [], 0
    for v, s, p in sizes:
        if cur and size + s > 60e6: batches.append(cur); cur, size = [], 0
        cur += [v, p]; size += s
    if cur: batches.append(cur)
    print(f"page: {len(cards)} cards, {sum(s for _, s, _ in sizes) / 1e6:.1f} MB; publish in {len(batches)} batch(es):")
    for b in batches: print("  " + json.dumps([{"path": x} for x in b]))


def deliver(S):
    """2026-10-28: through the QC gate into a T7 AirDrop folder (OB: no iCloud; nothing that fails gets copied).
    The folder is S["airdrop"], or "AIRDROP <icloud name>" under T7/OB-EDITS."""
    sys.path.insert(0, os.path.expanduser("~/ob-editor/bin")); import deliver as DL
    D = S.get("airdrop") or f"/Volumes/T7/OB-EDITS/AIRDROP {S['icloud']}"; n = 0
    for v in S["_variants"]:
        f = out_path(S, v)
        if not os.path.exists(f): print("missing", os.path.basename(f)); continue
        n += DL.deliver(f, D)
    print(f"{n} of {len(S['_variants'])} delivered to {D} (the rest were blocked by the QC gate or missing)")


# --------------------------------------------------------------------------------------------------------------- probe
def edges(img, thr=60):
    a = img.astype(np.int16)
    return np.abs(np.diff(a, axis=1)).sum(2) > thr, np.abs(np.diff(a, axis=0)).sum(2) > thr


def find_box(imgs):
    """The reaction box: the rectangle whose borders stay put while everything inside and outside it moves."""
    H, W = imgs[0].shape[:2]; es = [edges(f) for f in imgs]
    gx = np.mean([e[0] for e in es], 0) >= 0.7; gy = np.mean([e[1] for e in es], 0) >= 0.7
    cols = gx.sum(0); cand = [int(x) for x in np.argsort(cols)[::-1] if 4 < x < W - 6 and cols[x] > 0.12 * H][:14]
    best = None
    for i in range(len(cand)):
        for j in range(i + 1, len(cand)):
            a, b = sorted((cand[i], cand[j])); w = b - a
            if w < 0.25 * W: continue
            rows = gy[:, a + 1:b + 1].sum(1)
            for y in [int(r) for r in np.argsort(rows)[::-1][:8]]:
                yb = y + w * 16 / 9
                if yb <= H - 4:
                    lo, hi = int(yb - 8), int(min(H - 2, yb + 8)); k = int(np.argmax(rows[lo:hi])) + lo; s_bot = rows[k]; h = k - y
                else: s_bot = 0.5 * w; h = H - 1 - y                     # runs off the frame bottom (1230): no edge to find
                if h < 0.4 * w: continue
                score = cols[a] / H + cols[b] / H + rows[y] / w + s_bot / w
                short = 1 - h / (w * 16 / 9)                                  # a split line inside the clip (1230's "reality:" seam)
                if short > 0.15: score -= 3 * short                          # is a strong static edge too, but gives a squat box
                if not best or score > best[0]: best = (round(score, 3), a + 1, y + 1, w, h)
    return best


def small(img, w=54, h=96): return np.asarray(Image.fromarray(img).resize((w, h), Image.BILINEAR), np.float64)


def probe(path, outdir):
    os.makedirs(outdir, exist_ok=True); i = info(path); W, H, fps = i["w"], i["h"], i["fps"]
    cuts = scene_cuts(path)
    samp = [frame_at(path, t) for t in np.linspace(1.8, 3.0, 7)]
    b = find_box([s for s in samp if s is not None])
    if not b: print("no box found: pass the box by hand"); return
    _, bx, by, bw, bh = b; touches = by + bh >= H - 2
    nw = bw + 8; nh = int(round(nw * 16 / 9)) if touches else bh + 8; ny = min(by - 4, H - nh) if touches else by - 4
    new_box = [bx - 4, ny, nw, nh]
    # box phase end: the first cut after the sample window where the box borders are gone
    def has_box(img):
        gx, gy = edges(img); return gx[by:by + bh, bx - 1].mean() > 0.35 and gx[by:by + bh, bx + bw - 1].mean() > 0.35
    end_t, mode = None, None
    for c in [c for c in cuts if c > 3.0]:
        f = frame_at(path, c + 0.1)
        if f is not None and not has_box(f):
            end_t = c
            before = frame_at(path, c - 1.5 / float(fps)); inside = before[by:by + bh, bx:bx + bw] if before is not None else None
            cont = np.abs(small(inside) - small(f)).mean() if inside is not None else 999
            mode = "full" if cont < 28 else "hold"; break
    join_t, bgdiff = None, []
    if mode == "hold": join_t = end_t
    elif mode == "full":
        ref = samp[3].copy(); mask = np.ones((H, W), bool); mask[by:by + bh, bx:bx + bw] = False
        later = [c for c in cuts if c > end_t + 0.5]
        for k, c in enumerate(later):                 # look between this cut and the next (1230 has a card click 3 frames before the join)
            f = frame_at(path, c + min(0.15, ((later[k + 1] - c) / 2) if k + 1 < len(later) else 0.15))
            if f is None: continue
            dd = float(np.abs(ref.astype(np.float64) - f)[mask].mean()); bgdiff.append((round(c, 3), round(dd, 1)))
            if dd < 30 and join_t is None: join_t = c
    onset = None
    if join_t is not None:
        e = env_db(path, join_t, 2.0); thr = max(-45.0, np.percentile(e, 95) - 30)
        above = np.nonzero(e > thr)[0]; onset = round(join_t + above[0] / 100, 3) if len(above) else None
    res = dict(file=path, size=[W, H], fps=str(fps), duration=round(i["dur"], 3), cuts=[round(c, 3) for c in cuts],
               box=[bx, by, bw, bh], box_touches_bottom=touches, new_box=new_box, box_end=end_t, mode=mode,
               box_frames=(int(round(end_t * fps)) if mode == "full" else "all") if end_t else None,
               bg_start=0 if mode == "full" else "join", join=int(round(join_t * fps)) if join_t is not None else None,
               join_s=round(join_t, 3) if join_t is not None else None, speech_onset_after_join=onset, background_match=bgdiff[:12])
    json.dump(res, open(f"{outdir}/probe.json", "w"), indent=1)
    tiles = [(2.4, "box"), (end_t - 0.05 if end_t else 3.1, "before end"), (end_t + 0.1 if end_t else 3.3, "after end")]
    if join_t: tiles += [(join_t - 0.1, "before join"), (join_t + 0.1, "after join")]
    sh_ = Image.new("RGB", (len(tiles) * 274, 520), (18, 18, 16)); d = ImageDraw.Draw(sh_)
    for k, (t, lab) in enumerate(tiles):
        f = frame_at(path, t)
        if f is None: continue
        im = Image.fromarray(f); dr = ImageDraw.Draw(im)
        if lab == "box": dr.rectangle([bx, by, bx + bw - 1, by + bh - 1], outline=(255, 40, 40), width=6); dr.rectangle([new_box[0], new_box[1], new_box[0] + nw - 1, new_box[1] + nh - 1], outline=(40, 255, 40), width=3)
        sh_.paste(im.resize((270, 480)), (k * 274, 36)); d.text((k * 274 + 4, 6), f"{lab} {t:.2f}", fill=(247, 220, 58), font=FONT)
    sh_.save(f"{outdir}/probe.jpg", quality=86)
    print(json.dumps({k: v for k, v in res.items() if k != "cuts"}, indent=1))


# --------------------------------------------------------------------------------------------------------------- clips
LABEL = re.compile(r"([a-z][a-z'.-]+ [a-z][a-z'.-]+)[ ,]+(\d{2})\b")     # "adriana lima, 44": first + last name, then the age


def majority(labels):
    """The label most samples agree on, counting OCR misreads ("beila hadid 29") with the label they resemble."""
    groups = []
    for lab in labels:
        for g in groups:
            if difflib.SequenceMatcher(None, g[0], lab).ratio() > 0.75: g.append(lab); break
        else: groups.append([lab])
    if not groups: return None
    g = max(groups, key=len); return max(set(g), key=g.count)


def ocr_texts(img_path):
    p = subprocess.run([f"{BIN}/frame_obstacles", img_path], capture_output=True, text=True)
    try: return json.loads(p.stdout)["texts"]
    except Exception: return []


def clips(S):
    os.makedirs(f"{S['out']}/_work/qc", exist_ok=True); report = {}
    for key, path in S["sources"].items():
        i = info(path); fps = float(i["fps"]); tmpd = tempfile.mkdtemp()
        run(["ffmpeg", "-nostdin", "-loglevel", "error", "-i", path, "-vf", "fps=3,scale=540:-2", f"{tmpd}/f_%04d.png"])
        shots = sorted(os.listdir(tmpd)); samples = []
        for k, name in enumerate(shots):
            t = (k + 0.5) / 3; tx = ocr_texts(f"{tmpd}/{name}")
            txt = " ".join(x[4] for x in sorted(tx, key=lambda x: (x[1], x[0]))).lower()
            m = LABEL.search(txt); card = bool(re.search(r"\bfollow(ing|ers)?\b", txt))
            samples.append((t, f"{m.group(1)} {m.group(2)}" if m else None, card, txt))
        shutil.rmtree(tmpd)
        card_t = next((t for t, _, c, _ in samples if c), None)
        bottom = scene_cuts(path, 0.3, f"iw:ih/2:0:ih/2"); full = scene_cuts(path)
        e = env_db(path)
        def quiet_at(t, win=0.12):
            lo, hi = max(0, int((t - win) * 100)), min(len(e), int((t + win) * 100) + 1)
            k = int(np.argmin(e[lo:hi])) + lo if hi > lo else 0; return round(k / 100, 2), round(float(e[k]), 1) if hi > lo else 0
        # the picture says where a speaker changes (a cut in the bottom half, where the interview sits); the labels only name them
        cuts = [c for c in bottom if 0.2 < c < i["dur"] - 0.2]; bounds = [0.0] + cuts + [i["dur"]]; segs = []
        for a, b in zip(bounds, bounds[1:]):
            who = majority([lab for t, lab, c, _ in samples if lab and not c and a <= t < b]) or "?"   # card text ("Message") is not a name
            if segs and b - a < 0.3: segs[-1]["t1"] = round(b, 4); continue
            if segs and (segs[-1]["who"] == who or (who != "?" and segs[-1]["who"] != "?" and
                                                    difflib.SequenceMatcher(None, segs[-1]["who"], who).ratio() > 0.75)):
                segs[-1]["t1"] = round(b, 4)                                    # a cut inside one speaker's clip
            else: segs.append(dict(who=who, t0=round(a, 4), t1=round(b, 4)))
        if card_t is not None:                     # stop before the follow card, on a pause before the last sample without it
            limit = card_t - 1 / 3 - 0.05; segs = [s for s in segs if s["t0"] < limit - 0.3]
            if segs:
                lo = max(segs[-1]["t0"], limit - 1.5); best = None
                q = min(-26.0, float(np.percentile(e[int(segs[-1]["t0"] * 100):int(limit * 100)], 90)) - 13)   # 80 ms well under speech
                for k in range(int(lo * 100), int(limit * 100)):
                    if k + 8 <= len(e) and e[k:k + 8].max() < q: best = k + 4
                if best is None: segs[-1]["no_clean_pause"] = True              # the card lands mid-sentence: end on the speaker before
                segs[-1]["t1"] = round(min(segs[-1]["t1"], (best / 100) if best else limit), 4)
        for s in segs:
            s["t1"] = min(s["t1"], round(i["dur"] - 1 / fps, 4))
            s["f0"], s["f1"] = int(round(s["t0"] * fps)), int(round(s["t1"] * fps)); s["edge"] = quiet_at(s["t1"])
            a = audio(path, s["t0"], s["t1"] - s["t0"]); s["lufs"] = round(lufs(a), 1)
        sil = subprocess.run(["ffmpeg", "-nostdin", "-i", path, "-vn", "-af", "silencedetect=n=-60dB:d=0.2", "-f", "null", "-"],
                             capture_output=True, text=True).stderr
        silences = [round(float(x), 2) for x in re.findall(r"silence_start: ([0-9.]+)", sil)]
        wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
        run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", path, "-vn", "-ac", "1", "-ar", "16000", wav])
        tx = subprocess.run(["whisper-cli", "-m", WHISPER_MED, "-f", wav], capture_output=True, text=True).stdout; os.unlink(wav)
        lines = [l.strip() for l in tx.splitlines() if l.strip().startswith("[")]
        song = any(("♪" in l) or ("music" in l.lower()) for l in lines)
        report[key] = dict(file=os.path.basename(path), duration=round(i["dur"], 3), fps=str(i["fps"]), size=[i["w"], i["h"]], segments=segs,
                           follow_card=card_t, digital_silence_at=silences, song_or_music=song, full_cuts=[round(c, 3) for c in full],
                           transcript=lines)
        tw, th = 120, 213; ts = np.arange(0.2, i["dur"], 1.0)
        sh_ = Image.new("RGB", (min(len(ts), 16) * (tw + 2), ((len(ts) + 15) // 16) * (th + 30)), (18, 18, 16)); d = ImageDraw.Draw(sh_)
        for k, t in enumerate(ts):
            f = frame_at(path, t, tw, th)
            if f is None: continue
            x, y = (k % 16) * (tw + 2), (k // 16) * (th + 30); sh_.paste(Image.fromarray(f), (x, y + 26))
            who = next((s["who"].split()[0] for s in segs if s["t0"] <= t < s["t1"]), "-")
            d.text((x + 2, y + 2), f"{t:.1f} {who}" + (" CARD" if card_t and t >= card_t else ""), fill=(247, 220, 58), font=FONT)
        sh_.save(f"{S['out']}/_work/qc/clips_{key}.jpg", quality=84)
        print(f"== {key} {os.path.basename(path)} {i['dur']:.2f} s | card {card_t} | song {song} | digital silence {silences or 'none'}")
        for s in segs: print(f"   {s['who']:28s} {s['t0']:7.3f}-{s['t1']:7.3f} (f {s['f0']}-{s['f1']}) {s['lufs']} LUFS, cut level {s['edge'][1]} dB")
    json.dump(report, open(f"{S['out']}/_work/clips.json", "w"), indent=1)
    print(f"wrote {S['out']}/_work/clips.json and qc/clips_<key>.jpg")


def main():
    a = argparse.ArgumentParser(description="trial-reel versions of a posted reaction reel"); sp = a.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("probe"); p.add_argument("posted"); p.add_argument("--out", default=".")
    for c in ("clips", "render", "qc", "page", "deliver"):
        p = sp.add_parser(c); p.add_argument("spec")
        if c in ("render", "qc"): p.add_argument("ids", nargs="*")
        if c == "qc": p.add_argument("--no-asr", action="store_true")
        if c == "page": p.add_argument("outdir")
    o = a.parse_args()
    if o.cmd == "probe": return probe(os.path.abspath(o.posted), os.path.abspath(o.out))
    S = load(o.spec)
    if o.cmd == "clips": clips(S)
    elif o.cmd == "render":
        for v in S["_variants"]:
            if not o.ids or v["id"] in o.ids: wait_free(); render(S, v)
    elif o.cmd == "qc": qc(S, set(o.ids), asr=not o.no_asr)
    elif o.cmd == "page": page(S, os.path.abspath(o.outdir))
    elif o.cmd == "deliver": deliver(S)


if __name__ == "__main__":
    main()
