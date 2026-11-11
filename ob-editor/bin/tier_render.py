#!/usr/bin/env python3
"""Render a tier-list / this-or-that reel from its EDL (C4079 cardio, C4080 food; OB approved 2026-10-17).

  python3 tier_render.py WORK NAME [--lut B] [--out OUT.mp4] [--rows N]

1. Pieces: every EDL row is cut on the 30000/1001 frame grid from the camera file (T7 root or RAW-FOOTAGE/camera),
   with its own face-centred crop (tier_stills.py), scaled to 1080x1920, graded with luts/T_<lut>.png and blurred
   below the board (y 1510+) when there is a board. A row owns [fr(edit_in), fr(next edit_in)), so its gap plays the
   source after src_out, as in lecture_render. Pieces are cached by content key.
2. HyperFrames renders hf/compositions/NAME.html (tier_cards.py: graphics + word-timed captions) over the cut.
3. Voice: the take's mic cut at the same instants, room tone in "fill": "room" gaps, 8 ms fades except at joins,
   80 Hz high-pass, set to -20 LUFS. Music: music_mix.bed under it (the EDL's "music"). Master: the C4352/C4353
   chain OB called "way better" (two-pass loudnorm I -13, TP -2 so AAC lands under -1.5, LRA 11, then a gentle downward expander). No SFX.
--rows N renders only the first N rows (a short test). Temp files live on T7 (WORK/render/NAME).
"""
import argparse, hashlib, json, os, re, subprocess, sys
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfiltfilt

BIN = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BIN)
import lecture_render as LR     # noqa: E402  (frame grid, run/cache helpers, encoder settings, room tone; read only)
import music_mix                # noqa: E402

FPS_N, FPS_D, SR = LR.FPS_N, LR.FPS_D, LR.SR
fr, ft, ss, run, cached, mark, nframes = LR.fr, LR.ft, LR.ss, LR.run, LR.cached, LR.mark, LR.nframes
BLUR_TOP = 1510
EXP = "agate=mode=downward:range=0.2:threshold=0.03:ratio=2:attack=3:release=90:knee=2"


def source(take):
    for p in (f"/Volumes/T7/{take}.MP4", f"/Volumes/T7/RAW-FOOTAGE/camera/{take}.MP4"):
        if os.path.exists(p): return p
    sys.exit(f"{take}.MP4 not found on the T7 (root or RAW-FOOTAGE/camera)")


def piece(src, lut, src_f0, n, crop, blur, out):
    key = f"{src}:{src_f0}:{n}:{crop}:{blur}:{LR.mtime(lut)}"
    if cached(out, key): return key
    cw, ch, x, y = crop
    g = (f"[0:v]crop={cw}:{ch}:{x}:{y},scale=1080:1920:flags=lanczos[s];[s][1:v]haldclut=interp=tetrahedral"
         + (f",split=2[a][b];[b]crop=1080:{1920 - BLUR_TOP}:0:{BLUR_TOP},gblur=sigma=26[bl];[a][bl]overlay=0:{BLUR_TOP}[v]" if blur else "[v]"))
    run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-ss", ss(src_f0), "-i", src, "-i", lut, "-filter_complex", g,
         "-map", "[v]", "-frames:v", str(n)] + LR.VENC + [out])
    mark(out, key); return key


def lufs(arr):
    return music_mix.lufs_of(arr if arr.ndim > 1 else arr[:, None].repeat(2, 1), SR)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("work"); ap.add_argument("name")
    ap.add_argument("--lut", default="B"); ap.add_argument("--out"); ap.add_argument("--rows", type=int)
    a = ap.parse_args()
    W, name = a.work, a.name
    spec = json.load(open(f"{W}/{name}_edl.json"))
    if a.rows:                                   # short test: the first N rows only
        spec["rows"] = spec["rows"][:a.rows]; last = spec["rows"][-1]
        spec["duration"] = round(last["edit_out"] + last.get("gap", 0), 3)
        spec["events"] = [e for e in spec["events"] if e["shot"] < a.rows]
        name = f"{name}_test"
    rows = spec["rows"]; tag = name
    R = f"{W}/render/{tag}"; os.makedirs(f"{R}/pieces", exist_ok=True); os.makedirs(f"{W}/out", exist_ok=True)
    src = source(spec["take"]); lut = f"{W}/luts/T_{a.lut}.png"; blur = spec["board"]["kind"] != "thisorthat"
    D_f = fr(spec["duration"]); starts = [fr(r["edit_in"]) for r in rows] + [D_f]
    print(f"{tag}: {len(rows)} rows, {D_f} frames, source {src}, LUT T_{a.lut}, blur {blur}", flush=True)

    # 1. graded, framed cut
    parts, keys = [], []
    for i, r in enumerate(rows):
        n = starts[i + 1] - starts[i]; r["_f0"] = fr(r["src_in"])
        out = f"{R}/pieces/p{i:03d}.mp4"
        keys.append(piece(src, lut, r["_f0"], n, r["crop"], blur, out)); parts.append(out)
        if i % 8 == 0: print(f"  pieces {i + 1}/{len(rows)}", flush=True)
    cut = f"{W}/hf/assets/{tag}_cut.mp4"; ckey = hashlib.sha1("|".join(keys).encode()).hexdigest()
    if not cached(cut, ckey):
        lst = f"{R}/pieces/list.txt"; open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
        run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", cut]); mark(cut, ckey)
    nf = nframes(cut); print(f"{tag}: cut {nf} frames (expected {D_f})", flush=True)
    assert abs(nf - D_f) <= 1, "frame count drifted"

    # 2. graphics + captions over the cut (frame-aligned copy of the EDL, next to it so tier_cards finds the islands)
    spec_r = {k: v for k, v in spec.items()}; spec_r["duration"] = round(ft(D_f), 6)
    edl_r = f"{W}/{tag}_edl.render.json"; json.dump(spec_r, open(edl_r, "w"), indent=1)
    run([sys.executable, "-I", f"{BIN}/tier_cards.py", edl_r, f"{W}/hf", tag])
    comp = f"{W}/hf/compositions/{tag}.html"
    gfx = f"{R}/{tag}_gfx.mp4"; gkey = hashlib.sha1((open(comp).read() + ckey).encode()).hexdigest()
    if not cached(gfx, gkey):
        env = dict(os.environ, TMPDIR="/Volumes/T7/OB-EDITS/tmp", HYPERFRAMES_NO_TELEMETRY="1")
        os.makedirs("/Volumes/T7/OB-EDITS/tmp", exist_ok=True)
        print(f"{tag}: HyperFrames render ...", flush=True)
        r_ = subprocess.run(["npx", "--prefix", os.path.expanduser("~/ob-editor"), "hyperframes", "render", f"{W}/hf", "-c", f"compositions/{tag}.html",
                             "-o", gfx, "--fps", f"{FPS_N}/{FPS_D}", "--quality", "looks", "--workers", os.environ.get("OB_HF_WORKERS", "4"),  # 2026-11-03 M5 Pro (was 1 on the 8 GB Air)
                            "--browser-gpu", "--gpu", "--quiet"],
                            capture_output=True, text=True, env=env)
        if r_.returncode != 0 or not os.path.exists(gfx): sys.exit(f"HyperFrames failed:\n{(r_.stdout + r_.stderr)[-3000:]}")
        mark(gfx, gkey)
    print(f"{tag}: graphics {nframes(gfx)} frames", flush=True)

    # 3. voice at the same instants, music bed, master
    sr, x = wavfile.read(f"{W}/{spec['take']}.wav"); assert sr == SR
    x = x.astype(np.float64) / 32768.0; x = x.mean(1) if x.ndim > 1 else x
    tone = LR.room_tone(x); total = round(ft(D_f) * SR); voice = np.zeros(total); fade = int(0.008 * SR)
    for i, r in enumerate(rows):
        a0 = round(ft(starts[i]) * SR); b0 = round(ft(starts[i + 1]) * SR); L = b0 - a0
        s0 = round(ft(r["_f0"]) * SR); seg = x[s0:s0 + L].copy()
        if len(seg) < L: seg = np.pad(seg, (0, L - len(seg)))
        if r.get("fill") == "room":
            k = max(0, min(L, round((r["src_out"] - ft(r["_f0"])) * SR)))
            fill = np.resize(tone, L - k); xf = min(int(0.012 * SR), k, L - k)
            if xf > 0: ramp = np.linspace(0, 1, xf); fill[:xf] = seg[k:k + xf] * (1 - ramp) + fill[:xf] * ramp
            seg[k:] = fill
        jp = i > 0 and rows[i - 1].get("gap", 0) == 0 and abs(rows[i - 1]["src_out"] - r["src_in"]) < 0.002
        jn = i + 1 < len(rows) and r.get("gap", 0) == 0 and abs(r["src_out"] - rows[i + 1]["src_in"]) < 0.002
        if not jp: seg[:fade] *= np.linspace(0, 1, fade)
        if not jn: seg[-fade:] *= np.linspace(1, 0, fade)
        voice[a0:b0] = seg
    voice = sosfiltfilt(butter(2, 80, btype="highpass", fs=SR, output="sos"), voice)
    voice *= 10 ** ((-20.0 - lufs(voice)) / 20)
    mix = voice[:, None].repeat(2, 1)
    mu = spec.get("music")
    if mu:
        mix = mix + music_mix.bed(mu["file"], mu.get("start", 0.0), voice, SR, mu.get("rel", -16.0), mu.get("duck", 5.0))[: len(mix)]
        print(f"{tag}: music {os.path.basename(mu['file'])} from {mu.get('start', 0)} s, {mu.get('rel', -16)} dB under, ducked {mu.get('duck', 5)} dB", flush=True)
    MIX = f"{R}/{tag}_mix.wav"; wavfile.write(MIX, SR, mix.astype(np.float32))
    r_ = run(["ffmpeg", "-nostdin", "-i", MIX, "-af", "highpass=f=70,loudnorm=I=-13:TP=-2.0:LRA=11:print_format=json", "-f", "null", "-"])
    m_ = json.loads(r_.stderr[r_.stderr.rindex("{"): r_.stderr.rindex("}") + 1])
    af = (f"highpass=f=70,loudnorm=I=-13:TP=-2.0:LRA=11:measured_I={m_['input_i']}:measured_TP={m_['input_tp']}:"
          f"measured_LRA={m_['input_lra']}:measured_thresh={m_['input_thresh']}:offset={m_['target_offset']}:linear=true,{EXP}")
    out = a.out or f"{W}/out/{tag}.mp4"
    run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", gfx, "-i", MIX, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
         "-af", af + ",aresample=48000", "-c:a", "aac_at", "-b:a", "256k", "-movflags", "+faststart", "-shortest", out])
    r_ = run(["ffmpeg", "-nostdin", "-i", out, "-af", "ebur128=peak=true", "-f", "null", "-"])
    I_ = re.findall(r"I:\s+(-?[\d.]+) LUFS", r_.stderr)[-1]; tp_ = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r_.stderr)[-1]
    print(f"done -> {out}  ({ft(D_f):.2f} s, {I_} LUFS, true peak {tp_} dBFS, loudnorm {m_.get('normalization_type')})", flush=True)
    try:   # 2026-10-28: the QC gate runs on every render (OB: "wire it in"); deliver.py keeps a FAIL out of his AirDrop folders
        sys.path.insert(0, os.path.expanduser("~/ob-editor/bin")); import qc_gate; qc_gate.after_render(out)
    except Exception as e: print("qc_gate not run:", e, flush=True)


if __name__ == "__main__":
    main()
