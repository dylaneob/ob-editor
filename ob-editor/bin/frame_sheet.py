#!/usr/bin/env python3
"""QC contact sheet: frames of a video at given times, 10 per row, time labels on top.
  python3 frame_sheet.py VIDEO OUT.jpg T1 T2 ...      (times in seconds)
"""
import os, subprocess, sys, tempfile
from PIL import Image, ImageDraw, ImageFont

video, out, times = sys.argv[1], sys.argv[2], [float(t) for t in sys.argv[3:]]
tw, th, lab, per = 216, 384, 30, 10
font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 22)
rows = (len(times) + per - 1) // per
sheet = Image.new("RGB", (min(per, len(times)) * (tw + 6), rows * (th + lab)), (18, 18, 16))
d = ImageDraw.Draw(sheet)
with tempfile.TemporaryDirectory() as tmp:
    for i, t in enumerate(times):
        f = f"{tmp}/f_{i}.jpg"
        subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-ss", f"{t:.3f}", "-i", video, "-frames:v", "1",
                        "-vf", f"scale={tw}:{th}:force_original_aspect_ratio=decrease,pad={tw}:{th}:(ow-iw)/2:(oh-ih)/2", "-q:v", "3", f], check=True)
        x, y = (i % per) * (tw + 6), (i // per) * (th + lab)
        sheet.paste(Image.open(f), (x, y + lab))
        d.text((x + 4, y + 3), f"{t:.1f} s", fill=(247, 220, 58), font=font)
sheet.save(out, quality=88)
print(out)
