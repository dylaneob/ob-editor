#!/usr/bin/env python3
"""Split a take into speech chunks by loudness and transcribe each chunk on its own.

  python3 chunks.py TAKE.wav OUT.json [--pause 0.40] [--thresh -42]

Chunk boundaries sit inside real silences (never on Whisper's word times), so any
chunk can be kept or dropped and the cut lands cleanly. Prints "#id  start-end | words".
"""
import argparse, json, os, subprocess, tempfile
import numpy as np
from scipy.io import wavfile

MODEL = os.path.expanduser("~/.whisper-models/ggml-base.en.bin")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("wav"); ap.add_argument("out")
    ap.add_argument("--pause", type=float, default=0.40)
    ap.add_argument("--thresh", type=float, default=-42.0)
    a = ap.parse_args()
    sr, x = wavfile.read(a.wav)
    x = x.astype(np.float64)
    if x.ndim > 1: x = x.mean(1)
    x /= 32768.0
    hop = int(sr * 0.02); n = len(x) // hop
    db = 20 * np.log10(np.sqrt((x[:n * hop].reshape(n, hop) ** 2).mean(1)) + 1e-9)
    v = db > a.thresh
    runs, i = [], 0
    while i < n:
        if v[i]:
            j = i
            while j < n and v[j]: j += 1
            if (j - i) * 0.02 >= 0.12: runs.append([i * 0.02, j * 0.02])
            i = j
        else:
            i += 1
    merged = [runs[0]]
    for s, e in runs[1:]:
        if s - merged[-1][1] < a.pause: merged[-1][1] = e
        else: merged.append([s, e])
    out = []
    with tempfile.TemporaryDirectory() as td:
        for k, (s, e) in enumerate(merged):
            s0, e0 = max(0, s - 0.08), e + 0.12
            seg = os.path.join(td, "c.wav")
            subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-ss", f"{s0:.3f}", "-t", f"{e0 - s0:.3f}", "-i", a.wav,
                            "-ac", "1", "-ar", "16000", seg], check=True)
            r = subprocess.run(["whisper-cli", "-m", MODEL, "-f", seg, "-nt"], capture_output=True, text=True)
            txt = " ".join(l.strip() for l in r.stdout.splitlines() if l.strip()).strip()
            pk = float(db[int(s / 0.02):int(e / 0.02)].max()) if e > s else -99
            out.append({"id": k, "start": round(s, 2), "end": round(e, 2), "peak_db": round(pk, 1), "text": txt})
            print(f"#{k:03d} {s:7.2f}-{e:7.2f} ({e - s:4.1f}s) | {txt}", flush=True)
    json.dump(out, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
