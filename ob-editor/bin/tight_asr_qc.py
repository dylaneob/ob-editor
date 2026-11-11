#!/usr/bin/env python3
"""Whisper proof that tight cuts clip no words (rows that touch in the source are checked as one run).

  python3 tight_asr_qc.py EDL.json TAKE_16k.wav [--model base.en]

Rows less than 0.8 s apart in the source form a run. For each run:
  inner: the run's pieces joined back to back vs the same span of the source played straight through.
         A word the source has and the joined pieces don't = a word lost at an internal cut.
  outer: the joined run vs a +-1 s window. Extra words at an edge with no 120 ms pause before them = clipped.
"""
import difflib, json, os, re, subprocess, sys, tempfile
import numpy as np
from scipy.io import wavfile

def words(t):
    t = re.sub(r"\\[[^\\]]*\\]|\\([^)]*\\)", " ", t.lower())
    return [w for w in re.sub(r"[^a-z0-9' ]+", " ", t).replace("'", "").split() if w]

def asr(model, path):
    r = subprocess.run(["whisper-cli", "-m", model, "-f", path, "-nt"], capture_output=True, text=True)
    return " ".join(l.strip() for l in r.stdout.splitlines() if l.strip())

def main():
    edl, wav = sys.argv[1], sys.argv[2]
    model = os.path.expanduser("~/.whisper-models/ggml-" + (sys.argv[sys.argv.index("--model") + 1] if "--model" in sys.argv else "base.en") + ".bin")
    rows = json.load(open(edl))["rows"]
    sr, x = wavfile.read(wav); x = x.astype(np.float32); x = x.mean(1) if x.ndim > 1 else x
    hop = int(sr * 0.01); n = len(x) // hop
    L = 10 * np.log10(np.convolve(((x[:n * hop] / 32768.0).reshape(n, hop) ** 2).mean(1), np.ones(10) / 10, mode="same") + 1e-12)
    th = max(-48.0, float(np.percentile(L, 10)) + 8)
    runs, cur = [], [0]
    for i in range(1, len(rows)):
        if 0 <= rows[i]["src_in"] - rows[i - 1]["src_out"] < 0.8: cur.append(i)
        else: runs.append(cur); cur = [i]
    runs.append(cur)
    seg = lambda a, b: x[max(0, int(a * sr)):int(b * sr)]
    flags = 0
    with tempfile.TemporaryDirectory() as td:
        def tx(arr, tag):
            p = os.path.join(td, tag + ".wav"); wavfile.write(p, sr, arr.astype(np.int16)); return asr(model, p)
        for run in runs:
            a, b = rows[run[0]]["src_in"], rows[run[-1]]["src_out"]
            joined = np.concatenate([seg(rows[i]["src_in"], rows[i]["src_out"]) for i in run])
            K = words(tx(joined, "k")); S = words(tx(seg(a, b), "s")); Wd = words(tx(seg(a - 1.0, b + 1.0), "w"))
            notes = []
            if len(run) > 1:
                sm = difflib.SequenceMatcher(None, S, K, autojunk=False)
                lost = [S[i1:i2] for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag in ("delete", "replace") and i2 > i1]
                lost = [w for grp in lost for w in grp]
                if lost: notes.append(f"inner: the straight-through source has {lost} that the joined pieces lose")
            sm = difflib.SequenceMatcher(None, Wd, K, autojunk=False); bl = [m for m in sm.get_matching_blocks() if m.size]
            if bl:
                tail, head = Wd[bl[-1].a + bl[-1].size:], Wd[:bl[0].a]
                def pause(t0, t1):
                    q = L[int(t0 * 100):int(t1 * 100)] <= th; best = cur_ = 0
                    for v in q: cur_ = cur_ + 1 if v else 0; best = max(best, cur_)
                    return best >= 12
                if tail and not pause(b - 0.05, b + 0.6): notes.append(f"outer tail: source goes on '{' '.join(tail[:3])}' right after the cut")
                if head and not pause(a - 0.6, a + 0.05): notes.append(f"outer head: source has '{' '.join(head[-3:])}' right before the cut")
            flags += len(notes)
            lab = f"rows {run[0] + 1}-{run[-1] + 1}" if len(run) > 1 else f"row {run[0] + 1}"
            print(f"{lab:12s} {'OK  ' if not notes else 'FLAG'} | {' '.join(K)[:80]}" + "".join(f"\n             {m}" for m in notes))
    print(f"{os.path.basename(edl)}: {flags} flag(s) over {len(runs)} runs")

if __name__ == "__main__":
    main()
