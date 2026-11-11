#!/usr/bin/env python3
"""Echo-proof sync measure: GCC-PHAT on the raw waveforms, window by window.
sync_av.py matches loudness onsets; in a live room the camera mic's reverb smears them and the fit wanders
(C4359/C4360, 2026-10-18: 235 and 1255 ppm "drift"). PHAT whitening keeps only phase, so the direct sound
dominates and each window gives a sharp, sub-millisecond lag.

  python3 sync_gcc.py CAMERA.MP4 EXT.wav COARSE_OFFSET [--out SYNCED.wav]

COARSE_OFFSET: camera time of ext t=0 (sync_av's "coarse").
FIXED 2026-10-19: the window maths counted the 0.35 s search pad twice, so every result was 0.35 s too late and
C4359/C4360 shipped with the voice 351 ms behind the lips (sync_av's "coarse" was right all along). --out now
re-measures the written file against the camera's own audio and fails unless it is within 3 ms. Prints one line per 8 s window (cam time, implied
offset, peak quality), the robust fit cam = b + (1+k) * ext, and with --out writes the external audio on the
camera timeline (48 kHz 24-bit), stretched for drift exactly like sync_av.py.
"""
import argparse, os, subprocess, sys, tempfile
import numpy as np
from scipy.io import wavfile

SR = 16000


def mono16k(src, dst):
    subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", src, "-vn", "-ac", "1", "-ar", str(SR),
                    "-c:a", "pcm_s16le", dst], check=True)
    return wavfile.read(dst)[1].astype(np.float64) / 32768.0


def gcc_phat(a, b, max_lag):
    """Where b sits inside the longer a, searched over 0..max_lag samples: a[n + lag] ~ b[n].
    Returns lag, quality (peak over the next best peak)."""
    n = 1 << int(np.ceil(np.log2(len(a) + len(b))))
    A, B = np.fft.rfft(a, n), np.fft.rfft(b, n)
    R = A * np.conj(B); R /= np.abs(R) + 1e-12
    r = np.fft.irfft(R, n)[: max_lag + 1]                           # lag 0 = b at the very start of a
    i = int(np.argmax(r)); pk = r[i]
    if 0 < i < len(r) - 1:
        p, q, s = r[i - 1], r[i], r[i + 1]; frac = 0.5 * (p - s) / (p - 2 * q + s)
    else:
        frac = 0.0
    guard = int(0.002 * SR)
    rest = np.concatenate([r[:max(0, i - guard)], r[i + guard + 1:]])
    return i + frac, float(pk / (rest.max() + 1e-12))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video"); ap.add_argument("ext"); ap.add_argument("coarse", type=float)
    ap.add_argument("--out"); ap.add_argument("--win", type=float, default=8.0); ap.add_argument("--step", type=float, default=6.0)
    a = ap.parse_args()
    with tempfile.TemporaryDirectory() as td:
        cam = mono16k(a.video, os.path.join(td, "c.wav")); ext = mono16k(a.ext, os.path.join(td, "e.wav"))
    W, S = int(a.win * SR), int(0.35 * SR)
    pts = []
    t = 2.0
    while True:
        te = t; tc = a.coarse + te                              # ext window [te, te+win] lands near cam tc
        c0 = int((tc) * SR) - S; e0 = int(te * SR)
        if e0 + W > len(ext) or c0 + W + 2 * S > len(cam): break
        if c0 >= 0:
            seg_e = ext[e0:e0 + W]
            if np.sqrt((seg_e ** 2).mean()) > 0.01:              # skip near-silent windows (pauses between takes)
                lag, q = gcc_phat(cam[c0:c0 + W + 2 * S], seg_e, 2 * S)   # the cam window starts S early: lag S = coarse exact
                cam_t = (c0 + lag) / SR                           # cam time where ext time te sits (window start)
                pts.append((te, cam_t - te, q))
        t += a.step
    pts = np.array(pts)
    for te, off, q in pts:
        print(f"  ext {te:6.1f}s  offset {off:+.4f}s  q {q:5.2f}")
    good = pts[pts[:, 2] > 1.5]
    k, b = np.polyfit(good[:, 0], good[:, 1], 1)
    for _ in range(4):
        r = good[:, 1] - (k * good[:, 0] + b)
        keep = np.abs(r) < max(4 * np.median(np.abs(r)), 0.002)
        good = good[keep]; k, b = np.polyfit(good[:, 0], good[:, 1], 1)
    r = good[:, 1] - (k * good[:, 0] + b)
    print(f"fit: offset {b:+.5f}s drift {k * 1e6:+.1f} ppm | {len(good)}/{len(pts)} windows | residual {np.sqrt((r ** 2).mean()) * 1000:.2f} ms")
    if a.out:
        # cam time = b + (1+k) ext time  ->  same filter as sync_av.py
        rate = 48000 / (1 + k); shift = -b
        af = f"asetrate={rate:.5f},aresample=48000:filter_size=64:phase_shift=10:cutoff=0.97,"
        af += f"atrim=start={shift:.5f}," if shift >= 0 else f"adelay={-shift * 1000:.1f}:all=1,"
        af += "asetpts=PTS-STARTPTS,apad"
        d = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", a.video]).strip())
        subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", a.ext, "-af", af, "-t", f"{d:.3f}",
                        "-c:a", "pcm_s24le", "-ar", "48000", a.out], check=True)
        print("synced audio ->", a.out)
        verify(cam, a.out)


def verify(cam, out, pad=0.5, win=3.0):
    """Independent check of the written file: each 3 s window of it must sit exactly `pad` into the camera audio
    taken from pad seconds earlier. Exits non-zero unless the median error is within 3 ms."""
    with tempfile.TemporaryDirectory() as td:
        syn = mono16k(out, os.path.join(td, "s.wav"))
    P, Wn = int(pad * SR), int(win * SR); errs = []
    for t in np.linspace(5.0, len(cam) / SR - win - 5.0, 12):
        s0 = int(t * SR); seg = syn[s0:s0 + Wn]
        if np.sqrt((seg ** 2).mean()) < 0.01 or s0 - P < 0: continue
        lag, q = gcc_phat(cam[s0 - P:s0 + Wn + P], seg, 2 * P)
        if q > 1.5: errs.append((lag - P) / SR * 1000.0)
    if len(errs) < 4: sys.exit(f"SYNC CHECK: only {len(errs)} clean windows, can't confirm {out}")
    med = float(np.median(errs))
    print(f"check vs camera audio: {len(errs)} windows, error median {med:+.1f} ms (+ = voice early), spread {min(errs):+.1f} to {max(errs):+.1f} ms")
    if abs(med) > 3.0: sys.exit(f"SYNC CHECK FAILED: {out} is {med:+.1f} ms off the camera audio")


if __name__ == "__main__":
    main()
