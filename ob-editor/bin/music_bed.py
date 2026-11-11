#!/usr/bin/env python3
"""A licensed music bed under a long-form voice track: seamless loops, carved for speech, ducked while OB talks.

  as a module (assemble.py does this when OB_MUSIC is set):  long_bed(track, voice, sr, rel_db=-20, duck_db=5) -> (N, 2)
  preview:  python3 -I music_bed.py TRACK VOICE.wav OUT.m4a [--seconds 60] [--rel -20] [--duck 5]

A song shorter than the video loops on a seam the audio itself chooses: the loop end is the point near the track's end
whose next 4 s best match the 4 s after the loop start (onset-envelope correlation, about 6 ms resolution), joined with a
40 ms crossfade, so the groove never stumbles and the intro is heard once. EQ makes room for the voice (-3 dB at 2.5 kHz,
-2 dB below 150 Hz). Level: the bed sits rel_db under the voice's loudness and dips duck_db more while he speaks
(80 ms attack, 300 ms release), fading in over 1.5 s and out over 3 s. Never use with songs that aren't licensed.
"""
import os, subprocess, sys, tempfile
import numpy as np

SR = 48000
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from music_mix import lufs_of, duck_gain   # noqa: E402  (same loudness meter and ducking as the reels)


def _load(track):
    raw = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-i", track, "-af",
                          "equalizer=f=2500:t=q:w=1.0:g=-3,lowshelf=f=150:g=-2", "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64)


def _features(x, hop=1024):
    """Per-frame chroma (12 pitch classes) + onset strength, each frame L2-normalised: harmony and groove together."""
    m = x.mean(1); N = 4096; win = np.hanning(N); n = (len(m) - N) // hop
    S = np.abs(np.array([np.fft.rfft(m[i * hop: i * hop + N] * win) for i in range(n)]))
    f = np.fft.rfftfreq(N, 1 / SR); ok = (f > 60) & (f < 5000)
    pc = np.round(12 * np.log2(f[ok] / 440.0)).astype(int) % 12
    chroma = np.zeros((n, 12))
    for k in range(12): chroma[:, k] = S[:, ok][:, pc == k].sum(1)
    chroma = np.log1p(chroma)
    on = np.maximum(np.diff(np.log1p(S.sum(1)), prepend=0), 0)[:, None]
    F = np.hstack([chroma, 3 * on / (on.std() + 1e-9)])
    F -= F.mean(0); F /= (np.linalg.norm(F, axis=1, keepdims=True) + 1e-9)
    return F, hop


def loop_points(x, min_gap_s=60.0, win_s=4.0):
    """(L0, L1, score): the pair of moments at least min_gap_s apart whose next win_s seconds sound most alike."""
    F, hop = _features(x); fps = SR / hop; W = int(win_s * fps); n = len(F)
    a_lo, a_hi = int(0.5 * fps), int(30 * fps)
    best = (-1.0, 0, 0)
    for a in range(a_lo, min(a_hi, n - W)):
        ref = F[a: a + W]
        lo = a + int(min_gap_s * fps); hi = n - W - int(2 * fps)
        if lo >= hi: break
        # mean frame-wise cosine similarity for every candidate b (vectorised over b)
        sims = np.zeros(hi - lo)
        for k in range(W): sims += F[lo + k: hi + k] @ ref[k]
        b = int(np.argmax(sims)); sc = sims[b] / W
        if sc > best[0]: best = (sc, a, lo + b)
    sc, a, b = best
    A, B = a * hop, b * hop
    # refine the seam to ~1 ms: line up the fine onset envelopes of the 2 s after each point (search +-40 ms)
    h = 48; m = x.mean(1)
    def env(i):
        seg = m[i: i + 2 * SR]; k = len(seg) // h
        e = np.log((seg[: k * h].reshape(k, h) ** 2).mean(1) + 1e-9); d = np.maximum(np.diff(e, prepend=e[0]), 0)
        return (d - d.mean()) / (d.std() + 1e-9)
    ref = env(A); bestd, bestc = 0, -1e9
    for d in range(-40, 41):
        c = float(np.dot(env(B + d * h), ref))
        if c > bestc: bestc, bestd = c, d
    return A, B + bestd * h, sc


def long_bed(track, voice, sr=SR, rel_db=-20.0, duck_db=5.0):
    assert sr == SR
    x = _load(track); n = len(voice)
    L0, L1, q = loop_points(x)
    out = x[:L1].copy(); xf = int(0.04 * SR); ramp = np.linspace(0, 1, xf)[:, None]
    while len(out) < n:   # each pass: crossfade the loop end into the loop start, then the body again
        body = x[L0:L1]
        out[-xf:] = out[-xf:] * (1 - ramp) + body[:xf] * ramp
        out = np.concatenate([out, body[xf:]])
    m = out[:n]
    v = voice if voice.ndim == 1 else voice.mean(1)
    target = lufs_of(np.stack([v, v], 1), sr) + rel_db
    m = m * 10 ** ((target - lufs_of(m, sr)) / 20)
    m = m * duck_gain(v, sr, duck_db)[:, None]
    fi, fo = int(1.5 * sr), int(3.0 * sr)
    m[:fi] *= np.linspace(0, 1, fi)[:, None]; m[-fo:] *= np.linspace(1, 0, fo)[:, None]
    long_bed.info = {"loop_start_s": round(L0 / SR, 3), "loop_end_s": round(L1 / SR, 3), "seam_match": round(q, 3), "loops": round((n - L1) / (L1 - L0), 2)}
    return m


def main():
    a = sys.argv; track, vwav, out = a[1], a[2], a[3]
    opt = lambda k, d: float(a[a.index(k) + 1]) if k in a else d
    secs, rel, duck = opt("--seconds", 60.0), opt("--rel", -20.0), opt("--duck", 5.0)
    raw = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-i", vwav, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    v = np.frombuffer(raw, np.float32).astype(np.float64)[: int(secs * SR)]
    v *= 10 ** ((-20.0 - lufs_of(np.stack([v, v], 1), SR)) / 20)
    mix = np.stack([v, v], 1) + long_bed(track, v, SR, rel, duck)
    mix *= 10 ** ((-14.0 - lufs_of(mix, SR)) / 20)
    peak = np.abs(mix).max()
    if peak > 0.89: mix *= 0.89 / peak
    with tempfile.TemporaryDirectory() as td:
        from scipy.io import wavfile
        p = os.path.join(td, "m.wav"); wavfile.write(p, SR, mix.astype(np.float32))
        subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", p, "-c:a", "aac", "-b:a", "192k", out], check=True)
    print(out, long_bed.info)


if __name__ == "__main__":
    main()
