#!/usr/bin/env python3
"""Final audit of a reaction cut list (C4354, OB 10-17: "make sure u dont cut me off, no repeats on showing reaction, no dead
space and make sure it flows well between reactions").

Audio is judged as it will play: OB shots on his synced mic, clip plays on the clip's own file.
  * cut-offs: at every real cut (not a zoom cut, where the source runs on), speech energy inside the first/last 30 ms of an
    OB shot = a word cut into. Speech = 10 ms RMS above max(-45 dBFS, noise floor + 14 dB).
  * joins: the pause a viewer hears at every real cut = tail of the shot before + lead of the shot after (clip audio for a
    play). Under 120 ms feels rushed; over 700 ms is dead air.
  * dead air inside OB shots: any silence over 900 ms (the cut list trims >= 0.8 s pauses to 0.4 s; zoom cuts keep audio).
  * repeats: per clip, the clip-time ranges the panel shows must not overlap (> 0.05 s) and must not skip (> 0.3 s).
  * bleed: no OB shot may overlap a play's exact edges (matches_mic.json): a clip sounding through his speakers.
  * framing: a jump cut between two long OB shots changes framing.

  python3 -I react_audit.py WORK_DIR   -> qc/audit.json + printed flags
"""
import json, sys
import numpy as np
from scipy.io import wavfile
W = sys.argv[1]
shots = json.load(open(f"{W}/react_cutlist.json"))["shots"]
idx = {l.split("\t")[1]: int(l.split("\t")[0][1:]) for l in open(f"{W}/clips_index.txt")}
sr, mic = wavfile.read(f"{W}/mic16.wav"); mic = mic.astype(np.float64) / 32768
H = sr // 100
def lvl(x):
    n = len(x) // H; return 20 * np.log10(np.sqrt((x[:n * H].reshape(n, H) ** 2).mean(1)) + 1e-9) if n else np.array([-120.0])
mdb = lvl(mic); thr = max(-45.0, float(np.percentile(mdb, 10)) + 14.0)
clips = {}
def clip_db(k):
    if k not in clips:
        s2, c = wavfile.read(f"{W}/cliptx/c{k:02d}.wav"); c = c.astype(np.float64) / 32768; n = len(c) // (s2 // 100)
        cd = 20 * np.log10(np.sqrt((c[:n * (s2 // 100)].reshape(n, s2 // 100) ** 2).mean(1)) + 1e-9)
        clips[k] = (cd, max(-45.0, float(np.percentile(cd, 10)) + 14.0))
    return clips[k]
gate = {round(g["rec_in"], 3): g for g in json.load(open(f"{W}/gate.json"))}
def audio(s):   # (10 ms levels as played, speech threshold)
    if s["layout"] == "split":
        cd, ct = clip_db(s["k"]); c0 = int(round((s["src_in"] - s["offset"]) * 100)); c1 = int(round((s["src_out"] - s["offset"]) * 100))
        seg = cd[max(0, c0):max(0, c1)].copy()
        g = next((g for g in gate.values() if g["clip"] == s["clip"] and g["rec_in"] - 0.5 <= s["src_in"] and s["src_out"] <= g["rec_out"] + 0.5), None)
        for m0, m1 in (g or {}).get("mute_clip", []):   # muted clip sound: his mic plays there instead
            a, b = int((m0 - (s["src_in"] - s["offset"])) * 100), int((m1 - (s["src_in"] - s["offset"])) * 100)
            seg[max(0, a):max(0, b)] = mdb[int(s["src_in"] * 100) + max(0, a): int(s["src_in"] * 100) + max(0, b)][:len(seg[max(0, a):max(0, b)])]
        return seg, ct
    return mdb[int(round(s["src_in"] * 100)):int(round(s["src_out"] * 100))], thr
rows, flags = [], []
tc = lambda t: f"{int(t // 60)}:{t % 60:04.1f}"
for i, s in enumerate(shots):
    seg, th = audio(s); sp = np.flatnonzero(seg > th)
    lead = int(sp[0] * 10) if len(sp) else None; tail = int((len(seg) - 1 - sp[-1]) * 10) if len(sp) else None
    rows.append(dict(i=i, layout=s["layout"], edit_in=s["edit_in"], src_in=s["src_in"], src_out=s["src_out"], lead_ms=lead, tail_ms=tail,
                     edge_in=round(float(seg[:3].max()), 1) if len(seg) else None, edge_out=round(float(seg[-3:].max()), 1) if len(seg) else None, thr=round(th, 1)))
for i, r in enumerate(rows):
    prev = rows[i - 1] if i else None; nxt = rows[i + 1] if i + 1 < len(rows) else None
    cut_in = prev is None or abs(prev["src_out"] - r["src_in"]) > 0.02 or prev["layout"] != r["layout"]
    cut_out = nxt is None or abs(nxt["src_in"] - r["src_out"]) > 0.02 or nxt["layout"] != r["layout"]
    r["cut_in"], r["cut_out"] = cut_in, cut_out
    if r["layout"] == "ob" and cut_in and prev is not None and r["edge_in"] is not None and r["edge_in"] > r["thr"]:
        flags.append(dict(kind="cut_off_start", shot=i, at=tc(r["edit_in"]), src=r["src_in"], db=r["edge_in"]))
    if r["layout"] == "ob" and cut_out and nxt is not None and r["edge_out"] is not None and r["edge_out"] > r["thr"]:
        flags.append(dict(kind="cut_off_end", shot=i, at=tc(shots[i]["edit_out"]), src=r["src_out"], db=r["edge_out"]))
    if cut_out and nxt is not None and r["tail_ms"] is not None and rows[i + 1]["lead_ms"] is not None:
        pause = r["tail_ms"] + rows[i + 1]["lead_ms"]; r["join_ms"] = pause
        if pause > 700: flags.append(dict(kind="dead_air_join", shot=i, at=tc(shots[i]["edit_out"]), ms=pause, sides=f"{r['layout']}->{rows[i + 1]['layout']}", tail=r["tail_ms"], lead=rows[i + 1]["lead_ms"]))
        if pause < 120 and r["layout"] == "ob" and rows[i + 1]["layout"] == "ob": flags.append(dict(kind="rushed_join", shot=i, at=tc(shots[i]["edit_out"]), ms=pause))
    if r["layout"] == "ob":   # silences inside the shot
        seg, th = audio(shots[i]); quiet = seg <= th; run = 0
        for j, q in enumerate(quiet):
            run = run + 1 if q else 0
            if run == 91: flags.append(dict(kind="dead_air_inside", shot=i, at=tc(shots[i]["edit_in"] + (j - 90) / 100), src=round(shots[i]["src_in"] + (j - 90) / 100, 2)))
# repeats / skips in what each clip panel shows
seen = {}
for i, s in enumerate(shots):
    if s["layout"] != "split": continue
    c0, c1 = s["src_in"] - s["offset"], s["src_out"] - s["offset"]
    for a, b, j in seen.get(s["clip"], []):
        ov = min(b, c1) - max(a, c0)
        if ov > 0.05: flags.append(dict(kind="clip_repeat", shot=i, at=tc(s["edit_in"]), clip=idx[s["clip"]], overlap_s=round(ov, 2), with_shot=j))
    if seen.get(s["clip"]):
        last = max(b for a, b, j in seen[s["clip"]])
        if c0 - last > 0.3: flags.append(dict(kind="clip_skip", shot=i, at=tc(s["edit_in"]), clip=idx[s["clip"]], skipped_s=round(c0 - last, 2)))
    seen.setdefault(s["clip"], []).append((c0, c1, i))
# bleed: OB shots over a play's exact edges (matches_mic.json from react_edges.py; the raw clipmatch chunks run 1-2 s wide)
for m in json.load(open(f"{W}/matches_mic.json")):
    for p in m["segments"]:
        for i, s in enumerate(shots):
            if s["layout"] == "ob":
                ov = min(p["rec_out"], s["src_out"]) - max(p["rec_in"], s["src_in"])
                if ov > 0.1: flags.append(dict(kind="clip_bleed_in_ob_shot", shot=i, at=tc(s["edit_in"]), clip=idx[m["clip"]], overlap_s=round(ov, 2), src=[s["src_in"], s["src_out"]]))
# framing: a jump cut between two OB shots of 2.5 s or more keeps the same framing (the head jumps in place)
for i in range(1, len(shots)):
    a, b = shots[i - 1], shots[i]
    if a["layout"] == b["layout"] == "ob" and abs(a["src_out"] - b["src_in"]) > 0.02 and a.get("framing") == b.get("framing") \
            and a["src_out"] - a["src_in"] >= 2.5 and b["src_out"] - b["src_in"] >= 2.5:
        flags.append(dict(kind="same_framing_jump", shot=i, at=tc(b["edit_in"]), framing=b.get("framing")))
json.dump(dict(rows=rows, flags=flags), open(f"{W}/qc/audit.json", "w"), indent=1)
kinds = {}
for f in flags: kinds[f["kind"]] = kinds.get(f["kind"], 0) + 1
print(f"{len(shots)} shots, speech threshold {thr:.1f} dB | flags: {kinds or 'none'}")
for f in flags: print("  ", json.dumps(f))
