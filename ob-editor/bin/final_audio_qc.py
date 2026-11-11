#!/usr/bin/env python3
"""Word-by-word check of the exact voice track assemble.py will render: is every kept word there, and nothing extra?

  python3 -I final_audio_qc.py WORK_DIR

Builds the voice the way assemble.py does (frame-snapped cuts, per-shot audio_shift_ms, head/tail mutes, 6 ms fades),
transcribes it with whisper medium.en (same model as WORK/mic_words.json, the raw recording), and diffs the two.
Raw words whose audio is kept must appear in the edit; words in removed takes must not. Writes qc/final_audio_qc.json.
Whisper word times drift by up to ~0.5 s, so each diff is reported with its context for a human call.
"""
import difflib, json, os, re, subprocess, sys
import numpy as np
from scipy.io import wavfile

W = sys.argv[1]; Q = f"{W}/qc"; os.makedirs(Q, exist_ok=True)
MODEL = os.path.expanduser("~/.whisper-models/ggml-medium.en.bin")
FPS = 30000 / 1001; fr = lambda t: int(round(t * FPS)); ft = lambda f: f / FPS
segs = json.load(open(f"{W}/cutlist.json"))["segments"]
raw = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-i", f"{W}/master_synced.wav", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                     capture_output=True, check=True).stdout
m = np.frombuffer(raw, np.float32).astype(np.float64); sr = 16000
fade = int(0.006 * sr); ramp = np.linspace(0, 1, fade)
voice, table, e = [], [], 0.0
for s in segs:
    a0, b0 = fr(s["src_in"]), fr(s["src_out"])
    if b0 <= a0: continue
    d = s.get("audio_shift_ms", 0) / 1000
    A = int(round(ft(a0) * sr)) - int(round(d * sr)); B = A + (int(round(ft(b0) * sr)) - int(round(ft(a0) * sr)))
    p = m[max(A, 0):B].copy()
    if A < 0: p = np.pad(p, (-A, 0))
    h, t = int(round(s.get("audio_head_mute_ms", 0) / 1000 * sr)), int(round(s.get("audio_tail_mute_ms", 0) / 1000 * sr))
    if h: p[:h] = 0
    if t: p[len(p) - t:] = 0
    if len(p) > 2 * fade + h + t: p[h:h + fade] *= ramp; q = len(p) - t; p[q - fade:q] *= ramp[::-1]
    dur = len(p) / sr
    table.append({"i": s["i"], "e0": e, "e1": e + dur, "s0": A / sr, "keep0": (A + h) / sr, "keep1": (B - t) / sr})
    voice.append(p); e += dur
v = np.concatenate(voice)
wavfile.write(f"{Q}/final_voice16.wav", sr, (np.clip(v, -1, 1) * 32767).astype(np.int16))
if not os.path.exists(f"{Q}/final_words.json") or os.path.getmtime(f"{Q}/final_words.json") < os.path.getmtime(f"{Q}/final_voice16.wav"):
    subprocess.run(["whisper-cli", "-m", MODEL, "-f", f"{Q}/final_voice16.wav", "-l", "en", "-t", "8", "-ml", "1", "-sow", "-oj", "-of", f"{Q}/final_words", "-np"],
                   check=True, capture_output=True)
norm = lambda w: re.sub(r"[^a-z0-9']", "", w.lower())
E = [(x["offsets"]["from"] / 1000, x["text"].strip()) for x in json.load(open(f"{Q}/final_words.json"))["transcription"]]
E = [(t, w) for t, w in E if norm(w)]
def e2s(t):
    for r in table:
        if r["e0"] <= t < r["e1"]: return r["s0"] + (t - r["e0"])
    return table[-1]["keep1"]
kept = lambda t: any(r["keep0"] - 0.05 <= t <= r["keep1"] + 0.05 for r in table)
lo, hi = table[0]["keep0"], table[-1]["keep1"]
O = [(x["offsets"]["from"] / 1000, x["offsets"]["to"] / 1000, x["text"].strip()) for x in json.load(open(f"{W}/mic_words.json"))["transcription"]]
O = [o for o in O if lo - 0.5 <= o[0] <= hi + 0.5 and norm(o[2])]
sm = difflib.SequenceMatcher(None, [norm(o[2]) for o in O], [norm(w) for _, w in E], autojunk=False)
lost, extra, cut_ok = [], [], []
for op, i1, i2, j1, j2 in sm.get_opcodes():
    if op == "equal": continue
    miss = O[i1:i2]; add = E[j1:j2]
    ctx = " ".join(o[2] for o in O[max(0, i1 - 6):i1]) + " [[" + " ".join(o[2] for o in miss) + "]] " + " ".join(o[2] for o in O[i2:i2 + 6])
    row = {"raw_t": round(miss[0][0], 2) if miss else None, "edit_t": round(add[0][0], 2) if add else None,
           "missing": " ".join(o[2] for o in miss), "heard_instead": " ".join(w for _, w in add), "context": ctx}
    if miss and not any(kept((o[0] + o[1]) / 2) for o in miss): cut_ok.append(row)
    elif miss: lost.append(row)
    else: extra.append(row)
json.dump({"raw_words": len(O), "edit_words": len(E), "removed_as_intended": cut_ok, "differences_in_kept_audio": lost, "extra_in_edit": extra},
          open(f"{Q}/final_audio_qc.json", "w"), indent=1)
print(f"raw {len(O)} words, edit {len(E)} words ({len(v) / sr / 60:.2f} min)")
print(f"\nwords removed on purpose ({len(cut_ok)}):"); [print("  ", r["context"]) for r in cut_ok]
print(f"\ndifferences inside kept audio ({len(lost)}): each needs a listen-level call"); [print(f'   raw {r["raw_t"]} | missing "{r["missing"]}" | heard "{r["heard_instead"]}" | {r["context"]}') for r in lost]
print(f"\nextra words in the edit ({len(extra)}):"); [print(f'   edit {r["edit_t"]} | "{r["heard_instead"]}"') for r in extra]
