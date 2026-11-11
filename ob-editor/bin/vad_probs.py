#!/usr/bin/env python3
"""Silero VAD v6 speech probability for a whole audio file, every 32 ms (512 samples at 16 kHz). Breaths, room tone and clicks come
out low; words come out high. Run with the OpenMontage venv (onnxruntime + faster-whisper's bundled model):
  ~/OpenMontage/.venv/bin/python vad_probs.py AUDIO OUT.npy"""
import subprocess, sys
import numpy as np
from faster_whisper.vad import get_vad_model
src, out = sys.argv[1], sys.argv[2]
raw = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-i", src, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                     capture_output=True, check=True).stdout
a = np.frombuffer(raw, np.float32).copy(); a = np.pad(a, (0, (-len(a)) % 512))
p = np.asarray(get_vad_model()(a)).reshape(-1).astype(np.float32)
np.save(out, p); print(f"{len(p)} windows of 32 ms, {(p > 0.5).mean() * 100:.0f}% speech -> {out}")
