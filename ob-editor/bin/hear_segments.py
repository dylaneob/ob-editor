#!/usr/bin/env python3
"""Hear candidate takes one by one: Whisper medium on each segment, padded with 0.5 s of silence each side
(unpadded clips drop their last word). For picking the best read of each script line.

  python3 hear_segments.py TAKE.wav START-END [START-END ...]        (seconds on the take's timeline)
"""
import os, subprocess, sys, tempfile
import numpy as np
from scipy.io import wavfile

MODEL = os.path.expanduser("~/.whisper-models/ggml-medium.en.bin")
wav = sys.argv[1]
sr, x = wavfile.read(wav)
x = x.astype(np.float64) / (32768.0 if x.dtype == np.int16 else 1.0)
x = x.mean(1) if x.ndim > 1 else x
pad = np.zeros(int(0.5 * sr))
with tempfile.TemporaryDirectory() as td:
    for spec in sys.argv[2:]:
        a, b = (float(v) for v in spec.split("-"))
        seg = np.concatenate([pad, x[int(a * sr):int(b * sr)], pad])
        p = os.path.join(td, "s.wav"); q = os.path.join(td, "s16.wav")
        wavfile.write(p, sr, (np.clip(seg, -1, 1) * 32767).astype(np.int16))
        subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", p, "-ac", "1", "-ar", "16000", q], check=True)
        out = subprocess.run(["whisper-cli", "-m", MODEL, "-f", q, "-np", "-nt"], capture_output=True, text=True).stdout
        print(f"{a:7.2f}-{b:7.2f} | {' '.join(out.split())}")
