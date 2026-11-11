#!/usr/bin/env python3
"""540p rough cut of a long-form cut list, no graphics (2026-10-31; the PRESET's "WORK/roughcut.py" step, made generic).

The proxy's frames in edit order (wide, or the 120% punch-in as assemble.py frames it), the synced master cut the way
assemble.py cuts it (per-shot audio_shift_ms, 6 ms fades at every cut), the house grade. OB judges the flow of the story
edit on it before any graphics exist. Clip holds play black and silent, so label the file a rough cut without graphics.

  python3 -I roughcut.py WORK PROXY.mp4 OUT.mp4 [--lut LUT.png] [--cutlist cutlist.json]

PROXY = make_proxy.sh's 960x540 copy (same frames and timestamps as the camera file). Temp files go to WORK/render/rough_tmp
(the Mac's disk is nearly full) and are deleted at the end.
"""
import json, os, shutil, subprocess, sys
import numpy as np
from scipy.io import wavfile

W, PROXY, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
LUT = sys.argv[sys.argv.index("--lut") + 1] if "--lut" in sys.argv else os.path.expanduser("~/ob-editor/luts/ob_grade_warmtan_hald.png")
CL = sys.argv[sys.argv.index("--cutlist") + 1] if "--cutlist" in sys.argv else "cutlist.json"
FF = "/opt/homebrew/bin/ffmpeg"
FPS = 30000 / 1001
fr = lambda t: int(round(t * FPS))
segs = json.load(open(f"{W}/{CL}"))["segments"]
T = f"{W}/render/rough_tmp"; shutil.rmtree(T, ignore_errors=True); os.makedirs(T)

# ---- voice, as assemble.py plays it
sr, m = wavfile.read(f"{W}/master_synced.wav")
m = m.astype(np.float64) / (2 ** 31 if m.dtype == np.int32 else 2 ** 15 if m.dtype == np.int16 else 1.0)
if m.ndim == 1: m = m[:, None]
fade = int(0.006 * sr); ramp = np.linspace(0, 1, fade)[:, None]; voice = []
for s in segs:
    n = fr(s["src_out"]) - fr(s["src_in"])
    if s.get("hold"):
        voice.append(np.zeros((int(round(n / FPS * sr)), m.shape[1]))); continue
    d = int(round(s.get("audio_shift_ms", 0.0) / 1000 * sr))
    a0 = int(round(fr(s["src_in"]) / FPS * sr)) - d; a1 = a0 + int(round(n / FPS * sr))
    p = m[max(a0, 0):a1].copy()
    if a0 < 0: p = np.pad(p, ((-a0, 0), (0, 0)))
    if len(p) < a1 - a0: p = np.pad(p, ((0, a1 - a0 - len(p)), (0, 0)))
    if len(p) > 2 * fade: p[:fade] *= ramp; p[-fade:] *= ramp[::-1]
    voice.append(p)
v = np.concatenate(voice); wavfile.write(f"{T}/voice.wav", sr, (np.clip(v, -1, 1) * 32767).astype(np.int16))

# ---- pictures: one exact-frame piece per shot from the proxy (input -ss is frame-accurate when transcoding; no B-frames)
lst = []
for k, s in enumerate(segs):
    n = fr(s["src_out"]) - fr(s["src_in"])
    if n <= 0: continue
    o = f"{T}/s{k:04d}.mp4"
    if s.get("hold"):
        cmd = [FF, "-nostdin", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=black:s=960x540:r=30000/1001", "-frames:v", str(n)]
    else:
        vf = "crop=800:450:80:30,scale=960:540:flags=bicubic" if s.get("framing") == "punch" else "scale=960:540"
        cmd = [FF, "-nostdin", "-v", "error", "-y", "-ss", f"{fr(s['src_in']) / FPS:.6f}", "-i", PROXY, "-frames:v", str(n), "-vf", vf + ",setsar=1"]
    subprocess.run(cmd + ["-an", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20", "-pix_fmt", "yuv420p", "-r", "30000/1001", o], check=True)
    lst.append(f"file '{o}'\n")
open(f"{T}/list.txt", "w").write("".join(lst))
subprocess.run([FF, "-nostdin", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", f"{T}/list.txt", "-c", "copy", f"{T}/video.mp4"], check=True)
subprocess.run([FF, "-nostdin", "-v", "error", "-y", "-i", f"{T}/video.mp4", "-i", f"{T}/voice.wav", "-i", LUT, "-filter_complex", "[0:v][2:v]haldclut[v]",
                "-map", "[v]", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast", "-crf", "24", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
                "-movflags", "+faststart", "-shortest", OUT], check=True)
nv = int(subprocess.check_output(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", OUT]))
want = sum(max(0, fr(s["src_out"]) - fr(s["src_in"])) for s in segs)
shutil.rmtree(T, ignore_errors=True)
print(f"{OUT}: {nv} frames (cut list {want}), {len(segs)} shots, {want / FPS / 60:.2f} min")
