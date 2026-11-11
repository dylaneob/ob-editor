#!/usr/bin/env python3
"""Sync an external audio recording (Shure MOTIV Mix WAV) to camera video.

Measures offset AND clock drift by matching speech-onset envelopes of the
camera's scratch audio against the external WAV every 15 s, robust-fits a line,
then renders: video (optionally graded with a Hald CLUT) + external audio,
stretched for drift and trimmed so it lines up with frame 1.

  python3 ~/ob-editor/bin/sync_av.py CAMERA.MP4 MainOutput_24bit.wav OUT.mov [--lut hald.png] [--measure-only]

Default LUT: ~/ob-editor/luts/ob_grade_warmtan_hald.png (OB picked "warm tan" 2026-10-16; grade A made him look pale).
"""
import argparse, os, subprocess, sys, tempfile
import numpy as np
from scipy.io import wavfile
from scipy.signal import fftconvolve, butter, sosfiltfilt

SR = 16000
HOP = 16  # 1 ms envelope
DEFAULT_LUT = os.path.expanduser("~/ob-editor/luts/ob_grade_warmtan_hald.png")


def dur(path):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", path]).strip())


def mono16k(src, dst):
    subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", src, "-vn", "-ac", "1",
                    "-ar", str(SR), "-c:a", "pcm_s16le", dst], check=True)
    return wavfile.read(dst)[1].astype(np.float64)


def onset_env(x):
    sos = butter(4, [200, 4000], btype="band", fs=SR, output="sos")
    x = sosfiltfilt(sos, x) ** 2
    m = len(x) // HOP * HOP
    e = np.log(x[:m].reshape(-1, HOP).mean(1) + 1e-3)
    return np.diff(e, prepend=e[0]).clip(0)


def nz(x):
    x = x - x.mean()
    return x / (np.sqrt((x ** 2).mean()) + 1e-12)


def lag_ms(a, b):
    """lag L maximizing sum a[n+L]*b[n] (a is the longer search window)."""
    c = fftconvolve(a, b[::-1], mode="valid")
    i = int(np.argmax(c))
    if 0 < i < len(c) - 1:
        p, q, r = c[i - 1], c[i], c[i + 1]
        i = i + 0.5 * (p - r) / (p - 2 * q + r)
    return i, c.max() / len(b)


def measure(cam, ext, coarse_override=None, pad=300):
    C, E = onset_env(cam), onset_env(ext)
    # coarse: whole-file loudness envelope averaged into 10 ms bins
    # (striding the spiky onset signal misses peaks and finds false matches)
    def bins(x, d=10):
        m = len(x) // d * d
        return x[:m].reshape(-1, d).mean(1)
    cb, eb = bins(C), bins(E)
    full = fftconvolve(nz(cb), nz(eb)[::-1], mode="full")
    coarse = (int(np.argmax(full)) - (len(eb) - 1)) * 10 / 1000.0
    if coarse_override is not None:   # C4372 (2026-10-23): on a 1h44m take with many re-read lines the whole-file
        coarse = coarse_override      # envelope peak was 1.55 s off; pass the offset found by matching words (--coarse)
    W, pts = 20000, []
    for t in range(15, int(len(E) / 1000) - 25, 15):
        e0 = t * 1000
        c0 = e0 + int(coarse * 1000) - pad
        if c0 < 0 or c0 + W + 2 * pad > len(C):
            continue
        i, peak = lag_ms(nz(C[c0:c0 + W + 2 * pad]), nz(E[e0:e0 + W]))
        pts.append((t, (c0 + i - e0) / 1000.0, peak))
    pts = np.array(pts)
    good = pts[pts[:, 2] > np.percentile(pts[:, 2], 25)]
    for _ in range(3):
        k, b = np.polyfit(good[:, 0], good[:, 1], 1)
        r = good[:, 1] - (k * good[:, 0] + b)
        good = good[np.abs(r) < max(3 * np.median(np.abs(r)), 0.003)]
    k, b = np.polyfit(good[:, 0], good[:, 1], 1)
    r = good[:, 1] - (k * good[:, 0] + b)
    return coarse, b, k, len(pts), len(good), float(np.sqrt((r ** 2).mean()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video"); ap.add_argument("audio"); ap.add_argument("out", nargs="?")
    ap.add_argument("--lut", default=DEFAULT_LUT, help="Hald CLUT png; 'none' for no grade")
    ap.add_argument("--bitrate", default="60M")
    ap.add_argument("--measure-only", action="store_true")
    ap.add_argument("--coarse", type=float, help="camera minus mic offset in s, when the whole-file match locks onto a wrong peak (long multi-take recordings)")
    ap.add_argument("--pad-ms", type=int, default=300, help="per-window search either side of the coarse offset (raise it when the drift over the take is bigger)")
    ap.add_argument("--audio-only", metavar="WAV", help="write only the synced external audio (camera timeline, 48k 24-bit) and skip the video render")
    a = ap.parse_args()

    with tempfile.TemporaryDirectory() as td:
        cam = mono16k(a.video, os.path.join(td, "c.wav"))
        ext = mono16k(a.audio, os.path.join(td, "e.wav"))
    coarse, b, k, n, kept, rms = measure(cam, ext, a.coarse, a.pad_ms)
    print(f"coarse {coarse:+.3f}s | offset {b:+.5f}s | drift {k*1e6:+.2f} ppm "
          f"({k*len(ext)/SR*1000:+.1f} ms over take) | {kept}/{n} windows, residual {rms*1000:.1f} ms")
    if kept < min(10, max(5, int(0.6 * n))) or rms > 0.015:   # a 3-min take only has ~9 windows (one per 15 s), a quarter dropped by design
        sys.exit("Sync confidence too low (few matching windows or residual >15 ms). Is this the right take?")
    if a.measure_only or (not a.out and not a.audio_only):
        return

    # ext time t maps to cam time b + (1+k) t  ->  stretch by (1+k), then shift by b
    rate = 48000 / (1 + k)
    shift = -b
    af = f"asetrate={rate:.5f},aresample=48000:filter_size=64:phase_shift=10:cutoff=0.97,"
    af += f"atrim=start={shift:.5f}," if shift >= 0 else f"adelay={-shift*1000:.1f}:all=1,"
    af += "asetpts=PTS-STARTPTS,apad"
    if a.audio_only:
        subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", a.audio, "-af", af, "-t", f"{dur(a.video):.3f}",
                        "-c:a", "pcm_s24le", "-ar", "48000", a.audio_only], check=True)
        print("synced audio ->", a.audio_only); return
    cmd = ["ffmpeg", "-nostdin", "-loglevel", "error", "-stats", "-y", "-i", a.video, "-i", a.audio]
    if a.lut != "none":
        cmd += ["-i", a.lut]
        fc = f"[0:v][2:v]haldclut=interp=tetrahedral[v];[1:a]{af}[a]"
    else:
        fc = f"[0:v]null[v];[1:a]{af}[a]"
    cmd += ["-filter_complex", fc, "-map", "[v]", "-map", "[a]",
            "-c:v", "h264_videotoolbox", "-b:v", a.bitrate, "-profile:v", "high", "-pix_fmt", "yuv420p",
            "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-tag:v", "avc1",
            "-c:a", "pcm_s24le", "-t", f"{dur(a.video):.3f}", "-map_metadata", "0", a.out]
    print(" ".join(cmd))
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
