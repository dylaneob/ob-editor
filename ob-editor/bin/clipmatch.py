#!/usr/bin/env python3
"""Find where each reaction clip was played inside a recording, by its audio.

  python3 clipmatch.py RECORDING_16k.wav CLIP [CLIP ...] --out matches.json
  python3 clipmatch.py RECORDING_16k.wav --selftest

The clip was played on speakers, so the recording holds a room-coloured, quieter copy of
the clip audio, often with OB talking over it, sometimes paused / scrubbed / replayed.
Method: log-mel features with per-band temporal high-pass (kills room EQ and level),
4 s clip chunks (1 s hop) matched by normalised cross-correlation against the whole
recording, peaks clustered into constant-offset runs = playback segments, then each run's
offset refined to ~1 ms on the waveform onset envelope.
"""
import argparse, json, os, subprocess, sys
import numpy as np
from scipy.io import wavfile
from scipy.signal import fftconvolve, butter, sosfiltfilt
from scipy.ndimage import uniform_filter1d

SR = 16000
HOP = 320            # 20 ms
NFFT = 1024
NMEL = 48
CHUNK = 200          # 4 s
STEP = 50            # 1 s
FPS = SR / HOP


def load16(path):
    if path.lower().endswith(".wav"):
        sr, x = wavfile.read(path)
        if sr == SR:
            x = x.astype(np.float64)
            return (x.mean(1) if x.ndim > 1 else x) / (32768.0 if np.abs(x).max() > 2 else 1.0)
    raw = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-i", path, "-vn", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).astype(np.float64)


def mel_fb():
    f = np.fft.rfftfreq(NFFT, 1 / SR)
    m = lambda hz: 2595 * np.log10(1 + hz / 700)
    im = lambda mm: 700 * (10 ** (mm / 2595) - 1)
    pts = im(np.linspace(m(120), m(6500), NMEL + 2))
    fb = np.zeros((NMEL, len(f)))
    for i in range(NMEL):
        l, c, r = pts[i], pts[i + 1], pts[i + 2]
        fb[i] = np.clip(np.minimum((f - l) / (c - l), (r - f) / (r - c)), 0, None)
    return fb


FB = mel_fb()


def features(x):
    n = 1 + (len(x) - NFFT) // HOP
    if n <= 0: return np.zeros((NMEL, 0))
    idx = np.arange(NFFT)[None, :] + HOP * np.arange(n)[:, None]
    win = np.hanning(NFFT)
    S = np.abs(np.fft.rfft(x[idx] * win, axis=1)) ** 2
    M = np.log(S @ FB.T + 1e-9).T                       # (NMEL, n)
    M = M - uniform_filter1d(M, size=100, axis=1, mode="nearest")   # 2 s temporal high-pass per band
    M = np.clip(M, -6, 6)
    M -= M.mean(0, keepdims=True)                        # remove broadband level per frame
    return M


class Recording:
    def __init__(self, x):
        self.F = features(x)
        self.n = self.F.shape[1]
        L = 1 << int(np.ceil(np.log2(self.n + CHUNK + 1)))
        self.L = L
        self.RF = np.fft.rfft(self.F, n=L, axis=1)
        e = (self.F ** 2).sum(0)
        self.cs = np.concatenate([[0], np.cumsum(e)])

    def ncc(self, C):
        """Normalised cross-correlation of chunk C (NMEL, m) at every recording position."""
        m = C.shape[1]
        CF = np.fft.rfft(C[:, ::-1], n=self.L, axis=1)
        corr = np.fft.irfft((self.RF * CF).sum(0), n=self.L)[m - 1: m - 1 + self.n - m + 1]
        win_e = self.cs[m:self.n + 1] - self.cs[:self.n - m + 1]
        return corr / (np.sqrt(win_e * (C ** 2).sum()) + 1e-9)


def onset_env(x, hop=16):
    sos = butter(4, [200, 4000], btype="band", fs=SR, output="sos")
    y = sosfiltfilt(sos, x) ** 2
    m = len(y) // hop * hop
    e = np.log(y[:m].reshape(-1, hop).mean(1) + 1e-7)
    return np.diff(e, prepend=e[0]).clip(0)


def refine(rec_x, clip_x, rec_t, clip_t, dur):
    """ms-accurate offset for a segment: onset-envelope xcorr within +-0.25 s."""
    a = int(clip_t * SR); b = int(min(len(clip_x), (clip_t + min(dur, 20)) * SR))
    cseg = onset_env(clip_x[a:b])
    r0 = int((rec_t - 0.25) * SR); r1 = int((rec_t + min(dur, 20) + 0.25) * SR)
    if r0 < 0 or r1 > len(rec_x) or len(cseg) < 200: return rec_t, 0.0
    rseg = onset_env(rec_x[r0:r1])
    nz = lambda v: (v - v.mean()) / (v.std() + 1e-9)
    c = fftconvolve(nz(rseg), nz(cseg)[::-1], mode="valid") / len(cseg)
    i = int(np.argmax(c))
    return r0 / SR + i * 0.001, float(c[i])


def match_clip(rec, rec_x, clip_x, name, z_thresh=7.0):
    C = features(clip_x)
    m = C.shape[1]
    if m < CHUNK // 2: return {"clip": name, "segments": [], "note": "clip too short"}
    hits = []  # (clip_frame, rec_frame, z)
    for c0 in range(0, max(1, m - CHUNK + 1), STEP):
        ch = C[:, c0:c0 + CHUNK]
        if (ch ** 2).sum() < 1e-3: continue
        v = rec.ncc(ch)
        med = np.median(v); mad = np.median(np.abs(v - med)) * 1.4826 + 1e-9
        z = (v - med) / mad
        for _ in range(4):                        # up to 4 plays of this chunk
            i = int(np.argmax(z))
            if z[i] < z_thresh: break
            hits.append((c0, i, float(z[i])))
            z[max(0, i - 3 * CHUNK): i + 3 * CHUNK] = -1e9
    # cluster by offset (rec - clip): colouring makes peak positions jitter a few frames per chunk,
    # so group offsets within 8 frames (160 ms), then split each group into contiguous runs by clip time.
    hits.sort(key=lambda h: h[1] - h[0])
    groups = []
    for h in hits:
        d = h[1] - h[0]
        if groups and d - np.median([g[1] - g[0] for g in groups[-1]]) <= 8: groups[-1].append(h)
        else: groups.append([h])
    runs = []
    for g in groups:
        g.sort(key=lambda h: h[0])
        cur = [g[0]]
        for h in g[1:]:
            if h[0] - cur[-1][0] <= 2 * STEP: cur.append(h)
            else: runs.append(cur); cur = [h]
        runs.append(cur)
    runs = [{"d": float(np.median([h[1] - h[0] for h in r])), "c0": r[0][0], "c1": r[-1][0], "zs": [h[2] for h in r]} for r in runs]
    # extend each run outward at its own offset in 1 s windows with a relaxed threshold: talk-over
    # hides the clip from 4 s chunks but 1 s windows at a KNOWN offset still correlate.
    def presence(cf, rf):
        if cf < 0 or cf + 50 > m or rf < 0 or rf + 50 > rec.n: return -1
        a = C[:, cf:cf + 50]; b = rec.F[:, rf:rf + 50]
        return float((a * b).sum() / (np.sqrt((a ** 2).sum() * (b ** 2).sum()) + 1e-9))
    for R in runs:
        d = int(round(R["d"]))
        end = R["c1"] + CHUNK; miss = 0
        while end + 50 <= m and miss < 2:
            ok = presence(end, end + d) > 0.25
            miss = 0 if ok else miss + 1; end += 50
        R["c1"] = end - 50 * miss - CHUNK if miss else end - CHUNK
        start = R["c0"]; miss = 0
        while start - 50 >= 0 and miss < 2:
            ok = presence(start - 50, start - 50 + d) > 0.25
            miss = 0 if ok else miss + 1; start -= 50
        R["c0"] = start + 50 * miss if miss else start
    segs = []
    for R in runs:
        if len(R["zs"]) < 2 and max(R["zs"]) < z_thresh + 4: continue    # lone weak hit = noise
        clip_in = R["c0"] / FPS; clip_out = min(m / FPS, (R["c1"] + CHUNK) / FPS)
        rec_in = clip_in + R["d"] / FPS
        rt, conf = refine(rec_x, clip_x, rec_in, clip_in, clip_out - clip_in)
        segs.append({"rec_in": round(rt, 3), "rec_out": round(rt + clip_out - clip_in, 3), "clip_in": round(clip_in, 3),
                     "clip_out": round(clip_out, 3), "chunks": len(R["zs"]), "z_med": round(float(np.median(R["zs"])), 1), "fine_conf": round(conf, 3)})
    segs.sort(key=lambda s: s["rec_in"])
    return {"clip": name, "duration": round(len(clip_x) / SR, 2), "segments": segs}


def selftest(rec_x):
    """Plant speaker-coloured excerpts (10 dB SNR) with a talk-over and a pause, then find them."""
    rng = np.random.default_rng(1)
    sos = butter(2, [300, 3000], btype="band", fs=SR, output="sos")
    N = len(rec_x); ok = 0
    for trial in range(3):
        t = rng.uniform(120, N / SR - 450); d = 30.0
        clip = rec_x[int(t * SR): int((t + d) * SR)].copy()                    # the "clip file" (clean)
        heard = sosfiltfilt(sos, clip) * 0.3
        rms = np.sqrt((heard ** 2).mean())
        heard += rng.standard_normal(len(heard)) * rms * 10 ** (-10 / 20)
        talk = rec_x[int((t + 300) * SR): int((t + 306) * SR)]                  # 6 s of other speech over it
        heard[int(8 * SR): int(14 * SR)] += talk * 1.5
        # played with a 4 s pause after 12 s: build a synthetic recording region
        rec2 = rec_x.copy()
        p1 = heard[: int(12 * SR)]; p2 = heard[int(12 * SR):]
        at = int((t + 400) * SR)
        rec2[at: at + len(p1)] = p1; rec2[at + len(p1) + 4 * SR: at + len(p1) + 4 * SR + len(p2)] = p2
        rec = Recording(rec2)
        res = match_clip(rec, rec2, clip, f"selftest{trial}")
        want = [(at / SR, 0.0), ((at + len(p1) + 4 * SR) / SR, 12.0)]
        found = [(sg["rec_in"] - sg["clip_in"], sg) for sg in res["segments"]]
        good = 0
        for w_rec, w_clip in want:
            off = w_rec - w_clip
            if any(abs(o - off) < 0.02 for o, _ in found): good += 1
        print(f"trial {trial}: want pieces at {[round(w[0],2) for w in want]}, found " +
              ", ".join(f"[{sg['rec_in']:.2f}-{sg['rec_out']:.2f} clip {sg['clip_in']:.1f}-{sg['clip_out']:.1f}]" for _, sg in found) + f"  -> {good}/2")
        ok += good == 2
    print("selftest", "PASS" if ok == 3 else "FAIL")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("recording"); ap.add_argument("clips", nargs="*")
    ap.add_argument("--out"); ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    rec_x = load16(a.recording)
    if a.selftest: return selftest(rec_x)
    rec = Recording(rec_x)
    out = []
    for c in a.clips:
        r = match_clip(rec, rec_x, load16(c), os.path.basename(c))
        print(f'{r["clip"]}: {len(r["segments"])} segment(s) ' + " ".join(f'[{s["rec_in"]:.2f}-{s["rec_out"]:.2f} <- clip {s["clip_in"]:.1f}-{s["clip_out"]:.1f}]' for s in r["segments"]), flush=True)
        out.append(r)
    if a.out: json.dump(out, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
