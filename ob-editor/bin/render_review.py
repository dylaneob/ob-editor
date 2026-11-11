#!/usr/bin/env python3
"""Review a finished long-form render (assemble.py output) before it ships: the "review the edit" stage.

  python3 -I render_review.py WORK OUT.mp4 --src CAMERA.MP4 [--out DIR] [--every 2] [--phone]

Writes to DIR (default WORK/review):
  review.json      length vs the cut list, black and frozen stretches, loudness (I / LRA / true peak), A/V sync per shot
  frames_NN.jpg    the frame-by-frame: one frame every --every s (default 2), 6 x 5 per sheet (one minute at 2 s),
                   each labelled with its edit timecode and the graphic on screen (events_resolved.json)
  phone/part_N.mp4 with --phone: 720p copies split under 28 MB each, which is what the app will play on OB's phone
Sync: the camera's own scratch audio, cut along the cut list exactly as assemble.py cuts the picture, against the
render's sound, GCC-PHAT per shot. The camera mic is ~2 m away, so a perfectly synced voice reads about +6 ms;
anything over 25 ms off that is flagged (a frame is 33 ms).
"""
import argparse, json, os, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ap = argparse.ArgumentParser(); ap.add_argument("work"); ap.add_argument("out_mp4"); ap.add_argument("--src", required=True)
ap.add_argument("--out"); ap.add_argument("--every", type=float, default=2.0); ap.add_argument("--phone", action="store_true"); a = ap.parse_args()
W, F = a.work, a.out_mp4; D = a.out or f"{W}/review"; os.makedirs(D, exist_ok=True)
FPS = 30000 / 1001; fr = lambda t: int(round(t * FPS)); ft = lambda f: f / FPS
run = lambda c: subprocess.run(c, capture_output=True, text=True)
segs = json.load(open(f"{W}/cutlist.json"))["segments"]
evs = json.load(open(f"{W}/events_resolved.json"))["events"] if os.path.exists(f"{W}/events_resolved.json") else []
rep = {}

# ---- length: frames in the file vs the cut list
want = sum(max(0, fr(s["src_out"]) - fr(s["src_in"])) for s in segs)
nf = int(run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets", "-show_entries", "stream=nb_read_packets", "-of", "csv=p=0", F]).stdout.split(",")[0])
rep["frames"] = {"file": nf, "cut_list": want, "match": nf == want}

# ---- black / frozen frames, loudness (one decode pass for the video filters, one for audio)
r = run(["ffmpeg", "-nostdin", "-i", F, "-vf", "scale=480:-2,blackdetect=d=0.25:pix_th=0.06,freezedetect=n=0.002:d=1.5", "-an", "-f", "null", "-"]).stderr
black = [(float(l.split("black_start:")[1].split()[0]), float(l.split("black_end:")[1].split()[0])) for l in r.splitlines() if "black_start:" in l]
fz, cur = [], None
for l in r.splitlines():
    if "freeze_start:" in l: cur = float(l.split("freeze_start:")[1].split()[0])
    if "freeze_end:" in l and cur is not None: fz.append((cur, float(l.split("freeze_end:")[1].split()[0]))); cur = None
rep["black"] = black; rep["frozen"] = fz
s = run(["ffmpeg", "-nostdin", "-i", F, "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"]).stderr; s = s[s.rfind("Summary:"):]
g = lambda k: float(s.split(k)[1].split()[0])
rep["loudness"] = {"I_LUFS": g("I:"), "LRA_LU": g("LRA:"), "true_peak_dBTP": g("Peak:")}

# ---- A/V sync per shot: camera scratch audio cut like the picture vs the render's audio
SR = 16000
def pcm(p, ss=None, t=None):
    c = ["ffmpeg", "-nostdin", "-loglevel", "error"] + (["-ss", f"{ss:.4f}"] if ss is not None else []) + (["-t", f"{t:.4f}"] if t else [])
    return np.frombuffer(subprocess.run(c + ["-i", p, "-vn", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout, np.float32).astype(np.float64)
ren = pcm(F)
def gcc(x, y, maxlag=0.12):
    n = min(len(x), len(y)); x, y = x[:n] * np.hanning(n), y[:n] * np.hanning(n); N = 1 << (2 * n - 1).bit_length()
    f = np.fft.rfftfreq(N, 1 / SR); R = np.fft.rfft(x, N) * np.conj(np.fft.rfft(y, N)); R /= np.abs(R) + 1e-12; R[(f < 300) | (f > 4000)] = 0
    c = np.fft.irfft(R, N); L = int(maxlag * SR); c = np.concatenate([c[-L:], c[:L + 1]]); k = int(np.argmax(c))
    rest = np.delete(c, range(max(0, k - 30), min(len(c), k + 31)))   # clamp: a peak at the lag edge crashed this (C4369, k = 2L)
    q = c[k] / ((np.max(rest) if len(rest) else 0.0) + 1e-12); return (k - L) / SR * 1000, q
sync, e = [], 0
for sg in segs:
    a0, b0 = fr(sg["src_in"]), fr(sg["src_out"]); nfr = b0 - a0
    if nfr <= 0: continue
    if sg.get("hold"): e += nfr; continue   # a clip hold plays the clip's own sound over unused camera frames: nothing to sync (C4367)
    dur = ft(nfr); lags = []
    for off in np.arange(0.3, max(dur - 3.3, 0.31), 3.0):          # 3 s windows inside the shot
        wl = min(3.0, dur - off - 0.1)   # C4369: a full 3 s window on a 1.5 s shot read past its end into the next shot (false +107 ms)
        if wl < 1.0: continue
        cam = pcm(a.src, ft(a0) + off, wl); i0 = int((ft(e) + off) * SR); rr = ren[i0:i0 + len(cam)]
        if len(rr) < len(cam) or np.sqrt((rr ** 2).mean()) < 0.003: continue
        lag, q = gcc(cam, rr)
        if q > 1.6: lags.append(lag)
    sync.append({"shot": sg["i"], "edit_s": round(ft(e), 2), "lag_ms": round(float(np.median(lags)), 1) if lags else None, "windows": len(lags)})
    e += nfr
ok = [x["lag_ms"] for x in sync if x["lag_ms"] is not None]
rep["sync"] = {"per_shot": sync, "median_ms": round(float(np.median(ok)), 1) if ok else None,
               "flagged": [x for x in sync if x["lag_ms"] is not None and abs(x["lag_ms"] - 6) > 25]}

# ---- frame-by-frame sheets
tc = lambda t: f"{int(t // 60)}:{t % 60:04.1f}"
on = lambda t: next((ev["id"] for ev in evs if ev["edit_in"] <= t < ev["edit_out"]), "")
fdir = f"{D}/_frames"; os.makedirs(fdir, exist_ok=True)
subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", F, "-vf", f"fps=1/{a.every},scale=320:180", "-q:v", "4", f"{fdir}/f_%05d.jpg"], check=True)
frames = sorted(n for n in os.listdir(fdir) if n.endswith(".jpg") and not n.startswith("._")); font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 15)
per = 30
for k in range(0, len(frames), per):
    S = Image.new("RGB", (6 * 324, 5 * 184), "white")
    for j, name in enumerate(frames[k:k + per]):
        t = (k + j) * a.every; im = Image.open(f"{fdir}/{name}").convert("RGB"); d = ImageDraw.Draw(im)
        lab = f"{tc(t)} {on(t)}"; d.rectangle((0, 0, d.textlength(lab, font=font) + 8, 19), fill="black"); d.text((4, 1), lab, font=font, fill="#F7DC3A")
        S.paste(im, ((j % 6) * 324, (j // 6) * 184))
    S.save(f"{D}/frames_{k // per + 1:02d}.jpg", quality=80)
for name in os.listdir(fdir):   # on T7 (exFAT) deleting f_N.jpg also removes its "._f_N.jpg" twin
    if os.path.exists(f"{fdir}/{name}"): os.remove(f"{fdir}/{name}")
os.rmdir(fdir)
rep["frame_sheets"] = (len(frames) + per - 1) // per

# ---- phone copies (720p, parts under 28 MB)
if a.phone:
    os.makedirs(f"{D}/phone", exist_ok=True); total = nf / FPS
    kbps = 1600; part = int(28 * 8 * 1024 / (kbps + 128)) - 5           # seconds per part at this bitrate
    for i, st in enumerate(np.arange(0, total, part)):
        subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-ss", f"{st:.3f}", "-t", f"{part:.3f}", "-i", F, "-vf", "scale=1280:-2",
                        "-c:v", "h264_videotoolbox", "-b:v", f"{kbps}k", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", f"{D}/phone/part_{i + 1}.mp4"], check=True)
    rep["phone_parts"] = sorted(n for n in os.listdir(f"{D}/phone") if not n.startswith("._"))
json.dump(rep, open(f"{D}/review.json", "w"), indent=1)
print(json.dumps({k: v for k, v in rep.items() if k != "sync"}, indent=1))
print(f'sync: median {rep["sync"]["median_ms"]} ms over {len(ok)} shots (about +6 is perfect); flagged: '
      + (", ".join(f'shot {x["shot"]} ({x["lag_ms"]:+.0f} ms at {tc(x["edit_s"])})' for x in rep["sync"]["flagged"]) or "none"))
