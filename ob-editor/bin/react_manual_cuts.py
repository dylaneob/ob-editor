#!/usr/bin/env python3
"""Apply WORK_DIR/manual_cuts.json (outtakes and OB's cut requests, raw camera times, each verified by ear) to
react_cutlist.json: OB shots lose the cut span; a shot cut in two keeps its framing on the left and flips it on the
right, so a jump cut inside a sentence reads as a camera change. Edit times are re-derived on the 30000/1001 frame grid.

  python3 -I react_manual_cuts.py WORK_DIR [--apply]   (keeps qc/react_cutlist_pre_manual.json)
"""
import json, os, shutil, sys
W = sys.argv[1]; FPS = 30000 / 1001; fr = lambda t: int(round(t * FPS)); ft = lambda f: f * 1001 / 30000
CL = json.load(open(f"{W}/react_cutlist.json")); cuts = json.load(open(f"{W}/manual_cuts.json"))["cuts"]; log = []
new = []
for s in CL["shots"]:
    pieces = [dict(s)]
    for c in cuts:
        nxt = []
        for p in pieces:
            if p["layout"] == "insert" or p["src_out"] <= c["src_in"] or p["src_in"] >= c["src_out"]: nxt.append(p); continue
            if p["layout"] == "split": log.append(f"!! cut {c['src_in']}-{c['src_out']} touches a clip play at {p['src_in']}: skipped there"); nxt.append(p); continue
            L = dict(p, src_out=c["src_in"]); R = dict(p, src_in=c["src_out"])
            keepL, keepR = L["src_out"] - L["src_in"] >= 0.2, R["src_out"] - R["src_in"] >= 0.2
            if keepL: nxt.append(L)
            if keepR:
                if keepL: R["framing"] = "punch" if p.get("framing") == "wide" else "wide"
                nxt.append(R)
            log.append(f"cut {c['src_in']:.2f}-{c['src_out']:.2f} from OB shot {p['src_in']:.2f}-{p['src_out']:.2f}: " + ("split, right side flips framing" if keepL and keepR else "trimmed" if keepL or keepR else "shot removed") + f"  ({c['why'][:50]})")
        pieces = nxt
    new += pieces
fe = 0
for s in new:
    n = fr(s["dur"]) if s["layout"] == "insert" else max(0, fr(s["src_out"]) - fr(s["src_in"]))
    s["edit_in"], s["edit_out"] = round(ft(fe), 4), round(ft(fe + n), 4); fe += n
print("\n".join(log)); print(f"{len(CL['shots'])} -> {len(new)} shots, {CL.get('total')} -> {ft(fe):.3f} s")
used = {c["src_in"] for c in cuts if any(c["src_in"] <= s["src_in"] < c["src_out"] or s["src_in"] < c["src_in"] < s["src_out"] for s in CL["shots"] if s["layout"] == "ob")}
for c in cuts:
    if c["src_in"] not in used: print(f"   (cut {c['src_in']:.2f}-{c['src_out']:.2f} touched no OB shot: already outside the edit)")
if "--apply" not in sys.argv: print("dry run"); sys.exit()
os.makedirs(f"{W}/qc", exist_ok=True); shutil.copy2(f"{W}/react_cutlist.json", f"{W}/qc/react_cutlist_pre_manual.json")
CL["shots"] = new; CL["total"] = round(ft(fe), 3); CL["manual_cuts"] = [c["why"][:80] for c in cuts]
json.dump(CL, open(f"{W}/react_cutlist.json", "w"), indent=1); print("applied")
