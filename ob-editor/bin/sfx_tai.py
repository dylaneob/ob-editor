#!/usr/bin/env python3
"""Anderson Tai's "Top 5 SFX" pack for the editor (opt-in; nothing imports this yet).

OB sent the pack on 2026-10-29 (Drive folder "Top 5 SFX", owner [email removed]) with the reel that shows
how to use it (https://www.instagram.com/reel/Dd18Qb1RDpT/). Originals, Drive ids and hashes: vendor/anderson-tai-top5-sfx/SOURCE.md.
Each sound becomes three variants in ~/ob-editor/assets/sfx_tai/ as ROLE_1.wav (as recorded), ROLE_2.wav (about a semitone
down, longer) and ROLE_3.wav (about a semitone up, shorter): the same ROLE_N naming sfx.py and sfx_real.py use, so they rotate.

    python3 -I sfx_tai.py            # build anything missing, then print the table
    python3 -I sfx_tai.py build -f   # rebuild every file
    python3 -I sfx_tai.py list       # just print the table

From code:
    import sfx_tai
    sfx_tai.build()                          # idempotent, never rewrites an existing file
    sfx_tai.hit_on("whoosh", 12.40, n=0)     # its loudest moment lands on the cut at 12.40 s -> {"t": 11.5, "file": ..., "db": -25.0}
    sfx_tai.hit("click", 3.10, n=1)          # the file starts at 3.10 s (clicks and glitches peak at once)
    # drop those dicts into story/sfx_plan.json {"hits": [...]} (assemble.py OB_SFX_PLAN path). Not wired into assemble.py or sfx.py.

The pack's own rules (from the reel): click when something pops up on screen, flash on a quick cut, whoosh from scene to scene,
glitch when text pops on screen, riser to build tension. Place a whoosh, flash or riser by its peak (hit_on), not by its start:
the whoosh swells for 0.9 s and the riser builds for about 1.7 s before the moment they belong to.
Level convention: same as sfx_real ("db" = the file's loudest 100 ms RMS relative to his speech); house range -25 to -28.
The reel mixes these 11 to 29 dB louder than that; OB wants them quiet (SKILL.md motion rule 3).
Licence: none given (a free comment-to-get giveaway). Organic and trial reels only, never ads or boosted posts.
"""
import json, os, subprocess, sys
import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sfx_real  # levels(): the loudest-100 ms measure assemble.py uses

SR = 48000
HOME = os.path.expanduser("~/ob-editor")
SRC = f"{HOME}/vendor/anderson-tai-top5-sfx"
OUT = f"{HOME}/assets/sfx_tai"
LICENCE = "none given (free giveaway pack): organic and trial reels only, never ads or boosted posts"

# role -> (source file, what it is, recommended plan db inside the -25..-28 house range)
PICKS = {
    "click":  ("click.wav", "very bright UI click, about 0.1 s", -27.0),
    "flash":  ("camera_flash.mp3", "camera-flash burst, loudest 0.25-0.40 s in", -27.0),
    "whoosh": ("whoosh.wav", "real recorded whoosh, swells to 0.9 s then a long tail", -25.0),
    "glitch": ("glitch.wav", "bright digital glitch, 0.4 s plus a short tail", -28.0),
    "riser":  ("riser.wav", "builds for about 1.7 s and stops dead at the top", -28.0),
}
PITCH = [(1, 1), (18, 17), (17, 18)]   # resample_poly up/down: as recorded, 0.99 semitone down, 0.99 semitone up
ROLES = list(PICKS)
DB = {role: v[2] for role, v in PICKS.items()}


def _decode(path):
    """48 kHz mono. The mid when L and R agree; the louder channel when they don't (the riser is out of phase, and the mid would cancel it)."""
    raw = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-i", path, "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    st = np.frombuffer(raw, np.float32).astype(np.float64).reshape(-1, 2)
    if np.corrcoef(st[:, 0], st[:, 1])[0, 1] >= 0.5:
        return st.mean(1), "mid"
    ch = int(np.argmax((st ** 2).sum(0)))
    return st[:, ch].copy(), "LR"[ch]


def _clean(x):
    """Trim digital silence at the start (-60 dBFS) and the tail once it stays 40 dB under the loudest 10 ms; 30 ms fade-out, peak -6 dBFS."""
    idx = np.where(np.abs(x) > 10 ** (-60 / 20))[0]
    x = x[max(0, idx[0] - int(0.002 * SR)):]
    w = int(0.01 * SR); k = len(x) // w
    e = 10 * np.log10((x[:k * w].reshape(k, w) ** 2).mean(1) + 1e-20)
    x = x[:min(len(x), (np.where(e > e.max() - 40)[0][-1] + 1) * w + int(0.03 * SR))].copy()
    fo = min(len(x) // 2, int(0.03 * SR)); x[-fo:] *= 0.5 * (1 + np.cos(np.linspace(0, np.pi, fo)))
    fi = min(len(x) // 2, int(0.001 * SR)); x[:fi] *= 0.5 * (1 - np.cos(np.linspace(0, np.pi, fi)))
    return x / (np.abs(x).max() + 1e-12) * 10 ** (-6 / 20)


def _peak_s(x):
    """Seconds from the file start to the middle of its loudest 20 ms (where the cut, white frame or reveal should land)."""
    w = int(0.02 * SR)
    return round((int(np.argmax(np.convolve(x ** 2, np.ones(w), mode="valid"))) + w / 2) / SR, 3)


def files(role):
    return [f"{OUT}/{role}_{i + 1}.wav" for i in range(len(PITCH))]


def build(force=False):
    """Convert the pack to 48 kHz mono 32-bit WAV, three pitches each. Never rewrites an existing file unless force=True. Returns the paths."""
    os.makedirs(OUT, exist_ok=True); made = []; info = {}
    for role, (src, why, _db) in PICKS.items():
        base, fold = _decode(f"{SRC}/{src}")
        for (up, down), dst in zip(PITCH, files(role)):
            if force or not os.path.exists(dst):
                y = np.clip(_clean(base if up == down else resample_poly(base, up, down)), -1, 1)
                wavfile.write(dst, SR, (y * (2 ** 31 - 1)).astype(np.int32)); made.append(dst)
            x = wavfile.read(dst)[1].astype(np.float64) / 2 ** 31; pk, rms = sfx_real.levels(x)
            info[os.path.basename(dst)] = dict(source=f"anderson-tai-top5-sfx/{src}", fold=fold, semitones=round(-12 * np.log2(up / down), 2),
                                               dur_s=round(len(x) / SR, 3), peak_s=_peak_s(x), peak_dbfs=pk, rms100_dbfs=rms, why=why, licence=LICENCE)
    json.dump(info, open(f"{OUT}/LEVELS.json", "w"), indent=1)
    return made


def hit(role, t, n=0, db=None):
    """One entry for story/sfx_plan.json, the file starting at t. n rotates the variants (use a running counter)."""
    fs = files(role)
    return {"t": float(t), "file": fs[n % len(fs)], "db": DB[role] if db is None else db}


def hit_on(role, t_event, n=0, db=None):
    """The same, placed so the file's loudest moment lands on t_event (the cut, the white frame, the reveal)."""
    h = hit(role, t_event, n, db)
    h["t"] = round(max(0.0, t_event - json.load(open(f"{OUT}/LEVELS.json"))[os.path.basename(h["file"])]["peak_s"]), 3)
    return h


def table():
    info = json.load(open(f"{OUT}/LEVELS.json"))
    lines = [f"{'file':12s} {'fold':4s} {'semi':>5s} {'dur':>5s} {'peak@':>6s} {'peak':>6s} {'rms100':>7s}  note"]
    for role in ROLES:
        for f in files(role):
            k = os.path.basename(f); v = info[k]
            lines.append(f"{k:12s} {v['fold']:4s} {v['semitones']:+5.2f} {v['dur_s']:5.2f} {v['peak_s']:6.2f} {v['peak_dbfs']:6.1f} {v['rms100_dbfs']:7.1f}  {v['why']}")
        lines.append(f"{'':12s} recommended plan db for {role}: {DB[role]}")
    lines.append(f"licence: {LICENCE}")
    return "\n".join(lines)


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] == "build":
        made = build(force="-f" in args)
        print(f"built {len(made)} file(s) into {OUT}" if made else f"nothing to build ({OUT} is complete)")
    print(table())
