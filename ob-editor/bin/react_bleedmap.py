#!/usr/bin/env python3
"""Exact map of every clip's audio inside OB's mic (plays, pauses, replays, aborted starts), at 0.1 s steps.

  python3 -I react_bleedmap.py WORK_DIR     -> WORK/bleedmap.json

clipmatch.py finds plays with 4 s chunks on a 1 s grid: it misses aborted starts shorter than ~4 s (OB's laptop sometimes
restarts a clip on play) and rounds play edges to whole clip seconds, which put repeat cuts in the wrong place (C4353 0:47
cut OB off). Here, per clip and offset (known plays + short occurrences found by a 1.2 s template of the opening), the
clip's spectrogram is turned into the bleed it would leave in the mic (|H(f)| = median |mic|/|clip| over the play), and
every 0.1 s: R = share of the predicted bleed energy that the mic actually holds, in the clip's loud bins.
  R >= 0.55 -> playing; R <= 0.25 with the mic quiet -> not playing; OB talking over it (mic far above the bleed) = unknown.
Unknown frames between two playing frames count as playing (a talk-over); a play ends at its last playing frame.
"""
import json, os, sys
import numpy as np
from scipy.ndimage import uniform_filter1d
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from clipmatch import features, load16, Recording, SR

W = sys.argv[1]; N, HOPS = 1024, 160            # 16 kHz STFT, 10 ms hop; decisions every 0.1 s
mic = load16(f"{W}/mic16.wav")


def spec(x, a, b):   # |STFT| of x[a:b] (samples), frames every HOPS
    seg = x[max(0, a): b]
    if a < 0: seg = np.concatenate([np.zeros(-a), seg])
    n = 1 + (len(seg) - N) // HOPS
    if n <= 0: return np.zeros((N // 2 + 1, 0))
    idx = np.arange(N)[None, :] + HOPS * np.arange(n)[:, None]
    return np.abs(np.fft.rfft(seg[idx] * np.hanning(N), axis=1)).T


def track(cx, off, lo, hi):
    """Presence of clip cx at offset off (s) over rec [lo, hi]: list of (t, state) every 0.1 s, plus |H|."""
    a, b = int(lo * SR), int(hi * SR)
    Y = spec(mic, a, b); X = spec(cx, int((lo - off) * SR), int((hi - off) * SR)); n = min(Y.shape[1], X.shape[1]); Y, X = Y[:, :n], X[:, :n]
    act = X.sum(0) > np.percentile(X.sum(0), 40)
    Hm = np.median(Y[:, act] / (X[:, act] + 1e-9), axis=1) if act.any() else np.ones(Y.shape[0])
    B = Hm[:, None] * uniform_filter1d(X, 5, axis=1)
    out = []
    for f in range(0, n - 10, 10):
        Bs, Ys = B[:, f:f + 10], Y[:, f:f + 10]
        loud = Bs.mean(1) > np.percentile(Bs.mean(1), 70)
        eb = (Bs[loud] ** 2).sum(); ey = (Ys[loud] ** 2).sum()
        if eb < 1e-12: out.append((lo + (f + 5) * HOPS / SR, "silent")); continue
        R = (np.minimum(Ys[loud], Bs[loud]) ** 2).sum() / eb
        state = "talk" if ey > 6 * eb and R > 0.55 else ("play" if R >= 0.55 else ("off" if R <= 0.25 else "?"))
        out.append((lo + (f + 5) * HOPS / SR, state))
    return out, Hm


def runs(tr, off, min_len=0.6):
    """Playing runs: 'play' frames, bridged across 'talk'/'?'/'silent' gaps when both sides play."""
    occ, cur, last_play = [], None, None
    for t, s in tr:
        if s == "play":
            if cur is None: cur = [t, t]
            else: cur[1] = t
            last_play = t
        elif s == "off":
            if cur and cur[1] - cur[0] >= min_len: occ.append(cur)
            cur = None
    if cur and cur[1] - cur[0] >= min_len: occ.append(cur)
    return [{"rec_in": round(a - 0.05, 2), "rec_out": round(b + 0.05, 2), "clip_in": round(a - 0.05 - off, 2), "clip_out": round(b + 0.05 - off, 2),
             "offset": round(off, 3)} for a, b in occ]


segs = json.load(open(f"{W}/matches_mic.json")); names = {}
for line in open(f"{W}/clips_index.txt"):
    k, name, *_ = line.rstrip("\n").split("\t"); names[name] = k
RF = features(mic); REC = Recording.__new__(Recording)
REC.F = RF; REC.n = RF.shape[1]; REC.L = 1 << int(np.ceil(np.log2(REC.n + 400 + 1))); REC.RF = np.fft.rfft(RF, n=REC.L, axis=1)
REC.cs = np.concatenate([[0], np.cumsum((RF ** 2).sum(0))])
out = {}
for m in segs:
    clip = m["clip"]; k = names.get(clip, "?"); cx = load16(f"{W}/clips/{clip}"); dur = len(cx) / SR
    offs = {round(s["rec_in"] - s["clip_in"], 3): (s["rec_in"], s["rec_out"]) for s in m["segments"]}
    CF = features(cx); z = REC.ncc(CF[:, 10:70]); zz = (z - np.median(z)) / (np.std(z) + 1e-9)
    for p in np.argsort(zz)[::-1][:20]:   # short occurrences of the clip's opening at a new offset (aborted starts)
        if zz[p] < 9: break
        o = round((p - 10) / 50, 3)
        if all(abs(o - x) > 0.5 for x in offs): offs[o] = (o, o + 6)
    occ = []
    for o, (r0, r1) in sorted(offs.items()):
        tr, _ = track(cx, o, max(0, r0 - 4), min(len(mic) / SR, r1 + 4, o + dur))
        occ += runs(tr, o)
    occ.sort(key=lambda r: r["rec_in"])
    out[k] = {"clip": clip, "duration": round(dur, 2), "occurrences": occ}
    print(k, f"{len(occ)}:", [(o["rec_in"], o["rec_out"], o["clip_in"], o["clip_out"]) for o in occ], flush=True)
json.dump(out, open(f"{W}/bleedmap.json", "w"), indent=1)
