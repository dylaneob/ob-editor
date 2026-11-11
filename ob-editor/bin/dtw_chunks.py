#!/usr/bin/env python3
"""Whisper DTW word times for a long recording, in 60 s chunks with 6 s overlap (C4354, 2026-10-17: one full-file
-dtw run stalled at 2:56). Each chunk: whisper-cli medium.en -nfa -dtw medium.en -ojf; a word is kept from the chunk where
it sits furthest from an edge. Output: [[t0, t1, word], ...] like dtw_words.py. Chunk results are kept next to OUT
(_dtwchunk_FROM_TO.json), so re-running after a stop only transcribes the chunks still missing.

  python3 -I dtw_chunks.py IN16k.wav OUT.json [--from S] [--to E]
"""
import json, os, re, subprocess, sys
import numpy as np
from scipy.io import wavfile
src, outp = sys.argv[1], sys.argv[2]
sr, x = wavfile.read(src); T = len(x) / sr
A = float(sys.argv[sys.argv.index("--from") + 1]) if "--from" in sys.argv else 0.0
B = float(sys.argv[sys.argv.index("--to") + 1]) if "--to" in sys.argv else T
M = "/Users/YOU/.whisper-models/ggml-medium.en.bin"; tmp = os.path.join(os.path.dirname(os.path.abspath(outp)), "_dtwchunk")
L, OV = 60.0, 6.0; starts = list(np.arange(A, max(A + 0.1, B - OV), L - OV)); allw = []
for k, c0 in enumerate(starts):
    c1 = min(B, c0 + L)
    keep = f"{tmp}_{c0:.1f}_{c1:.1f}.json"   # each chunk's whisper JSON is kept, so a stopped run resumes where it left off (C4368, 2026-10-20)
    if not os.path.exists(keep):
        wavfile.write(tmp + ".wav", sr, x[int(c0 * sr):int(c1 * sr)])
        subprocess.run(["whisper-cli", "-m", M, "-f", tmp + ".wav", "-l", "en", "-t", "6", "-np", "-nfa", "-dtw", "medium.en", "-ojf", "-of", tmp],
                       capture_output=True, timeout=600)
        os.replace(tmp + ".json", keep)
    J = json.load(open(keep))["transcription"]; ws = []
    for seg in J:
        s0 = seg["offsets"]["from"] / 1000; cur = []
        for tk in seg.get("tokens", []):
            tx = tk["text"]
            if tx.startswith("[_") or tk.get("t_dtw", -1) < 0: continue
            t = tk["t_dtw"] / 100
            if tx.startswith(" ") or not cur: cur.append([t, tx.strip()])
            else: cur[-1][0] = t; cur[-1][1] += tx
        prev = s0
        for end, w in cur:
            if not re.search(r"[A-Za-z0-9]", w): continue
            est = min(0.6, max(0.12, 0.075 * len(re.sub(r"[^A-Za-z0-9]", "", w))))
            st = max(prev, s0, end - est) if end - prev > est + 0.25 else prev
            ws.append([c0 + st, c0 + max(end, st + 0.03), w]); prev = end
    lo = c0 + (OV / 2 if k > 0 else -1e9); hi = c1 - (OV / 2 if c1 < B else -1e9)
    allw += [w for w in ws if lo <= (w[0] + w[1]) / 2 < hi]
    print(f"chunk {k + 1}/{len(starts)} {c0:7.1f}-{c1:7.1f}s: {len(ws)} words", flush=True)
allw.sort(key=lambda w: w[0])
json.dump({"words": [[round(a, 3), round(b, 3), w] for a, b, w in allw], "source": "whisper DTW chunks (t_dtw = token end)"}, open(outp, "w"))
print(f"{len(allw)} words -> {outp}")
