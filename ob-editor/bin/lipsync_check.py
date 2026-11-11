#!/usr/bin/env python3
"""Lip sync, measured on every piece (ledger M36; OB 2026-11-03 on C4411: "the lean guy also the lips dont sync, you have been
doing that ... i thought you had a built in loop so you upgrade and never make the same mistake twice").

Each piece of his voice in a render is found in the camera's own sound at the picture's place (GCC-PHAT, 200-4000 Hz, so the
podcast mic and the camera's scratch mic still line up). delta > 0: his voice comes before his lips.
  FAIL  a piece more than 40 ms off, or a piece whose sound can't be found within +-1 s of its picture (C4411's MOTIV skip
        put 8 lines 0.812 s off; at +-0.5 s they simply didn't match)
  WARN  a piece 25-40 ms off
Renders record the camera map: qc_gate.after_render(out, segs=..., cam=[(camera file, cam start, cam end, t_out), ...]).

  python3 -I lipsync_check.py FILE.mp4                 the map from the render's pieces file (qc/pieces)
  python3 -I lipsync_check.py scan CAMERA MIC T0 T1    mic vs camera, 3 s windows every 1 s (M36: find skips before a CFG)
  python3 -I lipsync_check.py --selftest
"""
import json, os, subprocess, sys
import numpy as np

SR = 16000
FAIL_MS, WARN_MS, MARGIN, MIN_LEN, CONF = 40.0, 25.0, 1.0, 0.8, 10.0


def decode(path, ss=None, t=None):
    cmd = ["ffmpeg", "-nostdin", "-v", "error"] + (["-ss", f"{max(0.0, ss):.3f}"] if ss is not None else []) + ["-i", path] + \
          (["-t", f"{t:.3f}"] if t is not None else []) + ["-map", "0:a:0", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"]
    return np.frombuffer(subprocess.run(cmd, capture_output=True).stdout, np.float32)


def gcc(x, y, lo=200, hi=4000):
    """Where x sits inside y: (sample offset, peak over the median of |r|)."""
    n = 1 << int(np.ceil(np.log2(len(x) + len(y))))
    X, Y = np.fft.rfft(x, n), np.fft.rfft(y, n); f = np.fft.rfftfreq(n, 1 / SR)
    R = Y * np.conj(X); R /= np.abs(R) + 1e-12; R[(f < lo) | (f > hi)] = 0
    r = np.fft.irfft(R, n)[: len(y) - len(x) + 1]
    k = int(np.argmax(r)); return k, float(r[k] / (np.median(np.abs(r)) + 1e-12))


def measure(final, cam_map, margin=MARGIN, win=1.2, hop=0.6):
    """[(t_out, cam, a, b, delta_s or None, conf)] for every piece long enough to measure that has his voice in it. A piece over
    2 windows long is the median of its 1.2 s windows (11-03 C4412: her muted intro's last 30 ms at the head of the first line
    pulled the whole-piece match to +41 ms while every window inside it sat at -1 to -3 ms); a real skip is off in every window."""
    fin = decode(final); rows = []
    for cam, a, b, t in cam_map:
        if b - a < MIN_LEN: continue
        y0 = max(0.0, a - margin); y = decode(cam, y0, (b - a) + 2 * margin)
        subs = [(0.0, b - a)] if b - a < 2 * win else [(u, u + win) for u in np.arange(0.0, b - a - win + 1e-6, hop)]
        ds, cs = [], []   # votes: (delta, confidence) from the whole piece and each window
        x = fin[int(t * SR): int((t + b - a) * SR)]
        if len(x) >= MIN_LEN * SR and len(y) > len(x) and np.sqrt(np.mean(x ** 2)) >= 1e-3:
            k, c = gcc(x, y); cs.append(c)
            if c >= CONF: ds.append(((y0 + k / SR) - a, c))
        for u0, u1 in subs if len(subs) > 1 else []:
            x = fin[int((t + u0) * SR): int((t + u1) * SR)]
            if len(x) < MIN_LEN * SR * 0.75 or np.sqrt(np.mean(x ** 2)) < 1e-3: continue
            s0 = max(0, int((a + u0 - margin - y0) * SR)); yy = y[s0: int((a + u1 + margin - y0) * SR)]
            if len(yy) <= len(x): continue
            k, c = gcc(x, yy); cs.append(c)
            if c >= CONF: ds.append((y0 + (s0 + k) / SR - (a + u0), c))
        if not cs: continue
        # 11-03 C4410 34.8 s: two of ten windows locked onto a similar phrase (-326, -941 ms) and an even-count median read -164 ms.
        # The answer is the delta the most confidence agrees on (votes within 20 ms); a real skip is every window's answer.
        best = max(ds, key=lambda v: sum(c for d, c in ds if abs(d - v[0]) <= 0.02)) if ds else None
        rows.append((t, cam, a, b, float(np.median([d for d, c in ds if abs(d - best[0]) <= 0.02])) if best else None, float(np.median(cs))))
    return rows


def verdict(rows):
    if not rows: return "SKIP", "no piece long enough to measure"
    off = [r for r in rows if r[4] is not None and abs(r[4]) * 1000 > FAIL_MS]
    lost = [r for r in rows if r[4] is None and r[3] - r[2] >= 1.0]
    warn = [r for r in rows if r[4] is not None and WARN_MS < abs(r[4]) * 1000 <= FAIL_MS]
    good = [r[4] for r in rows if r[4] is not None]
    med = f"median {np.median(good) * 1000:+.0f} ms, worst {max(good, key=abs) * 1000:+.0f} ms" if good else "none matched"
    if off or lost:
        bits = [f"{r[0]:.1f}s {r[4] * 1000:+.0f} ms" for r in off[:6]] + [f"{r[0]:.1f}s not found within {MARGIN:.0f} s" for r in lost[:4]]
        return "FAIL", f"his voice is off his lips on {len(off) + len(lost)} of {len(rows)} pieces (" + "; ".join(bits) + f"); {med}"
    if warn: return "WARN", f"{len(warn)} of {len(rows)} pieces 25-40 ms off ({', '.join(f'{r[0]:.1f}s {r[4]*1000:+.0f} ms' for r in warn[:4])}); {med}"
    return "PASS", f"{len(rows)} pieces in sync, {med}"


def check(final, cam_map):
    return verdict(measure(final, cam_map))


def scan(cam, mic, t0, t1, win=3.0, step=1.0, margin=4.0):
    """M36: where each mic window sits in the camera's sound (prints offset and confidence per window)."""
    c, m = decode(cam), decode(mic)
    for t in np.arange(t0, t1, step):
        x = m[int(t * SR): int((t + win) * SR)]
        if len(x) < win * SR * 0.9 or np.sqrt(np.mean(x ** 2)) < 1e-3: continue
        y0 = max(0, int((t - margin) * SR)); y = c[y0: int((t + win + margin) * SR)]
        if len(y) <= len(x): continue
        k, conf = gcc(x, y); print(f"  mic {t:7.1f}  offset {((y0 + k) / SR - t) * 1000:+8.1f} ms  conf {conf:5.1f}")


def selftest():
    """A planted 0.3 s offset must FAIL, the same pieces in sync must PASS (speech-like bursts, written as real files)."""
    import tempfile, wave
    rng = np.random.default_rng(7); n = 30 * SR
    env = np.repeat((rng.random(n // 1600 + 1) > 0.45).astype(np.float32), 1600)[:n] * (0.3 + 0.7 * rng.random(n).astype(np.float32))
    cam = (rng.standard_normal(n).astype(np.float32) * env * 0.2)
    def wav(p, x):
        with wave.open(p, "wb") as w: w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
    with tempfile.TemporaryDirectory() as td:
        wav(f"{td}/cam.wav", cam); ok = True
        for shift, want in ((0.0, "PASS"), (0.3, "FAIL"), (0.03, "WARN")):
            pieces = [(2.0, 5.0), (8.0, 11.5), (15.0, 19.0)]; out, cmap, t = [], [], 0.0
            for a, b in pieces:
                s0 = int((a + shift) * SR); out.append(cam[s0: s0 + int((b - a) * SR)]); cmap.append((f"{td}/cam.wav", a, b, t)); t += b - a
            wav(f"{td}/fin.wav", np.concatenate(out) + rng.standard_normal(sum(len(o) for o in out)).astype(np.float32) * 0.005)
            st, d = check(f"{td}/fin.wav", cmap); good = st == want; ok &= good
            print(f"  lipsync selftest: offset {shift * 1000:.0f} ms -> {st} (want {want}) {'ok' if good else 'WRONG'}: {d}")
    return ok


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a: print(__doc__); sys.exit(2)
    if a[0] == "--selftest": sys.exit(0 if selftest() else 1)
    if a[0] == "scan": scan(a[1], a[2], float(a[3]), float(a[4])); sys.exit(0)
    BIN = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, BIN)
    import qc_gate as Q
    p = Q.pieces_path(a[0]); d = json.load(open(p)) if os.path.exists(p) else {}
    if not d.get("cam"): sys.exit(f"no camera map recorded for {a[0]} (renders pass cam= to qc_gate.after_render)")
    st, det = check(a[0], d["cam"]); print(st, det); sys.exit(1 if st == "FAIL" else 0)
