#!/usr/bin/env python3
"""Reaction edit decision list: which parts of the recording survive, and in which layout.

  python3 react_cutlist.py WORK_DIR [--start S] [--end E]

Reads gate.json (clip playback segments + OB speech inside them) and mic16.wav.
Writes react_cutlist.json: shots in edited order, each {src_in, src_out, layout, clip...}.
  layout "split": a clip is playing (clip left panel, OB right, clip audio, OB mic gated)
  layout "ob":    OB talking with no clip (full frame, alternating wide / punch)
Clip playback is never trimmed. Outside playback, pauses >= 0.8 s shrink to ~0.4 s and
silence (loading clips, searching) is dropped.
"""
import argparse, json, os, sys
import numpy as np
from scipy.io import wavfile

ap = argparse.ArgumentParser(); ap.add_argument("work")
ap.add_argument("--start", type=float, default=None); ap.add_argument("--end", type=float, default=None)
a = ap.parse_args(); W = a.work

gate = json.load(open(f"{W}/gate.json"))
sr, mic = wavfile.read(f"{W}/mic16.wav"); mic = mic.astype(np.float64) / 32768
HOP = int(0.02 * sr); n = len(mic) // HOP
P = (mic[:n * HOP].reshape(n, HOP) ** 2).mean(1)
db = 10 * np.log10(P + 1e-12)                                          # raw 20 ms level
sdb = 10 * np.log10(np.convolve(P, np.ones(5) / 5, "same") + 1e-12)    # 100 ms smoothed level
T = n * 0.02

# 1. playback segments, overlaps resolved (one clip plays at a time: earlier play yields)
plays = sorted(gate, key=lambda g: g["rec_in"])
for p, q in zip(plays, plays[1:]):
    if p["rec_out"] > q["rec_in"]:
        cut = q["rec_in"]; p["clip_out"] -= p["rec_out"] - cut; p["rec_out"] = cut
plays = [p for p in plays if p["rec_out"] - p["rec_in"] >= 0.5]

# 2. OB speech outside playback (energy VAD on the close mic). The level is smoothed over 100 ms so a word's
#    consonant dips ("de-fi-cit") can't split it into sub-0.15 s pieces that get dropped, and the threshold
#    sits at -48 dB (room floor ~-85) so soft, sentence-final words survive. QC 2026-10-16: raw 20 ms frames
#    at -44 dB shaved ~15 words ("deficit", "heart beat", "visceral fat").
voiced = sdb > -48
in_play = np.zeros(n, bool)
for p in plays: in_play[int(p["rec_in"] / 0.02): int(p["rec_out"] / 0.02)] = True
runs, i = [], 0
while i < n:
    if voiced[i] and not in_play[i]:
        j = i
        while j < n and voiced[j] and not in_play[j]: j += 1
        if (j - i) * 0.02 >= 0.15: runs.append([i * 0.02, j * 0.02])
        i = j
    else: i += 1
merged = []
for s, e in runs:
    if merged and s - merged[-1][1] < 0.8: merged[-1][1] = e
    else: merged.append([s, e])
# stray blips: isolated from other speech and short or never loud (a click, a cough, whispering while searching)
loud = lambda s, e: np.sum(db[int(s / 0.02): int(e / 0.02)] > -38) * 0.02
kept = []
for k, (s, e) in enumerate(merged):
    gap = min(s - merged[k - 1][1] if k else 1e9, merged[k + 1][0] - e if k + 1 < len(merged) else 1e9)
    near_play = any(-0.3 < s - p["rec_out"] < 0.8 or -0.3 < p["rec_in"] - e < 0.8 for p in plays)
    if gap > 2.5 and not near_play and (e - s < 1.2 or loud(s, e) < 0.3): continue
    kept.append([s, e])
speech = [[max(0, s - 0.2), e + 0.2] for s, e in kept]

# 3. timeline: playback (keep whole) + speech (pauses trimmed), in recording order
items = [{"src_in": p["rec_in"], "src_out": p["rec_out"], "layout": "split", "clip": p["clip"], "k": p["k"],
          "offset": p["offset"], "ob_speech": p["ob_speech"]} for p in plays]
for s, e in speech:
    # clip speech regions to not overlap playback
    for p in plays:
        if s < p["rec_out"] and e > p["rec_in"]:
            if s < p["rec_in"]: e = min(e, p["rec_in"])
            else: s = max(s, p["rec_out"])
    if e - s >= 0.3: items.append({"src_in": s, "src_out": e, "layout": "ob"})
items.sort(key=lambda x: x["src_in"])
lo = a.start if a.start is not None else 0.0; hi = a.end if a.end is not None else T
items = [x for x in items if x["src_out"] > lo and x["src_in"] < hi]
# a layout switch never drops audio: close small gaps between an OB shot and a clip play, so a word running
# into or out of a clip survives ("...the kids starving in Africa" right before the clip starts)
for p, q in zip(items, items[1:]):
    if p["layout"] != q["layout"] and 0 < q["src_in"] - p["src_out"] < 0.8:
        if p["layout"] == "ob": p["src_out"] = q["src_in"]
        else: q["src_in"] = p["src_out"]
# B-roll inserts (inserts.json): extra time with its own picture and sound, dropped into a pause in OB's
# speech. The OB item spanning the cut point splits in two; the insert has no camera time (src_in == src_out).
INS = json.load(open(f"{W}/inserts.json"))["inserts"] if os.path.exists(f"{W}/inserts.json") else []
for ins in INS:
    for j, x in enumerate(items):
        if x["layout"] == "ob" and x["src_in"] < ins["at"] < x["src_out"]:
            after = dict(x, src_in=ins["at"], keep_framing=True); x["src_out"] = ins["at"]
            dur = round(sum(bt[2] - bt[1] for bt in ins["bites"]) + ins.get("pad_in", 0) + ins.get("pad_out", 0), 3)
            items[j + 1:j + 1] = [{"src_in": ins["at"], "src_out": ins["at"], "layout": "insert", "id": ins["id"], "dur": dur,
                                   "bites": ins["bites"], "pad_in": ins.get("pad_in", 0), "pad_out": ins.get("pad_out", 0)}, after]
            break
    else:
        sys.exit(f"insert {ins['id']}: no OB shot spans {ins['at']}")
# merge adjacent ob items that touch (keep 0.35 s beats), alternate framing per ob shot
shots, t, k, held = [], 0.0, 0, 0.0
for x in items:
    x["src_in"] = round(max(lo, x["src_in"]), 3); x["src_out"] = round(min(hi, x["src_out"]), 3)
    d = x["dur"] if x["layout"] == "insert" else x["src_out"] - x["src_in"]
    if d <= 0: continue
    if x["layout"] == "ob":
        # flip framing at a cut only after the current framing has held 2.5 s (no flicker on micro-shots);
        # the far side of an insert keeps the framing it had, so an insert never re-deals the whole edit
        if not x.pop("keep_framing", False) and held >= 2.5: k += 1; held = 0.0
        x["framing"] = "wide" if k % 2 == 0 else "punch"; held += d
    elif x["layout"] == "split":
        held = 2.5   # coming back from a clip: next OB shot may flip
    x["edit_in"] = round(t, 3); x["edit_out"] = round(t + d, 3); t += d
    shots.append(x)
json.dump({"shots": shots, "total": round(t, 3)}, open(f"{W}/react_cutlist.json", "w"), indent=1)
raw = (hi - lo)
print(f"recording {raw/60:.1f} min -> edit {t/60:.1f} min | {len(shots)} shots "
      f"({sum(1 for s in shots if s['layout']=='split')} split, {sum(1 for s in shots if s['layout']=='ob')} OB, {sum(1 for s in shots if s['layout']=='insert')} insert) | removed {raw - t:.0f} s")
