#!/usr/bin/env python3
"""Synthesize the editor's sound-design kit in code (48 kHz, 24-bit WAV).

whoosh: band-passed noise, centre frequency sweeping up, smooth envelope (panel slides, card entrances)
pop:    sine with a fast downward pitch glide + soft transient (photo / tile pop-ins)
tick:   short bright sine blip (bullet reveals, number ticks)
thud:   low sine with pitch drop + soft noise attack (chapter cards)
"""
import os, sys
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

SR = 48000
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/ob-editor/assets/sfx")
rng = np.random.default_rng(3)


def env(n, a, d, curve=4.0):
    t = np.arange(n) / SR
    att = np.clip(t / a, 0, 1) ** 2
    dec = np.exp(-curve * np.clip(t - a, 0, None) / d)
    return att * dec


def norm(x, peak_db):
    return x / (np.abs(x).max() + 1e-12) * 10 ** (peak_db / 20)


def whoosh(dur=0.42, f0=400, sweep=8, shape=1.5):
    n = int(SR * dur); x = rng.standard_normal(n); y = np.zeros(n); blk = 480
    for i in range(0, n, blk):  # time-varying band-pass: sweep f0 -> f0 * sweep Hz
        fc = f0 * (sweep ** (i / n)); lo, hi = fc / 1.6, min(fc * 1.6, 20000)
        sos = butter(2, [lo, hi], btype="band", fs=SR, output="sos")
        y[i:i + blk] = sosfilt(sos, x[max(0, i - 2048):i + blk])[-len(y[i:i + blk]):]
    t = np.linspace(0, 1, n); e = np.sin(np.pi * t) ** shape  # swell in and out
    return norm(y * e, -6)


def pop(dur=0.16, base=520, glide=420):
    n = int(SR * dur); t = np.arange(n) / SR
    f = base + glide * np.exp(-t / 0.018)  # (base + glide) Hz gliding to base Hz
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = np.sin(ph) * env(n, 0.002, 0.06)
    y += 0.25 * rng.standard_normal(n) * env(n, 0.0005, 0.004)  # tiny transient
    return norm(y, -6)


def tick(dur=0.05, f=2400):
    n = int(SR * dur); t = np.arange(n) / SR
    y = np.sin(2 * np.pi * f * t) * env(n, 0.0008, 0.012) + 0.5 * np.sin(2 * np.pi * 2 * f * t) * env(n, 0.0005, 0.006)
    return norm(y, -6)


def thud(dur=0.45, base=52):
    n = int(SR * dur); t = np.arange(n) / SR
    f = base + 48 * np.exp(-t / 0.05)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.003, 0.22)
    nz = sosfilt(butter(2, 900, fs=SR, output="sos"), rng.standard_normal(n)) * env(n, 0.001, 0.03)
    return norm(y + 0.35 * nz / (np.abs(nz).max() + 1e-12), -6)


def write(name, y):
    y = np.clip(y, -1, 1)
    wavfile.write(f"{OUT}/{name}.wav", SR, (y * (2 ** 31 - 1)).astype(np.int32))


os.makedirs(OUT, exist_ok=True)
kit = {"whoosh": whoosh(), "pop": pop(), "tick": tick(), "thud": thud()}
for k, v in kit.items():
    if not os.path.exists(f"{OUT}/{k}.wav"): write(k, v)   # never rewrite the originals other renders may load

# Variants (OB 2026-10-16: one sample repeated ~300 times "gets so repetitive"). assemble.py rotates through
# NAME_1..NAME_4 so the same sound never plays twice in a row.
VARIANTS = {
    "whoosh": [dict(dur=0.34, f0=500, sweep=6, shape=1.8), dict(dur=0.48, f0=320, sweep=9, shape=1.3),
               dict(dur=0.40, f0=650, sweep=4, shape=2.0), dict(dur=0.55, f0=260, sweep=10, shape=1.6)],
    "pop": [dict(base=440, glide=360), dict(base=600, glide=480), dict(base=380, glide=300, dur=0.18), dict(base=700, glide=420, dur=0.13)],
    "tick": [dict(f=1800), dict(f=2100, dur=0.045), dict(f=2700, dur=0.04), dict(f=1500, dur=0.055)],
    "thud": [dict(base=46), dict(base=58, dur=0.40), dict(base=50, dur=0.5)],
}
FN = {"whoosh": whoosh, "pop": pop, "tick": tick, "thud": thud}
for name, params in VARIANTS.items():
    for i, p in enumerate(params, 1): write(f"{name}_{i}", FN[name](**p))
gap = np.zeros(int(SR * 0.7))
write("_preview", np.concatenate(sum([[v, gap] for v in kit.values()], [])))
print("sfx kit:", {k: f"{len(v)/SR:.2f}s" for k, v in kit.items()}, "+", sum(len(v) for v in VARIANTS.values()), "variants ->", OUT)
