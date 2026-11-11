#!/usr/bin/env python3
"""Trial-reel music variants: same finished picture, a different song under the voice. No re-render.
OB 2026-10-17: "we can test hooks, frames, background music, the more the better honestly because trials i can post 10 a day".

  python3 music_variants.py WORK NAME TAG TRACK START [--rel -16] [--duck 5] [--phone PHONE.mp4 PHONE_OUT.mp4]

Needs a finished lecture_render.py run with ALSO_NOMUSIC=1: WORK/render/NAME/NAME_gfx.mp4 (the picture) and
NAME_mix_raw_nomusic.wav (voice + SFX before mastering). The bed is placed exactly like the render's
(music_mix.bed: REL dB under the voice, ducked DUCK dB while he talks, 0.4 s fade in, 1.2 s fade out), then
mastered by lecture_render.loudnorm_mux (-14 LUFS, limiter) -> WORK/out/NAME_A_mus-TAG.mp4.
--phone muxes the mastered audio (AAC 128k) onto an existing phone copy's video stream: same picture, under 15 MB.
"""
import argparse, os, subprocess, sys
import numpy as np
from scipy.io import wavfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lecture_render as LR, music_mix   # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("work"); ap.add_argument("name"); ap.add_argument("tag"); ap.add_argument("track"); ap.add_argument("start", type=float)
    ap.add_argument("--rel", type=float, default=-16.0); ap.add_argument("--duck", type=float, default=5.0)
    ap.add_argument("--phone", nargs=2, metavar=("PHONE_SRC", "PHONE_OUT"))
    a = ap.parse_args()
    R = f"{a.work}/render/{a.name}"
    gfx, raw = f"{R}/{a.name}_gfx.mp4", f"{R}/{a.name}_mix_raw_nomusic.wav"
    for p in (gfx, raw, a.track):
        if not os.path.exists(p): sys.exit(f"missing {p} (render with ALSO_NOMUSIC=1 first)")
    sr, x = wavfile.read(raw); x = x.astype(np.float64)
    assert sr == LR.SR, f"{raw} is {sr} Hz"
    mono = x.mean(1) if x.ndim > 1 else x
    bed = music_mix.bed(a.track, a.start, mono, sr, a.rel, a.duck)
    mix = mono[:, None].repeat(2, 1) + bed[: len(mono)]
    os.makedirs(f"{R}/variants", exist_ok=True)
    mixp = f"{R}/variants/{a.name}_mix_mus-{a.tag}.wav"
    wavfile.write(mixp, sr, mix.astype(np.float32))
    out = f"{a.work}/out/{a.name}_A_mus-{a.tag}.mp4"
    LR.loudnorm_mux(gfx, mixp, out)
    os.remove(mixp)
    if a.phone:
        src, dst = a.phone
        subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", src, "-i", out, "-map", "0:v", "-map", "1:a",
                        "-c:v", "copy", "-c:a", "aac_at", "-b:a", "128k", "-movflags", "+faststart", "-shortest", dst], check=True)
        print(f"phone -> {dst} ({os.path.getsize(dst) / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
