#!/usr/bin/env python3
"""Music previews for the tier reels: 20 s of the edit's real voice with one of OB's saved tracks under it, as mp3.

  python3 tier_music.py EDL.json TAKE_48k.wav TRACK START OUT.mp3 [--seconds 20] [--rel -16] [--duck 5]

Voice and bed are exactly music_mix.py's (voice at -20 LUFS, track at voice + rel, ducked while he talks).
The difference is the master: music_mix.preview gains to -14 LUFS and hard-clips at -1 dBFS, which on these
takes (peaks ~22 dB over loudness) clipped ~300 times in 20 s. This masters like the render instead
(lecture_render.loudnorm_mux): gain to -14 LUFS, then a peak limiter at -3 dBFS, so what OB hears is the mix.
"""
import os, subprocess, sys, tempfile
import numpy as np
from scipy.io import wavfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import music_mix as M   # noqa: E402


def main():
    a = sys.argv
    edl, take, track, start, out = a[1], a[2], a[3], float(a[4]), a[5]
    opt = lambda k, d: float(a[a.index(k) + 1]) if k in a else d
    secs, rel, duck = opt("--seconds", 20.0), opt("--rel", -16.0), opt("--duck", 5.0)
    v, sr = M.voice_track(edl, take, secs)
    v *= 10 ** ((-20.0 - M.lufs_of(v, sr)) / 20)
    mix = v[:, None].repeat(2, 1) + M.bed(track, start, v, sr, rel, duck)
    g = -14.0 - M.lufs_of(mix, sr)
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "m.wav"); wavfile.write(p, sr, mix.astype(np.float32))
        subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", p, "-af",
                        f"volume={g:.2f}dB,alimiter=limit=0.708:attack=1:release=60:level=false,aresample=48000",
                        "-c:a", "libmp3lame", "-b:a", "160k", out], check=True)
    r = subprocess.run(["ffmpeg", "-nostdin", "-i", out, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
    I = r[r.rfind("I:"):].split()[1]; tp = r[r.rfind("Peak:"):].split()[1]
    print(f"{out}: {I} LUFS, true peak {tp} dBFS")


if __name__ == "__main__":
    main()
