#!/usr/bin/env python3
"""A Johnny Harris-style score under a long-form edit (C4367, OB 2026-10-20: "make sure the background music matches a Johnny
Harris type of video... really analyze his style"). Several licensed tracks, each owning a stretch of the edit (a chapter or a
beat), silence where the music drops out so a line lands dry, fades or hard stops at the joins, every cue EQ-carved for speech
(music_bed._load: -3 dB at 2.5 kHz, -2 dB below 150 Hz) and ducked under the voice.

cue sheet (JSON): {"duck_db": 4, "ceiling_db": -6 (the bed never closer to his speech level), "swells": [[edit t0, edit t1, +dB], ...],
  "cues": [{"track": path, "t0": edit s, "t1": edit s, "start": s into the track (0), "db": level vs the voice (-22),
            "fade_in": s (0.8), "fade_out": s (1.2), "loop": true}]}
build(sheet, voice, sr, t_offset) -> (N, 2): the bed for a voice array that starts at edit time t_offset (assemble.py --range).
Levels are relative to the voice's speech RMS, so a test range and the full render sit the same. Licensed tracks only.

  preview: python3 -I score.py SHEET.json VOICE.wav OUT.m4a START END
"""
import json, os, subprocess, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from music_bed import _load, loop_points, SR   # noqa: E402
from music_mix import duck_gain                 # noqa: E402

_cache, _loops = {}, {}


def _track(path):
    if path not in _cache: _cache[path] = _load(path)
    return _cache[path]


def _speech_db(v):
    """Typical speech level: the 70th percentile of 100 ms RMS over the frames within 30 dB of the loudest."""
    fr = int(0.1 * SR); n = len(v) // fr
    if n < 3: return -24.0
    r = 10 * np.log10((v[: n * fr].reshape(n, fr) ** 2).mean(1) + 1e-12)
    return float(np.percentile(r[r > r.max() - 30], 70))


def _music_db(x):
    fr = int(0.4 * SR); m = x.mean(1); n = len(m) // fr
    if n < 1: return -40.0
    r = 10 * np.log10((m[: n * fr].reshape(n, fr) ** 2).mean(1) + 1e-12)
    return float(np.percentile(r, 60))


def _ride(x, target, win=3.0, smooth=2.0, cut=6.0, boost=3.0):
    """A slow level rider (C4367 v4, OB: "doesnt flow well"): the cue's 3 s loudness held near its target, so a track's own swells
    (bell phrases, drops, builds) don't push 10 dB in and out under the voice. Cuts up to `cut` dB, lifts up to `boost` dB, eased
    over `smooth` seconds; the track's beat and phrasing inside a few seconds are untouched."""
    from scipy.signal import lfilter
    from scipy.ndimage import uniform_filter1d
    y = lfilter([1.53512485958697, -2.69169618940638, 1.19839281085285], [1.0, -1.69065929318241, 0.73248077421585], x, axis=0)
    y = lfilter([1.0, -2.0, 1.0], [1.0, -1.99004745483398, 0.99007225036621], y, axis=0)
    hop, w = int(0.25 * SR), int(win * SR)
    if len(y) < w + hop: return x
    p = (y ** 2).sum(1); c = np.concatenate([[0.0], np.cumsum(p)])
    centres = np.arange(0, len(y) - w, hop)
    L = -0.691 + 10 * np.log10((c[centres + w] - c[centres]) / w + 1e-12)
    gdb = np.clip(target - L, -cut, boost)
    gdb[L < target - 30] = 0.0                       # a gap or a tail in the track: leave it be, don't lift it
    gdb = uniform_filter1d(gdb, max(1, int(smooth / 0.25)))
    t = centres + w / 2
    return x * (10 ** (np.interp(np.arange(len(x)), t, gdb) / 20))[:, None]


def _music_lufs(x):
    """BS.1770 gated loudness of a stereo block at 48 kHz (K-weighted): matches tracks by how loud they sound, not by raw level
    (C4367 v4: by raw p60 level a beat-heavy track sat 7 LU quieter than a pad cued to the same number)."""
    from scipy.signal import lfilter
    y = lfilter([1.53512485958697, -2.69169618940638, 1.19839281085285], [1.0, -1.69065929318241, 0.73248077421585], x, axis=0)
    y = lfilter([1.0, -2.0, 1.0], [1.0, -1.99004745483398, 0.99007225036621], y, axis=0)
    blk, hop = int(0.4 * SR), int(0.1 * SR)
    if len(y) < blk: return -70.0
    p = (y ** 2).sum(1); c = np.concatenate([[0.0], np.cumsum(p)])
    ms = (c[blk::hop][: (len(y) - blk) // hop + 1] - c[0:len(y) - blk + 1:hop][: (len(y) - blk) // hop + 1]) / blk
    L = -0.691 + 10 * np.log10(ms + 1e-12); g = ms[L > -70]
    if not len(g): return -70.0
    rel = -0.691 + 10 * np.log10(g.mean()) - 10; g2 = ms[L > rel]
    return float(-0.691 + 10 * np.log10((g2 if len(g2) else g).mean()))


def _cue_audio(path, start, length, loop=True):
    x = _track(path); s = int(start * SR)
    if s + length <= len(x): return x[s: s + length].copy()
    out = x[s:].copy()
    if not loop: return np.pad(out, ((0, length - len(out)), (0, 0)))
    if path not in _loops: _loops[path] = loop_points(x)
    L0, L1, _ = _loops[path]
    if s >= L1: out = x[L0:L1].copy()        # started past the loop end: carry on from the loop body
    else: out = x[s:L1].copy()
    xf = int(0.04 * SR); ramp = np.linspace(0, 1, xf)[:, None]; body = x[L0:L1]
    while len(out) < length:
        out[-xf:] = out[-xf:] * (1 - ramp) + body[:xf] * ramp
        out = np.concatenate([out, body[xf:]])
    return out[:length]


def build(sheet, voice, sr=SR, t_offset=0.0):
    assert sr == SR
    S = json.load(open(sheet)) if isinstance(sheet, str) else sheet
    v = voice if voice.ndim == 1 else voice.mean(1); n = len(v)
    bed = np.zeros((n, 2)); ref = _speech_db(v)
    for c in S["cues"]:
        a, b = c["t0"] - t_offset, c["t1"] - t_offset          # this cue in the range's own time
        if b <= 0 or a >= n / SR: continue
        start = c.get("start", 0.0)
        L = int(round((c["t1"] - c["t0"]) * SR))
        x = _cue_audio(c["track"], start, L, c.get("loop", True))
        lev = _music_lufs(x) if S.get("level") == "lufs" else _music_db(x)
        g = 10 ** ((ref + c.get("db", -22.0) - lev) / 20)   # level vs the voice, from the cue's own loudness
        x = x * g
        if S.get("ride"): x = _ride(x, ref + c.get("db", -22.0), **S["ride"])
        fi, fo = int(c.get("fade_in", 0.8) * SR), int(c.get("fade_out", 1.2) * SR)
        if fi: x[:fi] *= np.linspace(0, 1, fi)[:, None]
        if fo: x[-fo:] *= np.linspace(1, 0, fo)[:, None]
        i0 = int(round(a * SR))                              # may be negative (the cue began before the range)
        lo, hi = max(0, i0), min(n, i0 + L)
        if hi > lo: bed[lo:hi] += x[lo - i0: hi - i0]
    def swells():
        for a, b, db in S.get("swells", []):   # [edit t0, edit t1, +dB]: the bed rises over a title or a closing line (0.4 s ramps)
            a, b = a - t_offset, b - t_offset
            if b <= 0 or a >= n / SR: continue
            g = np.ones(n); ia, ib = int(round(a * SR)), int(round(b * SR)); r = int(0.4 * SR); top = 10 ** (db / 20)
            env = np.concatenate([np.linspace(1, top, r), np.full(max(0, ib - ia - 2 * r), top), np.linspace(top, 1, r)])
            lo, hi = max(0, ia), min(n, ia + len(env))
            if hi > lo: g[lo:hi] = env[lo - ia: hi - ia]
            bed[:] *= g[:, None]
    late = S.get("swells_after_ceiling", False)   # C4367 v4: a title swell over silence may sit above the ceiling (no voice to cover)
    if not late: swells()
    ceil = S.get("ceiling_db")
    if ceil is not None:   # never closer than ceil dB to his speech level: a crescendo inside a cue plus a swell can creep up on the voice
        from scipy.ndimage import minimum_filter1d, uniform_filter1d
        hop = int(0.1 * SR); m = bed.mean(1); nh = len(m) // hop
        if nh:
            p = np.convolve((m[: nh * hop].reshape(nh, hop) ** 2).mean(1), np.ones(4) / 4, "same")   # 0.4 s level
            g = np.minimum(1.0, 10 ** ((ref + ceil - 10 * np.log10(p + 1e-12)) / 20))
            g = uniform_filter1d(minimum_filter1d(g, 5), 7)                                        # hold, then ease: no pumping
            bed *= np.interp(np.arange(len(m)), np.arange(nh) * hop + hop / 2, g)[:, None]
    if late: swells()
    for a, b, db, ri, ro in S.get("dips", []):   # [edit t0, t1, dB, ramp in, ramp out]: the running cue dips (or goes silent) for a line
        fl = 10 ** (db / 20)                        # and comes back where it would have been: a mute, not a stop and a new start
        i0, i1 = max(0, int((a - ri - t_offset) * SR)), min(n, int((b + ro - t_offset) * SR))
        if i1 <= i0: continue
        ts = np.arange(i0, i1) / SR + t_offset
        g = np.where(ts < a, 1 + (fl - 1) * np.clip((ts - (a - ri)) / ri, 0, 1),
                     np.where(ts <= b, fl, fl + (1 - fl) * np.clip((ts - b) / ro, 0, 1)))
        bed[i0:i1] *= g[:, None]
    if S.get("duck_release"):   # C4367 v4 (OB: "doesn't flow well"): a slow, held duck instead of one that pumps on every word gap
        bed *= _duck(v, sr, S.get("duck_db", 4.0), S.get("duck_attack", 0.15), S["duck_release"], S.get("duck_hold", 0.5))[:, None]
    else:
        bed *= duck_gain(v, sr, S.get("duck_db", 4.0))[:, None]
    return bed


def _duck(v, sr, db, att, rel, hold):
    """Gain that dips db while he talks: voice activity per 20 ms, held across gaps shorter than `hold` (a breath between phrases
    is still talking), then eased down over `att` and back up over `rel` seconds."""
    from scipy.ndimage import maximum_filter1d
    hop = int(sr * 0.02); n = len(v) // hop + 1
    x = np.pad(v, (0, n * hop - len(v)))
    act = (10 * np.log10((x.reshape(n, hop) ** 2).mean(1) + 1e-12) > -42).astype(np.float64)
    act = maximum_filter1d(act, size=2 * int(hold / 0.02) + 1)
    env = np.zeros(n); a_up, a_dn = 1 - np.exp(-0.02 / att), 1 - np.exp(-0.02 / rel)
    for i in range(n):
        prev = env[i - 1] if i else 0.0
        env[i] = prev + (a_up if act[i] > prev else a_dn) * (act[i] - prev)
    return np.repeat(10 ** (-db * env / 20), hop)[: len(v)]


def main():
    sheet, vwav, out, t0, t1 = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4]), float(sys.argv[5])
    raw = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-ss", str(t0), "-t", str(t1 - t0), "-i", vwav, "-ac", "1", "-ar", str(SR),
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    v = np.frombuffer(raw, np.float32).astype(np.float64)
    mix = np.stack([v, v], 1) + build(sheet, v, SR, t0)
    mix *= 0.89 / max(np.abs(mix).max(), 1e-9)
    import tempfile
    from scipy.io import wavfile
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "m.wav"); wavfile.write(p, SR, mix.astype(np.float32))
        subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", p, "-c:a", "aac", "-b:a", "192k", out], check=True)
    print(out)


if __name__ == "__main__":
    main()
