#!/usr/bin/env python3
"""Real UI sounds for the editor (opt-in; nothing imports this yet).

Maps OB's six sound roles to chosen Kenney CC0 files (vendor/kenney/...), converted to 48 kHz mono WAV in
~/ob-editor/assets/sfx_real/ as ROLE_1.wav, ROLE_2.wav, ROLE_3.wav (the same ROLE_N naming the synthesized kit uses, so the
variants rotate and one sound never repeats back to back).

    python3 -I sfx_real.py            # build anything missing, then print the pick list with levels
    python3 -I sfx_real.py build -f   # rebuild every file
    python3 -I sfx_real.py list       # just print the table

From code:
    import sfx_real
    sfx_real.build()                                  # idempotent, never rewrites an existing file
    sfx_real.hit("click", 41.2, n=0)                  # -> {"t": 41.2, "file": ".../click_1.wav", "db": -26.0}
    # drop those dicts into story/sfx_plan.json {"hits": [...]} (assemble.py OB_SFX_PLAN path). Not wired into assemble.py or sfx.py.

Level convention (same as assemble.py's plan path): "db" = the file's loudest 100 ms (RMS) relative to his speech level.
House level is subtle, -25 to -28. Files are peak-normalised to -6 dBFS like sfx.py; assemble re-scales each hit by its own measured
loudest-100 ms level, so the converted files only need to be clean (trimmed, 4 ms fade-out, no clipping).
Note: clicks and ticks last 20 to 100 ms, so their peak sits about 25 dB above their 100 ms level. At -26 a click's peak ends near his speech level; if clicks or ticks feel present, drop them another 6 dB in the plan.

Kenney has no true whoosh or paper recording. The closest matches by spectrum and length were chosen (noise sweeps for swipe and whoosh,
scratch noise for paper). Audition them once: they were picked from names and measured levels, not by ear.
Licence: CC0 (see vendor/LICENSES.md).
"""
import json, os, subprocess, sys
import numpy as np
from scipy.io import wavfile

SR = 48000
HOME = os.path.expanduser("~/ob-editor")
SRC = f"{HOME}/vendor/kenney"
OUT = f"{HOME}/assets/sfx_real"
PACK = {"i": "kenney_interface-sounds", "u": "kenney_ui-audio"}

# role -> [(pack, file, why)]  (three variants each, in rotation order)
PICKS = {
    "click":  [("i", "click_001", "soft plastic click, 0.10 s, mid-bright"), ("u", "click3", "short dry click, 0.08 s"), ("u", "click1", "rounder click, 0.09 s")],
    "tick":   [("i", "tick_002", "very short bright blip, 0.02 s"), ("i", "tick_001", "short bright blip, 0.04 s"), ("i", "tick_004", "slightly lower tick, 0.06 s")],
    "pop":    [("i", "drop_002", "low soft plop, 0.19 s"), ("i", "drop_003", "lower plop, 0.19 s"), ("i", "drop_001", "brighter bubble, 0.13 s")],
    "swipe":  [("i", "open_002", "short rising noise swish, 0.31 s"), ("i", "open_004", "rising swish, 0.32 s"), ("i", "maximize_003", "quick swipe, 0.21 s")],
    "paper":  [("i", "scratch_004", "soft paper-like rub, 0.33 s"), ("i", "scratch_005", "paper slide, 0.33 s, falling"), ("i", "scratch_002", "short rub, 0.14 s")],
    "whoosh": [("i", "maximize_005", "long rising sweep, 0.53 s"), ("i", "maximize_004", "rising sweep, 0.42 s"), ("i", "minimize_005", "falling sweep, 0.53 s")],
}
# recommended level vs his speech, in assemble.py's convention (loudest 100 ms RMS), inside the -25..-28 house range
DB = {"click": -26.0, "tick": -28.0, "pop": -26.0, "swipe": -25.0, "paper": -27.0, "whoosh": -25.0}
ROLES = list(PICKS)


def _decode(path):
    raw = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).astype(np.float64)


def _clean(x):
    a = np.abs(x); idx = np.where(a > 10 ** (-60 / 20))[0]          # trim digital silence (-60 dBFS)
    if len(idx):
        x = x[max(0, idx[0] - int(0.002 * SR)): idx[-1] + int(0.005 * SR)]
    n = len(x); fo = min(n // 2, int(0.004 * SR)); fi = min(n // 2, int(0.001 * SR))
    if fo > 1: x[-fo:] *= 0.5 * (1 + np.cos(np.linspace(0, np.pi, fo)))
    if fi > 1: x[:fi] *= 0.5 * (1 - np.cos(np.linspace(0, np.pi, fi)))
    return x / (np.abs(x).max() + 1e-12) * 10 ** (-6 / 20)           # peak -6 dBFS, same as sfx.py


def levels(x):
    """peak dBFS and loudest-100 ms RMS dBFS (the measure assemble.py uses for plan hits)."""
    fr = int(0.1 * SR); k = max(1, int(np.ceil(len(x) / fr))); xx = np.zeros(k * fr); xx[:len(x)] = x
    return (round(20 * np.log10(np.abs(x).max() + 1e-12), 1), round(10 * np.log10(max((xx.reshape(k, fr) ** 2).mean(1).max(), 1e-12)), 1))


def files(role):
    return [f"{OUT}/{role}_{i + 1}.wav" for i in range(len(PICKS[role]))]


def build(force=False):
    """Convert the picks to 48 kHz mono 32-bit WAV. Never rewrites an existing file unless force=True. Returns the paths."""
    os.makedirs(OUT, exist_ok=True); made = []
    for role, picks in PICKS.items():
        for i, (pk, name, _why) in enumerate(picks):
            dst = f"{OUT}/{role}_{i + 1}.wav"
            if os.path.exists(dst) and not force:
                continue
            src = f"{SRC}/{PACK[pk]}/Audio/{name}.ogg"
            x = _clean(_decode(src)); y = np.clip(x, -1, 1)
            wavfile.write(dst, SR, (y * (2 ** 31 - 1)).astype(np.int32)); made.append(dst)
    info = {}
    for role, picks in PICKS.items():
        for i, (pk, name, why) in enumerate(picks):
            f = f"{OUT}/{role}_{i + 1}.wav"
            if os.path.exists(f):
                x = wavfile.read(f)[1].astype(np.float64) / 2 ** 31; pkdb, rms = levels(x)
                info[os.path.basename(f)] = dict(source=f"{PACK[pk]}/Audio/{name}.ogg", dur_s=round(len(x) / SR, 3), peak_dbfs=pkdb, rms100_dbfs=rms, why=why)
    json.dump(info, open(f"{OUT}/LEVELS.json", "w"), indent=1)
    return made


def hit(role, t, n=0, db=None):
    """One entry for story/sfx_plan.json. n rotates the variants (use a running counter so the same file never repeats back to back)."""
    fs = files(role)
    return {"t": float(t), "file": fs[n % len(fs)], "db": DB[role] if db is None else db}


def table():
    info = json.load(open(f"{OUT}/LEVELS.json"))
    lines = [f"{'file':14s} {'source':36s} {'dur':>5s} {'peak':>6s} {'rms100':>7s}  note"]
    for role in ROLES:
        for i in range(len(PICKS[role])):
            k = f"{role}_{i + 1}.wav"; v = info[k]
            lines.append(f"{k:14s} {v['source'].replace('kenney_', '').replace('/Audio', ''):36s} {v['dur_s']:5.2f} {v['peak_dbfs']:6.1f} {v['rms100_dbfs']:7.1f}  {v['why']}")
        lines.append(f"{'':14s} recommended plan db for {role}: {DB[role]}")
    return "\n".join(lines)


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] == "build":
        made = build(force="-f" in args)
        print(f"built {len(made)} file(s) into {OUT}" if made else f"nothing to build ({OUT} is complete)")
    print(table())
