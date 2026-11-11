#!/usr/bin/env python3
"""What really happens in the room at every play edge (C4354 final audit, 2026-10-17: "make sure u dont cut me off, no
repeats on showing reaction").

react_edges.py places edges with 0.4 s windows and a 0.45 s vote, so an edge can sit 0.2-0.7 s off the moment OB clicked
pause / play. Then the clip's last word plays on as room echo inside his shot, a resumed clip is heard twice (echo, then
clean), or his first word lands inside the play where his mic is muted. Per edge this measures, at the clip's physical
offset (matches_mic.json):
  * audible: the clip heard in the room (whitened correlation of mic vs clip, 0.2 s windows every 20 ms, above the play's
    threshold, where the clip itself is not silent); the physical stop / start is where that runs out (gaps <= 0.8 s
    inside the clip's own pauses are bridged)
  * OB's own words: his mic with the clip's bleed spectrally removed (only inside the physical span), transcribed with
    whisper DTW; voiced = residual 20 ms level above -42 dBFS

  python3 -I react_edge_truth.py WORK_DIR   -> qc/edge_truth.json (+ qc/edge_truth/*.wav snippets)
"""
import json, os, re, subprocess, sys
import numpy as np
from scipy.io import wavfile
from scipy.ndimage import maximum_filter1d, uniform_filter1d
from scipy.signal import stft, istft

W = sys.argv[1]; SR = 16000; MODEL = os.path.expanduser("~/.whisper-models/ggml-medium.en.bin")
OUT = f"{W}/qc/edge_truth"; os.makedirs(OUT, exist_ok=True)
gate = sorted(json.load(open(f"{W}/gate.json")), key=lambda g: g["rec_in"])
ref = json.load(open(f"{W}/matches_mic.json"))
idx = {l.split("\t")[1]: int(l.split("\t")[0][1:]) for l in open(f"{W}/clips_index.txt")}
_, mic = wavfile.read(f"{W}/mic16.wav"); mic = mic.astype(np.float64) / 32768
clips = {}


def clip(k):
    if k not in clips: _, c = wavfile.read(f"{W}/cliptx/c{k:02d}.wav"); clips[k] = c.astype(np.float64) / 32768
    return clips[k]


def seg(x, a, n):   # x[a:a+n] with zeros outside
    out = np.zeros(n); lo, hi = max(0, a), min(len(x), a + n)
    if hi > lo: out[lo - a:hi - a] = x[lo:hi]
    return out


def whiten(x):
    if len(x) < 1024: return np.zeros(len(x))
    f, t, Z = stft(x, SR, nperseg=512, noverlap=384)
    Z = Z / (uniform_filter1d(np.abs(Z), 9, axis=0) + 1e-6); Z[(f < 250) | (f > 3500)] = 0
    _, y = istft(Z, SR, nperseg=512, noverlap=384); y = y[: len(x)]
    return np.pad(y, (0, len(x) - len(y)))


def corr_track(c, off, t0, t1, hw=0.1, hop=0.02, slack=32):
    a = int((t0 - hw - 0.1) * SR); n = int((t1 - t0 + 2 * hw + 0.2) * SR)
    mw = whiten(seg(mic, a, n)); cw = whiten(seg(c, a - int(round(off * SR)) - slack, n + 2 * slack))
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


def lvl20(x):
    n = len(x) // 320; return 10 * np.log10((x[:n * 320].reshape(n, 320) ** 2).mean(1) + 1e-12)


NF, HOP = 1024, 256
def transfer(k, off, t0, t1, talk):   # |mic| / |clip| per frequency where only the clip sounds (as react_render.play_hm)
    a = int(t0 * SR); n = int((t1 - t0) * SR); y = seg(mic, a, n); x = seg(clip(k), a - int(round(off * SR)), n)
    _, _, Y = stft(y, SR, nperseg=NF, noverlap=NF - HOP); _, _, X = stft(x, SR, nperseg=NF, noverlap=NF - HOP)
    tt = t0 + np.arange(Y.shape[1]) * HOP / SR; quiet = np.ones(len(tt), bool)
    for a_, b_ in talk: quiet &= ~((tt > a_ - 0.3) & (tt < b_ + 0.3))
    mag = np.abs(X).sum(0); act = quiet & (mag > np.percentile(mag, 40))
    return np.median(np.abs(Y[:, act]) / (np.abs(X[:, act]) + 1e-9), axis=1) if act.sum() > 20 else None


def suppress(y, x, hm, beta=2.0, floor=0.1):
    _, _, Y = stft(y, SR, nperseg=NF, noverlap=NF - HOP); _, _, X = stft(x, SR, nperseg=NF, noverlap=NF - HOP)
    B = hm[:, None] * maximum_filter1d(uniform_filter1d(np.abs(X), 3, axis=1), 9, axis=1)
    G = uniform_filter1d(np.clip(1 - beta * B / (np.abs(Y) + 1e-9), floor, 1.0), 3, axis=0)
    _, z = istft(Y * G, SR, nperseg=NF, noverlap=NF - HOP); z = z[: len(y)]
    return np.pad(z, (0, len(y) - len(z)))


def whisper_words(wav, t_base):
    js = wav[:-4]
    subprocess.run(["whisper-cli", "-m", MODEL, "-f", wav, "-l", "en", "-t", "6", "-np", "-nfa", "-dtw", "medium.en", "-ojf", "-of", js],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    J = json.load(open(js + ".json"))["transcription"]; words = []
    for sg in J:
        cur = []
        for tk in sg.get("tokens", []):
            tx = tk["text"]
            if tx.startswith("[_") or tk.get("t_dtw", -1) < 0: continue
            if tx.startswith(" ") or not cur: cur.append([tk["t_dtw"] / 100, tx.strip()])
            else: cur[-1][0] = tk["t_dtw"] / 100; cur[-1][1] += tx
        words += [[round(t_base + e, 2), w] for e, w in cur if re.search(r"[A-Za-z0-9]", w)]
    return words   # [end time, word]


def physical(g):   # the refined (physical) segment behind a gate play: same clip, biggest overlap
    k = g["k"]; m = next(m for m in ref if idx[m["clip"]] == k)
    best = max(m["segments"], key=lambda s: min(s["rec_out"], g["rec_out"]) - max(s["rec_in"], g["rec_in"]))
    return best


res = []
for g in gate:
    k = g["k"]; p = physical(g); off = g["offset"] if k == 8 else p["offset"]; c = clip(k)
    ts, cc = corr_track(c, off, g["rec_in"] + 0.5, g["rec_out"] - 0.5)
    _, bg = corr_track(c, off + 0.37, g["rec_in"] + 0.5, g["rec_out"] - 0.5)
    thr = max(np.percentile(bg, 95) * 1.3 if len(bg) else 0.05, 0.3 * (np.median(cc) if len(cc) else 0.2), 0.06)
    cl_db = lvl20(c); c_floor = max(-50.0, float(np.percentile(cl_db, 10)) + 10)
    hm = transfer(k, off, g["rec_in"], g["rec_out"], g.get("ob_speech", []))
    for side in ("start", "end"):
        E = g["rec_in"] if side == "start" else g["rec_out"]
        lo, hi = (E - 2.5, E + 1.5) if side == "start" else (E - 1.5, E + 2.5)
        t2, c2 = corr_track(c, off, lo, hi)
        ci = np.clip(((t2 - off) * 50).astype(int), 0, len(cl_db) - 1)
        aud = (c2 > thr) & (cl_db[ci] > c_floor)
        # walk out from inside the play; bridge the clip's own pauses up to 0.8 s
        order = range(len(t2) - 1, -1, -1) if side == "start" else range(len(t2))
        inside = [i for i in order if (t2[i] >= E - 0.3 if side == "start" else t2[i] <= E + 0.3)]
        last, edge = None, None
        for i in order:
            if not aud[i]: continue
            if last is None:
                if (side == "start" and t2[i] < E - 1.0) or (side == "end" and t2[i] > E + 1.0): break
            elif abs(t2[i] - last) > 0.8: break
            last = t2[i]
        if last is not None: edge = round(last - 0.1, 2) if side == "start" else round(last + 0.1, 2)
        # his own words: bleed removed only where the clip physically sounds
        a = int(lo * SR); n = int((hi - lo) * SR); y = seg(mic, a, n); x = seg(c, a - int(round(off * SR)), n)
        ps, pe = (edge if side == "start" and edge else E), (edge if side == "end" and edge else E)
        span0, span1 = (ps, g["rec_out"]) if side == "start" else (g["rec_in"], pe)
        tt = lo + np.arange(n) / SR; x = x * ((tt >= span0 - 0.05) & (tt <= span1 + 0.05))
        z = suppress(y, x, hm) if hm is not None else y
        wav = f"{OUT}/{side}_{E:08.2f}_c{k}.wav"; wavfile.write(wav, SR, (np.clip(z, -1, 1) * 32767).astype(np.int16))
        wavfile.write(wav.replace(".wav", "_raw.wav"), SR, (np.clip(y, -1, 1) * 32767).astype(np.int16))
        ow = whisper_words(wav, lo)
        rz = lvl20(z); tz = lo + 0.01 + np.arange(len(rz)) * 0.02; voiced = tz[rz > -42]
        cw = json.load(open(f"{W}/cliptx/c{k:02d}_words.json"))["words"]
        clipw = [[round(w[1] + off, 2), w[2]] for w in cw if lo <= w[1] + off <= hi]
        r = dict(k=k, side=side, E=E, offset=off, gate_offset=g["offset"], clip_t=round(E - g["offset"], 3), phys=edge,
                 ob_words=ow, clip_words=clipw, voiced=[round(float(v), 2) for v in voiced], thr=round(float(thr), 3))
        res.append(r)
        d = f"{edge - E:+.2f}" if edge is not None else "none"
        print(f"c{k} {side:5s} E {E:8.3f} (clip {E - g['offset']:6.2f})  physical {edge} ({d})")
        print(f"      clip: {' '.join(f'{w[1]}<{w[0]:.2f}' for w in clipw)}")
        print(f"      OB  : {' '.join(f'{w[1]}<{w[0]:.2f}' for w in ow)}")
        vs = [v for v in voiced if abs(v - E) < 1.2]
        print(f"      OB voiced within 1.2 s of E: {vs[0] - E:+.2f} .. {vs[-1] - E:+.2f} ({len(vs) * 0.02:.2f} s)" if vs else "      OB voiced within 1.2 s of E: none", flush=True)
json.dump(res, open(f"{W}/qc/edge_truth.json", "w"), indent=1)
