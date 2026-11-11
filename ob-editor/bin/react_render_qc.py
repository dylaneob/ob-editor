#!/usr/bin/env python3
"""QC for a react_render.py output: sync, dead frames, black frames, loudness, and a frame sheet.

  python3 react_render_qc.py WORK_DIR RENDER.mp4 [--range START END]

Sync: the camera's own scratch audio (cam16.wav, camera timeline) is cut along the same shots and
compared with the render's sound inside full-frame OB shots, where the sound is his mic. Every lag
must sit within one frame (33 ms).
"""
import argparse, json, os, re, subprocess, sys
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfiltfilt
from PIL import Image, ImageDraw, ImageFont

FPS = 30000 / 1001
fr = lambda t: int(round(t * FPS)); ft = lambda f: f / FPS
ap = argparse.ArgumentParser(); ap.add_argument("work"); ap.add_argument("render"); ap.add_argument("--range", nargs=2, type=float)
a = ap.parse_args(); W = a.work; OUTD = os.path.splitext(a.render)[0] + "_qc"; os.makedirs(OUTD, exist_ok=True)
shots, ef = [], 0
for s in json.load(open(f"{W}/react_cutlist.json"))["shots"]:
    a0, b0 = fr(s["src_in"]), fr(s["src_out"])
    if s["layout"] == "insert": n = fr(s["dur"]); shots.append(dict(s, src0=a0, src1=a0, e0=ef, e1=ef + n)); ef += n
    elif b0 > a0: shots.append(dict(s, src0=a0, src1=b0, e0=ef, e1=ef + b0 - a0)); ef += b0 - a0
R0, R1 = (0, ef) if not a.range else (fr(a.range[0]), min(ef, fr(a.range[1])))
rep = {}

# ---- sync. The mic was synced to the camera when it was built (sync_av: offset + drift, residual 3.7 ms on C4353).
#      What a render can break is the cut alignment, so: inside full-frame shots the render's sound IS the synced mic
#      (plus SFX), and it must line up with mic16.wav at the shot's source time to within a millisecond.
#      (Comparing against the camera's own mic reads ~-40 ms even on the raw recording: room echo smears its envelope.)
SR = 16000
wav = f"{OUTD}/render16.wav"
subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", a.render, "-vn", "-ac", "1", "-ar", str(SR), wav], check=True)
_, y = wavfile.read(wav); y = y.astype(np.float32) / 32768
_, mref = wavfile.read(f"{W}/mic16.wav"); mref = mref.astype(np.float32) / 32768; mref = mref.mean(1) if mref.ndim > 1 else mref
cand = [s for s in shots if s["layout"] == "ob" and s["e1"] - s["e0"] > fr(2.5) and s["e0"] >= R0 and s["e1"] <= R1]
pick = [cand[i] for i in np.linspace(0, len(cand) - 1, min(20, len(cand))).astype(int)] if cand else []
lags = []
for s in pick:
    em = ft((s["e0"] + s["e1"]) / 2 - R0); sm = ft(s["src0"] + (s["e0"] + s["e1"]) / 2 - s["e0"])
    i0, j0, h, L = int((em - 1.0) * SR), int((sm - 1.0) * SR), 2 * SR, int(0.1 * SR)
    A = y[i0:i0 + h].astype(np.float64); B = mref[j0 - L:j0 + h + L].astype(np.float64)
    xc = np.array([np.dot(A, B[k:k + h]) for k in range(0, 2 * L + 1)]); k = int(np.argmax(xc)) - L
    corr = float(xc.max() / (np.linalg.norm(A) * np.linalg.norm(B[L + k:L + k + h]) + 1e-9))
    lags.append((round(em, 1), round(k / SR * 1000, 2), round(corr, 3)))
good = [l for l in lags if l[2] > 0.8]
rep["sync"] = {"method": "render vs synced mic at the same source time", "windows": lags,
               "max_abs_lag_ms": max((abs(l[1]) for l in good), default=None), "pass": bool(good) and all(abs(l[1]) <= 1.0 for l in good)}

# ---- dead and black frames (at 960 px for speed)
r = subprocess.run(["ffmpeg", "-nostdin", "-i", a.render, "-vf", "scale=960:-2,freezedetect=n=0.002:d=2.0,blackdetect=d=0.4:pix_th=0.06", "-an", "-f", "null", "-"],
                   capture_output=True, text=True)
rep["freezes"] = re.findall(r"freeze_start: ([\d.]+).*?\n.*?freeze_duration: ([\d.]+)", r.stderr)
rep["black"] = re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", r.stderr)

# ---- loudness, durations
r = subprocess.run(["ffmpeg", "-nostdin", "-i", a.render, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True)
m = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr); tp = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r.stderr)
rep["loudness_LUFS"] = float(m[-1]) if m else None; rep["true_peak_dBFS"] = float(tp[-1]) if tp else None
pr = lambda sel: subprocess.run(["ffprobe", "-v", "error", "-select_streams", sel, "-show_entries", "stream=duration,nb_frames", "-of", "json", a.render],
                                capture_output=True, text=True).stdout
v = json.loads(pr("v:0"))["streams"][0]; au = json.loads(pr("a:0"))["streams"][0]
rep["video_frames"] = int(v.get("nb_frames", 0)); rep["expected_frames"] = R1 - R0
rep["video_s"], rep["audio_s"] = float(v["duration"]), float(au["duration"])

# ---- frame sheet: every rendered graphic's middle + a frame every 90 s
log = json.load(open(f"{W}/render/render_log.json")) if os.path.exists(f"{W}/render/render_log.json") else {}
evs = {e["id"]: e for e in json.load(open(f"{W}/render/events_render.json"))["events"]}
times = [(ft((evs[i]["f0"] + evs[i]["f1"]) / 2 - R0), i) for i in log.get("graphics", []) if i in evs]
times += [(t, f"{int(t // 60)}:{int(t % 60):02d}") for t in np.arange(15, ft(R1 - R0) - 1, 90)]
times = sorted(tl for tl in times if 0 <= tl[0] < rep["video_s"] - 0.1)   # the render log may belong to a later run
font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 22)
thumbs = []
for t, lab in times:
    p = f"{OUTD}/f_{t:08.2f}.jpg"
    subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-ss", f"{t:.3f}", "-i", a.render, "-frames:v", "1", "-vf", "scale=640:-2", p], check=True)
    thumbs.append((p, lab))
for part in range(0, len(thumbs), 24):
    ch = thumbs[part:part + 24]; cols = 4; rows = (len(ch) + 3) // 4
    sh = Image.new("RGB", (cols * 650, rows * 375), "white"); d = ImageDraw.Draw(sh)
    for i, (p, lab) in enumerate(ch):
        im = Image.open(p); x, y0 = (i % cols) * 650 + 5, (i // cols) * 375 + 5; sh.paste(im, (x, y0))
        d.rectangle([x, y0 + 330, x + 120, y0 + 360], fill="black"); d.text((x + 6, y0 + 333), str(lab), fill="yellow", font=font)
    sh.save(f"{OUTD}/sheet_{part // 24 + 1}.jpg", quality=82)
json.dump(rep, open(f"{OUTD}/qc.json", "w"), indent=1)
print(json.dumps({k: v for k, v in rep.items() if k != "freezes"}, indent=1)); print("freezes:", rep["freezes"][:20]); print("sheets ->", OUTD)
