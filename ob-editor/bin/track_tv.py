#!/usr/bin/env python3
"""Track tripod shake of a static TV region (phase correlation vs a reference frame) and its exposure drift.

  ~/OpenMontage/.venv/bin/python track_tv.py SRC.MP4 T_START T_END T_REF X Y W H OUT.json

Coordinates are display-space (after rotation). Output: [{"t", "dx", "dy", "gain", "resp"}] per frame;
dx/dy = how far the region moved relative to the reference frame (add to the patch position).
"""
import json, subprocess, sys
import numpy as np, cv2

src, t0, t1, tref = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4])
X, Y, W, H = map(int, sys.argv[5:9]); out = sys.argv[9]


def frames(ss, dur):
    cmd = ["ffmpeg", "-nostdin", "-loglevel", "error", "-ss", f"{ss:.3f}", "-t", f"{dur:.3f}", "-i", src,
           "-vf", f"crop={W}:{H}:{X}:{Y},format=gray", "-f", "rawvideo", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    n = W * H
    while True:
        b = p.stdout.read(n)
        if len(b) < n: break
        yield np.frombuffer(b, np.uint8).reshape(H, W).astype(np.float32)
    p.wait()


ref = next(frames(tref, 0.05))
win = cv2.createHanningWindow((W, H), cv2.CV_32F)
bright = ref > 150
res, fps = [], 30000 / 1001
for i, fr in enumerate(frames(t0, t1 - t0)):
    (dx, dy), resp = cv2.phaseCorrelate(ref, fr, win)
    m = cv2.warpAffine(fr, np.float32([[1, 0, -dx], [0, 1, -dy]]), (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    gain = float(m[bright].mean() / ref[bright].mean())
    res.append({"t": round(t0 + i / fps, 4), "dx": round(float(dx), 2), "dy": round(float(dy), 2), "gain": round(gain, 4), "resp": round(float(resp), 3)})
json.dump(res, open(out, "w"))
dx = np.array([r["dx"] for r in res]); dy = np.array([r["dy"] for r in res]); g = np.array([r["gain"] for r in res])
print(f"{len(res)} frames  dx {dx.min():.1f}..{dx.max():.1f}  dy {dy.min():.1f}..{dy.max():.1f}  gain {g.min():.4f}..{g.max():.4f}  resp min {min(r['resp'] for r in res):.2f}")
