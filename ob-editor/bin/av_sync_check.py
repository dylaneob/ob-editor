#!/usr/bin/env python3
"""Lip-sync check for a rendered EDL reel, measured against the camera file itself (OB 10-19: "the audio seems to not match my lips").

For each talking-head row (no full-screen cover) it measures:
  video lag  = which camera frame the final shows, vs the frame the EDL asked for (motion signature, face region)
  audio lag  = where the final's voice sits, vs the camera's own scratch audio at the same instant (cross-correlation)
The camera's picture and its own mic are in sync by construction, so  A/V error = audio lag - video lag.
Positive A/V error = the voice comes EARLY (before the lips); negative = LATE.

  python3 av_sync_check.py WORK NAME [FINAL.mp4]      (default FINAL = WORK/out/NAME_A_nomusic.mp4)
"""
import json, os, subprocess, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lecture_render as LR   # noqa: E402

FPS = 30000 / 1001; SR = 48000; W, H = 108, 192
fr = lambda t: int(round(t * FPS))


def frames(path, vf, ss=None, n=None):
    cmd = ["ffmpeg", "-nostdin", "-loglevel", "error"] + (["-ss", f"{ss:.4f}"] if ss is not None else []) + ["-i", path]
    cmd += ["-vf", f"{vf}scale={W}:{H}:flags=area,format=gray"] + (["-frames:v", str(n)] if n else []) + ["-f", "rawvideo", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, H, W).astype(np.float32)


def audio(path, ss=0.0, dur=None):
    cmd = ["ffmpeg", "-nostdin", "-loglevel", "error", "-ss", f"{ss:.4f}", "-i", path] + (["-t", f"{dur:.4f}"] if dur else [])
    cmd += ["-map", "0:a:0", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"]
    return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, np.float32).astype(np.float64)


def motion(F):                      # per-frame motion energy in the face band (above the captions)
    band = F[:, 10:85, 15:93]
    return np.abs(np.diff(band, axis=0)).mean(axis=(1, 2))


def xcorr_ms(seg, ref, maxlag_s=1.0):   # lag of seg inside ref (ref padded by maxlag on both sides), GCC-PHAT
    n = len(ref) + len(seg); nfft = 1 << (n - 1).bit_length()
    A = np.fft.rfft(ref, nfft); B = np.fft.rfft(seg, nfft); X = A * np.conj(B); X /= np.abs(X) + 1e-12
    cc = np.fft.irfft(X, nfft); m = int(maxlag_s * SR)
    k = int(np.argmax(cc[: 2 * m + 1]))
    return (k - m) / SR * 1000.0, float(cc[k] / (np.abs(cc[: 2 * m + 1]).mean() + 1e-12))


def main():
    work, name = sys.argv[1:3]
    final = sys.argv[3] if len(sys.argv) > 3 else f"{work}/out/{name}_A_nomusic.mp4"
    spec = json.load(open(f"{work}/{name}_edl.json")); rows = spec["rows"]
    take = spec.get("take") or LR.TAKES[name][0]
    src = next(p for p in (f"/Volumes/T7/{take}.MP4", f"/Volumes/T7/RAW-FOOTAGE/camera/{take}.MP4") if os.path.exists(p))
    Ffin = frames(final, ""); Afin = audio(final)
    starts = [fr(r["edit_in"]) for r in rows] + [len(Ffin)]
    out = []
    for i, r in enumerate(rows):
        if (r.get("fx") or {}).keys() & {"card", "proof", "cuts"}: continue        # covered rows show no lips
        if ((r.get("fx") or {}).get("pills") or {}).get("on") == "card": continue
        n = starts[i + 1] - starts[i]
        if n < 30: continue
        f0 = fr(r["src_in"]); pad = 6
        crop = LR.FRAMES.get(r.get("framing") or "wide", "")
        Fcam = frames(src, crop, ss=(f0 - pad) / FPS - 0.002, n=n + 2 * pad)      # lands on frame f0 - pad, as lecture_render's ss()
        mf, mc = motion(Ffin[starts[i]: starts[i + 1]]), motion(Fcam)
        best, bd = -9, 0
        for dd in range(-pad, pad + 1):                       # final frame j shows camera frame f0 + j + dd
            y = mc[pad + dd: pad + dd + len(mf)]
            if len(y) < len(mf): continue
            c = np.corrcoef(mf, y)[0, 1]
            if c > best: best, bd = c, dd
        vlag_ms = bd / FPS * 1000.0
        # audio: the middle of the row (skip 0.15 s at each end), final vs camera's own audio around the same source instant
        a0 = starts[i] / FPS + 0.15; dur = max(0.6, n / FPS - 0.3)
        seg = Afin[int(a0 * SR): int((a0 + dur) * SR)]
        s_t = r["src_in"] + (a0 - starts[i] / FPS) + (f0 / FPS - r["src_in"])
        ref = audio(src, ss=s_t - 1.0, dur=dur + 2.0)
        alag_ms, pk = xcorr_ms(seg, ref)
        out.append({"row": i, "edit_in": r["edit_in"], "video_lag_ms": round(vlag_ms, 1), "video_corr": round(float(best), 2),
                    "audio_lag_ms": round(alag_ms, 1), "audio_peak": round(pk, 1), "av_error_ms": round(alag_ms - vlag_ms, 1)})
        print(f"row {i:2d} @{r['edit_in']:6.2f}  video {vlag_ms:+6.1f} ms (corr {best:.2f})  audio {alag_ms:+6.1f} ms (peak {pk:5.1f})  "
              f"=> A/V {alag_ms - vlag_ms:+6.1f} ms", flush=True)
    good = [o for o in out if o["video_corr"] > 0.5 and o["audio_peak"] > 8]
    if good:
        e = np.array([o["av_error_ms"] for o in good])
        print(f"{name}: {len(good)}/{len(out)} rows measured cleanly | A/V error median {np.median(e):+.1f} ms, range {e.min():+.1f} to {e.max():+.1f} ms "
              f"(+ = voice early, - = voice late)")
    json.dump(out, open(f"{work}/qc/{name}_avsync.json", "w"), indent=1)


if __name__ == "__main__":
    main()
