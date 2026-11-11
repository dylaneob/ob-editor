#!/usr/bin/env python3
"""QC a rendered tier / this-or-that reel: frame count vs the EDL, black and frozen frames, loudness and true peak,
and a contact sheet of every shot at its graphic moment (the same times as the review page's mocks).

  python3 tier_render_qc.py WORK NAME OUT.mp4 SHEET.jpg
"""
import json, os, re, subprocess, sys

W, name, out, sheet = sys.argv[1:5]
spec = json.load(open(f"{W}/{name}_edl.json")); lay = json.load(open(f"{W}/hf/{name}_layout.json"))
FPS = 30000 / 1001
r = lambda c: subprocess.run(c, capture_output=True, text=True)
nf = int(r(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets", "-show_entries", "stream=nb_read_packets", "-of", "csv=p=0", out]).stdout.strip().split(",")[0])
dur = float(r(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", out]).stdout.strip())
exp = round(spec["duration"] * FPS)
print(f"{os.path.basename(out)}: {dur:.2f} s, {nf} frames (EDL {exp})")
e = r(["ffmpeg", "-nostdin", "-i", out, "-vf", "blackdetect=d=0.1:pix_th=0.03,freezedetect=n=0.0015:d=1.5", "-af", "ebur128=peak=true", "-f", "null", "-"]).stderr
blacks = re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", e); freezes = re.findall(r"freeze_start: ([\d.]+)", e)
I = re.findall(r"I:\s+(-?[\d.]+) LUFS", e)[-1]; tp = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", e)[-1]
print(f"  black: {blacks or 'none'} | frozen 1.5 s+: {freezes or 'none'} | {I} LUFS, true peak {tp} dBFS")
tmp = sheet + ".d"; os.makedirs(tmp, exist_ok=True)
for i, t in enumerate(lay["mock_times"]):
    r(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-ss", f"{t:.3f}", "-i", out, "-frames:v", "1", "-vf", "scale=216:384", f"{tmp}/{i:03d}.jpg"])
cols = 9 if len(lay["mock_times"]) <= 27 else 12
r(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-pattern_type", "glob", "-i", f"{tmp}/*.jpg",
   "-vf", f"tile={cols}x{-(-len(lay['mock_times']) // cols)}:padding=4:color=white", "-frames:v", "1", sheet])
for f in os.listdir(tmp): os.remove(os.path.join(tmp, f))
os.rmdir(tmp)
print(f"  sheet -> {sheet}")
