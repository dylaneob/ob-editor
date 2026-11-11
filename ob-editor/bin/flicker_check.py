#!/usr/bin/env python3
"""No-flicker check (OB on the C4367 v7 preview, 2026-10-20: "too many overlays like showing the clip and me talking just looked
glitchy"). Scans the painted timeline (the same painter as assemble.py, see gate_lib.py) and flags:

  cover   a full-frame cover shorter than ~1.5 s sitting between two shots of his face (face, cover, face);
  face    a face stretch shorter than ~1.5 s between two covers (cover, face, cover);
  same    a card, face, same card break (a face break inside one card) shorter than ~2 s;
  sliver  any run of one thing (an event or one A-roll shot) shorter than 9 frames, a flash at a cut (story/flash_check.py);
  hold    a clip-hold frame that is not under a cover (assemble.py would exit on it).
A cover is any event of assemble.py's COVER types or with "full": true; consecutive covers count as one cover stretch, and a pill,
plate or self-quote on his face is still his face. Exit 1 on any hit that is not allow-listed.

The "~" is real: OB's rule is about 1.5 s, not a hard line. cover and face fail under --min-cover / --min-face (1.3 s) and are listed as
"near" (not counted) from there up to --near (1.5 s); on C4367, which OB approved, the shortest are 1.37 s (face) and 1.40 s (cover), apart
from the one 0.70 s gag. same fails under --min-same (2.0 s; C4367's shortest face break is 2.11 s).

  python3 -I flicker_check.py WORK [--allow ID,ID ...] [--min-cover 1.3] [--min-face 1.3] [--near 1.5] [--min-same 2.0] [--min-frames 9] [--events FILE]

Allow-list (intentional gags, by event id): --allow, env OB_FLICKER_ALLOW (comma list), WORK/story/flicker_allow.json
({"allow": {"ID": "why"}} or {"allow": ["ID"]}), or "allow_flicker": true on the event. A hit is allowed when an event inside the cover
stretch (for face and same: the two covers around the face) is on the list. Allowed hits are printed and not counted.
How to fix a hit: when a look-down forces a short cover, run the cover over the whole line, or hold the card before it longer; drop a
cover that only interrupts his face. Exit codes: 0 clean, 1 hits, 2 missing input.
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gate_lib as G


def load_allow(work, cli, events):
    allow = {}
    for chunk in cli + [os.environ.get("OB_FLICKER_ALLOW", "")]:
        for i in chunk.split(","):
            if i.strip(): allow[i.strip()] = "command line"
    p = f"{work}/story/flicker_allow.json"
    if os.path.exists(p):
        d = json.load(open(p)).get("allow", {})
        for i in (d if isinstance(d, list) else d.keys()):
            allow[i] = d[i] if isinstance(d, dict) else "flicker_allow.json"
    for e in events:
        if e.get("allow_flicker"): allow[e["id"]] = "allow_flicker on the event"
    return allow


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("work")
    ap.add_argument("--allow", action="append", default=[])
    ap.add_argument("--min-cover", type=float, default=1.3); ap.add_argument("--min-face", type=float, default=1.3)
    ap.add_argument("--near", type=float, default=1.5); ap.add_argument("--min-same", type=float, default=2.0)
    ap.add_argument("--min-frames", type=int, default=9)
    ap.add_argument("--events", default=None)
    a = ap.parse_args(); W = a.work.rstrip("/")
    try:
        tl = G.Timeline(W, events=a.events)
    except (OSError, ValueError, KeyError) as e:
        print(f"flicker_check: cannot read inputs in {W}: {e}", file=sys.stderr); return 2
    allow = load_allow(W, a.allow, tl.events)
    runs = tl.runs(); dur = lambda f0, f1: (f1 - f0) / G.FPS
    hits, near = [], []

    def add(cat, f0, f1, detail, owners, soft=False):
        ok = [i for i in owners if i in allow]
        (near if soft else hits).append({"cat": cat, "f0": f0, "f1": f1, "dur": dur(f0, f1), "detail": detail, "owners": owners, "allowed": ok})

    for i, (kind, f0, f1) in enumerate(runs):
        if i == 0 or i == len(runs) - 1: continue            # nothing on one side: a cold open or the last card is not "between"
        p, n = runs[i - 1], runs[i + 1]
        d = dur(f0, f1)
        if kind == "C" and d < a.near:
            ow = tl.owners(f0, f1)
            add("cover", f0, f1, f"{d:.2f} s cover ({', '.join(ow)}) between two shots of his face", ow, soft=d >= a.min_cover)
        elif kind == "F":
            before, after = tl.own[p[2] - 1], tl.own[n[1]]
            same = before is not None and before is after
            lim = a.min_same if same else a.near
            if d < lim:
                ow = [before["id"]] + ([] if after is before else [after["id"]])
                add("same" if same else "face", f0, f1,
                    (f"{d:.2f} s face break inside card {before['id']}" if same else
                     f"{d:.2f} s of his face between covers {before['id']} and {after['id']}"), ow,
                    soft=(not same) and d >= a.min_face)
    # frame-level slivers (any owner), as story/flash_check.py
    st, N = 0, tl.N
    labs = [tl.label(f) for f in range(N)]
    for f in range(1, N + 1):
        if f == N or labs[f] != labs[st]:
            if f - st < a.min_frames and st > 0 and f < N: add("sliver", st, f, f"{f - st} frame(s) of {labs[st]}", [labs[st]])
            st = f
    for f0, f1 in tl.hold_gaps(): add("hold", f0, f1, "clip hold frames with no cover on top", [])

    bad = [h for h in hits if not h["allowed"]]; okh = [h for h in hits if h["allowed"]]
    cov = [dur(f0, f1) for k, f0, f1 in runs[1:-1] if k == "C"]; fac = [dur(f0, f1) for k, f0, f1 in runs[1:-1] if k == "F"]
    print(f"flicker check on {W}: runtime {G.tc(tl.T)}, {sum(1 for r in runs if r[0] == 'C')} cover stretches, {sum(1 for r in runs if r[0] == 'F')} face stretches; "
          f"shortest cover between faces {min(cov):.2f} s, shortest face between covers {min(fac):.2f} s" if cov and fac else f"flicker check on {W}: runtime {G.tc(tl.T)}")
    for h in sorted(hits, key=lambda h: h["f0"]):
        tag = f"allowed ({', '.join(h['allowed'])}: {allow[h['allowed'][0]]})" if h["allowed"] else "FLICKER"
        print(f"{tag} [{h['cat']}] {G.tc(G.ft(h['f0']))}-{G.tc(G.ft(h['f1']))} {h['detail']}")
    for h in sorted(near, key=lambda h: h["f0"]):
        print(f"near (not counted) [{h['cat']}] {G.tc(G.ft(h['f0']))}-{G.tc(G.ft(h['f1']))} {h['detail']}")
    print(f"flicker_check: {'FAIL' if bad else 'OK'}: {len(bad)} hit(s)" + (f", {len(okh)} allowed" if okh else "") + (f", {len(near)} near the limit" if near else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
