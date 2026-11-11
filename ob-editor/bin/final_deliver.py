#!/usr/bin/env python3
"""After a long-form render: QC it and build frame-by-frame review sheets (no phone copies: OB 10-23 and 10-29).

  python3 -I final_deliver.py WORK_DIR FINAL.mp4 [--every 2] [--parts 0,199.8,303.2,489.1] [--sheets-only]

QC (printed and saved to WORK/qc/final_qc.json):
  - streams, duration vs the cut list, integrated loudness and true peak (ebur128)
  - black frames (blackdetect) and frozen stretches over 2 s (freezedetect), on a 480 px proxy
  - lip sync per shot: the final's audio vs the camera's own scratch audio cut the same way (GCC-PHAT, 300-4000 Hz),
    so the number is what a viewer sees (camera audio is locked to the picture). About +6 ms is perfect (the camera
    mic is ~2 m away); within -45..+60 ms is invisible.
No phone or AirDrop or iCloud copy of a YouTube video, ever (OB 10-23: "no need for iphone copy ... just wastes storage";
10-29: "stop saving to airdrop or icloud for youtube"): he uploads the T7 master from the Mac. --phone-previews (only if
he asks for one) cuts H.264 720p parts per chapter span under 28 MB into WORK/preview.
Frame-by-frame: one frame every N s with timecodes, 6 x 6 per sheet, in WORK/preview/frames. Each label also names the
graphic on screen (the breakdown's event IDs, from WORK/events_resolved.json) so OB can point at one in his notes.
--sheets-only rebuilds just the sheets (skips QC and previews).
"""
import json, os, re, subprocess, sys
import numpy as np

W, F = sys.argv[1], sys.argv[2]
arg = lambda k, d: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
EVERY = float(arg("--every", "2")); P = f"{W}/preview"; os.makedirs(f"{P}/frames", exist_ok=True)
SRC = os.environ.get("OB_SRC", "/Volumes/T7/C4353.MP4")
run = lambda c: subprocess.run(c, capture_output=True, text=True)
NAME = os.path.basename(os.path.normpath(W)).split("-")[0]   # "C4353B-edit" -> C4353B, the prefix of every file handed to OB
qc = {}
try:   # 2026-10-28: the QC gate first (OB: "wire it in"); a FAIL stops the delivery here
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import qc_gate
    try: cards = qc_gate.cover_spans(W)   # the edit's full-screen events: no face of his under their text (C4395's chapter cards)
    except Exception as e: cards = None; print("cover spans not read:", e, flush=True)
    if qc_gate.after_render(F, cards=cards) is False and not os.environ.get("OB_QC_OVERRIDE"):
        sys.exit("BLOCKED by the QC gate: fix the FAIL above and render again (OB_QC_OVERRIDE='why' only for a check proven wrong on this file)")
except SystemExit: raise
except Exception as e: print("qc_gate not run:", e, flush=True)
try:   # 2026-10-28 (C4395): no graphic on his face, measured 4 times a second on every card over his A-roll (the gate reads a frame every 2 s)
    oj = f"{W}/qc/overlay_touch.json"   # a report written after this render (overlay_touch.py WORK --json) is reused, not re-measured
    if os.path.exists(oj) and os.path.getmtime(oj) > os.path.getmtime(F) and not any(r["status"] == "FAIL" for r in json.load(open(oj))):
        print("overlay_touch: fresh report for this render, no graphic on his face", flush=True)
    elif os.path.isdir(f"{W}/render/events") and "--sheets-only" not in sys.argv:
        if subprocess.run([sys.executable, "-I", os.path.join(os.path.dirname(os.path.abspath(__file__)), "overlay_touch.py"), W, "--json", f"{W}/qc/overlay_touch.json"]).returncode \
                and not os.environ.get("OB_QC_OVERRIDE"):
            sys.exit("BLOCKED by overlay_touch: a graphic touches his face (face_clear.py narrows a quote card); render again")
except SystemExit: raise
except Exception as e: print("overlay_touch not run:", e, flush=True)


def sheets():
    """One frame every EVERY s (ffmpeg's fps filter samples the middle of each interval), 6 x 6 per sheet, each labelled
    with its timecode and the graphic on screen."""
    from PIL import Image, ImageDraw, ImageFont
    fd = f"{P}/frames/raw"; os.makedirs(fd, exist_ok=True)
    subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-hwaccel", "videotoolbox", "-i", F, "-vf", f"fps=1/{EVERY},scale=320:180", "-q:v", "4", f"{fd}/f_%04d.jpg"], check=True)
    d_s = float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", F]).stdout)
    evp = f"{W}/events_resolved.json"
    evs = [(e["edit_in"], e["edit_out"], e["id"]) for e in json.load(open(evp))["events"]] if os.path.exists(evp) else []
    fnt = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 16)
    frames = sorted(f for f in os.listdir(fd) if f.startswith("f_") and (int(f[2:6]) - 1) * EVERY < d_s)   # skip macOS ._ files on the T7 and leftovers from a longer cut
    per = 36; made = []
    for p in range(0, len(frames), per):
        S = Image.new("RGB", (6 * 324, 6 * 184), "white")
        for j, fn in enumerate(frames[p:p + per]):
            t = (int(fn[2:6]) - 1) * EVERY + EVERY / 2
            on = next((i for a, b, i in evs if a <= t < b), "")
            im = Image.open(f"{fd}/{fn}").convert("RGB"); d = ImageDraw.Draw(im); lab = f"{int(t // 60)}:{int(t % 60):02d} {on}".strip()
            d.rectangle((0, 0, len(lab) * 10 + 8, 20), fill="black"); d.text((4, 1), lab, font=fnt, fill="#F7DC3A")
            S.paste(im, ((j % 6) * 324, (j // 6) * 184))
        out = f"{P}/frames/{NAME}-FRAMES-{p // per + 1:02d}.jpg"; S.save(out, quality=80); made.append(out)
    print(len(frames), "frames ->", len(made), "sheets")


if "--sheets-only" in sys.argv:
    sheets(); sys.exit(0)

# ---- streams + duration
pr = json.loads(run(["ffprobe", "-v", "error", "-show_entries", "format=duration,size:stream=codec_type,codec_name,width,height,r_frame_rate,channels,sample_rate",
                     "-of", "json", F]).stdout)
dur = float(pr["format"]["duration"]); qc["duration_s"] = round(dur, 3); qc["size_gb"] = round(int(pr["format"]["size"]) / 1e9, 2)
qc["streams"] = [{k: v for k, v in s.items()} for s in pr["streams"]]
segs = json.load(open(f"{W}/cutlist.json"))["segments"]; FPS = 30000 / 1001
expect = sum(max(0, round(s["src_out"] * FPS) - round(s["src_in"] * FPS)) for s in segs) / FPS
qc["expected_s"] = round(expect, 3)

# ---- loudness
r = run(["ffmpeg", "-nostdin", "-i", F, "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"]).stderr
qc["lufs"] = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r)[-1]); qc["true_peak_dbfs"] = float(re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r)[-1])

# ---- black + frozen frames on a proxy
r = run(["ffmpeg", "-nostdin", "-hwaccel", "videotoolbox", "-i", F, "-an", "-vf",
         "scale=480:-2,blackdetect=d=0.2:pix_th=0.06,freezedetect=n=0.001:d=2", "-f", "null", "-"]).stderr
qc["black"] = re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", r)
qc["frozen"] = re.findall(r"freeze_start: ([\d.]+)[\s\S]*?freeze_end: ([\d.]+)", r)

# ---- lip sync per shot: final audio vs camera scratch audio cut identically
SR = 16000
def pcm(path, ch=1):
    raw = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-i", path, "-vn", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).astype(np.float64)
fin, cam = pcm(F), pcm(SRC)
def gcc(a, b, L=int(0.15 * SR)):
    n = len(a); Fn = 1 << (2 * n - 1).bit_length(); hw = np.hanning(n); f = np.fft.rfftfreq(Fn, 1 / SR); band = (f > 300) & (f < 4000)
    R = np.fft.rfft(a * hw, Fn) * np.conj(np.fft.rfft(b * hw, Fn)); R /= (np.abs(R) + 1e-12); R[~band] = 0
    r = np.fft.irfft(R, Fn); r = np.concatenate([r[-L:], r[:L + 1]]); k = int(np.argmax(r))
    sec = np.max(np.delete(r, range(max(0, k - 30), min(len(r), k + 31))))
    return (k - L) / SR * 1000, r[k] / (sec + 1e-12)
sync, e = [], 0.0
for s in segs:
    n = (round(s["src_out"] * FPS) - round(s["src_in"] * FPS)) / FPS; a0 = round(s["src_in"] * FPS) / FPS
    offs = []
    for t in np.arange(0.3, n - 3.3, 1.0):
        A = fin[int((e + t) * SR): int((e + t + 3) * SR)]; B = cam[int((a0 + t) * SR): int((a0 + t + 3) * SR)]
        if len(A) < 3 * SR or len(B) < 3 * SR or np.sqrt((A ** 2).mean()) < 0.01: continue
        o, q = gcc(B, A)            # + = the camera hears it later than the final's audio (final audio slightly early)
        if q > 1.5: offs.append(o)
    sync.append({"shot": s["i"], "edit_s": round(e, 1), "n": len(offs), "camera_minus_final_ms": round(float(np.median(offs)), 1) if offs else None})
    e += n
qc["sync"] = sync
json.dump(qc, open(f"{W}/qc/final_qc.json", "w"), indent=1)
ok = [x["camera_minus_final_ms"] for x in sync if x["camera_minus_final_ms"] is not None]
print(f"duration {dur:.2f} s (cut list {expect:.2f}), {qc['size_gb']} GB; {qc['lufs']} LUFS, true peak {qc['true_peak_dbfs']} dBFS")
print(f"black: {qc['black'] or 'none'}; frozen > 2 s: {qc['frozen'] or 'none'}")
print(f"lip sync per shot (camera minus final, ms; ~+6 is perfect): median {np.median(ok):+.1f}, range {min(ok):+.1f}..{max(ok):+.1f}")
print("  " + " ".join(f'{x["shot"]}:{x["camera_minus_final_ms"]:+.0f}' if x["camera_minus_final_ms"] is not None else f'{x["shot"]}:-' for x in sync))

# ---- phone previews: off unless OB asks for one (--phone-previews); 10-23 "no need for iphone copy ... just wastes storage"
cuts = [float(x) for x in arg("--parts", "0").split(",")] + [dur] if "--phone-previews" in sys.argv else []
for k, (a, b) in enumerate(zip(cuts, cuts[1:])):
    kbps = int(28 * 8 * 1000 / (b - a)) - 96   # total budget minus 96 kb/s audio
    out = f"{P}/{NAME}-PHONE-PREVIEW-part{k + 1}-of-{len(cuts) - 1}.mp4"
    subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", F, "-vf", "scale=1280:720",
                    "-c:v", "libx264", "-preset", "medium", "-b:v", f"{min(kbps, 3000)}k", "-maxrate", f"{min(kbps, 3000) * 5 // 4}k", "-bufsize", f"{min(kbps, 3000) * 2}k",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", out], check=True)
    print(out, f"{os.path.getsize(out) / 1e6:.1f} MB")

# ---- frame-by-frame sheets
sheets()
