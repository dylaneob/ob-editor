#!/usr/bin/env python3
"""Exact play edges + aborted starts for a reaction take (C4354, 2026-10-17).

clipmatch.py finds each play of each clip with 4 s chunks on a 1 s grid, so its edges can be ~1-2 s off (C4353 lost
sentence endings and kept double starts that way). Its offset (recording time - clip time) is good to ~1 ms. Here each
play's edges are re-found at that fixed offset: whitened cross-correlation of mic vs clip in 0.4 s windows every 50 ms,
+-2 ms around the offset; the play runs where it stays above a threshold set between the play's own level and the
level at a wrong lag. Starts within 0.6 s of clip 0 snap to 0 and ends within 0.6 s of the clip's end snap to the end.
Then, before every play, the clip's own opening (first 3 s of audio) is searched for in the 25 s of mic before it at any
lag: a hit at another offset is an aborted start (OB's laptop refreshes on play) and goes in "aborted".

  python3 -I react_edges.py WORK_DIR    (matches_mic.json -> kept as matches_mic_raw.json; writes the refined
                                          matches_mic.json and qc/edges_report.txt)
"""
import json, os, shutil, sys
import numpy as np
from scipy.io import wavfile
from scipy.ndimage import uniform_filter1d
from scipy.signal import stft, istft

W = sys.argv[1]; SR = 16000
if not os.path.exists(f"{W}/matches_mic_raw.json"): shutil.copy2(f"{W}/matches_mic.json", f"{W}/matches_mic_raw.json")
raw = json.load(open(f"{W}/matches_mic_raw.json"))
index = {l.split("\t")[1]: int(l.split("\t")[0][1:]) for l in open(f"{W}/clips_index.txt")}
_, mic = wavfile.read(f"{W}/mic16.wav"); mic = mic.astype(np.float64) / 32768


def whiten(x):
    if len(x) < 1024: return np.zeros(len(x))
    f, t, Z = stft(x, SR, nperseg=512, noverlap=384)
    Z = Z / (uniform_filter1d(np.abs(Z), 9, axis=0) + 1e-6); Z[(f < 250) | (f > 3500)] = 0
    _, y = istft(Z, SR, nperseg=512, noverlap=384); y = y[: len(x)]
    return np.pad(y, (0, len(x) - len(y)))


def corr_track(clip, off, t0, t1, hw=0.2, hop=0.05, slack=32):
    """normalised correlation of mic around time t vs clip at t - off (best within +-slack samples), t in [t0, t1]"""
    a, b = int(max(0, t0 - hw - 0.1) * SR), int(min(len(mic) / SR, t1 + hw + 0.1) * SR)
    mw = whiten(mic[a:b]); c0 = a - int(round(off * SR)) - slack
    seg = clip[max(0, c0):max(0, c0 + (b - a) + 2 * slack)]
    cw = np.zeros((b - a) + 2 * slack); cw[max(0, -c0):max(0, -c0) + len(seg)] = whiten(seg)[: len(cw) - max(0, -c0)]
    ts, out, H = [], [], int(hw * SR)
    for t in np.arange(t0, t1, hop):
        i = int(t * SR) - a
        if i - H < 0 or i + H > len(mw): continue
        y = mw[i - H:i + H]; ny = np.sqrt((y ** 2).sum()) + 1e-9; best = 0.0
        for d in range(0, 2 * slack + 1, 2):
            v = cw[i - H + d:i + H + d]; nv = np.sqrt((v ** 2).sum())
            if nv > 1e-9: best = max(best, float(np.dot(y, v) / (ny * nv)))
        ts.append(t); out.append(best)
    return np.array(ts), np.array(out)


def phat_find(seg, t_lo, t_hi):
    """best place of seg (clip audio) inside mic[t_lo, t_hi]: (time, strength)"""
    a, b = int(max(0, t_lo) * SR), int(min(len(mic) / SR, t_hi) * SR); x = mic[a:b]
    if len(x) <= len(seg): return None
    N = 1 << int(np.ceil(np.log2(len(x) + len(seg))))
    X = np.fft.rfft(x, N); Y = np.fft.rfft(seg, N); P = X * np.conj(Y); P /= np.abs(P) + 1e-9
    f = np.fft.rfftfreq(N, 1 / SR); P[(f < 250) | (f > 3500)] = 0
    r = np.fft.irfft(P)[: len(x) - len(seg)]; i = int(np.argmax(r))
    return a / SR + i / SR, float(r[i] / (np.median(np.abs(r)) + 1e-12))


clips, out, rep = {}, [], []
for m in raw:
    k = index[m["clip"]]
    if k not in clips:
        _, c = wavfile.read(f"{W}/cliptx/c{k:02d}.wav"); clips[k] = c.astype(np.float64) / 32768
    clip = clips[k]; dur = len(clip) / SR; segs = []
    for s in m["segments"]:
        off = s["rec_in"] - s["clip_in"]
        lo, hi = max(off, s["rec_in"] - 4), min(off + dur, s["rec_out"] + 4)
        ts, cc = corr_track(clip, off, lo, hi)
        _, bg = corr_track(clip, off + 0.37, lo, hi)   # same audio at a wrong lag: the noise floor
        inside = (ts >= s["rec_in"] + 1) & (ts <= s["rec_out"] - 1)
        lvl = np.median(cc[inside]) if inside.sum() > 5 else np.median(cc)
        thr = max(np.percentile(bg, 95) * 1.3, 0.35 * lvl, 0.05)
        on = uniform_filter1d((cc > thr).astype(float), 9) > 0.5   # 0.45 s majority vote
        # clipmatch's chunks prove the clip plays inside the raw segment, so only the edges move: the start is the first
        # window near raw_in after which it stays on for 1 s, the end the last window near raw_out after 1 s of on
        need = 20; rin = rout = None
        for i in range(len(ts)):
            if ts[i] > s["rec_in"] + 4: break
            if ts[i] >= s["rec_in"] - 4 and on[i:i + need].all(): rin = float(ts[i]) - 0.1; break
        for i in range(len(ts) - 1, -1, -1):
            if ts[i] < s["rec_out"] - 4: break
            if ts[i] <= s["rec_out"] + 4 and i - need >= 0 and on[i - need + 1:i + 1].all(): rout = float(ts[i]) + 0.1; break
        rin = s["rec_in"] if rin is None else rin; rout = s["rec_out"] if rout is None else rout
        cin, cout = rin - off, rout - off
        # snap to the clip's own start/end: always within 0.6 s, and within 1.5 s when clipmatch itself saw the play
        # start at clip 0 / run to the end (C4354: the openings of #1, #5, #7 are quieter than the rest)
        if cin < 0.6 or (cin < 1.5 and s["clip_in"] < 0.05): cin = 0.0; rin = off
        if dur - cout < 0.6 or (dur - cout < 1.5 and dur - s["clip_out"] < 1.0): cout = dur; rout = off + dur
        seg = dict(clip=m["clip"], rec_in=round(rin, 3), rec_out=round(rout, 3), clip_in=round(cin, 3), clip_out=round(cout, 3),
                   raw_in=s["rec_in"], raw_out=s["rec_out"], offset=round(off, 4), level=round(float(lvl), 3), thr=round(float(thr), 3),
                   z_med=s.get("z_med"), chunks=s.get("chunks"))
        segs.append(seg)
        rep.append(f"#{k} play raw {s['rec_in']:8.2f}-{s['rec_out']:8.2f} -> {rin:8.2f}-{rout:8.2f}  clip {cin:6.2f}-{cout:6.2f} of {dur:5.1f}  (level {lvl:.2f}, thr {thr:.2f})")
    out.append(dict(clip=m["clip"], segments=segs))

# aborted starts: the clip's opening heard at another offset in the 25 s before a play
aborted = []
for m in out:
    k = index[m["clip"]]; clip = clips[k]
    nz = np.flatnonzero(np.abs(clip) > 0.02); c0 = nz[0] / SR if len(nz) else 0.0
    head = clip[int(c0 * SR):int((c0 + 3.0) * SR)]
    for s in m["segments"]:
        lo = s["rec_in"] - 25; hi = s["rec_in"] - 0.5
        while hi - lo > 4:
            hit = phat_find(head, lo, hi)
            if not hit or hit[1] < 14: break
            t, z = hit; off2 = t - c0
            if abs(off2 - s["offset"]) < 0.5: break
            ts, cc = corr_track(clip, off2, t, min(t + 15, s["rec_in"]))
            _, bg = corr_track(clip, off2 + 0.37, t, min(t + 15, s["rec_in"]))
            thr = max(np.percentile(bg, 95) * 1.3, 0.05) if len(bg) else 0.05
            on = uniform_filter1d((cc > thr).astype(float), 9) > 0.5
            off_i = np.flatnonzero(~on); end = float(ts[off_i[0]]) if len(off_i) else (float(ts[-1]) if len(ts) else t + 1.0)
            aborted.append(dict(clip=m["clip"], k=k, rec_in=round(t - 0.1, 3), rec_out=round(end, 3), clip_in=round(c0, 3), strength=round(z, 1), before_play=s["rec_in"]))
            rep.append(f"#{k} ABORTED START {t:8.2f}-{end:8.2f} (clip opening, strength {z:.0f}) before the play at {s['rec_in']:.2f}")
            hi = t - 0.5
json.dump(out, open(f"{W}/matches_mic.json", "w"), indent=1)
json.dump(aborted, open(f"{W}/aborted_starts.json", "w"), indent=1)
open(f"{W}/qc/edges_report.txt", "w").write("\n".join(rep) + "\n"); print("\n".join(rep))
