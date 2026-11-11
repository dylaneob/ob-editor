#!/usr/bin/env python3
"""Pin each word to bleep to its exact span in the mic (C4354, OB 10-17: "bleep all curse words").

For each target (approximate time from the full-file transcript + the word): transcribe a +-1.6 s snippet with
whisper DTW token times (-nfa -dtw; the plain -ml 1 times were up to 1.2 s off here), take the word between its
own DTW start and the next word's, snap both edges to the level trough at the word boundary (5 ms frames), and
end early at the word's own decay if a pause follows. Verify: muting the span must remove the word and keep the
words either side of it.

  python3 -I bleep_pin.py WORK_DIR targets.json   ([[approx_t, "word"], ...]) -> WORK_DIR/bleeps.json
  OB_BLEEP_WAV=WORK_DIR/mic16.wav picks another mono copy of the synced mic (same timeline; C4395 has no mic_synced.wav)
"""
import json, os, re, subprocess, sys
import numpy as np
from scipy.io import wavfile
W, T = sys.argv[1], json.load(open(sys.argv[2]))
M = "/Users/YOU/.whisper-models/ggml-medium.en.bin"; sr, x = wavfile.read(os.environ.get("OB_BLEEP_WAV", f"{W}/mic_synced.wav")); x = x.astype(np.float32)
norm = lambda w: re.sub(r"[^a-z']", "", w.lower()); PAD = 0.5; tmp = f"{W}/qc/_bleep"


def words(y, dtw=True):
    p = np.concatenate([np.zeros(int(PAD * sr), np.float32), y, np.zeros(int(PAD * sr), np.float32)])
    wavfile.write(tmp + ".wav", sr, p)
    subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", tmp + ".wav", "-ar", "16000", "-ac", "1", tmp + "16.wav"], check=True)
    if not dtw:
        r = subprocess.run(["whisper-cli", "-m", M, "-f", tmp + "16.wav", "-l", "en", "-t", "6", "-np", "-nt"], capture_output=True, text=True)
        return [norm(w) for w in r.stdout.split() if norm(w)]
    subprocess.run(["whisper-cli", "-m", M, "-f", tmp + "16.wav", "-l", "en", "-t", "6", "-np", "-nfa", "-dtw", "medium.en", "-ojf", "-of", tmp], capture_output=True)
    out = []
    for s in json.load(open(tmp + ".json"))["transcription"]:
        for tk in s.get("tokens", []):
            tx = tk["text"]
            if tx.startswith("[_") or tk.get("t_dtw", -1) < 0: continue
            t = tk["t_dtw"] / 100 - PAD
            if tx.startswith(" ") or not out: out.append([t, tx.strip()])
            else: out[-1][1] += tx
    return [(t, w) for t, w in out if norm(w)]


out = []
H = int(0.005 * sr)
for t, target in T:
    for half in (1.6, 4.0):   # widen once if the word isn't in the snippet
        a = t - half; y = x[int(a * sr):int((t + half) * sr)]; ws = words(y)
        hit = [k for k, w in enumerate(ws) if norm(target) in norm(w[1])]
        if hit: break
    if not hit: out.append(dict(t=t, word=target, ok=False, heard=" ".join(w[1] for w in ws))); print(f"{target}: not heard in {ws}"); continue
    k = min(hit, key=lambda k: abs(a + ws[k][0] - t))
    # whisper.cpp's t_dtw marks where a token ENDS (C4354 check: muting [t_dtw(k), t_dtw(k+1)] removed the next word)
    nx = a + ws[k][0]; st = a + ws[k - 1][0] if k > 0 else nx - 0.45
    seg = x[int((st - 0.2) * sr):int((nx + 0.1) * sr)].astype(np.float64); n = len(seg) // H
    db = 10 * np.log10((seg[:n * H].reshape(n, H) ** 2).mean(1) + 1e-12); tt = st - 0.2 + (np.arange(n) + 0.5) * 0.005
    def trough(c, lo=0.08, hi=0.05):
        m = (tt >= c - lo) & (tt <= c + hi); i = np.flatnonzero(m); return float(tt[i[np.argmin(db[i])]]) if len(i) else c
    s0 = trough(st, 0.05, 0.08); s1 = trough(nx, 0.05, 0.08)
    body = (tt > s0) & (tt < s1); thr = db[body].max() - 20 if body.any() else -60
    above = np.flatnonzero(body & (db > thr))
    if len(above): s1 = min(s1, float(tt[above[-1]]) + 0.03)   # a pause follows: stop at the word's own decay
    s0, s1 = round(s0, 3), round(s1, 3)
    z = y.copy(); i0, i1 = int((s0 - a) * sr), int((s1 - a) * sr); f = int(0.004 * sr)
    z[i0:i1] = 0; z[i0 - f:i0] *= np.linspace(1, 0, f); z[i1:i1 + f] *= np.linspace(0, 1, f)
    before = [norm(w) for _, w in ws]; after = words(z, dtw=False)
    left = before[k - 1] if k > 0 else None; right = before[k + 1] if k + 1 < len(before) else None
    ok = norm(target) not in after and (left is None or left in after) and (right is None or right in after)
    out.append(dict(t=t, word=target, t0=s0, t1=s1, dur=round(s1 - s0, 3), heard=" ".join(before), muted=" ".join(after), ok=ok))
    print(f"{'OK ' if ok else 'BAD'} {target:9s} {s0:9.3f}-{s1:9.3f} ({s1 - s0:.2f}s)  heard: {' '.join(before)}\n{'':14s}muted: {' '.join(after)}", flush=True)
json.dump(out, open(f"{W}/bleeps.json", "w"), indent=1)
print("needs a look:", [(o["word"], o["t"]) for o in out if not o.get("ok")])
