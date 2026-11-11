#!/usr/bin/env python3
"""His podcast mic, mastered for short form without ever making it sound worse (OB 2026-10-28: "sometimes you make the audio sound
bad quality when im legit using a podcast external mic", "make sure you keep it sounds fantastic and only make it sound better not
worse").

What went wrong: his voice peaks about 20 dB over its loudness (the GUT 10/10: -20.4 LUFS, peaks -0.5 dBFS). The 10/10 engine
raised it 6.4 dB to -14 LUFS and then np.clip(-1, 1) BEFORE its limiter: 2,834 samples in 447 runs were hard-clipped (worst
+5.9 dBFS) on a 2-minute reel. Hard clipping is the crunchy, cheap sound on the loud syllables. Never clip; never limit hard.

The chain (float, 48 kHz, never resampled down, never clipped):
  1. high-pass 60 Hz, 12 dB/oct (rumble only; his voice starts about 85 Hz)
  2. ride the fader per script line: each line to the median line's speech level, at most +-8 dB (the GUT 10/10 takes sat 11 dB
     apart, -26.8 to -15.5; the ekko v4 masters OB approved were levelled the same way)
  3. a gentle compressor on the loudest tenth of the syllables: 10 ms RMS, 3:1, 6 dB soft knee, 10 ms attack, 150 ms release,
     never more than 6 dB off a syllable
  4. gain to -14 LUFS (integrated, the stereo file), then a 4x-oversampled limiter at -2 dBFS (2 ms / 60 ms; its 2 ms delay
     taken back out). It may only work lightly: in 20 ms windows, 99% under 3 dB and under 1% over 3 dB. If -14 would make it
     work harder, the master is made quieter instead, 0.5 dB at a time down to -16 LUFS: quieter beats crushed.
     GUT 10/10 (2026-10-28): -14 LUFS with the limiter over 1 dB in 3.4% of windows and over 3 dB in 0.3%; 0 clipped samples
     (the old chain hard-clipped 447 times).
  5. report: loudness in/out, line gains, the compressor's and the limiter's most gain reduction, true peak, LRA, clipped samples
     and flat-topped peaks (both must be 0)
Delivery stays AAC 256k 48 kHz (aac_at), from the MOTIV 24-bit file, never camera audio or a 16 kHz analysis copy.

  python3 -I voice_master.py master IN.wav OUT.wav [--target -14] [--lines EDL.json]   (EDL from takes.py: levels per line)
  python3 -I voice_master.py check FILE [FILE ...]      any render: loudness, true peak, LRA, flat-topped (clipped) peaks,
                                                        bandwidth; exit 1 on clipping or a true peak over -1 dBTP
As a library: y, rep = voice_master.master(x, sr) with x a float mono or (n, 2) array.
"""
import json, os, re, subprocess, sys, tempfile
import numpy as np
from scipy import signal
from scipy.io import wavfile

CEIL_DB = -2.0          # limiter ceiling (4x oversampled): stays under -1 dBTP after AAC
COMP_MAX_DB = 6.0       # the compressor never takes more than this off a syllable
LIM_P99_DB, LIM_OVER3 = 3.0, 1.0   # the limiter's work, in 20 ms windows: 99% of them under 3 dB, under 1% over 3 dB; past that
                                   # the master is made quieter instead, 0.5 dB at a time (never below FLOOR_LUFS)
FLOOR_LUFS = -16.0
RATIO, KNEE, ATT, REL = 3.0, 6.0, 0.010, 0.150
LINE_CLAMP = 8.0        # per-line levelling: at most +-8 dB toward the median line


def lufs(x, sr):
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "x.wav"); wavfile.write(p, sr, np.asarray(x, np.float32))
        r = subprocess.run(["ffmpeg", "-nostdin", "-i", p, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
    s = r[r.rfind("Summary:"):]
    get = lambda k: float(re.search(k + r":\s+(-?[\d.]+|-inf)", s).group(1).replace("-inf", "-120")) if re.search(k + r":\s+(-?[\d.]+|-inf)", s) else None
    return dict(I=get("I"), LRA=get("LRA"), TP=get("Peak"))


def _rms_db(m, sr, win=0.010):
    w = int(win * sr); return 20 * np.log10(np.sqrt(np.convolve(m * m, np.ones(w) / w, mode="same")) + 1e-9)


def _gr_curve(L, sr, th):
    """Smoothed gain reduction (dB, <= 0) of the soft-knee compressor at threshold th on the level curve L (dB, per sample)."""
    over = L - th; s = 1 - 1 / RATIO
    gr = np.where(over <= -KNEE / 2, 0.0, np.where(over >= KNEE / 2, -s * over, -s * (over + KNEE / 2) ** 2 / (2 * KNEE)))
    step = int(0.001 * sr); g = gr[::step]; out = np.empty_like(g); cur = 0.0
    a, r = np.exp(-0.001 / ATT), np.exp(-0.001 / REL)
    for k, v in enumerate(g):   # 1 ms steps: down at the attack time, back up at the release time
        cur = a * cur + (1 - a) * v if v < cur else r * cur + (1 - r) * v
        out[k] = cur
    return np.interp(np.arange(len(L)), np.arange(len(out)) * step, out)


def _limit(x, sr):
    """4x-oversampled limiter at CEIL_DB through ffmpeg (float in, float out). Its 2 ms lookahead delays the sound by 2 ms; that
    is taken back out, so the voice stays on the cut's frames."""
    with tempfile.TemporaryDirectory() as td:
        a, b = os.path.join(td, "a.wav"), os.path.join(td, "b.wav"); wavfile.write(a, sr, x.astype(np.float32))
        subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", a, "-af",
                        f"aresample={sr * 4},alimiter=limit={10 ** (CEIL_DB / 20):.4f}:attack=2:release=60:level=false,aresample={sr}",
                        "-c:a", "pcm_f32le", b], check=True)
        z = wavfile.read(b)[1].astype(np.float64); lag = int(round(0.002 * sr))
        return np.concatenate([z[lag:], np.zeros((lag,) + z.shape[1:])])[:len(x)]


def limiter_work(pre, z, sr):
    """Gain reduction (dB) per 20 ms window where there is sound: p99, max, and the share of windows over 1 and 3 dB."""
    w = int(0.02 * sr); n = len(pre) // w; a, b = pre[:n * w, 0].reshape(n, w), z[:n * w, 0].reshape(n, w)
    e0 = 10 * np.log10((a * a).mean(1) + 1e-12); e1 = 10 * np.log10((b * b).mean(1) + 1e-12); g = (e1 - e0)[e0 > e0.max() - 30]
    return dict(p99=round(float(-np.percentile(g, 1)), 1), max=round(float(-g.min()), 1), over1=round(float((g < -1).mean() * 100), 2),
                over3=round(float((g < -3).mean() * 100), 2))


def line_level(seg, sr):
    """A line's speech level: the 80th percentile of its 30 ms windows within 20 dB of its loudest (the ekko v4 measure)."""
    w, h = int(0.03 * sr), int(0.01 * sr); n = (len(seg) - w) // h
    if n < 5: return None
    cs = np.concatenate([[0.0], np.cumsum(seg * seg)]); i = h * np.arange(n); d = 10 * np.log10((cs[i + w] - cs[i]) / w + 1e-12)
    return float(np.percentile(d[d > np.percentile(d, 90) - 20], 80))


def master(x, sr, target=-14.0, lines=None):
    """x: float mono or (n, 2); lines: [(start_sample, end_sample), ...] of each script line in x (its cut pieces), for levelling."""
    x = np.asarray(x, np.float64)
    if x.ndim == 2: x = x.mean(1)
    b, a = signal.butter(2, 60 / (sr / 2), "highpass"); x = signal.lfilter(b, a, x)
    lv_gain = []
    if lines:   # ride the fader per line: every line to the median line's speech level (the takes sat 11 dB apart on the GUT 10/10)
        lv = [line_level(x[s:e], sr) for s, e in lines]; med = float(np.median([l for l in lv if l is not None]))
        x = x.copy()
        for (s, e), l in zip(lines, lv):
            if l is None: continue
            g = float(np.clip(med - l, -LINE_CLAMP, LINE_CLAMP)); x[s:e] *= 10 ** (g / 20); lv_gain.append(round(g, 1))
    L = _rms_db(x, sr); act = L[L > np.percentile(L, 99) - 25]
    th = float(np.percentile(act, 90))   # only the loudest tenth of the syllables are touched
    gr = _gr_curve(L, sr, th)
    while -gr.min() > COMP_MAX_DB: th += 1.0; gr = _gr_curve(L, sr, th)
    y = x * 10 ** (gr / 20); st = np.stack([y, y], 1); ceil = 10 ** (CEIL_DB / 20)
    l0 = lufs(np.stack([x, x], 1), sr)["I"]; ly = lufs(st, sr)["I"]
    tgt = target
    while True:
        pre = st * 10 ** ((tgt - ly) / 20); z = _limit(pre, sr); work = limiter_work(pre, z, sr)
        if (work["p99"] <= LIM_P99_DB and work["over3"] <= LIM_OVER3) or tgt <= FLOOR_LUFS: break
        tgt -= 0.5
    pk = np.abs(z).max()
    if pk > 1.0: z = z / pk * 0.999   # never clip: scale, don't flatten
    l1 = lufs(z, sr)
    rep = dict(in_lufs=l0, line_gains_db=[min(lv_gain), max(lv_gain)] if lv_gain else None, compressor_threshold=round(th, 1),
               compressor_max_gr_db=round(float(-gr.min()), 1), compressor_gr_p99_db=round(float(-np.percentile(gr, 1)), 1),
               limiter=work, target_lufs=round(tgt, 1), out_lufs=l1["I"], out_true_peak=l1["TP"],
               out_lra=l1["LRA"], clipped_samples=int((np.abs(z) >= 1.0).sum()), flat_tops=flat_tops(z))
    return z, rep


def flat_tops(x, min_run=4):
    """Hard-clipped peaks: runs of min_run+ samples (at 48 kHz) that barely move while loud (|step| under 1e-5 of full scale,
    level over a third of the file's peak). A clip leaves them even after a limiter scales them down; real speech never holds
    still that long near its peak (a 300 Hz wave moves about 4e-4 per sample at its top)."""
    m = x if x.ndim == 1 else x[:, 0]; top = np.abs(m).max()
    if top <= 0: return 0
    q = (np.abs(np.diff(m)) < 1e-5) & (np.abs(m[1:]) > top / 3); d = np.diff(np.concatenate([[0], q.astype(int), [0]]))
    s, e = np.flatnonzero(d == 1), np.flatnonzero(d == -1)
    return int(((e - s) >= min_run - 1).sum())


def check(path):
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", path, "-vn", "-ac", "2", "-ar", "48000", "-f", "f32le", "-"], capture_output=True).stdout
    x = np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64)
    l = lufs(x, 48000); f, p = signal.welch(x[:, 0], 48000, nperseg=8192); pdb = 10 * np.log10(p + 1e-20)
    bw = float(f[np.flatnonzero(pdb > pdb.max() - 60)[-1]])
    return dict(file=os.path.basename(path), lufs=l["I"], true_peak=l["TP"], lra=l["LRA"], flat_tops=flat_tops(x), bandwidth_khz=round(bw / 1000, 1))


def main():
    a = sys.argv[1:]
    if not a or a[0] not in ("master", "check"): print(__doc__); sys.exit(2)
    if a[0] == "master":
        sr, x = wavfile.read(a[1]); x = x.astype(np.float64) / (np.iinfo(x.dtype).max + 1 if x.dtype.kind == "i" else 1)
        target = float(a[a.index("--target") + 1]) if "--target" in a else -14.0
        lines = None
        if "--lines" in a:   # the voice is the EDL's pieces in order: each line's span in samples
            lines, cur = [], 0
            for l in json.load(open(a[a.index("--lines") + 1]))["lines"]:
                n = int(round(sum(q - p for p, q in l["pieces"]) * sr)); lines.append((cur, cur + n)); cur += n
        z, rep = master(x, sr, target, lines)
        with tempfile.TemporaryDirectory() as td:
            t = os.path.join(td, "z.wav"); wavfile.write(t, sr, z.astype(np.float32))
            subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", t, "-c:a", "pcm_s24le", a[2]], check=True)
        print(json.dumps(rep)); return
    bad = 0
    for p in a[1:]:
        r = check(p); ok = r["flat_tops"] == 0 and (r["true_peak"] or -99) <= -1.0; bad += not ok
        print(f"{r['file'][:50]:50s} {r['lufs']:6.1f} LUFS  TP {r['true_peak']:5.1f}  LRA {r['lra']:4.1f}  flat-topped peaks {r['flat_tops']:4d}  "
              f"bandwidth {r['bandwidth_khz']} kHz  {'OK' if ok else 'CHECK'}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
