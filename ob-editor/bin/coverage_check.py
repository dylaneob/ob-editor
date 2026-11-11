#!/usr/bin/env python3
"""Coverage gate (general version of C4367's story/coverage.py): how much of the cut is graphics, where only his face shows, and
whether every eyes-down run that was found and confirmed is under a full-frame card. Uses the painted timeline (gate_lib.py, the same
painter as assemble.py), so a card's face breaks and inlays count the way the render paints them.

  python3 -I coverage_check.py WORK [--max-face-only 8] [--intro-until SEC] [--cta-last 45] [--face-first 5] [--min-any 0.80] [--events FILE]

Fails (exit 1) on:
  1. a recorded eyes-down run not under a full-frame card: story/gaze_shots.json (bin/gaze_shots.py style: {"shot", "runs": [[a, b]],
     "said": [..]}, source seconds) plus story/gaze_manual.json {"runs": [...]} (glances confirmed by eye that the rule missed), minus
     story/gaze_exempt.json {"spans": [[a, b, note]]} (eye-checked as expression). Skipped, with a note, when none of those files exist:
     lookaway_check.py scans the raw gaze rows instead.
  2. a face-only stretch (nothing on screen but him) longer than --max-face-only (8 s; PRESET: "No face-only stretch over ~8 s,
     except the intro and the CTA"). The intro is everything before the first chapter or title card (or --intro-until), the CTA the
     last --cta-last seconds (45).
  3. a cover in the first --face-first seconds (5; PRESET: "Face first 5 s"). 0 turns it off.
Warns (no exit code) when graphics of any kind cover less than --min-any (0.80, the 80-90% target from OB 2026-10-17) of the runtime.
Prints the numbers C4367's coverage.py printed: runtime, full-frame cards %, any graphic %, the longest face-only stretches.
Exit codes: 0 clean, 1 problems, 2 missing input.
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gate_lib as G


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("work")
    ap.add_argument("--max-face-only", type=float, default=8.0); ap.add_argument("--intro-until", type=float, default=None)
    ap.add_argument("--cta-last", type=float, default=45.0); ap.add_argument("--face-first", type=float, default=5.0)
    ap.add_argument("--min-any", type=float, default=0.80); ap.add_argument("--events", default=None)
    a = ap.parse_args(); W = a.work.rstrip("/")
    try:
        tl = G.Timeline(W, events=a.events)
    except (OSError, ValueError, KeyError) as e:
        print(f"coverage_check: cannot read inputs in {W}: {e}", file=sys.stderr); return 2
    N, T = tl.N, tl.T
    full_pct = 100.0 * sum(tl.cov) / N; any_pct = 100.0 * sum(1 for o in tl.own if o is not None) / N
    # face-only stretches: frames with no event of any kind on them (a face break in a card counts: only he is on screen)
    fo, st = [], None
    for f in range(N + 1):
        none = f < N and tl.own[f] is None
        if none and st is None: st = f
        if not none and st is not None:
            if (f - st) / G.FPS > 0.5: fo.append((st, f))
            st = None
    fo_sorted = sorted(fo, key=lambda r: r[0] - r[1])
    print(f"coverage check on {W}: runtime {G.tc(T)}; full-frame cards {full_pct:.0f}% · any graphic {any_pct:.0f}%")
    print("  longest face-only stretches: " + (", ".join(f"{(f1 - f0) / G.FPS:.1f}s at {G.tc(G.ft(f0))}" for f0, f1 in fo_sorted[:6]) or "none"))
    problems = 0
    if any_pct < a.min_any * 100:
        print(f"WARN graphics cover {any_pct:.0f}% of the runtime, under the {a.min_any * 100:.0f}% target")
    # 2. face-only stretches
    first = min((e["edit_in"] for e in tl.events if e["type"] in ("chapter", "title", "jchapter", "jtitle")), default=0.0)
    intro = a.intro_until if a.intro_until is not None else first
    for f0, f1 in sorted(fo):
        d, t0 = (f1 - f0) / G.FPS, G.ft(f0)
        if d <= a.max_face_only: continue
        if t0 < intro or t0 >= T - a.cta_last: print(f"  (face-only {d:.1f}s at {G.tc(t0)} is in the intro or the CTA: allowed)"); continue
        problems += 1
        print(f"FACE-ONLY {d:.1f}s at {G.tc(t0)}-{G.tc(G.ft(f1))}: nothing on screen but him for more than {a.max_face_only:g} s; add a graphic or a face break's card")
    # 3. face first
    ff = G.fr(a.face_first)
    if a.face_first > 0 and any(tl.cov[f] for f in range(min(ff, N))):
        problems += 1
        c0 = next(f for f in range(min(ff, N)) if tl.cov[f])
        print(f"FACE-FIRST a full-frame cover starts at {G.tc(G.ft(c0))}, inside the first {a.face_first:g} s: the hook should open on his face")
    # 1. recorded eyes-down runs
    gz, files = [], []
    for name in ("gaze_shots.json", "gaze_manual.json"):
        p = f"{W}/story/{name}"
        if not os.path.exists(p): continue
        d = json.load(open(p)); files.append(name)
        gz += d if isinstance(d, list) else d.get("runs", [])
    exempt = G.load_exempt(W)
    if not files:
        print("  eyes-down runs: story/gaze_shots.json and gaze_manual.json not found, skipped (use lookaway_check.py on the raw gaze rows)")
    else:
        bad, n = [], 0
        for g in gz:
            for (x, y), said in zip(g["runs"], g.get("said") or [""] * len(g["runs"])):
                n += 1
                if any(ex0 <= x and y <= ex1 for ex0, ex1 in exempt): continue
                fa, fb = G.fr(x), G.fr(y)
                for sh in tl.shots:
                    if sh["hold"] or sh["src1"] <= fa or sh["src0"] >= fb: continue
                    ea, eb = sh["e0"] + max(fa, sh["src0"]) - sh["src0"], sh["e0"] + min(fb, sh["src1"]) - sh["src0"]
                    open_ = [f for f in range(ea, eb) if not tl.cov[f]]
                    if len(open_) >= 2: bad.append((ea, eb, open_[0], g.get("shot"), said, len(open_)))
        print(f"  eyes-down runs ({', '.join(files)}): {n} checked, {len(bad)} not under a full-frame card")
        for ea, eb, f0, shot, said, k in sorted(bad):
            problems += 1
            print(f"EYES-DOWN {G.tc(G.ft(ea))}-{G.tc(G.ft(eb))} ({k} frames uncovered from {G.tc(G.ft(f0))}) shot {shot} '{said}'")
    print(f"coverage_check: {'FAIL' if problems else 'OK'}: {problems} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
