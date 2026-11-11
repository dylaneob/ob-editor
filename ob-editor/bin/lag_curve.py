#!/usr/bin/env python3
"""Dense sync curve: a synced mic master against the camera's own audio, across the whole take (C4367, 2026-10-19).

OB 2026-10-19: "make sure there isnt any audio drift while its playing". A line fit (sync_gcc.py) removes the
clock drift, but MOTIV also drops a buffer now and then (a ~5 ms step), so the residual is checked everywhere:
GCC-PHAT (250-3500 Hz) of the master in WIN s windows every STEP s against the camera audio, searched +-SEARCH ms.
lag = camera minus mic, in ms (+ = the camera hears it later). A healthy master sits near +6 ms (about 2 m of air).

  python3 -I lag_curve.py CAMERA_AUDIO MASTER.wav OUT.json [--win 2] [--step 0.5] [--search 80] [--q 8]

Writes {"pts": [[t, lag_ms, q], ...]} (t = window centre, camera time) and prints a per-minute summary
(median, p10/p90, window count), so a drift or a dropout step shows at a glance.
"""
import argparse, json, subprocess
import numpy as np

SR = 16000


def load(path):
    raw = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-i", path, "-vn", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).astype(np.float64)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cam"); ap.add_argument("master"); ap.add_argument("out")
    ap.add_argument("--win", type=float, default=2.0); ap.add_argument("--step", type=float, default=0.5)
    ap.add_argument("--search", type=float, default=80.0); ap.add_argument("--q", type=float, default=8.0)
    a = ap.parse_args()
    cam, mic = load(a.cam), load(a.master)
    n, L = int(a.win * SR), int(a.search / 1000 * SR)
    N = 1 << int(np.ceil(np.log2(n + 2 * L + n)))
    f = np.fft.rfftfreq(N, 1 / SR); band = (f >= 250) & (f <= 3500)
    pts = []
    for m0 in range(L, min(len(mic), len(cam)) - n - L, int(a.step * SR)):
        y = mic[m0:m0 + n]
        if np.sqrt((y ** 2).mean()) < 0.003: continue          # silence: nothing to lock on
        x = cam[m0 - L:m0 + n + L]
        P = np.fft.rfft(x, N) * np.conj(np.fft.rfft(y, N)); P /= np.abs(P) + 1e-12; P[~band] = 0
        r = np.fft.irfft(P, N)[:2 * L + 1]; i = int(np.argmax(r)); d = 0.0
        if 0 < i < 2 * L:
            p, q, s = r[i - 1], r[i], r[i + 1]; den = p - 2 * q + s; d = 0.5 * (p - s) / den if den else 0.0
        qual = float(r[i] / (np.median(np.abs(r)) + 1e-12))
        pts.append([round((m0 + n / 2) / SR, 3), round((i + d - L) / SR * 1000, 3), round(qual, 2)])
    json.dump({"win": a.win, "step": a.step, "pts": pts}, open(a.out, "w"))
    P = np.array(pts); g = P[P[:, 2] >= a.q]
    print(f"{len(P)} windows with speech, {len(g)} confident (q >= {a.q}) | lag median {np.median(g[:, 1]):+.2f} ms, "
          f"p1/p99 {np.percentile(g[:, 1], 1):+.2f}/{np.percentile(g[:, 1], 99):+.2f} ms")
    for t0 in range(0, int(P[-1, 0]) + 60, 60):
        s = g[(g[:, 0] >= t0) & (g[:, 0] < t0 + 60)]
        if len(s): print(f"  {t0 // 60:3d}:00  n={len(s):3d}  median {np.median(s[:, 1]):+6.2f}  p10 {np.percentile(s[:, 1], 10):+6.2f}  p90 {np.percentile(s[:, 1], 90):+6.2f} ms")


if __name__ == "__main__":
    main()
