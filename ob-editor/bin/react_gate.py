#!/usr/bin/env python3
"""Mute-until-you-speak gate for reaction recordings.

  python3 react_gate.py WORK_DIR

Inputs in WORK_DIR: matches_mic.json (clipmatch output), cliptx/cNN_words.json (clip transcripts,
clip time), mic_words_clean.json (OB mic transcript, recording time; contains OB AND clip bleed),
mic16.wav (OB mic, camera timeline), clips_index.txt (#k -> clip file).
Output: gate.json with, per playback segment, the OB-speech intervals inside it (recording time).

Rules (OB, 2026-10-16): while a clip plays, the clip's own clean audio is heard and OB's mic is
muted until he speaks. A mic word that also appears in the clip transcript at the same moment
(+-0.9 s) is bleed; any other word is OB. Energy refines the edges: OB is speaking where the mic
is well above the clip's expected bleed level.
"""
import json, re, sys
from difflib import SequenceMatcher
import numpy as np
from scipy.io import wavfile

W = sys.argv[1]
matches = json.load(open(f"{W}/matches_mic.json"))
mic_words = json.load(open(f"{W}/mic_words_clean.json"))["words"]
index = {}
for line in open(f"{W}/clips_index.txt"):
    k, name, _ = line.rstrip("\n").split("\t"); index[name] = int(k[1:])
sr, mic = wavfile.read(f"{W}/mic16.wav"); mic = mic.astype(np.float64) / 32768
HOP = int(0.02 * sr)
nfr = len(mic) // HOP
mic_db = 20 * np.log10(np.sqrt((mic[:nfr * HOP].reshape(nfr, HOP) ** 2).mean(1)) + 1e-9)

NUM = {"zero":0,"one":1,"two":2,"three":3,"four":4,"five":5,"six":6,"seven":7,"eight":8,"nine":9,"ten":10,"eleven":11,"twelve":12,
       "thirteen":13,"fourteen":14,"fifteen":15,"sixteen":16,"seventeen":17,"eighteen":18,"nineteen":19,"twenty":20,"thirty":30,
       "forty":40,"fifty":50,"sixty":60,"seventy":70,"eighty":80,"ninety":90,"hundred":100,"thousand":1000}
def norm(w):
    w = w.lower().replace("’", "'")
    ws = w.strip(".,!?\"'")
    if re.fullmatch(r"[$]?\d+([.,]\d+)?%?", ws):
        return str(int(float(re.sub(r"[^0-9.]", "", ws.replace(",", "")) or 0)))
    w = re.sub(r"[^a-z0-9']", "", w)
    return str(NUM[w]) if w in NUM else w
SKIP = {"", "the", "a", "and", "to", "of", "is", "it", "i", "you", "that", "so", "in"}


def similar(a, b):
    if a == b: return True
    return len(a) > 3 and len(b) > 3 and SequenceMatcher(None, a, b).ratio() >= 0.75


def clip_audio_db(k, clip_in, clip_out):
    sr2, x = wavfile.read(f"{W}/cliptx/c{k:02d}.wav"); x = x.astype(np.float64) / 32768
    a, b = int(clip_in * sr2), int(clip_out * sr2); seg = x[a:b]; n = len(seg) // HOP
    return 20 * np.log10(np.sqrt((seg[:n * HOP].reshape(n, HOP) ** 2).mean(1)) + 1e-9)


out = []
for m in matches:
    k = index[m["clip"]]
    cw = json.load(open(f"{W}/cliptx/c{k:02d}_words.json"))["words"]
    for s in m["segments"]:
        d = s["rec_in"] - s["clip_in"]
        cwr = [(a + d, b + d, norm(t)) for a, b, t in cw if s["clip_in"] - 0.5 <= a <= s["clip_out"] + 0.5]
        inside = [(a, b, t) for a, b, t in mic_words if s["rec_in"] <= a < s["rec_out"]]
        lab = []   # (a, b, t, is_bleed or None for skip-words)
        for a, b, t in inside:
            n = norm(t)
            if n in SKIP: lab.append((a, b, t, None)); continue
            lab.append((a, b, t, any(abs(ca - a) <= 1.6 and similar(n, ct) for ca, cb, ct in cwr)))
        # context smoothing: a word flanked by bleed on both sides (within 3 content words) is bleed
        content = [i for i, x in enumerate(lab) if x[3] is not None]
        for j, i in enumerate(content):
            if lab[i][3] is False:
                left = [lab[q][3] for q in content[max(0, j - 2):j]]; right = [lab[q][3] for q in content[j + 1:j + 3]]
                if left and right and all(left) and all(right): lab[i] = lab[i][:3] + (True,)
        ob_words = [(a, b, t) for a, b, t, f in lab if f is False]
        # energy: OB frames = mic well above the clip's expected bleed (gain learned on bleed-only frames)
        f0, f1 = int(s["rec_in"] / 0.02), int(s["rec_out"] / 0.02)
        cdb = clip_audio_db(k, s["clip_in"], s["clip_out"])
        L = min(f1 - f0, len(cdb)); md = mic_db[f0:f0 + L]; cd = cdb[:L]
        live = cd > -45
        ob_mask_words = np.zeros(L, bool)
        for a, b, _ in ob_words: ob_mask_words[max(0, int((a - s["rec_in"]) / 0.02)): max(0, int((b - s["rec_in"]) / 0.02))] = True
        ref = live & ~ob_mask_words
        gain = float(np.median(md[ref] - cd[ref])) if ref.sum() > 25 else -6.0
        excess = md - (cd + gain)
        energetic = (excess > 7) & (md > -42)
        # OB intervals: word spans, grown over contiguous energetic frames, merged, padded
        iv = []
        for a, b, _ in ob_words:
            i0 = max(0, int((a - s["rec_in"]) / 0.02)); i1 = min(L - 1, int((b - s["rec_in"]) / 0.02))
            while i0 > 0 and energetic[i0 - 1]: i0 -= 1
            while i1 < L - 1 and energetic[i1 + 1]: i1 += 1
            iv.append([s["rec_in"] + i0 * 0.02 - 0.12, s["rec_in"] + i1 * 0.02 + 0.25])
        iv.sort(); merged = []
        for a, b in iv:
            if merged and a - merged[-1][1] < 0.6: merged[-1][1] = max(merged[-1][1], b)
            else: merged.append([a, b])
        def loud_enough(a, b):   # a real jump above the clip's bleed, not one stray word
            i0 = max(0, int((a - s["rec_in"]) / 0.02)); i1 = min(L, int((b - s["rec_in"]) / 0.02))
            return energetic[i0:i1].sum() * 0.02 >= 0.25
        merged = [[round(max(s["rec_in"], a), 3), round(min(s["rec_out"], b), 3)] for a, b in merged if b - a >= 0.35 and loud_enough(a, b)]
        out.append({"clip": m["clip"], "k": k, "rec_in": s["rec_in"], "rec_out": s["rec_out"], "clip_in": s["clip_in"], "clip_out": s["clip_out"],
                    "offset": round(d, 3), "bleed_gain_db": round(gain, 1), "ob_speech": merged,
                    "ob_words": " ".join(t for _, _, t in ob_words)[:400]})
out.sort(key=lambda g: g["rec_in"])
json.dump(out, open(f"{W}/gate.json", "w"), indent=1)
fmt = lambda t: f"{int(t//60)}:{t%60:04.1f}"
for g in out:
    talk = sum(b - a for a, b in g["ob_speech"])
    print(f'#{g["k"]:<2} {fmt(g["rec_in"])}-{fmt(g["rec_out"])} bleed {g["bleed_gain_db"]:+.0f} dB | OB talks {talk:4.1f}s in {len(g["ob_speech"])} spans | "{g["ob_words"][:90]}"')
