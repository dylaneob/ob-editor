#!/usr/bin/env python3
"""Piecewise sync fix for a long MOTIV take (C4372, 2026-10-23).

sync_av.py fits one line (offset + clock drift). Over a long take the MOTIV recorder also drops buffers, so the
residual is a sawtooth: a slow slide of a few ms a minute with 10-20 ms jumps (C4372: -35 ms to +30 ms over 1h44m).
This tool takes the line-synced master and the dense lag curve (lag_curve.py), and moves every stretch of speech by
its own measured lag, switching only in the middle of a quiet gap, so the camera hears him TARGET ms after the mic
everywhere (+6 ms is about 2 m of air, the house value).

  python3 -I sync_pieces.py MASTER_LINE.wav LAG.json OUT.wav [--target 6] [--report OUT.json]

A segment = the audio between the middles of two quiet gaps (10 ms RMS under the noise floor + 12 dB, 100 ms or
longer). Its lag = the median of the confident lag windows (q >= 8, within 15 ms of a 2-minute running median)
centred inside it; segments without one take the neighbours' value, then a 5-segment median filter removes noise
but keeps the recorder's steps. At each switch the change (a few ms of room tone repeated or skipped) gets a 5 ms
crossfade. Check the result with lag_curve.py again: expect a flat TARGET.
"""
import argparse, json, subprocess, os
import numpy as np

SR = 48000


def read_mono(path):
    raw = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("master"); ap.add_argument("lag"); ap.add_argument("out")
    ap.add_argument("--target", type=float, default=6.0); ap.add_argument("--report")
    ap.add_argument("--min-gap", type=float, default=0.10); ap.add_argument("--q", type=float, default=8.0)
    a = ap.parse_args()

    x = read_mono(a.master)
    hop = SR // 100
    n = len(x) // hop
    rms = np.empty(n)
    for c in range(0, n, 60000):                           # 10 min at a time (a float64 copy of 1h44m is 2.4 GB)
        blk = x[c * hop:min(n, c + 60000) * hop].reshape(-1, hop).astype(np.float64)
        rms[c:c + len(blk)] = np.sqrt((blk ** 2).mean(1) + 1e-12)
    db = 20 * np.log10(rms + 1e-12)
    floor = np.percentile(db[db > -150], 5)
    th = min(floor + 12, -45.0)
    quiet = db < th
    # quiet gaps of min_gap or longer -> their middles are the switch points
    cuts, i = [], 0
    while i < n:
        if quiet[i]:
            j = i
            while j < n and quiet[j]: j += 1
            if (j - i) * 0.01 >= a.min_gap: cuts.append(((i + j) // 2) * hop)
            i = j
        else:
            i += 1
    bounds = [0] + cuts + [len(x)]

    P = np.array(json.load(open(a.lag))["pts"])
    P = P[P[:, 2] >= a.q]
    # drop wild windows: more than 15 ms from a 2-minute running median
    keep = np.ones(len(P), bool)
    for k in range(len(P)):
        s = P[np.abs(P[:, 0] - P[k, 0]) <= 60, 1]
        keep[k] = abs(P[k, 1] - np.median(s)) <= 15
    P = P[keep]
    seg_lag = []
    for b0, b1 in zip(bounds[:-1], bounds[1:]):
        s = P[(P[:, 0] >= b0 / SR) & (P[:, 0] < b1 / SR), 1]
        seg_lag.append(float(np.median(s)) if len(s) else np.nan)
    seg_lag = np.array(seg_lag)
    good = ~np.isnan(seg_lag)
    mids = np.array([(b0 + b1) / 2 / SR for b0, b1 in zip(bounds[:-1], bounds[1:])])
    seg_lag[~good] = np.interp(mids[~good], mids[good], seg_lag[good])
    padded = np.pad(seg_lag, 2, mode="edge")
    smooth = np.array([np.median(padded[k:k + 5]) for k in range(len(seg_lag))])
    corr = smooth - a.target                               # ms: segment content moves this much later
    shift = np.round(corr / 1000 * SR).astype(int)

    y = np.zeros_like(x)
    xf = 5 * SR // 1000
    prev_end = None
    for (b0, b1), d in zip(zip(bounds[:-1], bounds[1:]), shift):
        o0, o1 = b0 + d, b1 + d                            # where the segment lands in the output
        s0, s1 = b0, b1
        if o0 < 0: s0 -= o0; o0 = 0
        if o1 > len(y): s1 -= o1 - len(y); o1 = len(y)
        if o1 <= o0: continue
        # extend the head back to the previous segment's end (fills a gap with this segment's own room tone)
        if prev_end is not None and o0 > prev_end:
            ext = o0 - prev_end
            s0 -= ext; o0 = prev_end
            if s0 < 0: o0 -= s0; s0 = 0
        seg = x[s0:s1].copy()
        if prev_end is not None and o0 < prev_end:         # overlap: crossfade the overlap region (at most xf)
            ov = prev_end - o0
            f = min(ov, xf)
            ramp = np.linspace(0, 1, f, dtype=np.float32)
            y[o0:o0 + f] = y[o0:o0 + f] * (1 - ramp) + seg[:f] * ramp
            y[o0 + f:o1] = seg[f:o1 - o0]
        else:
            y[o0:o1] = seg[:o1 - o0]
        prev_end = o1

    tmp = a.out + ".f32"
    y.astype("<f4").tofile(tmp)
    subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", tmp,
                    "-ac", "2", "-c:a", "pcm_s24le", a.out], check=True)
    os.remove(tmp)
    steps = np.abs(np.diff(shift)) / SR * 1000
    print(f"{len(bounds) - 1} segments, quiet threshold {th:.1f} dBFS (floor {floor:.1f}), lag windows used {len(P)}")
    print(f"correction ms: min {corr.min():+.1f} median {np.median(corr):+.1f} max {corr.max():+.1f}; "
          f"switch sizes ms: median {np.median(steps):.2f}, p99 {np.percentile(steps, 99):.2f}, max {steps.max():.2f}")
    if a.report:
        json.dump({"target": a.target, "bounds": bounds, "corr_ms": [round(float(c), 2) for c in corr]}, open(a.report, "w"))
    print("->", a.out)


if __name__ == "__main__":
    main()
