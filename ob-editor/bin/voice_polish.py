#!/usr/bin/env python3
"""Voice polish for OB's long-form edits: clarity EQ for his dark close-mic voice, applied to the synced master
before the render (the "audio polish" stage from Jason Cooperson's pipeline, tuned to OB's measured voice).

  python3 -I voice_polish.py IN.wav OUT.wav                          # polish the whole master (same length, same timing)
  python3 -I voice_polish.py IN.wav --ab START DUR OUT_PREFIX         # A/B preview pair: OUT_PREFIX-A-original.m4a / -B-polished.m4a
  python3 -I voice_polish.py IN.wav --measure [START DUR]             # loudness + spectrum report

Render with it unchanged: OB_MASTER=OUT.wav python3 -I assemble.py ...   (assemble.py needs no edit; cut pieces come from OUT)

Why this chain (measured on C4353B, MOTIV mic, 2026-10-17):
- loudness range 3.9 LU: the MOTIV app already levels him, so no compressor (it would squash him)
- sibilance (5-9 kHz) 1.6 % of speech energy: low, so no de-esser (it would dull him further)
- presence (2-5 kHz) 3.7 % and air (>9 kHz) 0.2 %: a dark dynamic-mic tone, so lift both
- low mids (100-300 Hz) 29 %: close-mic proximity boom, so a small cut; rumble (<100 Hz) 1 %, so only a gentle high-pass
Chain: high-pass 70 Hz · -1.5 dB at 220 Hz (Q 0.9) · +2 dB at 3.5 kHz (Q 0.8) · +1.5 dB shelf at 9 kHz · -2 dB trim for
headroom (the render normalises to -14 LUFS afterwards). Minimum-phase biquads: timing shift of about 1 sample (0.02 ms; a frame is 33 ms), checked by
cross-correlation; over 0.5 ms the script stops.
"""
import json, os, subprocess, sys, tempfile
import numpy as np

CHAIN = "highpass=f=70:p=2,equalizer=f=220:t=q:w=0.9:g=-1.5,equalizer=f=3500:t=q:w=0.8:g=2,highshelf=f=9000:g=1.5,volume=-2dB"


def pcm(path, start=None, dur=None, sr=48000, af=None):
    cmd = ["ffmpeg", "-nostdin", "-loglevel", "error"] + (["-ss", str(start)] if start is not None else []) + (["-t", str(dur)] if dur else []) + ["-i", path]
    if af: cmd += ["-af", af]
    raw = subprocess.run(cmd + ["-ac", "1", "-ar", str(sr), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).astype(np.float64)


def measure(x, sr=48000):
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "m.wav"); write(p, x, sr)
        r = subprocess.run(["ffmpeg", "-nostdin", "-i", p, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
    s = r[r.rfind("Summary:"):]
    get = lambda k: float(s.split(k)[1].split()[0])
    hop = int(0.05 * sr); n = len(x) // hop; lev = 20 * np.log10(np.sqrt((x[: n * hop].reshape(n, hop) ** 2).mean(1)) + 1e-9)
    F = 4096; win = np.hanning(F); spec = np.zeros(F // 2 + 1)
    for k in range(0, len(x) - F, F * 2):
        seg = x[k:k + F]
        if 20 * np.log10(np.sqrt((seg ** 2).mean()) + 1e-9) >= np.percentile(lev, 50): spec += np.abs(np.fft.rfft(seg * win)) ** 2
    f = np.fft.rfftfreq(F, 1 / sr); band = lambda a, b: float(spec[(f >= a) & (f < b)].sum()); tot = band(50, 16000)
    return {"LUFS": get("I:"), "LRA": get("LRA:"), "true_peak": get("Peak:"),
            "share_pct": {k: round(100 * band(a, b) / tot, 2) for k, (a, b) in
                          {"rumble<100": (20, 100), "lowmid100-300": (100, 300), "mid300-2k": (300, 2000), "presence2-5k": (2000, 5000),
                           "sibilance5-9k": (5000, 9000), "air>9k": (9000, 16000)}.items()}}


def write(path, x, sr=48000):
    from scipy.io import wavfile
    wavfile.write(path, sr, x.astype(np.float32))


def lag_samples(a, b, maxlag=480):
    n = min(len(a), len(b), 48000 * 20); a, b = a[:n], b[:n]
    F = 1 << (2 * n - 1).bit_length()
    c = np.fft.irfft(np.fft.rfft(a, F) * np.conj(np.fft.rfft(b, F)), F)
    c = np.concatenate([c[-maxlag:], c[:maxlag + 1]]); return int(np.argmax(c)) - maxlag


def main():
    a = sys.argv[1:]; src = a[0]
    if "--measure" in a:
        i = a.index("--measure"); st = float(a[i + 1]) if len(a) > i + 2 else None; du = float(a[i + 2]) if len(a) > i + 2 else None
        print(json.dumps({"original": measure(pcm(src, st, du)), "polished": measure(pcm(src, st, du, af=CHAIN))}, indent=1)); return
    if "--ab" in a:
        i = a.index("--ab"); st, du, pre = float(a[i + 1]), float(a[i + 2]), a[i + 3]
        for tag, af in (("A-original", None), ("B-polished", CHAIN)):
            x = pcm(src, st, du, af=af)
            with tempfile.TemporaryDirectory() as td:
                p = os.path.join(td, "x.wav"); write(p, x)
                subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", p, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000",
                                "-c:a", "aac", "-b:a", "192k", f"{pre}-{tag}.m4a"], check=True)
            print(f"{pre}-{tag}.m4a")
        return
    out = a[1]
    subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", src, "-af", CHAIN, "-c:a", "pcm_s24le", out], check=True)
    x0, x1 = pcm(src, 120, 20), pcm(out, 120, 20)
    lag = lag_samples(x0, x1)
    d0 = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", src]))
    d1 = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", out]))
    if abs(lag) > 24 or abs(d0 - d1) > 0.001: sys.exit(f"timing changed: lag {lag} samples, length {d0:.4f} -> {d1:.4f} s; not safe for sync")
    print(f"{out}: same length ({d1:.3f} s), timing shift {lag} samples ({lag / 48:.2f} ms); render with OB_MASTER={out}")


if __name__ == "__main__":
    main()
