#!/usr/bin/env python3
"""QC a rendered lecture reel: streams, length, black/frozen frames, loudness, and a contact sheet of
every graphic moment (frame 1, the hook clearing, each card landing, each stamp, the last frame).

  python3 lecture_render_qc.py OUT.mp4 EDL.json SHEET_PREFIX [--offset S]

--offset shifts the EDL times (a V version: the A edit starts after the flash-forward).
"""
import json, re, subprocess, sys
from PIL import Image, ImageDraw


def sh(cmd): return subprocess.run(cmd, capture_output=True, text=True)


def main():
    out, edl, prefix = sys.argv[1:4]
    off = float(sys.argv[sys.argv.index("--offset") + 1]) if "--offset" in sys.argv else 0.0
    spec = json.load(open(edl)); rows = spec["rows"]
    info = json.loads(sh(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,codec_name,width,height,r_frame_rate,nb_frames,duration,sample_rate,channels",
                          "-show_entries", "format=duration,size", "-of", "json", out]).stdout)
    v = [s for s in info["streams"] if s["codec_type"] == "video"][0]; a = [s for s in info["streams"] if s["codec_type"] == "audio"][0]
    print(f"{out}\n  video {v['codec_name']} {v['width']}x{v['height']} {v['r_frame_rate']} {v.get('nb_frames')} frames {float(v['duration']):.3f}s | "
          f"audio {a['codec_name']} {a['sample_rate']} Hz {a['channels']}ch {float(a['duration']):.3f}s | {int(info['format']['size']) / 1e6:.1f} MB")
    r = sh(["ffmpeg", "-nostdin", "-i", out, "-vf", "blackdetect=d=0.1:pix_th=0.03,freezedetect=n=0.0015:d=1.5", "-af", "ebur128=peak=true", "-f", "null", "-"])
    black = re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", r.stderr)
    frz = re.findall(r"freeze_start: ([\d.]+)", r.stderr)
    I = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr); tp = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r.stderr)
    print(f"  black runs: {black or 'none'} | frozen runs (1.5 s+): {frz or 'none'} | loudness {I[-1] if I else '?'} LUFS, true peak {tp[-1] if tp else '?'} dBFS")
    # graphic moments
    later = [x["edit_in"] for x in rows if (x["cue"] or {}).get("card") and x["edit_in"] >= 0.3]
    f1_out = min(2.5, (later[0] - 0.45) if later else 2.5) if spec.get("frame1") else 0.0
    moments = [(0.0, "frame 1")] if not off else [(0.0, "V frame 1"), (off + 0.03, "A starts")]
    if spec.get("frame1"): moments.append((off + f1_out + 0.45, "hook cleared"))
    for i, x in enumerate(rows):
        c = x["cue"] or {}
        if c.get("card") and x["edit_in"] >= f1_out: moments.append((off + x["edit_in"] + 0.75, f"#{i + 1} card"))
        if c.get("stamp"): moments.append((off + x["edit_in"] + 0.6, f"#{i + 1} stamp"))
        if c.get("hide"): moments.append((off + x["edit_in"] + 0.6, f"#{i + 1} card out"))
    moments.append((float(v["duration"]) - 0.1, "last frame"))
    tiles = []
    for t, lab in moments:
        p = f"{prefix}_tmp.png"
        subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-ss", f"{max(0, t):.3f}", "-i", out, "-frames:v", "1", "-vf", "scale=270:480", p])
        im = Image.open(p).convert("RGB"); d = ImageDraw.Draw(im); d.rectangle((0, 0, 150, 18), fill=(0, 0, 0)); d.text((3, 3), f"{t:.1f}s {lab}", fill=(255, 230, 0))
        tiles.append(im)
    cols = 6
    for part in range(0, len(tiles), 18):
        ch = tiles[part:part + 18]; sheet = Image.new("RGB", (270 * cols, 480 * ((len(ch) + cols - 1) // cols)), "black")
        for k, im in enumerate(ch): sheet.paste(im, ((k % cols) * 270, (k // cols) * 480))
        sheet.save(f"{prefix}_{part // 18}.jpg", quality=84); print("  sheet", f"{prefix}_{part // 18}.jpg")


if __name__ == "__main__":
    main()
