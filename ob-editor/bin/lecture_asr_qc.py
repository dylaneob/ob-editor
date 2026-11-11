#!/usr/bin/env python3
"""Second, independent proof that no lecture cut clips a word (the Whisper diff, as the skill's rule asks).

  python3 lecture_asr_qc.py EDL.json TAKE_16k.wav [--model base.en] [--pad 1.0]

For every row it transcribes the kept audio [src_in, src_out] and a wider window of the source
[src_in - pad, src_out + pad] with the same Whisper model the chunks used, then aligns the two
(difflib, autojunk off). Words the wide window has beyond the kept ones are candidates. A candidate
only counts as a clipped word when the audio between the cut and that sound never pauses
(100 ms-smoothed level stays above max(-48 dB, floor + 8) with no 120 ms dip), i.e. the cut sits
inside running speech. Extra words after a real pause are other sentences, cut on purpose.
Writes EDL-adjacent JSON with both transcripts per row for the record.
"""
import difflib, json, os, re, subprocess, sys, tempfile
import numpy as np
from scipy.io import wavfile


def level_db(x, sr):
    hop = int(sr * 0.01); n = len(x) // hop
    e = (x[:n * hop].reshape(n, hop) ** 2).mean(1)
    return 10 * np.log10(np.convolve(e, np.ones(10) / 10, mode="same") + 1e-12)


def words(t):
    t = re.sub(r"\[[^\]]*\]|\([^)]*\)", " ", t.lower())
    return [w for w in re.sub(r"[^a-z0-9' ]+", " ", t).replace("'", "").split() if w]


def transcribe(model, wav, a, b, td, tag):
    seg = os.path.join(td, f"{tag}.wav")
    subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-ss", f"{max(0, a):.3f}", "-t", f"{b - max(0, a):.3f}",
                    "-i", wav, "-ac", "1", "-ar", "16000", seg], check=True)
    r = subprocess.run(["whisper-cli", "-m", model, "-f", seg, "-nt"], capture_output=True, text=True)
    return " ".join(l.strip() for l in r.stdout.splitlines() if l.strip())


def pauses_between(L, th, t0, t1):
    """True if the level dips below th for 120 ms+ somewhere in [t0, t1] (a real pause)."""
    seg = L[int(t0 * 100):int(t1 * 100)] <= th
    run = best = 0
    for q in seg:
        run = run + 1 if q else 0; best = max(best, run)
    return best >= 12


def first_speech(L, th, t0, t1):
    i0, i1 = int(t0 * 100), int(t1 * 100)
    for i in range(i0, max(i0, i1 - 8)):
        if (L[i:i + 8] > th).all(): return i / 100
    return None


def last_speech_end(L, th, t0, t1):
    i0, i1 = int(t0 * 100), int(t1 * 100)
    for i in range(i1, i0 + 8, -1):
        if (L[i - 8:i] > th).all(): return i / 100
    return None


def main():
    edl, wav = sys.argv[1], sys.argv[2]
    model = os.path.expanduser("~/.whisper-models/ggml-" + (sys.argv[sys.argv.index("--model") + 1] if "--model" in sys.argv else "base.en") + ".bin")
    pad = float(sys.argv[sys.argv.index("--pad") + 1]) if "--pad" in sys.argv else 1.0
    spec = json.load(open(edl))
    sr, x = wavfile.read(wav); x = x.astype(np.float64); x = x.mean(1) if x.ndim > 1 else x
    L = level_db(x / 32768.0, sr); th = max(-48.0, float(np.percentile(L, 10)) + 8)
    out, flags = [], 0
    with tempfile.TemporaryDirectory() as td:
        for i, r in enumerate(spec["rows"]):
            a, b = r["src_in"], r["src_out"]
            kept = transcribe(model, wav, a, b, td, "k"); wide = transcribe(model, wav, a - pad, b + pad, td, "w")
            K, Wd = words(kept), words(wide)
            sm = difflib.SequenceMatcher(None, Wd, K, autojunk=False)
            blocks = [m for m in sm.get_matching_blocks() if m.size]
            notes = []
            if blocks and K:
                ws, we = blocks[0].a, blocks[-1].a + blocks[-1].size
                tail_extra, head_extra = Wd[we:], Wd[:ws]
                if tail_extra:
                    nxt = first_speech(L, th, b, b + pad)
                    if nxt is not None and not pauses_between(L, th, b - 0.05, nxt + 0.02):
                        notes.append(f"TAIL CLIP? kept ends '{' '.join(K[-3:])}', source goes on '{' '.join(tail_extra[:3])}' with no pause")
                if head_extra:
                    prv = last_speech_end(L, th, a - pad, a)
                    if prv is not None and not pauses_between(L, th, prv - 0.02, a + 0.05):
                        notes.append(f"HEAD CLIP? source has '{' '.join(head_extra[-3:])}' right before kept '{' '.join(K[:3])}' with no pause")
            elif not K:
                notes.append("kept audio transcribed to nothing")
            flags += len(notes)
            out.append({"shot": i + 1, "kept": kept, "wide": wide, "flags": notes})
            print(f"shot {i + 1:2d} {'OK ' if not notes else 'FLAG'} | kept: {kept[:70]!r}" + ("".join(f"\n        {n}" for n in notes)))
    json.dump(out, open(edl.replace(".json", ".asrqc.json"), "w"), indent=1)
    print(f"{os.path.basename(edl)}: {flags} flagged edge(s) of {len(spec['rows'])} shots")


if __name__ == "__main__":
    main()
