#!/usr/bin/env python3
"""Word-loss QC for a reaction cut list: does any cut clip a word?

  python3 react_qc.py WORK_DIR build      # qc/edit_mic16.wav = the close mic, cut exactly like the edit
  (whisper-cli -m ggml-medium.en.bin -f qc/edit_mic16.wav -ml 1 -sow -oj -of qc/edit_words)
  python3 react_qc.py WORK_DIR compare    # qc/wordqc.json + qc/removals.json

Compares the edit's transcript with the original recording's (same model) word for word. A word
present in the original but missing from the edit, next to a cut, is a clipped word. Whisper word
times drift up to ~1 s around silences, so a miss only counts when the removed audio there is
audible (> -45 dB); misses over silent gaps are transcription wobble ("gonna" vs "going to").
Every removal of 2 s or more is also transcribed on its own, so the breakdown can say what was cut.
"""
import difflib, json, os, re, subprocess, sys
import numpy as np
from scipy.io import wavfile

W, mode = sys.argv[1], sys.argv[2]
Q = f"{W}/qc"; os.makedirs(Q, exist_ok=True)
MODEL = os.path.expanduser("~/.whisper-models/ggml-medium.en.bin")
shots = json.load(open(f"{W}/react_cutlist.json"))["shots"]
sr, x = wavfile.read(f"{W}/mic16.wav")
if mode == "build":
    y = np.concatenate([np.zeros(int(round(s["dur"] * sr)), x.dtype) if s["layout"] == "insert" else x[int(round(s["src_in"] * sr)): int(round(s["src_out"] * sr))] for s in shots])
    wavfile.write(f"{Q}/edit_mic16.wav", sr, y); print(f"{Q}/edit_mic16.wav {len(y) / sr:.1f} s"); sys.exit()

xf = x.astype(np.float64) / 32768; HOP = int(0.02 * sr); n = len(xf) // HOP
P = (xf[:n * HOP].reshape(n, HOP) ** 2).mean(1); db = 10 * np.log10(P + 1e-12)
sdb = 10 * np.log10(np.convolve(P, np.ones(5) / 5, "same") + 1e-12)
peak = lambda a, b: float(db[int(a / 0.02): max(int(a / 0.02) + 1, int(b / 0.02))].max())
tc = lambda t: f"{int(t // 60)}:{t % 60:04.1f}"


def e2r(t):
    for s in shots:
        if s["edit_in"] <= t < s["edit_out"]: return s["src_in"] + t - s["edit_in"]
    return shots[-1]["src_out"]


def r2e(t):
    for s in shots:
        if s["src_in"] <= t < s["src_out"]: return s["edit_in"] + t - s["src_in"]
        if t < s["src_in"]: return s["edit_in"]
    return shots[-1]["edit_out"]


norm = lambda w: re.sub(r"[^a-z0-9']", "", w.lower().replace(",", ""))
lo, hi = shots[0]["src_in"], shots[-1]["src_out"]
O = [(x_["offsets"]["from"] / 1000, x_["offsets"]["to"] / 1000, x_["text"].strip()) for x_ in json.load(open(f"{W}/mic_words.json"))["transcription"]]
O = [o for o in O if lo - 1 <= o[0] <= hi + 1 and norm(o[2])]
E = [(e2r(x_["offsets"]["from"] / 1000), x_["text"].strip()) for x_ in json.load(open(f"{Q}/edit_words.json"))["transcription"]]
E = sorted((e for e in E if norm(e[1])), key=lambda e: e[0])   # recording order: blocks may be reordered in the edit
srt = sorted((s for s in shots if s["layout"] != "insert"), key=lambda s: s["src_in"])
gaps = [(p["src_out"], q["src_in"]) for p, q in zip(srt, srt[1:]) if q["src_in"] - p["src_out"] > 0.01]
sm = difflib.SequenceMatcher(None, [norm(o[2]) for o in O], [norm(e[1]) for e in E], autojunk=False)
clipped, wobble = [], 0
for op, i1, i2, j1, j2 in sm.get_opcodes():
    if op not in ("delete", "replace"): continue
    miss = O[i1:i2]; t0, t1 = miss[0][0], miss[-1][1]
    near = [g for g in gaps if g[0] - 1.0 <= t1 and t0 <= g[1] + 1.0]
    loud = [g for g in near if g[1] - g[0] <= 4 and peak(*g) > -45]
    if not loud: wobble += 1; continue
    g = loud[0]
    clipped.append({"rec": round(t0, 2), "edit": round(r2e(t0), 2), "gap": [round(g[0], 2), round(g[1], 2)], "gap_peak_db": round(peak(*g), 1),
                    "missing": " ".join(o[2] for o in miss), "heard": " ".join(e[1] for e in E[j1:j2]),
                    "context": " ".join(o[2] for o in O[max(0, i1 - 6): i1]) + " [[" + " ".join(o[2] for o in miss) + "]] " + " ".join(o[2] for o in O[i2: i2 + 6])})
json.dump({"orig_words": len(O), "edit_words": len(E), "wobble": wobble, "clipped": clipped}, open(f"{Q}/wordqc.json", "w"), indent=1)
print(f"original {len(O)} words, edit {len(E)}; transcription wobble {wobble}; possible clipped words at a cut: {len(clipped)}")
for c in clipped:
    print(f"  edit {tc(c['edit'])} (rec {tc(c['rec'])}) gap {c['gap'][1] - c['gap'][0]:.2f}s peak {c['gap_peak_db']} dB | {c['context']} | edit heard: '{c['heard']}'")

# every removal >= 2 s, transcribed on its own (whisper times are too loose to attribute words to a gap)
dur = len(xf) / sr
rem = [(0.0, srt[0]["src_in"])] + [g for g in gaps if g[1] - g[0] >= 2.0] + [(srt[-1]["src_out"], dur)]
out = []
for a, b in rem:
    speech = float(np.sum(sdb[int(a / 0.02): int(b / 0.02)] > -44) * 0.02)
    text = ""
    if speech >= 0.3:
        f = f"{Q}/_rem.wav"; wavfile.write(f, sr, x[int(a * sr): int(b * sr)])
        r = subprocess.run(["whisper-cli", "-m", MODEL, "-f", f, "-l", "en", "-t", "8", "-np", "-nt"], capture_output=True, text=True)
        text = " ".join(r.stdout.split()); os.remove(f)
        if re.fullmatch(r"[\[\(].*[\]\)]|silence\.?|", text, re.I): text = ""
    out.append({"rec_in": round(a, 2), "rec_out": round(b, 2), "len": round(b - a, 2), "edit_at": round(r2e(b), 2), "speech_s": round(speech, 2), "text": text})
json.dump(out, open(f"{Q}/removals.json", "w"), indent=1)
print(f"{len(out)} removals >= 2 s, {sum(r['len'] for r in out) / 60:.1f} min;", sum(1 for r in out if r["text"]), "contain words")
for r in out:
    if r["text"]: print(f"  rec {tc(r['rec_in'])} ({r['len']:.1f}s): {r['text'][:160]}")
