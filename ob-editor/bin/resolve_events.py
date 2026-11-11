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
words = json.load(open(f"{W}/words_clean.json"))["words"]
ALL = json.load(open(f"{W}/cutlist.json"))["segments"]
segs = [s for s in ALL if not s.get("hold")]   # clip holds (C4367) have no words: word times map through the A-roll only
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


def snap(t, win=0.7):
    """Nearest speech onset (quiet >=60 ms then voiced) within +-win of t."""
    i0, i1 = max(3, int((t - win) / HOP)), min(n - 1, int((t + win) / HOP))
    onsets = [i * HOP for i in range(i0, i1) if DB[i] > -40 and DB[i - 1] <= -40 and all(DB[i - k] < -42 for k in range(1, 4))]
    return min(onsets, key=lambda o: abs(o - t)) if onsets else t


def src2edit(t):
    for s in segs:
        if s["src_in"] <= t < s["src_out"]: return s["edit_in"] + (t - s["src_in"])
    # an end anchor on (or just past) a shot's last frame: that shot's out point (a pickup line ends where its last shot ends, even when
    # the next shot in the recording sits elsewhere in the story)
    prev = [s for s in segs if s["src_out"] - 1e-6 <= t < s["src_out"] + 0.3]
    if prev: return max(prev, key=lambda s: s["src_out"])["edit_out"]
    # not inside a kept shot: the next kept moment in SOURCE order (C4367 reshoot: the story reorders the take, so the first shot
    # in edit order that starts after t is no longer the next one in the recording)
    nxt = [s for s in segs if s["src_in"] > t]
    return min(nxt, key=lambda s: s["src_in"])["edit_in"] if nxt else segs[-1]["edit_out"]


def edit2src(e):
    for s in segs:
        if s["edit_in"] <= e < s["edit_out"]: return s["src_in"] + (e - s["edit_in"]), s["framing"], s["i"]
    s = segs[-1]; return s["src_out"] - 0.05, s["framing"], s["i"]


TOTAL = ALL[-1]["edit_out"]
HOLD = {s["clip"]: s for s in ALL if s.get("hold")}
CUTS = sorted({s["edit_in"] for s in ALL} | {TOTAL})   # every shot boundary on the edit (A-roll jump cuts and clip holds)
out, problems, inlays = [], [], []
for ev in spec["events"]:
    e = dict(ev)
    if ev.get("inlay"):   # resolved after the others: it sits on top of its parent (C4367 v2 pace pass)
        inlays.append(ev); continue
    if ev.get("cover_clip"):   # a clip card spans its hold exactly (C4367): the clip's own picture and sound play there
        h = HOLD[ev["cover_clip"]]
        h_out = h["edit_out"] + ev.get("extend", 0.0)   # C4367 v4: a title card may run on over the first words after its hold (a look-down)
        e.update(edit_in=h["edit_in"], edit_out=round(h_out, 3), dur=round(h_out - h["edit_in"], 6), src_anchor=None,
                 still_src=None, still_framing="wide", shot=h["i"])
        if ev.get("at"): e["at_t"] = {k: v for k, v in ev["at"].items() if isinstance(v, (int, float))}
        out.append(e); continue
    ta = ev.get("anchor_src") or find(ev["anchor"], ev["near"])
    if ta is None:
        problems.append(f'{ev["id"]}: anchor not found "{ev["anchor"]}"'); ta = ev["near"]
    ta = ta if ev.get("anchor_src") else snap(ta)
    e["src_anchor"] = round(ta, 3)
    e_in = max(0.0, src2edit(ta) - 0.08 + ev.get("shift", 0.0))
    if e_in < 0.35: e_in = 0.0  # open on the card
    if ev.get("to_end"):
        e_out = TOTAL
    elif ev.get("end_anchor") or ev.get("end_src"):   # end_src alone: an exact source time (C4367)
        te = ev.get("end_src") or find(ev["end_anchor"], ev.get("end_near", ta + 10), span=15)
        if te is None:
            problems.append(f'{ev["id"]}: end anchor not found "{ev["end_anchor"]}"'); te = ev.get("end_near", ta + 5)
        te = te if ev.get("end_src") else snap(te)
        e["src_end"] = round(te, 3)
        e_out = src2edit(te) - 0.05 + ev.get("extend", 0)
    else:
        e_out = e_in + ev["dur"]
    for h in HOLD.values():   # never start or end inside a clip hold (C4367): the clip card owns its hold
        if h["edit_in"] < e_in < h["edit_out"]: e_in = h["edit_out"]
        if h["edit_in"] < e_out < h["edit_out"]: e_out = h["edit_in"]
    # an edge that falls within 0.3 s of a shot boundary leaves a 1-9 frame sliver of the other shot on screen (a flicker before or
    # after a jump cut, C4367 v2.1 flash check: 37 of them): put the edge on the cut instead (item times below follow e_in)
    c = max([x for x in CUTS if x <= e_in + 1e-6], default=None)
    if c is not None and 1e-6 < e_in - c < 0.3: e_in = c
    c = min([x for x in CUTS if x >= e_out - 1e-6], default=None)
    if c is not None and 1e-6 < c - e_out < 0.3: e_out = c
    e["edit_in"], e["edit_out"] = round(e_in, 3), round(min(e_out, TOTAL), 3)
    e["dur"] = round(e["edit_out"] - e["edit_in"], 3)

    t_end_src = e.get("src_end", ta + ev.get("dur", 10))
    def rel(phrase, lo_t):
        t = find(phrase, (ta + t_end_src) / 2, span=(t_end_src - ta) / 2 + 3)
        if t is None:
            problems.append(f'{ev["id"]}: item anchor not found "{phrase}"'); return None
        return round(max(0.0, src2edit(snap(t, 0.4)) - e_in), 3)

    if ev["type"] == "photo_overlay":
        n = len(ev["items"])
        if ev.get("items_at"):  # explicit reveal times (s from event start), e.g. a second wave that cuts over the first
            e["items_t"] = [round(min(t, max(e["dur"] - 0.6, 0.1)), 3) for t in ev["items_at"]]
        elif ev.get("even") or ev.get("even_span"):
            span = min(e["dur"] - 0.35, ev.get("even_span", e["dur"] - 0.35))
            e["items_t"] = [round(0.05 + span * k / max(n, 1), 3) for k in range(n)]
        else:
            ts, last = [], -0.4
            for k, (_, _, ph) in enumerate(ev["items"]):
                r = rel(ph, ta + 1) if ph else None
                r = (0.1 if k == 0 else last + 0.8) if r is None or r <= last + 0.3 else r
                ts.append(round(min(r, max(e["dur"] - 0.5, 0.1)), 3)); last = ts[-1]
            e["items_t"] = ts
    if ev["type"] == "study":   # "hl_t": seconds from the card's start, for a card that spans two places in the take (C4367 v4)
        e["hl_t"] = ev["hl_t"] if "hl_t" in ev else (rel(ev["hl_anchor"], ta + 1) if ev.get("hl_anchor") else 1.1)
        e["stat_t"] = round(e["hl_t"] + 0.7, 3)
    if ev["type"] == "chart_line":
        e["callouts_t"] = [max(rel(c[2], ta + 2) or 2.0, 2.9 + 0.4 * k) for k, c in enumerate(ev["chart"].get("callouts", []))]
    if ev["type"] == "myths_overlay":
        ev = dict(ev, type="myths")
    def at_list(phrases, first=0.4, step=0.6):   # one reveal time per spoken anchor, in order (C4365 motion cards)
        ts, last = [], first - step
        for ph in phrases:
            r = rel(ph, ta + 1) if ph else None
            r = last + step if r is None or r < last + 0.2 else r
            ts.append(round(min(r, max(e["dur"] - 0.6, 0.3)), 3)); last = ts[-1]
        return ts
    if ev["type"] == "meal":
        e["rows_t"] = at_list([r[2] for r in ev.get("rows", [])], 0.6, 0.8)
        if ev.get("note"): e["note_t"] = at_list([ev["note"][1]], 1.2)[0]
        if ev.get("foods"):   # food plates land on their words (C4365 food plates)
            e["foods_t"] = at_list([f[2] for f in ev["foods"]], 0.4, 0.6)
            e["foods_label_t"] = [at_list([f[4]], 0.6)[0] if len(f) > 4 and f[4] else None for f in ev["foods"]]
        if ev.get("fx"): e["fx_t"] = at_list([ev["fx"][1]], 1.2)[0]
    if ev["type"] == "tape": e["rows_t"] = at_list([r[3] for r in ev["rows"]], 0.8, 1.0)
    if ev["type"] == "dotgrid": e["rows_t"] = at_list([x.get("at") for x in ev["rows"]], 0.6, 1.2)   # C4398 dot charts
    if ev["type"] == "belly": e["labels_t"] = at_list([lb[1] for lb in ev["labels"]], 0.9, 1.0)
    if ev["type"] == "cycle" and ev.get("title_anchor"): e["title_t"] = at_list([ev["title_anchor"]], 0.3)[0]
    if ev["type"] == "stat_bars" and any(len(b) > 3 and b[3] for b in ev["bars"]):
        e["bars_t"] = at_list([b[3] if len(b) > 3 else None for b in ev["bars"]], 0.2, 0.9)
    if "items" in ev and ev["type"] in ("split", "myths", "pills", "cycle"):
        ts, last = [], 0.0
        srcs = ev.get("items_src")
        if ev.get("even_span") and not srcs:   # reveal evenly from the start (a recap list with no spoken cue per item)
            srcs = [ta + 0.15 + ev["even_span"] * k / len(ev["items"]) for k in range(len(ev["items"]))]
        for k, (txt, ph) in enumerate((it[0], it[1]) for it in ev["items"]):   # pills carry a third field (icon)
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
        e["cols_t"] = [0.1, rel(ev.get("col2_anchor", "you know america bans"), ta + 5) or e["dur"] * 0.4]
    for key_in, key_out in (("shots", "shots_t"), ("steps", "steps_t")):   # screenshot cards / bowl steps: each at its own spoken anchor
        if ev["type"] in ("shots", "bowl") and key_in in ev:
            anc = [x[1] if key_in == "shots" else x[2] for x in ev[key_in]]
            ts, last = [], -0.2
            for k, a in enumerate(anc):
                r = rel(a, ta + 1) if a else None
                r = (0.35 if k == 0 else last + 0.5) if r is None or r <= last + 0.2 else r
                ts.append(round(min(r, max(e["dur"] - 1.2, 0.3)), 3)); last = ts[-1]
            e[key_out] = ts
    if ev["type"] == "photo" and any(len(p) > 2 and p[2] for p in ev["photos"]):   # [key, caption, anchor]: each photo pops as it's said
        ts, last = [], -0.2
        for k, p in enumerate(ev["photos"]):
            r = rel(p[2], ta + 1) if len(p) > 2 and p[2] else None
            r = (0.1 if k == 0 else last + 0.3) if r is None or r <= last + 0.2 else r
            ts.append(round(min(r, max(e["dur"] - 0.8, 0.1)), 3)); last = ts[-1]
        e["photos_t"] = ts
    if ev.get("at"):   # generic word-timed marks for any card (C4367): {"name": "spoken phrase" | seconds from the start}
        e["at_t"] = {}
        for k, v in ev["at"].items():
            # {"src": seconds}: an exact source second (C4372: anchors taken from island word times, so a reveal lands on the take that was kept)
            r = v if isinstance(v, (int, float)) else (round(max(0.0, src2edit(v["src"]) - e_in), 3) if isinstance(v, dict) else rel(v, ta + 1))
            e["at_t"][k] = round(min(max(0.0, r if r is not None else 0.5), max(e["dur"] - 0.4, 0.1)), 3)
    # representative still for the breakdown mockup
    rep = e["edit_in"] + min(1.2, e["dur"] / 2)
    s_t, fr, si = edit2src(rep)
    e["still_src"], e["still_framing"], e["shot"] = round(s_t, 3), fr, si
    out.append(e)

out.sort(key=lambda e: e["edit_in"])
FULL = {"chapter", "quote", "myths", "clip", "photo_full", "num", "math", "dose", "coins", "timeline", "title", "disclaimer",
        "wall", "versus", "checklist", "scissors", "detector", "find", "slider", "insert",
        "anchor", "ledger", "ribbon", "jtitle", "jchapter"}   # C4372 paper cards (a beside anchor is split off later)
for a, b in zip(out, out[1:]):  # back-to-back full-frame cards touch (no gap: a clip hold must stay covered, C4367)
    if (a["type"] in FULL or a.get("full")) and (b["type"] in FULL or b.get("full")) and 0 <= b["edit_in"] - a["edit_out"] < 0.15:
        # a gap this small is never meant: it flashes 1-4 frames of A-roll between two full-frame cards (C4367 v2, 2026-10-20)
        a["edit_out"] = b["edit_in"]; a["dur"] = round(a["edit_out"] - a["edit_in"], 3); continue
    if (a["type"] in FULL or a.get("full")) and (b["type"] in FULL or b.get("full")) and a["edit_out"] > b["edit_in"]:
        a["edit_out"] = b["edit_in"]; a["dur"] = round(a["edit_out"] - a["edit_in"], 3); continue
for a, b in zip(out, out[1:]):  # no overlaps: earlier event yields
    if a["edit_out"] > b["edit_in"] + 1e-6:
        problems.append(f'overlap {a["id"]} -> {b["id"]}: trimmed {a["id"]} end {a["edit_out"]:.2f} -> {b["edit_in"]:.2f}')
        a["edit_out"] = b["edit_in"]; a["dur"] = round(a["edit_out"] - a["edit_in"], 3)
    elif 1e-6 < b["edit_in"] - a["edit_out"] < 0.3:   # a 1-9 frame gap between two events is a blink, never a beat: they touch
        a["edit_out"] = b["edit_in"]; a["dur"] = round(a["edit_out"] - a["edit_in"], 3)   # (was a 0.05 s gap: C4367 v2.1 flash check)
if spec.get("chain"):  # back-to-back side cards share the panel: close the gap, cards.py swaps content instead of sliding out and in
    SIDE = {"photo", "equation", "stat_ratio", "stat_bars", "stat_list", "stat_columns", "stat_count", "stat_equals", "proof", "poster", "study", "chart_line", "shots", "bowl",
            "meal", "belly", "tape", "cycle"}
    # "chain_split": bullet cards join in too (2026-10-17: back-to-back cards slid out and straight back in). Their panel is
    # narrower, so a hand-off between a bullet card and a wide card resizes the panel (chain_from tells cards.py which way)
    PANEL = SIDE | ({"split"} if spec.get("chain_split") else set())
    for a, b in zip(out, out[1:]):
        if a["type"] in PANEL and (b["type"] in PANEL or b["type"] == "end") and 0 <= b["edit_in"] - a["edit_out"] < 0.25:
            a["edit_out"] = b["edit_in"]; a["dur"] = round(a["edit_out"] - a["edit_in"], 3)
            a["chain_out"] = b["chain_in"] = True
            if "split" in (a["type"], b["type"]):
                b["chain_from"] = "split" if a["type"] == "split" else "side"
# Inlays (C4367 v2, 2026-10-20): muted footage ON TOP of another event, which keeps playing underneath (a clip hold keeps its
# sound; a card keeps animating and resumes in step). Johnny Harris cuts to footage on a noun while the interview or the
# explainer runs on. "rel": [a, b] seconds from the parent's start (clip holds have no A-roll time), else anchor_src/end_src.
# Inlays skip the overlap and hold rules above; assemble.py paints them over their parent frame by frame.
byid = {e["id"]: e for e in out}
for ev in inlays:
    e = dict(ev); p = byid.get(ev["parent"])
    if p is None: problems.append(f'{ev["id"]}: parent {ev["parent"]} not found'); continue
    if ev.get("rel"): a, b = p["edit_in"] + ev["rel"][0], p["edit_in"] + ev["rel"][1]
    else: a, b = src2edit(ev["anchor_src"]) - 0.08, src2edit(ev["end_src"]) - 0.05
    a, b = max(a, p["edit_in"]), min(b, p["edit_out"])
    if a - p["edit_in"] < 0.4: a = p["edit_in"]        # never leave a sliver of the parent (a 1-12 frame flash)
    if p["edit_out"] - b < 0.4: b = p["edit_out"]
    e["edit_in"], e["edit_out"] = round(a, 3), round(b, 3); e["dur"] = round(b - a, 3)
    e["src_anchor"] = None; e["still_src"] = None; e["still_framing"] = "wide"; e["shot"] = p.get("shot")
    if ev.get("at"): e["at_t"] = {k: v for k, v in ev["at"].items() if isinstance(v, (int, float))}
    out.append(e)
out.sort(key=lambda e: e["edit_in"])
INL = sorted([e for e in out if e.get("inlay")], key=lambda e: e["edit_in"])
for a, b in zip(INL, INL[1:]):
    if a["parent"] == b["parent"] and -0.1 < a["edit_out"] - b["edit_in"] < 0.15:   # back to back on the same parent: they touch
        a["edit_out"] = b["edit_in"]; a["dur"] = round(a["edit_out"] - a["edit_in"], 3)   # (no 1-frame overlap, no sliver of the parent)
    elif b["edit_in"] < a["edit_out"] - 1e-6: problems.append(f'inlays overlap: {a["id"]} and {b["id"]}')
for e in out:
    if e["dur"] < 1.2 and not (e.get("inlay") and e["dur"] >= 0.5): problems.append(f'{e["id"]}: short ({e["dur"]:.2f}s)')
json.dump({"events": out, "total": TOTAL}, open(f"{W}/events_resolved.json", "w"), indent=1)
print(f"{len(out)} events, edit total {TOTAL/60:.2f} min")
for p in problems: print("!", p)
