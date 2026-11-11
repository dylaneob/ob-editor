#!/usr/bin/env python3
"""Find the audible breaths left inside a talking-head cut, and cut them like pauses (OB 2026-10-30 on the C4398/C4402 previews:
"seem you kept me breathing hard in some of it so the audio level raised tricking you in think i was talking"; C4372 10-23:
"cut the breaths"). The flow pass only drops gaps quieter than about -45 dB, so an inhale between two phrases counts as sound and
stays. Here a breath is unvoiced noise between his words: no pitch, louder than the room, 0.18-1.2 s long, not glued to a word
(a fricative like the "s" of "this" sits within ~40 ms of voicing and is shorter), spectral centre under ~3.5 kHz.

  python3 -I breaths.py WORK CUTLIST.json                  report: every breath with its level vs his speech, edge or mid-shot
  python3 -I breaths.py WORK CUTLIST.json --apply OUT.json [--min-rel -30]
      trims an edge breath off its shot; a mid-shot breath splits the shot: the gap between the two phrases closes to AIR_L + AIR_R
      of air (0.09 + 0.07 s), the second piece takes the other framing, and the framing of the shots after it flips until the cut
      alternates again (no same-framing jump). Clip holds and their neighbours' edges are left alone.
Audio: WORK/master_synced.wav (camera seconds, the same clock as the cutlist's src_in/src_out); speech probabilities:
WORK/qc/vad_probs.npy (~/OpenMontage/.venv/bin/python vad_probs.py WORK/master_synced.wav WORK/qc/vad_probs.npy)."""
import argparse, json, os, subprocess, sys
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfiltfilt, resample_poly

SR = 16000; HOP = 0.01; WIN = 0.03
AIR_L, AIR_R = 0.09, 0.07       # air kept after the phrase before the breath, and before the phrase after it


def _ff(path, a=None, b=None, sr=None, mono=True):
    cmd = ["ffmpeg", "-nostdin", "-loglevel", "error"] + (["-ss", f"{a:.6f}", "-t", f"{b - a:.6f}"] if a is not None else []) + ["-i", path]
    cmd += (["-ac", "1"] if mono else []) + (["-ar", str(sr)] if sr else []) + ["-f", "f32le", "-"]
    return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, np.float32).astype(np.float64)


def load(path, a, b):
    """Mono 16 kHz between a and b (s). WAVs scipy can map are sliced directly; 24-bit ones go through ffmpeg."""
    try:
        sr, x = wavfile.read(path, mmap=True)
    except ValueError:
        return _ff(path, a, b, SR)
    seg = np.asarray(x[int(a * sr): int(b * sr)], np.float64)
    if seg.ndim > 1: seg = seg.mean(1)
    if x.dtype.kind == "i": seg /= float(np.iinfo(x.dtype).max)
    return resample_poly(seg, SR, sr) if sr != SR else seg


SOS_V = butter(4, [60, 1000], btype="band", fs=SR, output="sos")


def frames(y):
    """Per 10 ms: level (dB over 30 ms), voicing (1 - YIN's cumulative-mean-normalised difference minimum at 70-400 Hz, over
    40 ms: about 0.75+ on his voiced speech, under 0.5 on air and fricatives), spectral centre (Hz)."""
    h, w = int(HOP * SR), int(WIN * SR); n = max(0, (len(y) - 640) // h + 1)
    if n == 0: return np.zeros(0), np.zeros(0), np.zeros(0)
    idx = np.arange(w)[None, :] + h * np.arange(n)[:, None]
    F = y[idx] * np.hanning(w); lv = 10 * np.log10((F ** 2).mean(1) + 1e-12)
    yb = sosfiltfilt(SOS_V, y) if len(y) > 30 else y
    W2 = 640; tmax = int(SR / 70); tmin = int(SR / 400)
    B = yb[np.arange(W2)[None, :] + h * np.arange(n)[:, None]]
    L = W2 - tmax                                              # the compared length, the same for every lag
    e0 = (B[:, :L] ** 2).sum(1)
    c = np.cumsum(B ** 2, axis=1); c = np.concatenate([np.zeros((n, 1)), c], 1)
    et = c[:, np.arange(1, tmax + 1) + L] - c[:, np.arange(1, tmax + 1)]   # energy of B[tau:tau+L]
    S1 = np.fft.rfft(B[:, :L], 2 * W2); S2 = np.fft.rfft(B, 2 * W2)
    xc = np.fft.irfft(np.conj(S1) * S2, 2 * W2)[:, 1:tmax + 1]            # sum B[j] B[j+tau]
    d = e0[:, None] + et - 2 * xc                                          # YIN difference d(tau), tau = 1..tmax
    cm = d * np.arange(1, tmax + 1)[None, :] / (np.cumsum(d, 1) + 1e-12)
    voi = 1 - cm[:, tmin - 1:].min(1)
    M = np.abs(np.fft.rfft(F, axis=1)); f = np.fft.rfftfreq(w, 1 / SR)
    cen = (M * f).sum(1) / (M.sum(1) + 1e-12)
    return lv, np.clip(voi, 0, 1), cen


def runs(mask):
    out, i, n = [], 0, len(mask)
    while i < n:
        if mask[i]:
            j = i
            while j < n and mask[j]: j += 1
            out.append((i, j)); i = j
        else: i += 1
    return out


def detect(work, cut):
    """Air between his words. A frame is speech if Silero VAD says so (WORK/qc/vad_probs.npy from vad_probs.py, 32 ms windows) or it
    is pitched and loud; it is air if the VAD calls it non-speech, it is unpitched, and it is 4 dB+ over the room (C4398 10-30: the inhale he heard
    before "Back" sat at -46 to -54 dB, 3-11 dB over the room, VAD 0.00, centre 2.0-2.9 kHz)."""
    segs = cut["segments"]; master = f"{work}/master_synced.wav"
    vp = np.load(f"{work}/qc/vad_probs.npy")
    P = lambda t: vp[np.clip((np.asarray(t) / 0.032).astype(int), 0, len(vp) - 1)]
    per, allv = [], []
    for k, s in enumerate(segs):
        if s.get("hold"): per.append(None); continue
        y = load(master, s["src_in"], s["src_out"]); lv, voi, cen = frames(y)
        t = s["src_in"] + np.arange(len(lv)) * HOP + WIN / 2
        per.append((lv, voi, cen, P(t))); allv.append(lv[(voi > 0.75) & (P(t) > 0.6)])
    av = np.concatenate([v for v in allv if len(v)]); ref = float(np.percentile(av, 70))          # his speech level
    alll = np.concatenate([p[0] for p in per if p is not None]); floor = float(np.percentile(alll, 8))
    found = []
    for k, (s, p) in enumerate(zip(segs, per)):
        if p is None: continue
        lv, voi, cen, vprob = p
        speech = (vprob > 0.5) | ((voi > 0.7) & (lv > floor + 12))
        cand = (vprob < 0.5) & (lv > floor + 4) & (voi < 0.62) & (lv < ref - 12)   # 12 dB+ under speech: a plosive or word onset is louder
        r = runs(cand); merged = []
        for a_, b_ in r:                                   # close 60 ms holes so one breath with a dip is one run
            if merged and a_ - merged[-1][1] <= 6: merged[-1] = (merged[-1][0], b_)
            else: merged.append((a_, b_))
        sidx = np.flatnonzero(speech)
        for a_, b_ in merged:
            d = (b_ - a_) * HOP
            if not 0.15 <= d <= 1.2: continue
            c = float(np.median(cen[a_:b_]))
            if not 800 <= c <= 3800: continue               # an "s" (higher) or a thump/handling noise (lower), not air
            prev_s = sidx[sidx < a_]; next_s = sidx[sidx >= b_]
            pk = float(np.max(np.convolve(10 ** (lv[a_:b_] / 10), np.ones(10) / 10, "same")))
            rel = 10 * np.log10(pk + 1e-12) - ref
            t0, t1 = s["src_in"] + a_ * HOP + WIN / 2, s["src_in"] + b_ * HOP + WIN / 2
            # the phrase before ends at pv, the phrase after starts at nv (camera seconds); None = the shot's edge
            pv = s["src_in"] + (prev_s[-1] + 1) * HOP + WIN / 2 if len(prev_s) else None
            nv = s["src_in"] + next_s[0] * HOP + WIN / 2 if len(next_s) else None
            found.append(dict(seg=k, t0=round(t0, 3), t1=round(t1, 3), dur=round(d, 2), rel_db=round(rel, 1), centre=round(c),
                              prev_voice=None if pv is None else round(pv, 3), next_voice=None if nv is None else round(nv, 3),
                              where="start" if pv is None else ("end" if nv is None else "mid")))
    return found, ref, floor


def edit_time(segs, k, t):
    s = segs[k]; return s["edit_in"] + (t - s["src_in"])


def apply(cut, found, min_rel):
    segs = [dict(s) for s in cut["segments"]]; flips = 0; n_edge = n_mid = 0
    by = {}
    for f in found:
        if f["rel_db"] >= min_rel: by.setdefault(f["seg"], []).append(f)
    out = []
    for k, s in enumerate(segs):
        bs = sorted(by.get(k, []), key=lambda f: f["t0"])
        if not bs or s.get("hold"): out.append(s); continue
        # neighbours that are clip holds keep their join exactly as it was
        lock_l = k > 0 and segs[k - 1].get("hold"); lock_r = k + 1 < len(segs) and segs[k + 1].get("hold")
        pieces = [[s["src_in"], s["src_out"]]]
        for f in bs:
            if f["where"] == "start" and not lock_l:
                pieces[0][0] = max(pieces[0][0], f["next_voice"] - AIR_R); n_edge += 1
            elif f["where"] == "end" and not lock_r:
                pieces[-1][1] = min(pieces[-1][1], f["prev_voice"] + AIR_L); n_edge += 1
            elif f["where"] == "mid":
                a, b = f["prev_voice"] + AIR_L, f["next_voice"] - AIR_R
                if b - a < 0.12: continue                               # nothing worth a cut
                last = pieces[-1]
                if not last[0] < a < b < last[1]: continue
                pieces[-1] = [last[0], a]; pieces.append([b, last[1]]); n_mid += 1
        fr = s.get("framing", "wide")
        for j, (a, b) in enumerate(pieces):
            if b - a < 0.25: continue
            ns = dict(s); ns["src_in"], ns["src_out"] = round(a, 6), round(b, 6); ns["dur"] = round(b - a, 6)
            ns["framing"] = fr if j % 2 == 0 else ("wide" if fr == "punch" else "punch")
            ns.pop("punch_at", None) if j else None
            if j: ns["breath_split"] = True
            out.append(ns)
        if len(pieces) % 2 == 0:   # an odd number of new cuts: flip the framing after this shot until the cut alternates again
            i = len(out)
            for m in range(k + 1, len(segs)):
                nxt = segs[m]
                if nxt.get("hold"): break
                prv = segs[m - 1]
                was_same = prv.get("framing") == nxt.get("framing") and not prv.get("hold")
                if was_same and m > k + 1: break                       # the original cut already broke here: stop flipping
                nxt["framing"] = "wide" if nxt.get("framing") == "punch" else "punch"; flips += 1
    # renumber the edit clock
    t = 0.0
    for i, s in enumerate(out):
        s["i"] = i; s["edit_in"] = round(t, 6); t += s["src_out"] - s["src_in"]; s["edit_out"] = round(t, 6)
    nc = dict(cut); nc["segments"] = out
    nc["breaths_cut"] = dict(min_rel_db=min_rel, edge_trims=n_edge, mid_cuts=n_mid, framing_flips=flips)
    return nc, n_edge, n_mid, flips


def edges(work, cut, ref=None, floor=None):
    """The breaths that matter most sit at a shot's edges: the cut keeps everything above about -50 dB before the first word and
    after the last, so a big inhale before a new line (C4398 2:08, 0.42 s before "Back") rides in as "speech". For each shot: the
    first and last strong speech frames, widened over word-edge consonants (an "s" or a plosive burst stays with its word), and the
    air outside them; if 0.12 s+ of that air is breath, the edge moves to 0.08 s before the first word / 0.10 s after the last.
    Returns [(seg index, new src_in or None, new src_out or None, head breath s, tail breath s)]."""
    segs = cut["segments"]; vp = np.load(f"{work}/qc/vad_probs.npy"); master = f"{work}/master_synced.wav"
    if ref is None or floor is None:
        _, ref, floor = detect(work, cut)
    out = []
    for k, s in enumerate(segs):
        if s.get("hold") or s["src_out"] - s["src_in"] < 0.6: continue
        y = load(master, s["src_in"], s["src_out"]); lv, voi, cen = frames(y); n = len(lv)
        if n < 20: continue
        t = s["src_in"] + np.arange(n) * HOP + WIN / 2; vv = vp[np.clip((t / 0.032).astype(int), 0, len(vp) - 1)]
        strong = ((voi > 0.7) & (lv > ref - 22)) | ((vv > 0.8) & (lv > ref - 15))
        idx = np.flatnonzero(strong)
        if not len(idx): continue
        cons = lambda i: (cen[i] > 3500 and lv[i] > floor + 8) or lv[i] > ref - 18
        on = idx[0]; lim = max(0, on - 25)
        while on > lim and cons(on - 1): on -= 1
        off = idx[-1] + 1; lim = min(n, off + 25)
        while off < lim and cons(off): off += 1
        air = (voi < 0.62) & (lv > floor + 4) & (lv < ref - 12) & (cen >= 800) & (cen <= 3800)
        hb = air[:on].sum() * HOP; tb = air[off:].sum() * HOP
        new_in = new_out = None
        if hb >= 0.12 and on * HOP - 0.08 >= 0.1: new_in = round(s["src_in"] + on * HOP + WIN / 2 - 0.08, 6)
        if tb >= 0.12 and (n - off) * HOP - 0.10 >= 0.1: new_out = round(s["src_in"] + off * HOP + WIN / 2 + 0.10, 6)
        if new_in or new_out: out.append((k, new_in, new_out, round(float(hb), 2), round(float(tb), 2)))
    return out


def apply_edges(cut, trims):
    segs = [dict(s) for s in cut["segments"]]
    for k, a, b, hb, tb in trims:
        if a: segs[k]["src_in"] = a
        if b: segs[k]["src_out"] = b
        segs[k]["dur"] = round(segs[k]["src_out"] - segs[k]["src_in"], 6); segs[k]["breath_trim"] = [hb if a else 0, tb if b else 0]
    t = 0.0
    for i, s in enumerate(segs):
        s["i"] = i; s["edit_in"] = round(t, 6); t += s["src_out"] - s["src_in"]; s["edit_out"] = round(t, 6)
    nc = dict(cut); nc["segments"] = segs; nc["breaths_cut"] = dict(edge_trims=len(trims))
    return nc


def debreath(work, cut, out_wav, ref, floor, gain_db=-12.0, guard=0.04, ramp=0.015):
    """Every remaining air run inside the kept shots (VAD non-speech, unpitched, 4 dB+ over the room, 12 dB+ under speech, 0.12 s+)
    turned down by gain_db in a copy of the master: audio only, so no picture or timing changes. guard s at each end stay untouched
    (word edges), with ramp s fades into and out of the dip."""
    segs = cut["segments"]; vp = np.load(f"{work}/qc/vad_probs.npy"); master = f"{work}/master_synced.wav"
    try:
        sr, x = wavfile.read(master, mmap=True); y = np.array(x, dtype=np.float32, copy=True)
        if x.dtype.kind == "i": y /= float(np.iinfo(x.dtype).max)
    except ValueError:   # 24-bit: decode the whole file through ffmpeg, keep its channels
        ch = int(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=channels", "-of", "csv=p=0", master],
                                capture_output=True, text=True).stdout.strip() or 1)
        sr = int(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=sample_rate", "-of", "csv=p=0", master],
                                capture_output=True, text=True).stdout.strip())
        y = _ff(master, mono=False).astype(np.float32).reshape(-1, ch)
    g = 10 ** (gain_db / 20)
    n_runs = 0; tot = 0.0
    for s in segs:
        if s.get("hold"): continue
        z = load(master, s["src_in"], s["src_out"]); lv, voi, cen = frames(z)
        if not len(lv): continue
        t = s["src_in"] + np.arange(len(lv)) * HOP + WIN / 2; vv = vp[np.clip((t / 0.032).astype(int), 0, len(vp) - 1)]
        air = (vv < 0.5) & (voi < 0.62) & (lv > floor + 4) & (lv < ref - 12) & (cen >= 800) & (cen <= 3800)
        r = runs(air); m = []
        for a_, b_ in r:
            if m and a_ - m[-1][1] <= 6: m[-1] = (m[-1][0], b_)
            else: m.append((a_, b_))
        for a_, b_ in m:
            if (b_ - a_) * HOP < 0.12: continue
            t0 = t[a_] - WIN / 2 + guard; t1 = t[b_ - 1] + WIN / 2 - guard
            if t1 - t0 < 2 * ramp + 0.02: continue
            i0, i1, rr = int(t0 * sr), int(t1 * sr), int(ramp * sr)
            env = np.full(i1 - i0, g, np.float32); env[:rr] = np.linspace(1, g, rr); env[-rr:] = np.linspace(g, 1, rr)
            y[i0:i1] *= env[:, None] if y.ndim > 1 else env
            n_runs += 1; tot += t1 - t0
    wavfile.write(out_wav, sr, y)
    return n_runs, tot


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("work"); ap.add_argument("cutlist")
    ap.add_argument("--apply"); ap.add_argument("--min-rel", type=float, default=-30.0)
    ap.add_argument("--edges", action="store_true", help="trim breath at shot edges only (no new cuts)")
    ap.add_argument("--debreath", help="write a copy of the master with every remaining breath 12 dB down (audio only)")
    a = ap.parse_args()
    cut = json.load(open(a.cutlist)); found, ref, floor = detect(a.work, cut)
    segs = cut["segments"]
    print(f"speech level {ref:.1f} dB, room floor {floor:.1f} dB, {len(found)} breaths in {len(segs)} shots")
    for f in sorted(found, key=lambda f: -f["rel_db"]):
        e = edit_time(segs, f["seg"], f["t0"])
        print(f"  edit {int(e // 60)}:{e % 60:05.2f}  cam {f['t0']:8.2f}-{f['t1']:8.2f}  {f['dur']:.2f}s  {f['rel_db']:+6.1f} dB  {f['where']:5}  {f['centre']} Hz")
    json.dump(dict(ref_db=ref, floor_db=floor, breaths=found), open(f"{a.work}/qc/breaths.json", "w"), indent=1)
    if a.debreath:
        nr, tt = debreath(a.work, json.load(open(a.apply)) if a.apply and os.path.exists(a.apply) else cut, a.debreath, ref, floor)
        print(f"debreath: {nr} breaths turned down 12 dB ({tt:.1f} s) -> {a.debreath}")
    if a.edges:
        tr = edges(a.work, cut, ref, floor); hs = sum(x[3] for x in tr if x[1]); ts = sum(x[4] for x in tr if x[2])
        print(f"edge breaths: {sum(1 for x in tr if x[1])} shot starts ({hs:.1f} s of air), {sum(1 for x in tr if x[2])} shot ends ({ts:.1f} s)")
        for k, a_, b_, hb, tb in tr:
            s_ = segs[k]; print(f"  shot {k:3d} edit {int(s_['edit_in'] // 60)}:{s_['edit_in'] % 60:05.2f}  in {s_['src_in']:.2f}->{a_ or s_['src_in']:.2f} ({hb:.2f}s air)  out {s_['src_out']:.2f}->{b_ or s_['src_out']:.2f} ({tb:.2f}s air)")
        if a.apply:
            nc = apply_edges(cut, tr); json.dump(nc, open(a.apply, "w"), indent=1)
            print(f"{segs[-1]['edit_out']:.2f}s -> {nc['segments'][-1]['edit_out']:.2f}s -> {a.apply}")
    elif a.apply:
        nc, ne, nm, fl = apply(cut, found, a.min_rel)
        old = segs[-1]["edit_out"]; new = nc["segments"][-1]["edit_out"]
        json.dump(nc, open(a.apply, "w"), indent=1)
        print(f"applied at >= {a.min_rel} dB: {ne} edge trims, {nm} mid-shot cuts, {fl} framing flips; {old:.2f}s -> {new:.2f}s ({new - old:+.2f}s) -> {a.apply}")
