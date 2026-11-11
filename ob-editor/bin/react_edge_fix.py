#!/usr/bin/env python3
"""Apply WORK_DIR/edge_fixes.json to react_cutlist.json: the last step after react_zoomcuts.py (C4354 final audit,
2026-10-17: "make sure u dont cut me off, no repeats on showing reaction, no dead space").

Each fix names one shot by its layout and current src_in and either drops it or sets fields (src_in, src_out, offset,
ob_speech, framing). What they are for (measured in qc/edge_truth.log, qc/audit.json):
  * a play's clean audio ends on the clip's last whole word, not 0.2-0.3 s into the next one;
  * an OB shot starts ~0.16 s before his first sound and ends ~0.2 s after his last, so it holds no pause/play click,
    no room echo of the clip and no dead air;
  * an OB shot that is only the clip replaying through the speakers (a resumed play heard twice) is dropped;
  * a resumed play starts exactly where the clip's clean audio last stopped (physical offset kept, so its end
    is never lost).
Then: modified plays are written back to gate.json (render lookups), a jump cut between two long OB shots never keeps
the same framing (the far side flips, its zoom-cut chain re-alternates), source frames never repeat, and edit times are
re-derived on the 30000/1001 grid. Re-run after any upstream rebuild of the cut list.

  python3 -I react_edge_fix.py WORK_DIR [--apply]   (keeps qc/react_cutlist_pre_edgefix.json, qc/gate_pre_edgefix.json)
"""
import json, shutil, sys
W = sys.argv[1]; APPLY = "--apply" in sys.argv
FPS = 30000 / 1001; fr = lambda t: int(round(t * FPS)); ft = lambda f: f * 1001 / 30000
CL = json.load(open(f"{W}/react_cutlist.json")); shots = CL["shots"]
FX = json.load(open(f"{W}/edge_fixes.json"))["fixes"]; gate = json.load(open(f"{W}/gate.json")); log = []
for fx in FX:
    hit = [s for s in shots if s["layout"] == fx["layout"] and abs(s["src_in"] - fx["src_in"]) < 0.002]
    if len(hit) != 1: sys.exit(f"fix {fx}: {len(hit)} shots match")
    s = hit[0]
    if fx.get("drop"):
        shots.remove(s); log.append(f"drop {s['layout']} {s['src_in']:.3f}-{s['src_out']:.3f}  ({fx['why']})"); continue
    old = {k: s.get(k) for k in fx["set"]}
    if s["layout"] == "split":   # keep gate.json's play in step (the render looks plays up there)
        g = next(g for g in gate if g["clip"] == s["clip"] and g["rec_in"] - 0.6 <= s["src_in"] <= g["rec_out"])
        s.update(fx["set"]); g.update(rec_in=s["src_in"], rec_out=s["src_out"], offset=s["offset"],
                                   clip_in=round(s["src_in"] - s["offset"], 3), clip_out=round(s["src_out"] - s["offset"], 3))
        if "ob_speech" in fx["set"]: g["ob_speech"] = fx["set"]["ob_speech"]
    else: s.update(fx["set"])
    log.append(f"{s['layout']} {old} -> {fx['set']}  ({fx['why']})")
# source frames never repeat
for a, b in zip(sorted((s for s in shots if s["layout"] != "insert"), key=lambda s: s["src_in"]),
                sorted((s for s in shots if s["layout"] != "insert"), key=lambda s: s["src_in"])[1:]):
    if a["src_out"] > b["src_in"] + 0.001: sys.exit(f"source overlap: {a['src_in']}-{a['src_out']} and {b['src_in']}-{b['src_out']}")
    if b["src_out"] - b["src_in"] < 0.2: sys.exit(f"shot under 0.2 s at {b['src_in']}")
# a jump cut between two OB shots of 2.5 s or more never keeps the framing; the far side's zoom-cut chain re-alternates
for i in range(1, len(shots)):
    a, b = shots[i - 1], shots[i]
    if a["layout"] == b["layout"] == "ob" and abs(a["src_out"] - b["src_in"]) > 0.02 and a.get("framing") == b.get("framing") \
            and a["src_out"] - a["src_in"] >= 2.5 and b["src_out"] - b["src_in"] >= 2.5:
        f = "punch" if b["framing"] == "wide" else "wide"; j = i
        while True:
            shots[j]["framing"] = f; j += 1
            if j >= len(shots) or not shots[j].get("zoomcut") or shots[j]["layout"] != "ob": break
            f = "punch" if f == "wide" else "wide"
        log.append(f"framing: OB {b['src_in']:.2f} flips to {b['framing']} (same framing as the shot before across a jump cut); {j - i} shot(s)")
fe = 0
for s in shots:
    m = fr(s["dur"]) if s["layout"] == "insert" else max(0, fr(s["src_out"]) - fr(s["src_in"]))
    s["edit_in"], s["edit_out"] = round(ft(fe), 4), round(ft(fe + m), 4); fe += m
print("\n".join(log)); print(f"{len(shots)} shots; length {ft(fe):.3f} s (was {CL['total']:.3f})")
if not APPLY: print("dry run"); sys.exit()
shutil.copy2(f"{W}/react_cutlist.json", f"{W}/qc/react_cutlist_pre_edgefix.json"); shutil.copy2(f"{W}/gate.json", f"{W}/qc/gate_pre_edgefix.json")
CL["shots"] = shots; CL["total"] = round(ft(fe), 3)
json.dump(CL, open(f"{W}/react_cutlist.json", "w"), indent=1); json.dump(gate, open(f"{W}/gate.json", "w"), indent=1); print("applied")
