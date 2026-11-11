#!/usr/bin/env python3
"""Pace gate (general version of C4367's story/pace.py, measured like the Johnny Harris study): visual changes a minute, median shot,
his face share. A 'shot' is a run of frames with one thing on screen: one A-roll shot, one full-frame card, one inlay. Same painter as
assemble.py (gate_lib.py): a card's face breaks give frames back to the A-roll, inlays sit on top, overlay cards over his face (pills,
self-quotes, plates) count as his face. A mid-shot punch-in is a visual change too, and a run under 0.3 s is a flicker at a cut, not
a shot: it folds into the run before it.

  python3 -I pace_check.py WORK [--min-rate 12] [--max-median 3.5] [--long] [--events FILE]

Fails (exit 1) when the edit is slower than --min-rate shots a minute or its median shot is longer than --max-median seconds, and
(OB 2026-10-21, after watching the published C4367: "Show me on camera more often when I'm talking, you went from overlay to overlay to
overlay and sometimes I felt I could've been shown in between a bit"; "the TikToks and the news could've been shown longer") when:
  - his face is on screen less than --min-face % of the runtime (C4367: 25%);
  - more than --max-chain full-frame overlays run in a row with no face beat of --min-beat s between them (a montage of chained clips
    counts once, up to 4 clips; C4367: 16 runs of 5+, the longest 16 in a row, 3:55-5:27);
  - clips with their own sound (TikToks, news) have a median under --min-clip-median s (C4367: 3.4 s), or muted B-roll inserts a median
    under --min-insert-median s (C4367: 2.1 s, 53 of 58 under 3 s).
The face, chain and clip limits are starting points set from that feedback, not OB's numbers: tune them with his next notes.
Calibration (2026-10-21): Johnny Harris 32.5 a minute, median 1.25 s; C4367 19.4 a minute, median 2.37 s, face 26%; the C4369 draft 16.1
and 2.70 s; the older edits OB moved away from 4.5-8.9 a minute, median 4.4-14 s, face 94-97%. The face-only limit (8 s) is in
coverage_check.py. --long lists the 20 longest shots. Exit codes: 0 clean, 1 too slow, 2 missing input.
"""
import argparse, os, statistics, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gate_lib as G


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("work")
    ap.add_argument("--min-rate", type=float, default=12.0); ap.add_argument("--max-median", type=float, default=3.5)
    ap.add_argument("--long", action="store_true"); ap.add_argument("--events", default=None)
    ap.add_argument("--min-face", type=float, default=40.0); ap.add_argument("--max-chain", type=int, default=3)
    ap.add_argument("--min-beat", type=float, default=2.0)
    ap.add_argument("--min-clip-median", type=float, default=4.0); ap.add_argument("--min-insert-median", type=float, default=3.0)
    a = ap.parse_args(); W = a.work.rstrip("/")
    try:
        tl = G.Timeline(W, events=a.events)
    except (OSError, ValueError, KeyError) as e:
        print(f"pace_check: cannot read inputs in {W}: {e}", file=sys.stderr); return 2
    N = tl.N
    if N < G.FPS * 5:
        print("pace_check: timeline shorter than 5 s", file=sys.stderr); return 2
    lab = []
    for k, sh in enumerate(tl.shots):
        for f in range(sh["e0"], sh["e1"]):
            o = tl.own[f]
            if o is not None and tl.cov[f]: lab.append(o["id"])
            else: lab.append(f"A{k}" + ("p" if sum(1 for p in sh["punch"] if p <= f) % 2 else ""))
    runs, st = [], 0
    for f in range(1, N + 1):
        if f == N or lab[f] != lab[st]: runs.append((st / G.FPS, f / G.FPS, lab[st])); st = f
    merged = []
    for x, y, l in runs:
        if merged and y - x < 9 / G.FPS: merged[-1] = (merged[-1][0], y, merged[-1][2])
        else: merged.append((x, y, l))
    runs = merged
    face = sum(y - x for x, y, l in runs if l.startswith("A") and not tl.shots[int(l[1:].rstrip("p"))]["hold"])
    T = N / G.FPS; d = [y - x for x, y, _ in runs]
    rate, med = len(runs) / (T / 60), statistics.median(d)
    print(f"{len(runs)} shots in {T / 60:.2f} min = {rate:.1f} a minute; median shot {med:.2f} s; his face {face / T * 100:.0f}% of the time; "
          f"shots over 8 s: {sum(1 for x in d if x >= 8)}")
    if a.long:
        for x, y, l in sorted(runs, key=lambda r: r[0] - r[1])[:20]: print(f"  {G.tc(x)}-{G.tc(y)} {y - x:5.1f}s {l}")
    problems = []
    if rate < a.min_rate: problems.append(f"only {rate:.1f} visual changes a minute (limit {a.min_rate:g}): add inserts, face breaks or punch-ins")
    if med > a.max_median: problems.append(f"median shot {med:.2f} s (limit {a.max_median:g}): the cut holds each picture too long")
    ev = {e["id"]: e for e in tl.events}
    is_face = lambda l: l.startswith("A") and not tl.shots[int(l[1:].rstrip("p"))]["hold"]
    chains, cur, mont, fa = [], [], 0, 0.0          # full-frame overlays between face beats of --min-beat s or more
    for x, y, l in runs:
        if l.startswith("A"):
            # a face beat is his face on screen without a break, however many jump cuts it holds (C4372: a median shot of 1.7 s
            # meant no single shot reached 2 s, so every stretch of face read as no beat at all)
            if is_face(l):
                fa += y - x
                if fa >= a.min_beat and cur: chains.append(cur); cur = []; mont = 0
            continue
        fa = 0.0
        if cur and cur[-1][2] == l: cur[-1][1] = y; continue
        e = ev.get(l, {})
        # footage laid on top of a card (inlay) is part of that card; a chained piece of the same kind (clip after clip, insert after
        # insert) is one montage (C4372: the era callback montage and the date-card inlays read as one overlay, as range_check counts them)
        chained = bool(e.get("inlay")) or bool(e.get("chain_in") and cur and ev.get(cur[-1][2], {}).get("type") == e.get("type"))
        mont = mont + 1 if chained else 0
        cur.append([x, y, l, 0 if chained and mont < 4 else 1])
    if cur: chains.append(cur)
    long_chains = [c for c in chains if sum(i[3] for i in c) > a.max_chain]
    on = {}
    for x, y, l in runs:
        if not l.startswith("A"): on[l] = on.get(l, 0) + y - x
    clip_d = [v for k, v in on.items() if ev.get(k, {}).get("type") == "clip"]
    ins_d = [v for k, v in on.items() if ev.get(k, {}).get("type") == "insert"]
    if face / T * 100 < a.min_face:
        problems.append(f"his face is on screen {face / T * 100:.0f}% of the time (limit {a.min_face:g}%): put his lines on his face, cut look-downs out in pauses instead of covering them")
    if long_chains:
        top = sorted(long_chains, key=lambda c: -sum(i[3] for i in c))[:5]
        problems.append(f"{len(long_chains)} runs of more than {a.max_chain} overlays with no {a.min_beat:g} s face beat between them; longest: "
                        + "; ".join(f"{G.tc(c[0][0])}-{G.tc(c[-1][1])} ({sum(i[3] for i in c)})" for c in top))
    if clip_d and statistics.median(clip_d) < a.min_clip_median:
        problems.append(f"clips with their own sound run a median {statistics.median(clip_d):.1f} s (limit {a.min_clip_median:g} s): let each TikTok or news clip finish its line")
    if ins_d and statistics.median(ins_d) < a.min_insert_median:
        problems.append(f"B-roll inserts run a median {statistics.median(ins_d):.1f} s (limit {a.min_insert_median:g} s): fewer, longer inserts")
    for p in problems: print("PACE " + p)
    print(f"pace_check: {'FAIL' if problems else 'OK'}: {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
