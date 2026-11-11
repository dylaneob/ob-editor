"""Duplicates among sound files: same bytes, same decoded audio, or the same sound (silence-trimmed log-band fingerprint,
best match over +-50 ms). usage: sfx_dupes.py NEW_DIR [EXISTING_DIR ...]"""
import glob, hashlib, os, subprocess, sys, itertools, numpy as np
SR = 16000
def pcm(p):
    return np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True).stdout, np.float32)
def trim(x, db=-45):
    a = np.abs(x); k = np.where(a > 10 ** (db / 20) * max(a.max(), 1e-9))[0]
    return x[k[0]:k[-1] + 1] if len(k) else x[:0]
def bands(x, hop=160, n=512, nb=32):
    if len(x) < n: x = np.pad(x, (0, n - len(x)))
    fr = np.lib.stride_tricks.sliding_window_view(x, n)[::hop] * np.hanning(n)
    S = np.abs(np.fft.rfft(fr, axis=1)) ** 2; edges = np.geomspace(60, SR / 2, nb + 1) / (SR / 2) * (n // 2)
    B = np.stack([S[:, int(edges[i]):max(int(edges[i]) + 1, int(edges[i + 1]))].sum(1) for i in range(nb)], 1)
    L = np.log10(B + 1e-10); return (L - L.mean()) / (L.std() + 1e-9)
def sim(A, B, maxlag=5):
    best = -1
    for lag in range(-maxlag, maxlag + 1):
        a, b = (A[lag:], B) if lag >= 0 else (A, B[-lag:]); m = min(len(a), len(b))
        if m < 3: continue
        best = max(best, float(np.mean(a[:m] * b[:m])) * m / max(len(A), len(B)))
    return best
files = [(os.path.basename(os.path.dirname(p)) if i else "NEW", p) for i, d in enumerate(sys.argv[1:]) for p in sorted(glob.glob(f"{d}/**/*", recursive=True))
         if p.lower().endswith((".wav", ".mp3", ".ogg", ".flac", ".m4a", ".aif", ".aiff")) and not os.path.basename(p).startswith("._")]
info = []
for lib, p in files:
    x = pcm(p); t = trim(x)
    info.append(dict(lib=lib, p=p, n=os.path.basename(p), md5=hashlib.md5(open(p, "rb").read()).hexdigest(),
                     pmd5=hashlib.md5((np.round(t * 2000)).astype(np.int16).tobytes()).hexdigest(), dur=len(t) / SR, F=bands(t) if len(t) else None))
print(f"{len(info)} files ({sum(i['lib'] == 'NEW' for i in info)} new)")
for i, j in itertools.combinations(range(len(info)), 2):
    a, b = info[i], info[j]
    if a["lib"] != "NEW" and b["lib"] != "NEW": continue
    why = "same bytes" if a["md5"] == b["md5"] else "same audio" if a["pmd5"] == b["pmd5"] else None
    if not why and a["F"] is not None and b["F"] is not None and min(a["dur"], b["dur"]) / max(a["dur"], b["dur"], 1e-9) > 0.8:
        s = sim(a["F"], b["F"]); why = f"sounds the same (similarity {s:.2f})" if s >= 0.85 else None
        if not why and s >= 0.70: print(f"  close, not a dup ({s:.2f}): {a['lib']}/{a['n']} ~ {b['lib']}/{b['n']}")
    if why: print(f"  DUP: {a['lib']}/{a['n']} == {b['lib']}/{b['n']}  ({why}; {a['dur']:.2f} s vs {b['dur']:.2f} s)")
