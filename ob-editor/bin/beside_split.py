#!/usr/bin/env python3
"""Put the anchor chart beside OB wherever his eyes are up (C4372, 2026-10-23, from the Johnny Harris study: in "1955 vs 2025" he stands
beside the chart board for half the runtime, and the video's most-replayed moment is him beside the board, then the chart full frame).

Each full-frame anchor event is cut into up to three parts on shot boundaries:
  full    while a look-down (story/cover_map.json "raw", eyes down 0.8 s+) sits under it, plus MARGIN either side
  beside  the longest eyes-up stretch, at least MIN_BESIDE long: the paper chart in the left panel, OB slid right (cards.py "beside")
  full    the tail, if another look-down follows
A full part is never shorter than MIN_FULL (OB's no-flicker rule); a card with no eyes-up stretch long enough stays as it was.
The parts keep the card's times (at_t re-based, negative = already happened, so the line starts as far drawn as it had got).
Run after resolve_events.py, before the gates:   python3 -I beside_split.py WORK [--dry]
Rewrites WORK/events_resolved.json (the unsplit file is kept as events_resolved.pre_beside.json).
"""
import json, os, shutil, sys

W = sys.argv[1]; DRY = "--dry" in sys.argv
MARGIN, MIN_FULL, MIN_BESIDE, MIN_CARD, SNAP = 0.25, 1.5, 3.0, 3.5, 1.2   # a card under 3.5 s stays full (a 2 s flash between two ledgers)
EV = f"{W}/events_resolved.json"; PRE = f"{W}/events_resolved.pre_beside.json"
D = json.load(open(EV))
FRESH = not any(e.get("split_of") for e in D["events"])   # the resolver's output (not split yet); else split again from its saved copy
if not FRESH: D = json.load(open(PRE))
segs = [s for s in json.load(open(f"{W}/cutlist.json"))["segments"] if not s.get("hold")]
raw = [(a, b) for a, b, *_ in json.load(open(f"{W}/story/cover_map.json"))["raw"]]


def to_src(t):
    s = next((s for s in segs if s["edit_in"] - 1e-6 <= t < s["edit_out"]), None)
    return round(s["src_in"] + (t - s["edit_in"]), 3) if s else None


def snap_fwd(t, lim):   # the next shot start at or after t (a cut on the breath), if one is close
    c = [s["edit_in"] for s in segs if t - 1e-6 <= s["edit_in"] <= min(t + SNAP, lim)]
    return min(c) if c else t


def snap_back(t, lim):
    c = [s["edit_out"] for s in segs if max(t - SNAP, lim) <= s["edit_out"] <= t + 1e-6]
    return max(c) if c else t


out, n_split, gained = [], 0, 0.0
EVS = sorted(D["events"], key=lambda e: e["edit_in"])
after_board = {b["id"] for a, b in zip(EVS, EVS[1:])          # the full chart a planner cuts to straight from a beside board
               if a["type"] == "anchor" and a.get("beside") and a.get("chain_out") and abs(b["edit_in"] - a["edit_out"]) < 0.1}
for e in D["events"]:
    if e["id"] in after_board: out.append(e); continue
    # a planner's own beside/full sequence (chain flags set by hand: the board cuts straight to the full chart) stays as designed
    if (e["type"] != "anchor" or e.get("beside") or e.get("full_only") or e.get("chain_in") or e.get("chain_out")
            or e["edit_out"] - e["edit_in"] < MIN_CARD):
        out.append(e); continue
    a0, a1 = e["edit_in"], e["edit_out"]
    blocked = sorted((max(a0, x - MARGIN), min(a1, y + MARGIN)) for x, y in raw if y > a0 and x < a1)
    free, t = [], a0
    for x, y in blocked:
        if x > t: free.append((t, x))
        t = max(t, y)
    if t < a1: free.append((t, a1))
    best = None
    for w0, w1 in free:
        if w0 > a0: w0 = max(snap_fwd(w0, w1), a0 + MIN_FULL)          # room for a full part in front (it covers a look-down)
        if w1 < a1: w1 = min(snap_back(w1, w0), a1 - MIN_FULL)          # and behind
        if w0 > a0 and w0 - a0 < MIN_FULL: w0 = a0 + MIN_FULL
        if w1 - w0 >= MIN_BESIDE and (best is None or w1 - w0 > best[1] - best[0]): best = (round(w0, 3), round(w1, 3))
    if not best:
        out.append(e); continue
    w0, w1 = best
    if w0 - a0 < 0.04: w0 = a0                                         # no sliver of full chart in front
    if a1 - w1 < 0.04: w1 = a1
    parts = [(a0, w0, False), (w0, w1, True), (w1, a1, False)]
    parts = [p for p in parts if p[1] - p[0] > 0.04]
    for k, (p0, p1, bes) in enumerate(parts):
        t0 = p0 - a0
        q = dict(e, id=e["id"] if k == 0 else f"{e['id']}_{k + 1}", edit_in=round(p0, 3), edit_out=round(p1, 3), dur=round(p1 - p0, 3),
                 at_t={kk: round(v - t0, 3) for kk, v in (e.get("at_t") or {}).items()}, split_of=e["id"], split_t0=round(t0, 3))
        for kk in ("src_anchor", "anchor_src"):
            if k > 0 and to_src(p0) is not None: q[kk] = to_src(p0)
        if k > 0: q.pop("chain_in", None)
        if k < len(parts) - 1: q.pop("chain_out", None)
        if bes:
            q["beside"] = True
            if k > 0: q["from_full"] = True
            if k < len(parts) - 1: q["to_full"] = True
            mid = to_src((p0 + p1) / 2)
            if mid is not None: q["still_src"], q["still_framing"] = mid, "wide"
            q["desc"] = e.get("desc", "") + " <i>(beside you: the chart on the left, you on the right)</i>"
            gained += p1 - p0
        else:
            q.pop("beside", None)
        out.append(q)
    n_split += 1
    print(f"{e['id']:8s} {a0:7.2f}-{a1:7.2f}: " + " | ".join(f"{'BESIDE' if b else 'full'} {p0:.2f}-{p1:.2f} ({p1 - p0:.1f}s)" for p0, p1, b in parts))
print(f"{n_split} anchor cards split, {gained:.1f} s of his face back beside the chart")
if not DRY:
    if FRESH: shutil.copy(EV, PRE)
    D["events"] = sorted(out, key=lambda e: e["edit_in"])
    json.dump(D, open(EV, "w"), indent=1)
