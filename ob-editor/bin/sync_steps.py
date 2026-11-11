#!/usr/bin/env python3
"""Sync a MOTIV mic WAV to camera footage when the recording has dropouts (C4354, 2026-10-17).

MOTIV loses whole buffers when the Mac is busy (C4354: one 0.73 s gap and a run of ~10-40 ms gaps while a 4K
render ran), so the offset (camera time - mic time) is a rising staircase, not a line, and sync_av.py's
single line fit is off by up to 0.7 s. Here:
  1. a dense PHAT offset curve (6 s windows every 1 s), narrow search around the running offset; a wide
     search only after 5 misses in a row, accepted when 3 windows in a row agree;
  2. outliers dropped against a running median, then a non-decreasing step fit (isotonic regression:
     a dropout can only lose samples), steps under 4 ms merged into their neighbours;
  3. each step pinned between its two levels' windows: whitened cross-correlation at the old vs the new lag,
     single change point (0.2 s windows, then 24 ms windows), snapped to the splice click when one stands out;
  4. the mic placed piece by piece on the camera timeline; every gap filled with the camera's own sound,
     high-passed, level-matched over the neighbouring second, 4 ms crossfades.

  python3 -I sync_steps.py CAMERA.MP4 MIC.wav OUT_48k.wav [--report OUT.json] [--hints ROUGH.json]

--hints (C4398, 2026-10-29): the MOTIV app can also pause for seconds at a time (C4398: six gaps of 5 to 80 s over
47 min), far outside the 1.5 s wide search. ROUGH.json = [{"mic_first", "mic_last", "off"}, ...], the rough
camera-minus-mic offset of each piece from matching the two transcripts' word 4-grams. The coarse start uses the
first piece, and a lost lock searches around the piece the window sits in (or the next one, inside a gap).

The report lists the pieces, steps and camera-audio fills (camera time), so an edit can avoid long fills.
"""
import argparse, json, subprocess
import numpy as np
from scipy.io import wavfile
from scipy.ndimage import median_filter, uniform_filter1d
from scipy.signal import butter, fftconvolve, sosfiltfilt, stft, istft

ap = argparse.ArgumentParser(); ap.add_argument("video"); ap.add_argument("mic"); ap.add_argument("out")
ap.add_argument("--report"); ap.add_argument("--hints"); a = ap.parse_args()
HINTS = sorted(json.load(open(a.hints)), key=lambda h: h["mic_first"]) if a.hints else []
def hint_at(t):
    """rough offset of the piece holding mic time t (inside a gap: the next piece)"""
    for h in HINTS:
        if t <= h["mic_last"]: return h["off"]
    return HINTS[-1]["off"] if HINTS else None
SR, R16, WS = 48000, 16000, 6


def load(path, sr):
    raw = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-i", path, "-vn", "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).copy()


cam16, mic16 = load(a.video, R16), load(a.mic, R16)


def phat(m0, n, guess, L):
    """offset (cam time - mic time) of mic[m0, m0+n) within guess +- L samples -> (offset s, peak/median)"""
    y = mic16[m0:m0 + n]; c0 = int(round((m0 / R16 + guess) * R16)) - L
    if c0 < 0 or len(y) < n or c0 + n + 2 * L > len(cam16): return None
    x = cam16[c0:c0 + n + 2 * L]; N = 1 << int(np.ceil(np.log2(len(x) + n)))
    X = np.fft.rfft(x, N); Y = np.fft.rfft(y, N); P = X * np.conj(Y); P /= np.abs(P) + 1e-9
    f = np.fft.rfftfreq(N, 1 / R16); P[(f < 250) | (f > 3500)] = 0
    r = np.fft.irfft(P)[:2 * L + 1]; i = int(np.argmax(r)); d = 0.0
    if 0 < i < 2 * L:
        p, q, s = r[i - 1], r[i], r[i + 1]; den = p - 2 * q + s; d = 0.5 * (p - s) / den if den else 0.0
    return (c0 + i + d) / R16 - m0 / R16, float(r[i] / (np.median(np.abs(r)) + 1e-12))


# 1. coarse offset (loudness-onset envelopes, first 10 min of mic against the whole camera), then the dense curve
def env10(x):
    sos = butter(4, [200, 4000], btype="band", fs=R16, output="sos"); e = sosfiltfilt(sos, x.astype(np.float64)) ** 2
    m = len(e) // 160 * 160; e = np.log(e[:m].reshape(-1, 160).mean(1) + 1e-6); return np.diff(e, prepend=e[0]).clip(0)
nz = lambda v: (v - v.mean()) / (v.std() + 1e-12)
Cn, Mn = nz(env10(cam16)), nz(env10(mic16)[:60000])
guess = int(np.argmax(fftconvolve(Cn, Mn[::-1], mode="valid"))) / 100.0; del Cn, Mn
if HINTS and abs(guess - HINTS[0]["off"]) > 0.5:
    print(f"coarse envelope match {guess:+.3f} s disagrees with the word hint {HINTS[0]['off']:+.3f} s: using the hint"); guess = HINTS[0]["off"]
WIN, CONF = WS * R16, 10.0
pts, miss, cand = [], 0, []
for m0 in range(0, len(mic16) - WIN, R16):
    o = phat(m0, WIN, guess, int(0.06 * R16))
    if o is not None and o[1] >= CONF:
        pts.append((m0 / R16, o[0], o[1])); guess = o[0]; miss = 0; cand = []; continue
    miss += 1
    if miss >= 5:   # lost lock: look wide, switch only when 3 windows in a row agree
        h = hint_at(m0 / R16) if HINTS else None
        w = phat(m0, WIN, h if h is not None and abs(h - guess) > 1.0 else guess, int(1.5 * R16))
        if w is not None and w[1] >= 15:
            cand = [c for c in cand if abs(c[1] - w[0]) < 0.004] + [(m0 / R16, w[0], w[1])]
            if len(cand) >= 3: pts += cand; guess = w[0]; miss = 0; cand = []
        else: cand = []
P = np.array(pts)
print(f"coarse {guess:+.3f} s at the end | {len(P)} confident {WS} s windows of {len(mic16) // R16 - WS}")

# 2. outliers vs a running median, then a non-decreasing step fit
med = median_filter(P[:, 1], size=15, mode="nearest"); keep = np.abs(P[:, 1] - med) < 0.006
P = P[keep]; print(f"  dropped {int((~keep).sum())} outlier windows")
def isotonic(y, w):   # pool-adjacent-violators, non-decreasing
    vals, wts, cnt = [], [], []
    for yi, wi in zip(y, w):
        vals.append(yi); wts.append(wi); cnt.append(1)
        while len(vals) > 1 and vals[-2] > vals[-1]:
            v = (vals[-2] * wts[-2] + vals[-1] * wts[-1]) / (wts[-2] + wts[-1]); ww = wts[-2] + wts[-1]; cc = cnt[-2] + cnt[-1]
            vals[-2:] = [v]; wts[-2:] = [ww]; cnt[-2:] = [cc]
    return vals, cnt
vals, cnt = isotonic(P[:, 1], np.minimum(P[:, 2], 60.0))
groups, i = [], 0
for v, c in zip(vals, cnt):
    if groups and v - groups[-1]["v"] < 0.004:   # merge sub-4 ms steps (clock drift, noise)
        g = groups[-1]; g["ix"] = list(range(g["ix"][0], i + c)); g["v"] = float(np.median(P[g["ix"], 1]))
    else: groups.append(dict(ix=list(range(i, i + c)), v=float(v)))
    i += c
pieces = [dict(t0=float(P[g["ix"][0], 0]), t1=float(P[g["ix"][-1], 0] + WS), off=float(np.median(P[g["ix"], 1])), n=len(g["ix"]),
               spread_ms=round(float(np.ptp(P[g["ix"], 1])) * 1000, 1), last=float(P[g["ix"][-1], 0]),
               off_head=float(np.median(P[g["ix"][:8], 1])), off_tail=float(np.median(P[g["ix"][-8:], 1]))) for g in groups]
for p_ in pieces: print(f"  piece: windows {p_['t0']:7.1f}-{p_['last']:7.1f}s  offset {p_['off']:+.4f}  ({p_['n']} windows, spread {p_['spread_ms']} ms)")

# 3. pin each step
def whiten(x):
    f, t, Z = stft(x, R16, nperseg=512, noverlap=384)
    Z = Z / (uniform_filter1d(np.abs(Z), 9, axis=0) + 1e-6); Z[(f < 250) | (f > 3500)] = 0
    _, y = istft(Z, R16, nperseg=512, noverlap=384); return y[: len(x)]

mic48 = load(a.mic, SR); steps = []; prev = 0.0
for k in range(1, len(pieces)):
    A, B = pieces[k - 1], pieces[k]
    lo, hi = A["last"] - 0.5, min(len(mic16) / R16 - 0.5, B["t0"] + WS + 0.5)   # A's last window holds A, B's first holds B
    lo = max(lo, prev + 0.05)   # steps stay in order when short pieces sit close together
    if hi - lo < 0.5: hi = lo + 0.5
    m_lo, m_hi = int(lo * R16), int(hi * R16); mw = whiten(mic16[m_lo:m_hi].astype(np.float64))
    def cw(off):
        c0 = int(round((lo + off) * R16)); return whiten(cam16[c0 - 32:c0 + (m_hi - m_lo) + 32].astype(np.float64))
    ca, cb = cw(A["off_tail"]), cw(B["off_head"])   # the offsets right at the step, not the piece medians
    def series(hw, c_from, c_to, hop):
        cs, ra, rb = [], [], []
        for c in range(max(hw, c_from), min(len(mw) - hw, c_to), hop):
            y = mw[c - hw:c + hw]; ny = np.sqrt((y ** 2).sum()) + 1e-9
            def best(cv):
                return max(np.dot(y, cv[c - hw + 32 + d:c + hw + 32 + d]) / (ny * (np.sqrt((cv[c - hw + 32 + d:c + hw + 32 + d] ** 2).sum()) + 1e-9)) for d in range(-32, 33, 2))
            cs.append(c); ra.append(best(ca)); rb.append(best(cb))
        return np.array(cs), np.array(ra), np.array(rb)
    cs, ra, rb = series(int(0.1 * R16), 0, len(mw), int(0.01 * R16))
    j = int(np.argmax(np.cumsum(ra - rb))); t1 = lo + cs[j] / R16
    sep = float(np.mean(ra[:j + 1]) - np.mean(rb[:j + 1]) + np.mean(rb[j + 1:]) - np.mean(ra[j + 1:])) if 0 < j < len(cs) - 1 else 0.0
    c2, ra2, rb2 = series(int(0.012 * R16), int((t1 - lo - 0.08) * R16), int((t1 - lo + 0.08) * R16), 16)
    t_est = lo + c2[int(np.argmax(np.cumsum(ra2 - rb2)))] / R16 if len(c2) else t1
    s0 = int((t_est - 0.04) * SR); x = mic48[s0:s0 + int(0.08 * SR)].astype(np.float64); d2 = np.abs(np.diff(x, 2))
    near = slice(int(0.036 * SR), int(0.044 * SR)); jj = int(np.argmax(d2[near])) + near.start
    click = float(d2[jj] / (np.percentile(d2, 95) + 1e-12)); t_drop = (s0 + jj + 1) / SR if click > 4 else t_est
    t_drop = max(t_drop, prev + 0.02); prev = t_drop
    steps.append(dict(mic_t=round(t_drop, 5), gap_ms=round((B["off"] - A["off"]) * 1000, 2), click=round(click, 1),
                      fine=round(t_est, 4), coarse=round(t1, 3), sep=round(sep, 3), search=[round(lo, 2), round(hi, 2)]))

# 4. assemble on the camera timeline, then fill every hole with level-matched camera sound
cam48 = load(a.video, SR); out = np.zeros(len(cam48), np.float32); filled = np.zeros(len(cam48), bool)
bounds = [0.0] + [s["mic_t"] for s in steps] + [len(mic48) / SR]; spans = []
assert all(b1 > b0 for b0, b1 in zip(bounds, bounds[1:])), "steps out of order"
X = 192
for k, p in enumerate(pieces):
    m0, m1 = int(round(bounds[k] * SR)), int(round(bounds[k + 1] * SR)); c0 = int(round((bounds[k] + p["off"]) * SR))
    a0 = max(0, -c0); seg = mic48[m0 + a0:m1].copy(); c0 += a0; seg = seg[: max(0, len(out) - c0)]
    if len(seg) > 2 * X and filled[c0]:   # overlap with the piece before: crossfade
        w = (np.sin(np.linspace(0, np.pi / 2, X)) ** 2).astype(np.float32); seg[:X] = out[c0:c0 + X] * (1 - w) + seg[:X] * w
    out[c0:c0 + len(seg)] = seg; filled[c0:c0 + len(seg)] = True; spans.append([round(c0 / SR, 4), round((c0 + len(seg)) / SR, 4)])
hp = butter(2, 100, btype="high", fs=SR, output="sos"); fills = []
edges = np.flatnonzero(np.diff(np.concatenate([[1], filled.astype(np.int8), [1]])))
for h0, h1 in zip(edges[::2], edges[1::2]):
    h0, h1 = int(h0), int(h1); n0, n1 = max(0, h0 - SR), min(len(out), h1 + SR)
    ref_m = np.concatenate([out[n0:h0], out[h1:n1]]).astype(np.float64); ref_c = np.concatenate([cam48[n0:h0], cam48[h1:n1]]).astype(np.float64)
    g = float(np.sqrt((ref_m ** 2).mean()) / (np.sqrt((ref_c ** 2).mean()) + 1e-12)) if len(ref_m) > SR // 4 else 1.0
    b0, b1 = max(0, h0 - X), min(len(out), h1 + X)
    piece = sosfiltfilt(hp, cam48[b0:b1].astype(np.float64)) * g
    if h1 - h0 > 0.1 * SR and len(ref_m) > SR:   # long fill: match the mic's tone too (EQ from the 3 s either side)
        m0_, m1_ = max(0, h0 - 3 * SR), min(len(out), h1 + 3 * SR)
        rm = np.concatenate([out[m0_:h0], out[h1:m1_]]).astype(np.float64); rc = np.concatenate([cam48[m0_:h0], cam48[h1:m1_]]).astype(np.float64) * g
        from scipy.signal import welch
        f_, Pm = welch(rm, SR, nperseg=2048); _, Pc = welch(rc, SR, nperseg=2048)
        eq = np.sqrt((Pm + 1e-14) / (Pc + 1e-14)); lf = np.log2(np.maximum(f_, 20.0))
        eq_s = np.array([np.median(eq[np.abs(lf - x) < 1 / 6]) for x in lf])   # 1/3-octave median
        eq_s = np.clip(eq_s, 10 ** (-15 / 20), 10 ** (15 / 20))
        _, _, Z = stft(piece, SR, nperseg=2048, noverlap=1536); Z *= eq_s[:, None]
        _, piece = istft(Z, SR, nperseg=2048, noverlap=1536); piece = np.pad(piece, (0, max(0, (b1 - b0) - len(piece))))[: b1 - b0]
    piece = piece.astype(np.float32); w = np.ones(len(piece), np.float32)
    if b0 == h0 - X: w[:X] = np.sin(np.linspace(0, np.pi / 2, X)) ** 2
    if b1 == h1 + X: w[-X:] = np.cos(np.linspace(0, np.pi / 2, X)) ** 2
    out[b0:b1] = out[b0:b1] * (1 - w) + piece * w
    fills.append(dict(cam_t0=round(h0 / SR, 4), cam_t1=round(h1 / SR, 4), dur_ms=round((h1 - h0) / SR * 1000, 1), gain_db=round(20 * np.log10(g + 1e-12), 1)))
wavfile.write(a.out, SR, out)
print(f"{len(pieces)} pieces, {len(steps)} steps -> {a.out}")
for s in steps: print(f"  step at mic {s['mic_t']:9.3f}s  gap {s['gap_ms']:+7.1f} ms  click {s['click']:5.1f}  fine {s['fine']:.3f} coarse {s['coarse']:.3f} sep {s['sep']:+.3f} search {s['search']}")
for h in fills: print(f"  camera fill {h['cam_t0']:9.3f}-{h['cam_t1']:9.3f}s ({h['dur_ms']:8.1f} ms, gain {h['gain_db']:+.1f} dB)")
# 5. verify: PHAT of the synced mic against the camera, 4 s windows every 5 s
o16 = out.reshape(-1, 3).mean(1) if len(out) % 3 == 0 else out[: len(out) // 3 * 3].reshape(-1, 3).mean(1)
mic16, ver = o16.astype(np.float32), []
for m0 in range(int(spans[0][0] * R16) + R16, int(spans[-1][1] * R16) - 5 * R16, 5 * R16):
    o = phat(m0, 4 * R16, 0.0, int(0.05 * R16))
    if o and o[1] >= 10: ver.append((m0 / R16, o[0] * 1000, o[1]))
V = np.array(ver); bad = V[np.abs(V[:, 1]) > 5]
print(f"verify: {len(V)} confident windows, lag median {np.median(V[:,1]):+.2f} ms, p1/p99 {np.percentile(V[:,1],1):+.2f}/{np.percentile(V[:,1],99):+.2f} ms, {len(bad)} beyond 5 ms")
for t, l, q in bad[:12]: print(f"  camera {t:8.1f}s  lag {l:+6.1f} ms  ({q:.0f})")
print("each step, synced mic vs camera just before / just after (3 s windows, 0.2 s away):")
for st, p in zip(steps, pieces[1:]):
    tc = st["mic_t"] + p["off"]; b = phat(int((tc - 3.2) * R16), 3 * R16, 0.0, int(0.05 * R16)); f_ = phat(int((tc + 0.2 + st["gap_ms"] / 1000) * R16), 3 * R16, 0.0, int(0.05 * R16))
    fmt = lambda o: f"{o[0]*1000:+5.1f} ms ({o[1]:4.0f})" if o else "   n/a"
    print(f"  camera {tc:8.2f}s gap {st['gap_ms']:+7.1f}: before {fmt(b)}  after {fmt(f_)}")
if a.report: json.dump(dict(pieces=pieces, steps=steps, fills=fills, mic_spans=spans, verify=dict(n=len(V), median_ms=float(np.median(V[:,1])), beyond5=bad.tolist())), open(a.report, "w"), indent=1)
