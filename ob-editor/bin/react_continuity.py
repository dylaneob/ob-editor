#!/usr/bin/env python3
"""No clip repeats (OB 2026-10-16, a HARD rule for reactions): every resumed play of a clip continues exactly where that
clip last stopped. Run on gate.json after react_edges.py + react_gate.py, before react_cutlist.py (C4354, 2026-10-17).

- Overlap (he resumed a little earlier than he stopped): the resumed play starts later, at the old stop point; the
  replayed seconds drop out (OB never talks over clips in C4354; any ob_speech inside them is reported, never dropped).
- Small gap (he resumed up to 1.5 s later than he stopped): the clip panel shows the clip from the old stop point instead
  (offset += gap), so nothing is skipped; the play keeps its recording frames, his mic is muted in plays anyway.
- Bigger gap: he skipped ahead on purpose; left alone and reported.

  python3 -I react_continuity.py WORK_DIR [--apply]   (keeps gate_pre_continuity.json)
"""
import json, os, shutil, sys
W = sys.argv[1]; APPLY = "--apply" in sys.argv
G = json.load(open(f"{W}/gate.json")); log = []; drop = set()
by = {}
for i, g in enumerate(sorted(range(len(G)), key=lambda i: G[i]["rec_in"])): by.setdefault(G[g]["clip"], []).append(g)
for clip, ix in by.items():
    seen = None
    for i in ix:
        g = G[i]
        if seen is None: seen = g["clip_out"]; continue
        if g["clip_in"] < seen - 0.04:
            d = round(seen - g["clip_in"], 3)
            talk = [sp for sp in g.get("ob_speech", []) if sp[0] < g["rec_in"] + d]
            if g["clip_out"] - seen < 0.5:
                drop.add(i); log.append(f"#{g['k']} play at {g['rec_in']:.2f}: clip {g['clip_in']:.2f}-{g['clip_out']:.2f} all shown before -> dropped" + (f"  !! OB talks in it {talk}" if talk else ""))
                continue
            g["rec_in"] = round(g["rec_in"] + d, 3); g["clip_in"] = round(seen, 3)
            log.append(f"#{g['k']} play resumed {d:.2f}s early -> starts at rec {g['rec_in']:.2f} (clip {seen:.2f})" + (f"  !! OB talks in the cut part {talk}" if talk else ""))
        elif g["clip_in"] > seen + 0.04:
            gap = round(g["clip_in"] - seen, 3)
            if gap <= 1.5:
                g["offset"] = round(g["offset"] + gap, 4); g["clip_in"] = round(seen, 3); g["clip_out"] = round(g["clip_out"] - gap, 3)
                log.append(f"#{g['k']} play resumed {gap:.2f}s late -> panel shows clip {seen:.2f}-{g['clip_out']:.2f} (offset {g['offset']:.3f})")
            else:
                log.append(f"#{g['k']} play skips clip {seen:.2f}-{g['clip_in']:.2f} ({gap:.1f}s): left as filmed")
        g["continuity"] = log[-1] if log else ""
        seen = max(seen, g["clip_out"])
print("\n".join(log) or "no repeats or gaps")
if not APPLY: print("dry run"); sys.exit()
if not os.path.exists(f"{W}/gate_pre_continuity.json"): shutil.copy2(f"{W}/gate.json", f"{W}/gate_pre_continuity.json")
json.dump([g for i, g in enumerate(G) if i not in drop], open(f"{W}/gate.json", "w"), indent=1); print("applied")
