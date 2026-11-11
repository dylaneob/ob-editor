#!/usr/bin/env python3
"""Look-away check (OB's rule, 2026-10-19: "if i look away cut it"). General version of C4367's tools/pupilscan.py.

Scans the raw gaze rows of the whole take and lists every run of 2+ samples where his eyes are down AND his face is visible on the
final timeline, i.e. not under a full-frame graphic (a side card, pill, plate or face-and-text overlay does not hide his face).
Exit 1 if any run is found.

  python3 -I lookaway_check.py WORK [--th 0.45] [--shut 0.13] [--bad 0.60] [--min 2] [--clear 0.05] [--yaw -0.5] [--strict]
                               [--gaze PATH:OFFSET_SECONDS ...] [--exempt FILE] [--events FILE] [--show-filtered] [--quiet] [--json OUT]

A gaze row is [frame, t, pitch, yaw, pupil_y, pupil_x, open]. One sample = one scanned frame (every 5th, 0.167 s).
  down     : pupil_y >= --th (0.45; on the lens he sits about 0.30-0.36), or eyes open < --shut (0.13), or no face found
  unknown  : open > --bad (0.60): a failed eye contour, not a wide eye. Unknown is never down and it ends a run.
  --yaw    : also count yaw below this as down (the pickups, where he reads a prompt off to the side; C4368 used -0.5). Off by default.
A visible run of --min (2) neighbouring down samples is a hit, with two exceptions that the C4367 strip review showed are not
look-aways (each was confirmed on eye strips; --strict counts them anyway, --show-filtered lists them):
  blink      exactly 2 samples and one of them shut: a long blink (eyes shut, so pupil_y is meaningless). 3+ samples is 0.5 s of
             eyes closed or down and always counts.
  borderline every sample is pupils-low but none reaches --th + --clear (0.50): his lens line drifting up to 0.45-0.48 with the eyes
             wide open in that shot, not a glance.
Inputs (all inside WORK, read only): cutlist.json, events_resolved.json, gaze/raw.json (combined-source frames) and, for every
extra source in cutlist["sources"], <name>/gaze_raw.json (frames local to that file; its start frame is added, C4367: c4368 at
83115 = 2773.2705 s). --gaze adds a file by hand. story/gaze_exempt.json {"spans": [[a, b, note]]} (source seconds) lists runs
already eye-checked as expression, not reading; they are skipped and counted.
A run that sits wholly under covers is fine and only counted. Fix a hit by covering the line (an insert or a clip over the
look-down, or hold the card before it longer) or by cutting it, then rerun. Exit codes: 0 clean, 1 runs found, 2 missing input.
Cut-backs (OB 2026-10-29, C4395 v4 at 30:27: "is it me talking or is it an outtake, looks odd"): inside a card's "face" windows
(reel_cards, where the footage stops and he is back on screen) one sample is enough: no face, or his head pitched down >= --bow
(0.5). The runs above missed that one: his face was under the cap brim and the landmarks still put his pupils on the lens line.
Fix a BOWED hit by moving the window off it (footage over the bow), then rerun.
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gate_lib as G


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("work")
    ap.add_argument("--th", type=float, default=0.45); ap.add_argument("--shut", type=float, default=0.13)
    ap.add_argument("--bad", type=float, default=0.60); ap.add_argument("--min", type=int, default=2)
    ap.add_argument("--clear", type=float, default=0.05); ap.add_argument("--yaw", type=float, default=None)
    ap.add_argument("--bow", type=float, default=0.5, help="cut-backs: head pitch at or over this is bowed (one sample counts)")
    ap.add_argument("--strict", action="store_true", help="count blinks and borderline runs too (the literal rule)")
    ap.add_argument("--gaze", action="append", default=[], metavar="PATH:OFFSET_S")
    ap.add_argument("--exempt", default=None); ap.add_argument("--events", default=None)
    ap.add_argument("--show-filtered", action="store_true"); ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--json", default=None, metavar="OUT.json", help="also write the runs (with source frames) to this file")
    a = ap.parse_args(); W = a.work.rstrip("/")
    try:
        tl = G.Timeline(W, events=a.events)
        extra = []
        for g in a.gaze:
            p, _, off = g.rpartition(":")
            extra.append((p, float(off)))
        rows, files = G.load_gaze(W, tl.cut, extra)
    except (OSError, ValueError, KeyError) as e:
        print(f"lookaway_check: cannot read inputs in {W}: {e}", file=sys.stderr); return 2
    if not rows:
        print(f"lookaway_check: no gaze rows found (expected {W}/gaze/raw.json from bin/gaze_raw.py)", file=sys.stderr); return 2
    exempt = G.load_exempt(W, a.exempt)
    frames = [r[0] for r in rows]; byf = {r[0]: r for r in rows}
    diffs = sorted(frames[i + 1] - frames[i] for i in range(min(len(frames) - 1, 2000)))
    step = diffs[len(diffs) // 2] if diffs else 5       # frames between samples (5 on every scan so far)
    mapped = tl.src_to_edit(frames)
    n_holds = sum(1 for s in tl.shots if s["hold"])
    if not a.quiet:
        print(f"look-away check on {W}: {len(rows)} gaze rows from {len(files)} file(s), {len(tl.shots) - n_holds} A-roll shots "
              f"({n_holds} clip holds), runtime {G.tc(tl.T)}")
        print(f"  down = pupil_y >= {a.th} or open < {a.shut} or no face{'' if a.yaw is None else f' or yaw < {a.yaw}'}; "
              f"open > {a.bad} = unknown; run = {a.min}+ neighbouring samples; step {step} frames")
    by_shot = {}
    for k, sf, ef in mapped: by_shot.setdefault(k, []).append((sf, ef))
    n_raw = n_cov = n_exempt = n_unknown = 0
    counted, filtered = [], []
    for k in sorted(by_shot):
        sh = tl.shots[k]
        st = [(sf, ef, G.gaze_state(byf[sf], a.th, a.shut, a.bad, a.yaw)) for sf, ef in by_shot[k]]
        n_unknown += sum(1 for x in st if x[2] == G.UNKNOWN)
        raw, cur = [], []
        for x in st:
            if x[2] in G.DOWN_KINDS and (not cur or x[0] - cur[-1][0] <= step * 1.6): cur.append(x)
            else:
                if len(cur) >= a.min: raw.append(cur)
                cur = [x] if x[2] in G.DOWN_KINDS else []
        if len(cur) >= a.min: raw.append(cur)
        for run in raw:
            n_raw += 1
            s0, s1 = run[0][0] / G.FPS - 1 / 12, run[-1][0] / G.FPS + 1 / 12
            if any(x - 0.1 <= s0 and s1 <= y + 0.1 for x, y in exempt): n_exempt += 1; continue
            vis, sub = [], []
            for x in run:                       # a sample counts only where his face shows
                if not tl.cov[x[1]]: sub.append(x)
                else:
                    if len(sub) >= a.min: vis.append(sub)
                    sub = []
            if len(sub) >= a.min: vis.append(sub)
            if not vis: n_cov += 1; continue
            for sub in vis:
                kinds = [x[2] for x in sub]
                pys = [byf[x[0]][4] for x in sub]
                why = None
                if not a.strict:
                    if len(sub) == 2 and G.SHUT in kinds and G.NOFACE not in kinds: why = "blink"
                    elif all(kd == G.LOW for kd in kinds) and all(p is not None and p >= a.th for p in pys) and max(pys) < a.th + a.clear - 1e-9:
                        why = "borderline"
                sf0, sf1 = sub[0][0], sub[-1][0]
                rec = {"edit": (G.ft(sub[0][1]), G.ft(sub[-1][1] + step)), "shot": sh["i"], "src": (sf0 / G.FPS, sf1 / G.FPS),
                       "src_frames": (sf0, sf1), "n": len(sub), "kinds": kinds, "why": why,
                       "where": "START" if sf0 - sh["src0"] < 6 else ("END" if sh["src1"] - sf1 <= 6 else "MID"),
                       "on": tl.owners(sub[0][1], sub[-1][1] + 1),
                       "py": [round(p, 2) if p is not None else None for p in pys],
                       "open": [round(byf[x[0]][6], 2) if byf[x[0]][6] is not None else None for x in sub]}
                (filtered if why else counted).append(rec)
    counted.sort(key=lambda h: h["edit"][0]); filtered.sort(key=lambda h: h["edit"][0])
    nb = sum(1 for h in filtered if h["why"] == "blink"); nd = len(filtered) - nb

    # cut-backs: every sample inside a "face" window must show his face, head up (see the docstring)
    evs = json.load(open(a.events or f"{W}/events_resolved.json"))["events"]
    wins = [(e["id"], e["edit_in"], e["edit_in"] + x, e["edit_in"] + y) for e in evs for x, y in (e.get("face") or [])]
    bowed, cur = [], None
    for k, sf, ef in sorted(mapped, key=lambda m: m[2]):
        t = G.ft(ef); r = byf[sf]
        hit = next((w for w in wins if w[2] <= t < w[3]), None) if not tl.cov[ef] else None
        if hit and (r[2] is None or r[2] >= a.bow):
            why = "no face" if r[2] is None else f"pitch {r[2]:.2f}"
            if cur and cur["id"] == hit[0] and t - cur["t1"] <= 1.6 * step / G.FPS: cur["t1"] = t; cur["why"].append(why)
            else: cur = {"id": hit[0], "in": hit[1], "t0": t, "t1": t, "why": [why]}; bowed.append(cur)
    if not a.quiet:
        print(f"  {n_raw} eyes-down runs of {a.min}+ samples on A-roll shots: {n_cov} wholly under full-frame graphics, {n_exempt} exempt "
              f"(eye-checked), {len(counted) + len(filtered)} visible, of which {nb} blinks and {nd} borderline are not counted; "
              f"{n_unknown} unknown samples (failed contours) ignored")

    def line(tag, h):
        return (f"{tag} edit {G.tc(h['edit'][0])}-{G.tc(h['edit'][1])} shot {h['shot']:<4} src {h['src'][0]:8.2f}-{h['src'][1] + 0.17:8.2f} "
                f"{h['where']:5s} {h['n']} samples {'/'.join(h['kinds'])} py {h['py']} open {h['open']} on screen: {', '.join(h['on']) or 'face only'}")
    for h in counted: print(line("LOOK-AWAY", h))
    if a.show_filtered:
        for h in filtered: print(line(f"skipped ({h['why']})", h))
    for b in bowed:
        print(f"BOWED edit {G.tc(b['t0'])}-{G.tc(b['t1'] + step / G.FPS)} {b['id']} +{b['t0'] - b['in']:.2f}-{b['t1'] - b['in'] + step / G.FPS:.2f} s "
              f"in a cut-back: {', '.join(b['why'])}")
    if a.json:
        json.dump({"work": W, "counted": counted, "filtered": filtered, "covered_runs": n_cov, "exempt_runs": n_exempt,
                   "bowed": bowed}, open(a.json, "w"), indent=1)
    bad = counted or bowed
    print(f"lookaway_check: {'FAIL' if bad else 'OK'}: {len(counted)} visible eyes-down run(s), {len(bowed)} bowed cut-back(s) "
          f"in {len(wins)} face windows")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
