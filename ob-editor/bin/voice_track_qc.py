#!/usr/bin/env python3
"""Final word check for a tight cut: build the edit's actual voice track (pieces + their gaps, as the render
plays it) and transcribe it with Whisper medium, then diff against the script (the rows' captions).

  python3 voice_track_qc.py EDL.json TAKE_48k.wav [OUT_PREFIX]
"""
import difflib, json, os, re, subprocess, sys
import numpy as np
from scipy.io import wavfile

def words(t):
    t = t.lower().replace("\u2019", "'").replace("%", " percent")
    t = re.sub(r"\[[^\]]*\]", " ", t); t = re.sub(r"\([^)]*\)", " ", t)
    return [w for w in re.sub(r"[^a-z0-9' ]+", " ", t).replace("'", "").split() if w]

edl, wav = sys.argv[1], sys.argv[2]; pre = sys.argv[3] if len(sys.argv) > 3 else edl.replace(".json", "")
spec = json.load(open(edl)); rows = spec["rows"]
sr, x = wavfile.read(wav); x = x.astype(np.float32); x = x.mean(1) if x.ndim > 1 else x
hop = int(sr * 0.05); lev = 10 * np.log10((x[:len(x) // hop * hop].reshape(-1, hop) ** 2).mean(1) + 1e-12)
q = min(range(len(lev) - 12), key=lambda i: lev[i:i + 12].max()); tone = x[q * hop:(q + 12) * hop]   # room tone, as the render uses
parts = []
for i, r in enumerate(rows):
    a, b = int(r["src_in"] * sr), int((r["src_out"] + r.get("gap", 0)) * sr)
    seg = x[a:b].copy(); f = int(0.008 * sr)
    if r.get("fill") == "room":                                  # the render plays room tone in this gap, not the source
        k = min(len(seg), int((r["src_out"] - r["src_in"]) * sr)); fill = np.resize(tone, len(seg) - k); xf = min(int(0.012 * sr), k, len(seg) - k)
        if xf > 0: ramp = np.linspace(0, 1, xf); fill[:xf] = seg[k:k + xf] * (1 - ramp) + fill[:xf] * ramp
        seg[k:] = fill
    joined_prev = i > 0 and rows[i - 1].get("gap", 0) == 0 and abs(rows[i - 1]["src_out"] - r["src_in"]) < 0.002
    joined_next = i + 1 < len(rows) and r.get("gap", 0) == 0 and abs(r["src_out"] - rows[i + 1]["src_in"]) < 0.002
    if not joined_prev: seg[:f] *= np.linspace(0, 1, f)          # joins play straight through: no fade there
    if not joined_next: seg[-f:] *= np.linspace(1, 0, f)
    parts.append(seg)
v = np.concatenate(parts); out = pre + "_voice16k.wav"
tmp = pre + "_voice48k.wav"; wavfile.write(tmp, sr, v.astype(np.int16))
subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", tmp, "-ac", "1", "-ar", "16000", out], check=True); os.remove(tmp)
r = subprocess.run(["whisper-cli", "-m", os.path.expanduser("~/.whisper-models/ggml-medium.en.bin"), "-f", out, "-nt"], capture_output=True, text=True)
heard = " ".join(l.strip() for l in r.stdout.splitlines() if l.strip())
H, S = words(heard), words(" ".join(r["caption"] for r in rows))
sm = difflib.SequenceMatcher(None, S, H, autojunk=False)
print(f"{os.path.basename(edl)}: voice track {len(v) / sr:.1f} s")
print("heard:", heard)
diffs = [(t, S[i1:i2], H[j1:j2]) for t, i1, i2, j1, j2 in sm.get_opcodes() if t != "equal"]
for t, a_, b_ in diffs: print(f"  {t:8s} script {a_} -> heard {b_}")
print(f"  {len(diffs)} difference(s) between script and edit")
