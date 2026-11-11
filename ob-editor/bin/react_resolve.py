#!/usr/bin/env python3
"""Resolve phrase-anchored events to edited-timeline times.

  python3 resolve_events.py WORK_DIR

Reads events_spec.json, words_clean.json, cutlist.json, out.wav from WORK_DIR.
Anchor = Whisper word time for the phrase, snapped to the nearest real speech
onset in the audio (Whisper word times can be ~0.5 s off). Writes
events_resolved.json with edited in/out times and item reveal times.
"""
import json, re, sys
import numpy as np
from scipy.io import wavfile

W = sys.argv[1]
spec = json.load(open(f"{W}/events_spec.json"))
WJ = json.load(open(f"{W}/words_clean.json")); words = WJ["words"]
# DTW word times (dtw_words.py / dtw_chunks.py) sit within ~0.1 s: snap only to an onset within 0.3 s, or a phrase start
# can jump to the next word's onset after a short pause (C4354 audit: C01, C04, S08 landed 0.5 s late). Plain whisper: 0.7 s.
SNAP = 0.3 if "DTW" in WJ.get("source", "") else 0.7
segs = json.load(open(f"{W}/cutlist.json"))["segments"]
sr, x = wavfile.read(f"{W}/out.wav")
x = x.astype(np.float64) / 32768
HOP = 0.02; hop = int(sr * HOP); n = len(x) // hop
DB = 20 * np.log10(np.sqrt((x[:n * hop].reshape(n, hop) ** 2).mean(1)) + 1e-9)

norm = lambda s: re.sub(r"[^a-z0-9%' ]", "", s.lower().replace("’", "'").replace("-", " "))
WT = [(a, tok) for a, b, t in words for tok in norm(t).split()]  # hyphenated words split into tokens


def find(phrase, near, span=25.0):
    """Start time of the best match of phrase's first words near `near`."""
    toks = norm(phrase).split()
    best = None
    for i, (a, w) in enumerate(WT):
        if abs(a - near) > span: continue
        k = min(len(toks), 4)
        cand = [WT[j][1] for j in range(i, min(i + k, len(WT)))]
        score = sum(1 for p, q in zip(toks[:k], cand) if p == q or (len(p) > 3 and q.startswith(p[:4])))
        if score >= max(1, k - 1):
            key = (-score, abs(a - near))
            if best is None or key < best[0]: best = (key, a)
    return None if best is None else best[1]


def snap(t, win=None):
    """Nearest speech onset (quiet >=60 ms then voiced) within +-win of t."""
    win = SNAP if win is None else win
    i0, i1 = max(3, int((t - win) / HOP)), min(n - 1, int((t + win) / HOP))
    onsets = [i * HOP for i in range(i0, i1) if DB[i] > -40 and DB[i - 1] <= -40 and all(DB[i - k] < -42 for k in range(1, 4))]
    return min(onsets, key=lambda o: abs(o - t)) if onsets else t


def src2edit(t):
    for s in segs:
        if s["src_in"] <= t < s["src_out"]: return s["edit_in"] + (t - s["src_in"])
        if t < s["src_in"]: return s["edit_in"]
    return segs[-1]["edit_out"]


def edit2src(e):
    for s in segs:
        if s["edit_in"] <= e < s["edit_out"]: return s["src_in"] + (e - s["edit_in"]), s["framing"], s["i"]
    s = segs[-1]; return s["src_out"] - 0.05, s["framing"], s["i"]


TOTAL = segs[-1]["edit_out"]
out, problems = [], []
for ev in spec["events"]:
    e = dict(ev)
    ta = ev.get("anchor_src") or find(ev["anchor"], ev["near"])
    if ta is None:
        problems.append(f'{ev["id"]}: anchor not found "{ev["anchor"]}"'); ta = ev["near"]
    ta = ta if ev.get("anchor_src") else snap(ta)
    e["src_anchor"] = round(ta, 3)
    e_in = max(0.0, src2edit(ta) - 0.08 + ev.get("shift", 0.0))
    if e_in < 0.35: e_in = 0.0  # open on the card
    if ev.get("to_end"):
        e_out = TOTAL
    elif ev.get("end_anchor"):
        te = ev.get("end_src") or find(ev["end_anchor"], ev.get("end_near", ta + 10), span=15)
        if te is None:
            problems.append(f'{ev["id"]}: end anchor not found "{ev["end_anchor"]}"'); te = ev.get("end_near", ta + 5)
        te = te if ev.get("end_src") else snap(te)
        e["src_end"] = round(te, 3)
        e_out = src2edit(te) - 0.05 + ev.get("extend", 0)
    else:
        e_out = e_in + ev["dur"]
    e["edit_in"], e["edit_out"] = round(e_in, 3), round(min(e_out, TOTAL), 3)
    e["dur"] = round(e["edit_out"] - e["edit_in"], 3)

    t_end_src = e.get("src_end", ta + ev.get("dur", 10))
    def rel(phrase, lo_t):
        t = find(phrase, (ta + t_end_src) / 2, span=(t_end_src - ta) / 2 + 3)
        if t is None:
            problems.append(f'{ev["id"]}: item anchor not found "{phrase}"'); return None
        return round(max(0.0, src2edit(snap(t, 0.4)) - e_in), 3)

    if "items" in ev and (ev["type"] in ("split", "myths") or (ev["type"] == "list" and ev.get("reveal") == "words")):
        ts, last = [], 0.0
        srcs = ev.get("items_src")
        for k, (txt, ph) in enumerate(ev["items"]):
            r = round(max(0.0, src2edit(srcs[k]) - e_in), 3) if srcs else rel(ph, ta + 2)
            r = last + 0.6 if r is None or r < last else r
            ts.append(min(r, max(e["dur"] - 0.6, 0.3))); last = ts[-1]
        e["items_t"] = ts
    if ev["type"] == "equation":
        e["right_t"] = rel("fire extinguisher", ta + 4) or e["dur"] * 0.45
    if ev["type"] == "stat_count":
        e["to_t"] = rel(ev["to_anchor"], ta + 8) or e["dur"] * 0.6
    if ev["type"] == "stat_equals":
        e["rows_t"] = [rel(r[2], ta + 3) or 0.1 for r in ev["rows"]]
    if ev["type"] == "proof_pages":
        e["page2_t"] = rel(ev["page2"]["anchor"], ta + 5) or e["dur"] * 0.4
    if ev["type"] == "stat_columns":
        e["cols_t"] = [0.1, rel("you know america bans", ta + 5) or e["dur"] * 0.4]
    # representative still for the breakdown mockup
    rep = e["edit_in"] + min(1.2, e["dur"] / 2)
    s_t, fr, si = edit2src(rep)
    e["still_src"], e["still_framing"], e["shot"] = round(s_t, 3), fr, si
    out.append(e)

out.sort(key=lambda e: e["edit_in"])
for a, b in zip(out, out[1:]):  # no overlaps: earlier event yields
    if a["edit_out"] > b["edit_in"] - 0.05:
        problems.append(f'overlap {a["id"]} -> {b["id"]}: trimmed {a["id"]} end {a["edit_out"]:.2f} -> {b["edit_in"]-0.05:.2f}')
        a["edit_out"] = round(b["edit_in"] - 0.05, 3); a["dur"] = round(a["edit_out"] - a["edit_in"], 3)
for e in out:
    if e["dur"] < 1.2: problems.append(f'{e["id"]}: short ({e["dur"]:.2f}s)')
json.dump({"events": out, "total": TOTAL}, open(f"{W}/events_resolved.json", "w"), indent=1)
print(f"{len(out)} events, edit total {TOTAL/60:.2f} min")
for p in problems: print("!", p)
