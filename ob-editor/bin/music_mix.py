#!/usr/bin/env python3
"""Music bed for OB's reels: one of his saved viral tracks under the voice, ducked while he talks.

  python3 music_mix.py preview EDL.json TAKE_48k.wav TRACK START OUT.m4a [--seconds 20] [--rel -16] [--duck 5]
  (as a module: bed(track, start, voice_mono, sr, rel_db, duck_db) -> stereo float array the length of voice)

Level: the track is set to (voice loudness + rel_db) LUFS, rel -16 for instrumentals, about -19 when the
song has vocals. It dips duck_db more while he speaks (80 ms attack, 300 ms release), and fades in over
0.4 s and out over 1.2 s. OB 2026-10-16: on short form, use his saved viral tracks; royalty-free doesn't
matter (those reels can't be boosted, his call). Give him several options to pick from.
"""
import json, os, subprocess, sys, tempfile
import numpy as np
from scipy.io import wavfile

SR = 48000


def lufs_of(arr, sr=SR):
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "x.wav"); wavfile.write(p, sr, arr.astype(np.float32))
        r = subprocess.run(["ffmpeg", "-nostdin", "-i", p, "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
    try: return float(r[r.rfind("I:"):].split()[1])
    except Exception: return -70.0


def load_track(track, start, length):
    raw = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-ss", f"{start:.3f}", "-t", f"{length + 0.5:.3f}", "-i", track,
                          "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    m = np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64)
    n = int(length * SR)
    if len(m) < n:                                   # short track: loop it with a 0.5 s crossfade
        out = m.copy(); xf = int(0.5 * SR)
        while len(out) < n:
            ramp = np.linspace(0, 1, xf)[:, None]; out[-xf:] = out[-xf:] * (1 - ramp) + m[:xf] * ramp; out = np.concatenate([out, m[xf:]])
        m = out
    return m[:n]


def duck_gain(voice, sr, duck_db):
    hop = int(sr * 0.02); n = len(voice) // hop + 1
    v = np.pad(voice, (0, n * hop - len(voice)))
    lev = 10 * np.log10((v.reshape(n, hop) ** 2).mean(1) + 1e-12)
    active = (lev > -42).astype(np.float64)
    env = np.zeros(n); a_up, a_dn = 1 - np.exp(-0.02 / 0.08), 1 - np.exp(-0.02 / 0.30)
    for i in range(n):
        prev = env[i - 1] if i else 0.0
        env[i] = prev + (a_up if active[i] > prev else a_dn) * (active[i] - prev)
    g = 10 ** (-duck_db * env / 20)
    return np.repeat(g, hop)[: len(voice)]


def bed(track, start, voice, sr, rel_db=-16.0, duck_db=5.0):
    m = load_track(track, start, len(voice) / sr)
    if len(m) != len(voice):   # the decoder can come back a sample short or long: match the voice exactly (11-07 crash)
        m = np.pad(m, ((0, max(0, len(voice) - len(m))), (0, 0)))[: len(voice)]
    target = lufs_of(voice[:, None].repeat(2, 1) if voice.ndim == 1 else voice, sr) + rel_db
    m *= 10 ** ((target - lufs_of(m, sr)) / 20)
    m *= duck_gain(voice if voice.ndim == 1 else voice.mean(1), sr, duck_db)[:, None]
    fi, fo = int(0.4 * sr), int(1.2 * sr)
    m[:fi] *= np.linspace(0, 1, fi)[:, None]; m[-fo:] *= np.linspace(1, 0, fo)[:, None]
    return m


def voice_track(edl, take_wav, seconds=None):
    """The edit's voice exactly as the render plays it (pieces, gaps, room-tone fills, no fades at joins).
    Rows with "audio": "clip" take their sound from spec["clip"]["wav"] at clip_in (a reaction's source video)."""
    spec = json.load(open(edl)); rows = spec["rows"]
    sr, x = wavfile.read(take_wav); x = x.astype(np.float64); x = x.mean(1) if x.ndim > 1 else x; x /= 32768.0
    clip = None
    if any(r.get("audio") == "clip" for r in rows):
        csr, clip = wavfile.read(spec["clip"]["wav"]); clip = clip.astype(np.float64); clip = clip.mean(1) if clip.ndim > 1 else clip; clip /= 32768.0
        assert csr == sr, f"clip wav is {csr} Hz, take is {sr} Hz"
    parts, f = [], int(0.008 * sr)
    for i, r in enumerate(rows):
        a, b = int(r["src_in"] * sr), int((r["src_out"] + r.get("gap", 0)) * sr)
        if r.get("audio") == "clip":
            ca = int(r["clip_in"] * sr); seg = clip[ca:ca + (b - a)].copy()
            if len(seg) < b - a: seg = np.pad(seg, (0, b - a - len(seg)))
        else:
            seg = x[a:b].copy()
        if r.get("fill") == "room":
            k = int((r["src_out"] - r["src_in"]) * sr); seg[k:] *= 0.05
        jp = i > 0 and rows[i - 1].get("gap", 0) == 0 and abs(rows[i - 1]["src_out"] - r["src_in"]) < 0.002
        jn = i + 1 < len(rows) and r.get("gap", 0) == 0 and abs(r["src_out"] - rows[i + 1]["src_in"]) < 0.002
        if not jp: seg[:f] *= np.linspace(0, 1, f)
        if not jn: seg[-f:] *= np.linspace(1, 0, f)
        parts.append(seg)
    v = np.concatenate(parts)
    return (v[: int(seconds * sr)] if seconds else v), sr


def preview(edl, take_wav, track, start, out, seconds=20.0, rel=-16.0, duck=5.0):
    v, sr = voice_track(edl, take_wav, seconds)
    v *= 10 ** ((-20.0 - lufs_of(v, sr)) / 20)                 # same voice level as the render (-20 LUFS mono)
    mix = v[:, None].repeat(2, 1) + bed(track, start, v, sr, rel, duck)
    mix *= 10 ** ((-14.0 - lufs_of(mix, sr)) / 20); mix = np.clip(mix, -0.89, 0.89)
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "m.wav"); wavfile.write(p, sr, mix.astype(np.float32))
        subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", p, "-c:a", "aac_at", "-b:a", "160k", out], check=True)
    print("preview", out)


if __name__ == "__main__":
    if sys.argv[1] == "preview":
        a = sys.argv
        opt = lambda k, d: float(a[a.index(k) + 1]) if k in a else d
        preview(a[2], a[3], a[4], float(a[5]), a[6], opt("--seconds", 20.0), opt("--rel", None) if "--rel" in a else sys.exit("music_mix preview: pass --rel DB (no default level any more: the bed is 27 LU under his voice, stem vs stem, from formats.json; run music_pick.py apply WORK instead)"), opt("--duck", 5.0))
