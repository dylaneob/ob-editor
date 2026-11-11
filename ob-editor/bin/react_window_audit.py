#!/usr/bin/env python3
"""Reaction shots must be him watching that very clip (M34). OB 2026-10-31: "that wasn't me reacting it that was me scratching my
leg" (C4405 Ken, the opener at 47.2 s) and "you can see me looking away and not playing the vids, I played the Gary vid you can hear
it" (C4402 2 Brecka: the claims' reactions came from pauses between his lines, 303-377 s; his one playback was at 24.26 s).

  sound   When the creator's clip is audible in his take, every reaction sits where his phone played those seconds:
          camera = clip + one of the playback offsets the sound finds (6 s windows of the clip, each matched against the camera's
          own audio; a playback is two or more windows from separate parts of the clip agreeing on one offset: overlapping windows
          agree by chance on music). A reaction anywhere else FAILs. No playback heard (he watched muted): WARN, the frames decide.
  hands   Information only: hand movement per 0.5 s inside the reaction. It can't tell a scratch from handling the phone (C4405's
          scratch 2.0-2.6; C4404's good reaction 1.7-2.8), so pick the stillest stretch with the phone in hand and look at the sheet.
  frames  A sheet of 8 frames per reaction in OUT_DIR, to look at before the render.

    python3 -I react_window_audit.py CAMERA CLIP WORDS.json OUT_DIR name:cam_start:clip_start:dur [...]
    python3 -I react_window_audit.py --selftest      (the 10-31 windows on the T7 takes: the old ones must FAIL or WARN, the new ones PASS)

Spectrogram matching: 32 log bands 200-4000 Hz, 20 ms hop, each band's slow level (2 s) removed so the phone speaker and the room
drop out, then normalized cross-correlation. Raw-waveform matching scattered on the same takes (the room smears a phone's sound).
"""
import json, os, subprocess, sys
import numpy as np
from scipy.signal import fftconvolve

SR, HOP, WIN, NB = 16000, 320, 1024, 32
FPS_A = SR / HOP
_CACHE = {}


def load(path):
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).astype(np.float64)


def feats(path):
    if path in _CACHE: return _CACHE[path]
    x = load(path); n = 1 + (len(x) - WIN) // HOP
    idx = np.arange(WIN)[None, :] + HOP * np.arange(n)[:, None]
    S = np.abs(np.fft.rfft(x[idx] * np.hanning(WIN), axis=1)) ** 2
    f = np.fft.rfftfreq(WIN, 1 / SR); edges = np.geomspace(200, 4000, NB + 1)
    L = np.log(np.stack([S[:, (f >= edges[i]) & (f < edges[i + 1])].sum(1) for i in range(NB)], 1) + 1e-10)
    k = int(2.0 * FPS_A); ker = np.ones(k) / k
    _CACHE[path] = L - np.stack([np.convolve(L[:, i], ker, mode="same") for i in range(NB)], 1)
    return _CACHE[path]


def speech_mask(words, n):
    m = np.zeros(n, bool)
    for w in words:
        a = w.get("start", w.get("s")) if isinstance(w, dict) else w[0]; b = w.get("end", w.get("e")) if isinstance(w, dict) else w[1]
        m[int(float(a) * FPS_A):int(float(b) * FPS_A) + 1] = True
    return m


def ncc_curve(cam, y, speech):
    m = len(y); c2 = np.concatenate([[0.0], np.cumsum((cam ** 2).sum(1))])
    num = sum(fftconvolve(cam[:, i], y[::-1, i], mode="valid") for i in range(NB))
    ncc = num / (np.sqrt(np.maximum(c2[m:] - c2[:-m], 1e-9)) * np.linalg.norm(y))
    sp = np.convolve(speech.astype(float), np.ones(m), mode="valid")[:len(ncc)] / m
    return np.where(sp > 0.3, -1.0, ncc)   # his own voice is not the clip


def playbacks(camera, clip, words):
    """Offsets (camera - clip) where his phone played the clip: [(offset, windows agreeing, mean ncc)]."""
    cam, src = feats(camera), feats(clip); speech = speech_mask(words, len(cam))
    win, step = int(8 * FPS_A), int(4 * FPS_A); hits = []
    for a in range(0, max(1, len(src) - win + 1), step):
        y = src[a:a + win]
        if len(y) < FPS_A * 4: break
        c = ncc_curve(cam, y, speech); k = int(np.argmax(c)); hits.append((round((k - a) / FPS_A, 2), float(c[k]), a / FPS_A))
    hits.sort(); groups = []
    for h in hits:
        if groups and h[0] - groups[-1][-1][0] <= 0.15: groups[-1].append(h)
        else: groups.append([h])
    out = []
    for g in groups:   # two windows from separate parts of the clip (8 s apart or more) must agree
        starts = [st for _, _, st in g]
        if max(starts) - min(starts) >= 8 and np.mean([v for _, v, _ in g]) >= 0.12:
            out.append((float(np.median([o for o, _, _ in g])), len(g), float(np.mean([v for _, v, _ in g]))))
    return out


def hands(camera, a, dur):
    """Mean frame difference per 0.5 s in his hands-and-lap band (36-70% of the frame height), 10 fps, 108 x 192 grey."""
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{a:.3f}", "-t", f"{dur:.3f}", "-i", camera, "-vf",
                          "fps=10,scale=108:192,format=gray", "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
    v = np.frombuffer(raw, np.uint8).reshape(-1, 192, 108).astype(np.float32)
    d = np.abs(np.diff(v, axis=0))[:, 70:135, 10:100].mean((1, 2))
    return [(a + (i + 1) / 10, float(d[i:i + 5].mean())) for i in range(0, len(d), 5)]


def sheet(camera, a, dur, path):
    ts = [a + dur * (j + 0.5) / 8 for j in range(8)]
    ins = sum((["-ss", f"{t:.3f}", "-i", camera] for t in ts), [])
    fc = "".join(f"[{j}:v]scale=180:-2,trim=end_frame=1[s{j}];" for j in range(8)) + "".join(f"[s{j}]" for j in range(8)) + "hstack=inputs=8"
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", *ins, "-filter_complex", fc, "-frames:v", "1", path], check=True)


def audit(camera, clip, words, out_dir, items, quiet=False):
    """items: [(name, camera start, clip start, dur)]. Returns ("PASS" | "WARN" | "FAIL", [lines])."""
    os.makedirs(out_dir, exist_ok=True); pb = playbacks(camera, clip, words); lines, worst = [], "PASS"
    rank = {"PASS": 0, "WARN": 1, "FAIL": 2}
    lines.append("  playback heard at " + (", ".join(f"camera = clip + {o:.2f} s ({n} windows, ncc {v:.2f})" for o, n, v in pb) if pb else
                                          "nowhere (he watched it muted): the frames decide"))
    for name, cs, ks, dur in items:
        st, why = "PASS", []
        if pb:
            off = cs - ks; near = min(pb, key=lambda p: abs(p[0] - off))
            if abs(near[0] - off) > 0.25:
                st = "FAIL"; why.append(f"his phone played clip {ks:.2f} s at camera {ks + near[0]:.2f}; this shot is at {cs:.2f}")
        else: st = "WARN"; why.append("no playback heard: check the sheet")
        hm = hands(camera, cs, dur); t_mx, v_mx = max(hm, key=lambda q: q[1]) if hm else (cs, 0.0)
        why.append(f"hands: most movement {v_mx:.1f} at {t_mx:.1f} s")
        sp = os.path.join(out_dir, f"{name}.jpg"); sheet(camera, cs, dur, sp)
        lines.append(f"  {st:4s} {name:7s} camera {cs:7.2f}-{cs + dur:7.2f} (clip {ks:5.2f}-{ks + dur:5.2f})  {'; '.join(why) or 'his phone was playing it'}  [{sp}]")
        worst = max(worst, st, key=rank.get)
    if not quiet: print("\n".join([f"reaction audit: {worst}"] + lines), flush=True)
    return worst, lines


def words_of(path):
    t = open(path).read(); d = json.loads(t[t.index("["):]) if t.lstrip()[0] != "{" else json.loads(t)
    return d if isinstance(d, list) else d.get("words", [])


def selftest():
    J = "/Volumes/T7/OB-EDITS/2026-10-31-fdoe-brecka"; out = os.path.join(J, "_work/fdoe/react_selftest"); ok = True
    gary = (f"/Volumes/T7/C4402 2.MP4", f"{J}/sources/garybrecka/icedcoffeehour_brecka_DH13wPaSV1d.mp4", words_of(f"{J}/_work/T1_cam_apple.json"))
    old = [("c2a", 303.0, 11.46, 8.22), ("c3", 331.5, 29.16, 7.86), ("c5", 376.6, 40.92, 8.28)]
    new = [("c1", 24.26, 0.0, 11.40), ("c2a", 35.72, 11.46, 8.22), ("c2b", 46.40, 22.14, 3.06), ("c3", 53.42, 29.16, 7.86),
           ("c4", 61.34, 37.08, 3.78), ("c5", 65.18, 40.92, 8.28)]
    s1, _ = audit(*gary, out, old, True); s2, l2 = audit(*gary, out, new, True)
    print(f"  Gary 10-30 windows (pauses between his lines): {s1} (must FAIL)"); ok &= s1 == "FAIL"
    print(f"  Gary 10-31 windows (his playback): {s2} (must PASS)"); ok &= s2 == "PASS"
    if s2 != "PASS": print("\n".join(l2))
    ken = ("/Volumes/T7/C4405.MP4", f"{J}/sources/kwpenn/kwpenn_DW88nj1jhm4.mp4", words_of(f"{J}/_work/T3_cam_apple.json"))
    s3, l3 = audit(*ken, out, [("open", 48.8, 0.0, 3.3)], True)
    print(f"  Ken 48.8 (watched muted): {s3} (must be WARN: no playback heard, no made-up one)"); ok &= s3 == "WARN"
    if s3 != "WARN": print("\n".join(l3))
    niz = ("/Volumes/T7/C4404.MP4", f"{J}/sources/nitzanazencot/nitzanazencot_DWEohb-jjGj.mp4", words_of(f"{J}/_work/T2_cam_apple.json"))
    s5, l5 = audit(*niz, out, [("open", 19.8, 0.0, 2.72)], True)
    print(f"  Nitzan 19.8 (watched muted): {s5} (must be WARN)"); ok &= s5 == "WARN"
    if s5 != "WARN": print("\n".join(l5))
    print("SELFTEST " + ("PASSED" if ok else "FAILED")); return ok


if __name__ == "__main__":
    if sys.argv[1:2] == ["--selftest"]: sys.exit(0 if selftest() else 1)
    if len(sys.argv) < 6: print(__doc__); sys.exit(2)
    items = [(p.split(":")[0], *map(float, p.split(":")[1:])) for p in sys.argv[5:]]
    st, _ = audit(sys.argv[1], sys.argv[2], words_of(sys.argv[3]), sys.argv[4], items)
    sys.exit(2 if st == "FAIL" else 0)
